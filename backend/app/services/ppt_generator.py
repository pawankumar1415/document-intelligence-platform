from __future__ import annotations

import re

from pptx import Presentation
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

from backend.app.models.schemas import GeneratePptxRequest, GenerateResult, GeneratedSlide
from backend.app.services.branding import (
    LOGO_PATH,
    PPT_TEMPLATE_PATH,
    PPT_RED,
    PPT_DARK_GREY,
    PPT_MID_GREY,
    PPT_WHITE,
    PPT_ACCENT_DARK,
    PPT_BODY_TEXT,
    FONT_FAMILY,
    add_ppt_accent_bar,
    add_ppt_slide_number,
    logo_exists,
    ppt_template_exists,
)
from backend.app.services.file_utils import build_output_path
from backend.app.services.llm_provider import generate_json_object
from backend.app.services.text_utils import build_section_candidates


# ── Prompt templates ───────────────────────────────────────────────────────

PPT_SYSTEM_PROMPT = """\
You are a management consultant preparing a board-ready executive presentation.

Rules:
- Slide titles MUST be punchy and under 8 words. Use title case.
- Bullets MUST be concise (max 16 words), actionable, and grounded in source data.
- Use varied slide types to create visual rhythm: section dividers, key metrics, two-column comparisons, and a closing slide.
- If quantitative data exists in the source, surface it in a metrics slide.
- Ground every claim in the provided source material. Write "To be confirmed" for missing data — never invent facts.
- Return ONLY valid JSON. No markdown, no commentary.
"""

PPT_USER_PROMPT_TEMPLATE = """\
Return ONLY JSON matching this schema:
{{
  "slides": [
    {{
      "title": "string",
      "bullets": ["string"],
      "slide_type": "content|section_divider|metrics|two_column|closing",
      "left_column": ["string"],
      "right_column": ["string"]
    }}
  ]
}}

Generate slides for a {max_slides}-slide deck in this order:
1. slide_type "section_divider" — title: "Executive Overview" (no bullets)
2. slide_type "content" — Executive Summary with 4-5 key bullets
3. slide_type "content" — Scope and Approach with 4-5 bullets
4. slide_type "metrics" — Key Numbers / Metrics (3-4 bullets showing key data points in format "Value — Description")
5. slide_type "two_column" — Strengths vs Risks or Current vs Future (left_column and right_column, 3-4 items each)
6. slide_type "content" — Deliverables with 4-5 bullets
7. slide_type "section_divider" — title: "Timeline & Next Steps" (no bullets)
8. slide_type "content" — Implementation Timeline with 3-5 bullets
9. slide_type "closing" — Next Steps with 3-4 action items as bullets

Deck title: {deck_title}
Subtitle: {subtitle}

Source:
{context_blob}
"""


class PptGenerator:
    def generate(self, request: GeneratePptxRequest, retrieval_context: list[str] | None = None) -> GenerateResult:
        slides = self._build_slides(request, retrieval_context=retrieval_context or [])
        output_path = build_output_path("deck", "pptx")
        self._write_presentation(output_path=str(output_path), request=request, slides=slides)
        artifact_name = output_path.name

        summary = f"PPT draft generated for {request.deck_title}"
        return GenerateResult(
            artifact_type="pptx",
            file_path=str(output_path),
            artifact_name=artifact_name,
            download_url=f"/api/v1/artifacts/{artifact_name}",
            summary=summary,
            slides=slides,
        )

    # ── Slide building ─────────────────────────────────────────────────────

    def _build_slides(self, request: GeneratePptxRequest, retrieval_context: list[str]) -> list[GeneratedSlide]:
        llm_slides = self._build_slides_from_llm(request, retrieval_context)
        if llm_slides:
            return self._truncate_slides(llm_slides, request.max_content_slides)

        # Fallback: keyword-heuristic path
        candidates = build_section_candidates(request.source_document)

        content_slides = [
            GeneratedSlide(
                title="Executive Overview",
                bullets=[],
                slide_type="section_divider",
            ),
            GeneratedSlide(
                title="Executive Summary",
                bullets=self._prepare_bullets(candidates["Project Overview"][:4]),
                slide_type="content",
            ),
            GeneratedSlide(
                title="Scope and Approach",
                bullets=self._prepare_bullets(candidates["Scope"][:4]),
                slide_type="content",
            ),
            GeneratedSlide(
                title="Key Deliverables",
                bullets=self._prepare_bullets(candidates["Deliverables"][:4]),
                slide_type="content",
            ),
            GeneratedSlide(
                title="Current State vs Future State",
                bullets=[],
                slide_type="two_column",
                left_column=self._prepare_bullets(candidates["Risks"][:3]) or ["To be confirmed"],
                right_column=self._prepare_bullets(candidates["Deliverables"][:3]) or ["To be confirmed"],
            ),
            GeneratedSlide(
                title="Timeline & Next Steps",
                bullets=[],
                slide_type="section_divider",
            ),
            GeneratedSlide(
                title="Implementation Timeline",
                bullets=self._prepare_bullets(
                    (candidates["Timeline"] + candidates["Risks"])[:5]
                ),
                slide_type="content",
            ),
            GeneratedSlide(
                title="Next Steps",
                bullets=[
                    "Confirm project scope and stakeholder alignment",
                    "Finalise resource plan and delivery timeline",
                    "Schedule kickoff workshop",
                    "Begin discovery phase",
                ],
                slide_type="closing",
            ),
        ]

        # Add extra content slides from source sections if space allows
        if request.max_content_slides > len(content_slides):
            for section in request.source_document.sections:
                if len(content_slides) >= request.max_content_slides:
                    break
                heading = self._clean_slide_title(section.heading or "Additional Detail")
                lines = [line.strip() for line in section.body.splitlines() if line.strip()]
                bullets = self._prepare_bullets(lines[:5])
                if not bullets:
                    continue
                content_slides.append(GeneratedSlide(title=heading, bullets=bullets, slide_type="content"))

        # Smart truncation: always keep closing slide and section dividers
        return self._truncate_slides(content_slides, request.max_content_slides)

    def _build_slides_from_llm(
        self,
        request: GeneratePptxRequest,
        retrieval_context: list[str],
    ) -> list[GeneratedSlide] | None:
        context_blob = self._build_context_blob(request.source_document.text, retrieval_context)
        user_prompt = PPT_USER_PROMPT_TEMPLATE.format(
            max_slides=request.max_content_slides,
            deck_title=request.deck_title,
            subtitle=request.subtitle or "",
            context_blob=context_blob,
        )

        try:
            payload = generate_json_object(
                provider=request.llm_provider,
                model=request.llm_model,
                system_prompt=PPT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
            )
            slides_payload = payload.get("slides", [])
            slides: list[GeneratedSlide] = []
            for item in slides_payload:
                title = str(item.get("title", "")).strip()
                if not title:
                    continue
                bullets = self._prepare_bullets([str(b).strip() for b in item.get("bullets", []) if str(b).strip()])
                slide_type = str(item.get("slide_type", "content")).strip()
                if slide_type not in ("content", "section_divider", "metrics", "two_column", "closing"):
                    slide_type = "content"
                left_col = self._prepare_bullets(
                    [str(b).strip() for b in item.get("left_column", []) if str(b).strip()]
                )
                right_col = self._prepare_bullets(
                    [str(b).strip() for b in item.get("right_column", []) if str(b).strip()]
                )
                slides.append(
                    GeneratedSlide(
                        title=self._clean_slide_title(title),
                        bullets=bullets[:5],
                        slide_type=slide_type,
                        left_column=left_col,
                        right_column=right_col,
                    )
                )
            return slides or None
        except Exception:
            return None

    # ── Presentation writing ───────────────────────────────────────────────

    def _write_presentation(self, *, output_path: str, request: GeneratePptxRequest, slides: list[GeneratedSlide]) -> None:
        presentation = Presentation(str(PPT_TEMPLATE_PATH)) if ppt_template_exists() else Presentation()
        self._clear_existing_slides(presentation)
        blank_layout = self._resolve_blank_layout(presentation)

        # ── Title slide ────────────────────────────────────────────────────
        title_slide = presentation.slides.add_slide(blank_layout)
        self._write_title_slide(
            slide=title_slide,
            prs=presentation,
            title_text=request.deck_title,
            subtitle_text=request.subtitle or request.source_document.title,
        )

        # ── Content slides ─────────────────────────────────────────────────
        for slide_data in slides:
            new_slide = presentation.slides.add_slide(blank_layout)
            slide_type = slide_data.slide_type

            if slide_type == "section_divider":
                self._write_section_divider(new_slide, presentation, slide_data)
            elif slide_type == "metrics":
                self._write_metrics_slide(new_slide, presentation, slide_data)
            elif slide_type == "two_column":
                self._write_two_column_slide(new_slide, presentation, slide_data)
            elif slide_type == "closing":
                self._write_closing_slide(new_slide, presentation, slide_data)
            else:
                self._write_content_slide(new_slide, presentation, slide_data)

        presentation.save(output_path)

    # ── Slide writers ──────────────────────────────────────────────────────

    def _write_title_slide(self, *, slide, prs, title_text: str, subtitle_text: str) -> None:
        """Title slide with dark gradient band, logo, title, subtitle, and date."""
        slide_width = prs.slide_width or Emu(12192000)
        # Dark gradient band behind title area
        band = slide.shapes.add_shape(1, Emu(0), Inches(0.4), slide_width, Inches(2.6))
        band.fill.solid()
        band.fill.fore_color.rgb = PPT_ACCENT_DARK
        band.line.fill.background()

        # Title
        tb = slide.shapes.add_textbox(Inches(0.9), Inches(0.65), Inches(10.5), Inches(1.2))
        tf = tb.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.name = FONT_FAMILY
        p.font.bold = True
        p.font.size = Pt(40)
        p.font.color.rgb = PPT_WHITE

        # Subtitle
        tb2 = slide.shapes.add_textbox(Inches(0.95), Inches(2.0), Inches(10.0), Inches(0.8))
        tf2 = tb2.text_frame
        tf2.clear()
        p2 = tf2.paragraphs[0]
        p2.text = subtitle_text
        p2.font.name = FONT_FAMILY
        p2.font.size = Pt(20)
        p2.font.color.rgb = PPT_MID_GREY

        # Date line below band
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%d %B %Y")
        tb3 = slide.shapes.add_textbox(Inches(0.95), Inches(3.3), Inches(5.0), Inches(0.4))
        tf3 = tb3.text_frame
        tf3.clear()
        p3 = tf3.paragraphs[0]
        p3.text = f"BSBI Consulting  |  {today}"
        p3.font.name = FONT_FAMILY
        p3.font.size = Pt(12)
        p3.font.color.rgb = PPT_MID_GREY

        # Confidential tag
        tb4 = slide.shapes.add_textbox(Inches(0.95), Inches(6.6), Inches(5.0), Inches(0.3))
        tf4 = tb4.text_frame
        tf4.clear()
        p4 = tf4.paragraphs[0]
        p4.text = "CONFIDENTIAL"
        p4.font.name = FONT_FAMILY
        p4.font.size = Pt(9)
        p4.font.color.rgb = PPT_MID_GREY

        self._add_logo(slide)
        add_ppt_accent_bar(slide, prs)

    def _write_content_slide(self, slide, prs, slide_data: GeneratedSlide) -> None:
        """Standard content slide: red title, bullet body, accent bar, logo."""
        # Title
        tb = slide.shapes.add_textbox(Inches(0.75), Inches(0.45), Inches(11.0), Inches(0.85))
        tf = tb.text_frame
        tf.clear()
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = self._clean_slide_title(slide_data.title)
        p.font.name = FONT_FAMILY
        p.font.bold = True
        p.font.size = Pt(28)
        p.font.color.rgb = PPT_RED

        # Thin divider line under title
        line = slide.shapes.add_shape(1, Inches(0.75), Inches(1.3), Inches(11.0), Pt(2))
        line.fill.solid()
        line.fill.fore_color.rgb = PPT_RED
        line.line.fill.background()

        # Body bullets
        tb2 = slide.shapes.add_textbox(Inches(0.85), Inches(1.55), Inches(11.0), Inches(4.7))
        tf2 = tb2.text_frame
        tf2.clear()
        tf2.word_wrap = True
        bullet_font_size = Pt(self._resolve_bullet_font_size(slide_data.bullets))
        for idx, bullet in enumerate(self._prepare_bullets(slide_data.bullets[:5])):
            para = tf2.paragraphs[0] if idx == 0 else tf2.add_paragraph()
            para.text = f"▸  {bullet}"
            para.level = 0
            para.font.size = bullet_font_size
            para.font.name = FONT_FAMILY
            para.font.color.rgb = PPT_BODY_TEXT
            para.space_after = Pt(8)

        self._add_logo(slide)
        add_ppt_accent_bar(slide, prs)
        add_ppt_slide_number(slide, prs)

    def _write_section_divider(self, slide, prs, slide_data: GeneratedSlide) -> None:
        """Full-red background with white centred title."""
        slide_width = prs.slide_width or Emu(12192000)
        slide_height = prs.slide_height or Emu(6858000)

        # Full background rectangle
        bg = slide.shapes.add_shape(1, Emu(0), Emu(0), slide_width, slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = PPT_RED
        bg.line.fill.background()

        # Centred title
        tb = slide.shapes.add_textbox(Inches(1.5), Inches(2.5), Inches(10.0), Inches(2.0))
        tf = tb.text_frame
        tf.clear()
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = slide_data.title
        p.font.name = FONT_FAMILY
        p.font.bold = True
        p.font.size = Pt(36)
        p.font.color.rgb = PPT_WHITE
        p.alignment = PP_ALIGN.CENTER
        tf.paragraphs[0].space_before = Pt(0)

        add_ppt_slide_number(slide, prs)

    def _write_metrics_slide(self, slide, prs, slide_data: GeneratedSlide) -> None:
        """Metrics slide with large numbers/stats."""
        # Title
        tb = slide.shapes.add_textbox(Inches(0.75), Inches(0.45), Inches(11.0), Inches(0.85))
        tf = tb.text_frame
        tf.clear()
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = self._clean_slide_title(slide_data.title)
        p.font.name = FONT_FAMILY
        p.font.bold = True
        p.font.size = Pt(28)
        p.font.color.rgb = PPT_RED

        # Divider
        line = slide.shapes.add_shape(1, Inches(0.75), Inches(1.3), Inches(11.0), Pt(2))
        line.fill.solid()
        line.fill.fore_color.rgb = PPT_RED
        line.line.fill.background()

        # Metric cards laid out horizontally
        bullets = self._prepare_bullets(slide_data.bullets[:4])
        card_count = len(bullets) or 1
        card_width = min(Inches(2.8), Inches(11.0 / card_count - 0.2))
        start_x = Inches(0.85)
        for i, bullet in enumerate(bullets):
            x = start_x + i * (card_width + Inches(0.2))
            # Card background
            card = slide.shapes.add_shape(
                5,  # Rounded rectangle
                x,
                Inches(1.8),
                card_width,
                Inches(3.5),
            )
            card.fill.solid()
            card.fill.fore_color.rgb = PPT_ACCENT_DARK
            card.line.fill.background()

            # Metric text inside card area
            mtb = slide.shapes.add_textbox(x + Inches(0.15), Inches(2.2), card_width - Inches(0.3), Inches(2.8))
            mtf = mtb.text_frame
            mtf.clear()
            mtf.word_wrap = True

            # Split "Value — Description" format if present
            parts = re.split(r"\s*[—–\-:]\s*", bullet, maxsplit=1)
            value_text = parts[0].strip() if parts else bullet
            desc_text = parts[1].strip() if len(parts) > 1 else ""

            vp = mtf.paragraphs[0]
            vp.text = value_text
            vp.font.name = FONT_FAMILY
            vp.font.bold = True
            vp.font.size = Pt(22)
            vp.font.color.rgb = PPT_WHITE
            vp.alignment = PP_ALIGN.CENTER

            if desc_text:
                dp = mtf.add_paragraph()
                dp.text = desc_text
                dp.font.name = FONT_FAMILY
                dp.font.size = Pt(13)
                dp.font.color.rgb = PPT_MID_GREY
                dp.alignment = PP_ALIGN.CENTER
                dp.space_before = Pt(8)

        self._add_logo(slide)
        add_ppt_accent_bar(slide, prs)
        add_ppt_slide_number(slide, prs)

    def _write_two_column_slide(self, slide, prs, slide_data: GeneratedSlide) -> None:
        """Two-column comparison slide."""
        # Title
        tb = slide.shapes.add_textbox(Inches(0.75), Inches(0.45), Inches(11.0), Inches(0.85))
        tf = tb.text_frame
        tf.clear()
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = self._clean_slide_title(slide_data.title)
        p.font.name = FONT_FAMILY
        p.font.bold = True
        p.font.size = Pt(28)
        p.font.color.rgb = PPT_RED

        # Divider
        line = slide.shapes.add_shape(1, Inches(0.75), Inches(1.3), Inches(11.0), Pt(2))
        line.fill.solid()
        line.fill.fore_color.rgb = PPT_RED
        line.line.fill.background()

        # Column headers
        left_items = slide_data.left_column or self._prepare_bullets(slide_data.bullets[:3])
        right_items = slide_data.right_column or self._prepare_bullets(slide_data.bullets[3:6])

        # Determine column labels from title
        title_lower = slide_data.title.lower()
        if "vs" in title_lower:
            parts = re.split(r"\s+vs\.?\s+", slide_data.title, flags=re.IGNORECASE)
            left_label = parts[0].strip() if parts else "Left"
            right_label = parts[1].strip() if len(parts) > 1 else "Right"
        elif "current" in title_lower and "future" in title_lower:
            left_label, right_label = "Current State", "Future State"
        else:
            left_label, right_label = "Challenges", "Opportunities"

        col_width = Inches(5.3)
        col_gap = Inches(0.4)

        for col_idx, (label, items) in enumerate([(left_label, left_items), (right_label, right_items)]):
            x = Inches(0.85) + col_idx * (col_width + col_gap)

            # Column header
            htb = slide.shapes.add_textbox(x, Inches(1.55), col_width, Inches(0.5))
            htf = htb.text_frame
            htf.clear()
            hp = htf.paragraphs[0]
            hp.text = label
            hp.font.name = FONT_FAMILY
            hp.font.bold = True
            hp.font.size = Pt(16)
            hp.font.color.rgb = PPT_ACCENT_DARK

            # Column items
            ctb = slide.shapes.add_textbox(x, Inches(2.1), col_width, Inches(4.0))
            ctf = ctb.text_frame
            ctf.clear()
            ctf.word_wrap = True
            for idx, item in enumerate(items[:5]):
                cp = ctf.paragraphs[0] if idx == 0 else ctf.add_paragraph()
                cp.text = f"▸  {item}"
                cp.font.name = FONT_FAMILY
                cp.font.size = Pt(15)
                cp.font.color.rgb = PPT_BODY_TEXT
                cp.space_after = Pt(6)

        self._add_logo(slide)
        add_ppt_accent_bar(slide, prs)
        add_ppt_slide_number(slide, prs)

    def _write_closing_slide(self, slide, prs, slide_data: GeneratedSlide) -> None:
        """Closing / next-steps slide with dark background."""
        slide_width = prs.slide_width or Emu(12192000)
        slide_height = prs.slide_height or Emu(6858000)

        # Dark background
        bg = slide.shapes.add_shape(1, Emu(0), Emu(0), slide_width, slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = PPT_ACCENT_DARK
        bg.line.fill.background()

        # Title
        tb = slide.shapes.add_textbox(Inches(1.0), Inches(0.8), Inches(10.5), Inches(1.0))
        tf = tb.text_frame
        tf.clear()
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = slide_data.title
        p.font.name = FONT_FAMILY
        p.font.bold = True
        p.font.size = Pt(32)
        p.font.color.rgb = PPT_WHITE

        # Thin red divider
        line = slide.shapes.add_shape(1, Inches(1.0), Inches(1.8), Inches(3.0), Pt(3))
        line.fill.solid()
        line.fill.fore_color.rgb = PPT_RED
        line.line.fill.background()

        # Bullets
        tb2 = slide.shapes.add_textbox(Inches(1.1), Inches(2.2), Inches(10.0), Inches(4.0))
        tf2 = tb2.text_frame
        tf2.clear()
        tf2.word_wrap = True
        for idx, bullet in enumerate(self._prepare_bullets(slide_data.bullets[:5])):
            bp = tf2.paragraphs[0] if idx == 0 else tf2.add_paragraph()
            bp.text = f"→  {bullet}"
            bp.font.name = FONT_FAMILY
            bp.font.size = Pt(18)
            bp.font.color.rgb = PPT_WHITE
            bp.space_after = Pt(12)

        # Thank-you line
        tb3 = slide.shapes.add_textbox(Inches(1.0), Inches(6.0), Inches(5.0), Inches(0.5))
        tf3 = tb3.text_frame
        tf3.clear()
        p3 = tf3.paragraphs[0]
        p3.text = "BSBI Consulting  |  Confidential"
        p3.font.name = FONT_FAMILY
        p3.font.size = Pt(10)
        p3.font.color.rgb = PPT_MID_GREY

        self._add_logo(slide)
        add_ppt_slide_number(slide, prs)

    # ── Utility methods ────────────────────────────────────────────────────

    def _truncate_slides(self, slides: list[GeneratedSlide], limit: int) -> list[GeneratedSlide]:
        """Truncate to limit while always keeping closing, divider, and two-column slides."""
        if len(slides) <= limit:
            return slides

        # Separate structural and removable slides
        keep_types = {"closing", "section_divider", "two_column"}
        structural = [(i, s) for i, s in enumerate(slides) if s.slide_type in keep_types]
        removable = [(i, s) for i, s in enumerate(slides) if s.slide_type not in keep_types]

        # Keep all structural, fill remaining budget with content slides from the front
        budget_for_content = limit - len(structural)
        if budget_for_content < 0:
            # More structural slides than budget — just truncate
            return slides[:limit]

        kept_content = removable[:budget_for_content]
        # Merge back in original order
        result_indices = sorted([i for i, _ in structural] + [i for i, _ in kept_content])
        return [slides[i] for i in result_indices]


    def _clear_existing_slides(self, presentation: Presentation) -> None:
        slide_id_list = presentation.slides._sldIdLst
        for slide_id in list(slide_id_list):
            relationship_id = slide_id.rId
            presentation.part.drop_rel(relationship_id)
            slide_id_list.remove(slide_id)

    def _resolve_blank_layout(self, presentation: Presentation):
        for layout in presentation.slide_layouts:
            if len(layout.placeholders) == 0:
                return layout
        if len(presentation.slide_layouts) >= 7:
            return presentation.slide_layouts[6]
        return presentation.slide_layouts[-1]

    def _add_logo(self, slide) -> None:
        if logo_exists():
            slide.shapes.add_picture(str(LOGO_PATH), Inches(10.9), Inches(0.15), width=Inches(1.4))

    def _build_context_blob(self, source_text: str, retrieval_context: list[str]) -> str:
        source = source_text[:8000]
        retrieval = "\n".join(chunk[:800] for chunk in retrieval_context[:5] if chunk.strip())
        return "\n\n".join(part for part in [source, retrieval] if part)

    def _prepare_bullets(self, bullets: list[str]) -> list[str]:
        prepared: list[str] = []
        for bullet in bullets:
            cleaned = self._clean_bullet(bullet)
            if not cleaned:
                continue
            if cleaned not in prepared:
                prepared.append(cleaned)
        return prepared[:5]

    def _clean_bullet(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        cleaned = re.sub(r"^[\d\-\.\)\(]+\s*", "", cleaned)
        cleaned = cleaned.replace("•", " ").strip(" -")
        if len(cleaned) > 140:
            cleaned = f"{cleaned[:137].rstrip()}..."
        return cleaned

    def _clean_slide_title(self, title: str) -> str:
        cleaned = re.sub(r"\s+", " ", title).strip()
        if len(cleaned) > 58:
            cleaned = f"{cleaned[:55].rstrip()}..."
        return cleaned

    def _resolve_bullet_font_size(self, bullets: list[str]) -> int:
        longest = max((len(item) for item in bullets), default=0)
        if longest > 115 or len(bullets) >= 5:
            return 15
        if longest > 88:
            return 17
        return 19
