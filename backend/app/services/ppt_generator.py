from __future__ import annotations

import re
from datetime import datetime, timezone

from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt, Emu

from backend.app.models.schemas import GeneratePptxRequest, GenerateResult, GeneratedSlide
from backend.app.services.branding import (
    LOGO_PATH,
    COMPANY_NAME,
    CONFIDENTIAL_TEXT,
    PPT_RED,
    PPT_DARK,
    PPT_HEADER,
    PPT_MID_GREY,
    PPT_WHITE,
    PPT_BODY_TEXT,
    PPT_COL_LEFT_BG,
    PPT_COL_RIGHT_BG,
    PPT_OFF_WHITE,
    FONT_HEADING,
    FONT_BODY,
    add_ppt_accent_bar,
    add_ppt_slide_number,
    logo_exists,
    get_ppt_template_path,
)
from backend.app.services.file_utils import build_output_path
from backend.app.services.llm_provider import generate_json_object
from backend.app.services.text_utils import build_section_candidates

# ── Slide dimensions (widescreen 16:9) ─────────────────────────────────────
SLIDE_W = Emu(12192000)   # 13.333 in
SLIDE_H = Emu(6858000)    # 7.5 in

# ── Layout constants ────────────────────────────────────────────────────────
MARGIN_L     = Inches(0.75)
MARGIN_R     = Inches(0.75)
CONTENT_W    = SLIDE_W - MARGIN_L - MARGIN_R  # usable content width
HEADER_H     = Inches(1.30)   # dark top-band height on content slides
RED_STRIPE_H = Pt(4)          # red divider stripe under header band
BOTTOM_BAR_H = Inches(0.22)   # red bar at very bottom
ACCENT_BAR_W = Inches(0.30)   # red left bar on dark slides
LOGO_W       = Inches(1.55)   # logo width

# ── Prompt templates ────────────────────────────────────────────────────────
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
4. slide_type "metrics" — Key Numbers / Metrics (3-4 bullets in format "Value — Description")
5. slide_type "two_column" — Strengths vs Risks (left_column = benefits/capabilities, right_column = risks/limitations/challenges found in the source — look in sections named "Current Challenges", "Risks", "Limitations", "Out of Scope", or Phase descriptions)
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
        return GenerateResult(
            artifact_type="pptx",
            file_path=str(output_path),
            artifact_name=artifact_name,
            download_url=f"/api/v1/artifacts/{artifact_name}",
            summary=f"Presentation generated: {request.deck_title}",
            slides=slides,
        )

    # ── Slide building ──────────────────────────────────────────────────────

    def _build_slides(self, request: GeneratePptxRequest, retrieval_context: list[str]) -> list[GeneratedSlide]:
        llm_slides = self._build_slides_from_llm(request, retrieval_context)
        if llm_slides:
            return self._truncate_slides(llm_slides, request.max_content_slides)

        candidates = build_section_candidates(request.source_document)
        content_slides = [
            GeneratedSlide(title="Executive Overview",     bullets=[],                                              slide_type="section_divider"),
            GeneratedSlide(title="Executive Summary",      bullets=self._prepare_bullets(candidates["Project Overview"][:4]), slide_type="content"),
            GeneratedSlide(title="Scope and Approach",     bullets=self._prepare_bullets(candidates["Scope"][:4]),            slide_type="content"),
            GeneratedSlide(title="Key Deliverables",       bullets=self._prepare_bullets(candidates["Deliverables"][:4]),     slide_type="content"),
            GeneratedSlide(
                title="Current State vs Future State",
                bullets=[],
                slide_type="two_column",
                left_column=self._prepare_bullets(candidates["Risks"][:3])       or ["To be confirmed"],
                right_column=self._prepare_bullets(candidates["Deliverables"][:3]) or ["To be confirmed"],
            ),
            GeneratedSlide(title="Timeline & Next Steps",  bullets=[],                                              slide_type="section_divider"),
            GeneratedSlide(
                title="Implementation Timeline",
                bullets=self._prepare_bullets((candidates["Timeline"] + candidates["Risks"])[:5]),
                slide_type="content",
            ),
            GeneratedSlide(
                title="Next Steps",
                bullets=["Confirm project scope and stakeholder alignment",
                         "Finalise resource plan and delivery timeline",
                         "Schedule kickoff workshop",
                         "Begin discovery phase"],
                slide_type="closing",
            ),
        ]

        if request.max_content_slides > len(content_slides):
            for section in request.source_document.sections:
                if len(content_slides) >= request.max_content_slides:
                    break
                heading = self._clean_title(section.heading or "Additional Detail")
                lines = [l.strip() for l in section.body.splitlines() if l.strip()]
                bullets = self._prepare_bullets(lines[:5])
                if bullets:
                    content_slides.append(GeneratedSlide(title=heading, bullets=bullets, slide_type="content"))

        return self._truncate_slides(content_slides, request.max_content_slides)

    def _build_slides_from_llm(self, request: GeneratePptxRequest, retrieval_context: list[str]) -> list[GeneratedSlide] | None:
        context_blob = self._build_context_blob(request.source_document, retrieval_context)
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
            slides: list[GeneratedSlide] = []
            for item in payload.get("slides", []):
                title = str(item.get("title", "")).strip()
                if not title:
                    continue
                slide_type = str(item.get("slide_type", "content")).strip()
                if slide_type not in ("content", "section_divider", "metrics", "two_column", "closing"):
                    slide_type = "content"
                slides.append(GeneratedSlide(
                    title=self._clean_title(title),
                    bullets=self._prepare_bullets([str(b).strip() for b in item.get("bullets", []) if str(b).strip()])[:5],
                    slide_type=slide_type,
                    left_column=self._prepare_bullets([str(b).strip() for b in item.get("left_column", []) if str(b).strip()]),
                    right_column=self._prepare_bullets([str(b).strip() for b in item.get("right_column", []) if str(b).strip()]),
                ))
            return slides or None
        except Exception:
            return None

    # ── Presentation writing ────────────────────────────────────────────────

    def _write_presentation(self, *, output_path: str, request: GeneratePptxRequest, slides: list[GeneratedSlide]) -> None:
        tpl_path = get_ppt_template_path()
        prs = Presentation(str(tpl_path)) if tpl_path else Presentation()
        self._clear_existing_slides(prs)
        blank = self._blank_layout(prs)

        # Title slide
        self._write_title_slide(prs.slides.add_slide(blank), prs, request)

        # Content slides
        for slide_data in slides:
            s = prs.slides.add_slide(blank)
            if slide_data.slide_type == "section_divider":
                self._write_section_divider(s, prs, slide_data)
            elif slide_data.slide_type == "metrics":
                self._write_metrics_slide(s, prs, slide_data)
            elif slide_data.slide_type == "two_column":
                self._write_two_column_slide(s, prs, slide_data)
            elif slide_data.slide_type == "closing":
                self._write_closing_slide(s, prs, slide_data)
            else:
                self._write_content_slide(s, prs, slide_data)

        prs.save(output_path)

    # ── Individual slide writers ────────────────────────────────────────────

    def _write_title_slide(self, slide, prs, request: GeneratePptxRequest) -> None:
        """
        Dark background. Thin red left accent bar. Logo top-right.
        Large white title, grey subtitle, company + date near bottom.
        """
        sw = prs.slide_width or SLIDE_W
        sh = prs.slide_height or SLIDE_H

        # Dark background
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = PPT_DARK

        # Red left accent bar
        bar = slide.shapes.add_shape(1, Emu(0), Emu(0), ACCENT_BAR_W, sh)
        bar.fill.solid()
        bar.fill.fore_color.rgb = PPT_RED
        bar.line.fill.background()

        # Thin red bottom bar
        bottom = slide.shapes.add_shape(1, Emu(0), sh - BOTTOM_BAR_H, sw, BOTTOM_BAR_H)
        bottom.fill.solid()
        bottom.fill.fore_color.rgb = PPT_RED
        bottom.line.fill.background()

        content_x = ACCENT_BAR_W + Inches(0.55)
        content_w  = sw - content_x - Inches(0.6)

        # Logo — top-right
        if logo_exists():
            logo_x = sw - LOGO_W - Inches(0.35)
            slide.shapes.add_picture(str(LOGO_PATH), logo_x, Inches(0.28), width=LOGO_W)
            title_w = logo_x - content_x - Inches(0.2)
        else:
            title_w = content_w

        # Deck title
        tb = slide.shapes.add_textbox(content_x, Inches(1.6), title_w, Inches(1.6))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = request.deck_title
        p.font.name = FONT_HEADING
        p.font.bold = True
        p.font.size = Pt(42)
        p.font.color.rgb = PPT_WHITE

        # Subtitle
        subtitle = request.subtitle or request.source_document.title
        tb2 = slide.shapes.add_textbox(content_x, Inches(3.4), content_w, Inches(0.85))
        tf2 = tb2.text_frame
        tf2.word_wrap = True
        p2 = tf2.paragraphs[0]
        p2.text = subtitle
        p2.font.name = FONT_BODY
        p2.font.size = Pt(18)
        p2.font.color.rgb = PPT_MID_GREY

        # Company | Date
        today = datetime.now(timezone.utc).strftime("%d %B %Y")
        tb3 = slide.shapes.add_textbox(content_x, Inches(6.3), Inches(6.0), Inches(0.4))
        tf3 = tb3.text_frame
        p3 = tf3.paragraphs[0]
        p3.text = f"{COMPANY_NAME}  ·  {today}"
        p3.font.name = FONT_BODY
        p3.font.size = Pt(11)
        p3.font.color.rgb = PPT_MID_GREY

        # Confidential — bottom-right
        tb4 = slide.shapes.add_textbox(sw - Inches(2.2), sh - Inches(0.5), Inches(2.0), Inches(0.3))
        tf4 = tb4.text_frame
        p4 = tf4.paragraphs[0]
        p4.text = CONFIDENTIAL_TEXT
        p4.alignment = PP_ALIGN.RIGHT
        p4.font.name = FONT_BODY
        p4.font.size = Pt(8)
        p4.font.color.rgb = PPT_MID_GREY

    def _write_content_slide(self, slide, prs, slide_data: GeneratedSlide) -> None:
        """
        White background. Dark header band with white title + logo.
        Red stripe separator. Clean bullets below. Red bottom bar.
        """
        sw = prs.slide_width or SLIDE_W
        sh = prs.slide_height or SLIDE_H

        # White background
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = PPT_WHITE

        # Dark header band
        header = slide.shapes.add_shape(1, Emu(0), Emu(0), sw, HEADER_H)
        header.fill.solid()
        header.fill.fore_color.rgb = PPT_HEADER
        header.line.fill.background()

        # Red stripe under header
        stripe = slide.shapes.add_shape(1, Emu(0), HEADER_H, sw, RED_STRIPE_H)
        stripe.fill.solid()
        stripe.fill.fore_color.rgb = PPT_RED
        stripe.line.fill.background()

        # Logo inside header — right-aligned
        if logo_exists():
            logo_x = sw - LOGO_W - Inches(0.25)
            logo_y = (HEADER_H - Inches(0.72)) // 2
            slide.shapes.add_picture(str(LOGO_PATH), logo_x, logo_y, width=LOGO_W)
            title_w = logo_x - MARGIN_L - Inches(0.1)
        else:
            title_w = sw - MARGIN_L * 2

        # Slide title — inside header
        tb = slide.shapes.add_textbox(MARGIN_L, Inches(0.22), title_w, HEADER_H - Inches(0.22))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = self._clean_title(slide_data.title)
        p.font.name = FONT_HEADING
        p.font.bold = True
        p.font.size = Pt(26)
        p.font.color.rgb = PPT_WHITE

        # Bullets
        bullet_top = HEADER_H + RED_STRIPE_H + Inches(0.22)
        bullet_h   = sh - bullet_top - BOTTOM_BAR_H - Inches(0.1)
        tb2 = slide.shapes.add_textbox(MARGIN_L, bullet_top, sw - MARGIN_L * 2, bullet_h)
        tf2 = tb2.text_frame
        tf2.word_wrap = True
        font_sz = Pt(self._bullet_font_size(slide_data.bullets))
        for idx, bullet in enumerate(self._prepare_bullets(slide_data.bullets[:6])):
            para = tf2.paragraphs[0] if idx == 0 else tf2.add_paragraph()
            para.text = f"–  {bullet}"
            para.font.name = FONT_BODY
            para.font.size = font_sz
            para.font.color.rgb = PPT_BODY_TEXT
            para.space_after = Pt(10)

        add_ppt_accent_bar(slide, prs)
        add_ppt_slide_number(slide, prs)

    def _write_section_divider(self, slide, prs, slide_data: GeneratedSlide) -> None:
        """
        Full red background. Large centred white title.
        Decorative white rectangle for visual texture. Slide number only.
        """
        sw = prs.slide_width or SLIDE_W
        sh = prs.slide_height or SLIDE_H

        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = PPT_RED

        # Decorative large circle (white, low-opacity feel via very light fill)
        # python-pptx doesn't do transparency, so use a slightly off-white rect
        deco = slide.shapes.add_shape(
            9,  # oval
            sw - Inches(3.4), sh - Inches(3.4),
            Inches(5.2), Inches(5.2),
        )
        deco.fill.solid()
        deco.fill.fore_color.rgb = PPT_WHITE
        # Simulate low-opacity by using a very faint color instead
        from pptx.dml.color import RGBColor as _RGB
        deco.fill.fore_color.rgb = _RGB(200, 20, 40)  # slightly lighter red
        deco.line.fill.background()

        # Thin white horizontal rule above title
        rule_y = sh // 2 - Inches(1.1)
        rule = slide.shapes.add_shape(1, Inches(1.5), rule_y, Inches(2.5), Pt(2))
        rule.fill.solid()
        rule.fill.fore_color.rgb = PPT_WHITE
        rule.line.fill.background()

        # Title — centred
        tb = slide.shapes.add_textbox(Inches(1.0), sh // 2 - Inches(0.85), sw - Inches(2.0), Inches(1.8))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = slide_data.title
        p.alignment = PP_ALIGN.LEFT
        p.font.name = FONT_HEADING
        p.font.bold = True
        p.font.size = Pt(42)
        p.font.color.rgb = PPT_WHITE

        # Optional subtitle / first bullet as tagline
        if slide_data.bullets:
            tb2 = slide.shapes.add_textbox(Inches(1.0), sh // 2 + Inches(0.85), sw - Inches(2.0), Inches(0.6))
            tf2 = tb2.text_frame
            p2 = tf2.paragraphs[0]
            p2.text = slide_data.bullets[0]
            p2.alignment = PP_ALIGN.LEFT
            p2.font.name = FONT_BODY
            p2.font.size = Pt(16)
            p2.font.color.rgb = PPT_WHITE

        add_ppt_slide_number(slide, prs)

    def _write_metrics_slide(self, slide, prs, slide_data: GeneratedSlide) -> None:
        """
        White bg + dark header band (same as content).
        Cards: white with red top border, large dark stat, grey description.
        """
        sw = prs.slide_width or SLIDE_W
        sh = prs.slide_height or SLIDE_H

        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = PPT_WHITE

        # Header band + stripe (same as content slide)
        self._draw_header_band(slide, prs, slide_data.title, sw)

        # Metric cards
        bullets = self._prepare_bullets(slide_data.bullets[:4])
        n = max(len(bullets), 1)
        total_gap   = Inches(0.25) * (n - 1)
        card_w      = (sw - MARGIN_L * 2 - total_gap) / n
        card_h      = Inches(3.2)
        card_top    = HEADER_H + RED_STRIPE_H + Inches(0.45)
        red_top_h   = Inches(0.08)

        for i, bullet in enumerate(bullets):
            cx = MARGIN_L + i * (card_w + Inches(0.25))

            # Red top accent on card
            red_top = slide.shapes.add_shape(1, cx, card_top, card_w, red_top_h)
            red_top.fill.solid()
            red_top.fill.fore_color.rgb = PPT_RED
            red_top.line.fill.background()

            # Card body (white, light grey border)
            card = slide.shapes.add_shape(1, cx, card_top + red_top_h, card_w, card_h - red_top_h)
            card.fill.solid()
            card.fill.fore_color.rgb = PPT_WHITE
            card.line.color.rgb = PPT_OFF_WHITE

            # Split "Value — Description"
            parts  = re.split(r"\s*[—–\-:]\s*", bullet, maxsplit=1)
            value  = parts[0].strip()
            desc   = parts[1].strip() if len(parts) > 1 else ""

            inner_x = cx + Inches(0.18)
            inner_w = card_w - Inches(0.36)

            vp_tb = slide.shapes.add_textbox(inner_x, card_top + red_top_h + Inches(0.35), inner_w, Inches(1.1))
            vp_tf = vp_tb.text_frame
            vp_tf.word_wrap = True
            vp = vp_tf.paragraphs[0]
            vp.text = value
            vp.alignment = PP_ALIGN.CENTER
            vp.font.name = FONT_HEADING
            vp.font.bold = True
            vp.font.size = Pt(30)
            vp.font.color.rgb = PPT_BODY_TEXT

            if desc:
                dp_tb = slide.shapes.add_textbox(inner_x, card_top + red_top_h + Inches(1.5), inner_w, Inches(1.4))
                dp_tf = dp_tb.text_frame
                dp_tf.word_wrap = True
                dp = dp_tf.paragraphs[0]
                dp.text = desc
                dp.alignment = PP_ALIGN.CENTER
                dp.font.name = FONT_BODY
                dp.font.size = Pt(13)
                dp.font.color.rgb = PPT_MID_GREY

        add_ppt_accent_bar(slide, prs)
        add_ppt_slide_number(slide, prs)

    def _write_two_column_slide(self, slide, prs, slide_data: GeneratedSlide) -> None:
        """
        White bg + dark header. Left column: light-red tint. Right: light grey.
        """
        sw = prs.slide_width or SLIDE_W
        sh = prs.slide_height or SLIDE_H

        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = PPT_WHITE

        self._draw_header_band(slide, prs, slide_data.title, sw)

        left_items  = slide_data.left_column or self._prepare_bullets(slide_data.bullets[:3])
        right_items = slide_data.right_column or self._prepare_bullets(slide_data.bullets[3:6])

        # Infer column labels
        title_lower = slide_data.title.lower()
        if "vs" in title_lower:
            parts = re.split(r"\s+vs\.?\s+", slide_data.title, flags=re.IGNORECASE)
            left_label  = parts[0].strip() if parts else "Left"
            right_label = parts[1].strip() if len(parts) > 1 else "Right"
        elif "current" in title_lower and "future" in title_lower:
            left_label, right_label = "Current State", "Future State"
        elif "strength" in title_lower or "risk" in title_lower:
            left_label, right_label = "Strengths", "Risks"
        else:
            left_label, right_label = "Challenges", "Opportunities"

        gap     = Inches(0.22)
        col_w   = (sw - MARGIN_L * 2 - gap) / 2
        col_top = HEADER_H + RED_STRIPE_H + Inches(0.25)
        col_h   = sh - col_top - BOTTOM_BAR_H - Inches(0.1)

        for col_idx, (label, items, bg_color, hdr_color) in enumerate([
            (left_label,  left_items,  PPT_COL_LEFT_BG,  PPT_RED),
            (right_label, right_items, PPT_COL_RIGHT_BG, PPT_BODY_TEXT),
        ]):
            cx = MARGIN_L + col_idx * (col_w + gap)

            # Column background panel
            panel = slide.shapes.add_shape(1, cx, col_top, col_w, col_h)
            panel.fill.solid()
            panel.fill.fore_color.rgb = bg_color
            panel.line.fill.background()

            # Column header label
            htb = slide.shapes.add_textbox(cx + Inches(0.2), col_top + Inches(0.18), col_w - Inches(0.4), Inches(0.55))
            htf = htb.text_frame
            hp = htf.paragraphs[0]
            hp.text = label
            hp.font.name = FONT_HEADING
            hp.font.bold = True
            hp.font.size = Pt(15)
            hp.font.color.rgb = hdr_color

            # Thin divider inside column
            div = slide.shapes.add_shape(1, cx + Inches(0.2), col_top + Inches(0.78), col_w - Inches(0.4), Pt(1))
            div.fill.solid()
            div.fill.fore_color.rgb = hdr_color
            div.line.fill.background()

            # Items
            itb = slide.shapes.add_textbox(cx + Inches(0.2), col_top + Inches(0.92), col_w - Inches(0.4), col_h - Inches(1.05))
            itf = itb.text_frame
            itf.word_wrap = True
            for idx, item in enumerate(items[:5]):
                ip = itf.paragraphs[0] if idx == 0 else itf.add_paragraph()
                ip.text = f"–  {item}"
                ip.font.name = FONT_BODY
                ip.font.size = Pt(14)
                ip.font.color.rgb = PPT_BODY_TEXT
                ip.space_after = Pt(8)

        add_ppt_accent_bar(slide, prs)
        add_ppt_slide_number(slide, prs)

    def _write_closing_slide(self, slide, prs, slide_data: GeneratedSlide) -> None:
        """
        Dark background + red left accent bar (mirrors title slide).
        Large white title, action-item bullets, company footer.
        """
        sw = prs.slide_width or SLIDE_W
        sh = prs.slide_height or SLIDE_H

        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = PPT_DARK

        # Red left accent bar
        bar = slide.shapes.add_shape(1, Emu(0), Emu(0), ACCENT_BAR_W, sh)
        bar.fill.solid()
        bar.fill.fore_color.rgb = PPT_RED
        bar.line.fill.background()

        # Red bottom bar
        bottom = slide.shapes.add_shape(1, Emu(0), sh - BOTTOM_BAR_H, sw, BOTTOM_BAR_H)
        bottom.fill.solid()
        bottom.fill.fore_color.rgb = PPT_RED
        bottom.line.fill.background()

        content_x = ACCENT_BAR_W + Inches(0.55)
        content_w  = sw - content_x - Inches(0.55)

        # Logo — top-right
        if logo_exists():
            slide.shapes.add_picture(str(LOGO_PATH), sw - LOGO_W - Inches(0.35), Inches(0.28), width=LOGO_W)

        # Title
        tb = slide.shapes.add_textbox(content_x, Inches(0.9), content_w, Inches(1.2))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = slide_data.title
        p.font.name = FONT_HEADING
        p.font.bold = True
        p.font.size = Pt(36)
        p.font.color.rgb = PPT_WHITE

        # Red accent line under title
        line = slide.shapes.add_shape(1, content_x, Inches(2.25), Inches(4.5), Pt(3))
        line.fill.solid()
        line.fill.fore_color.rgb = PPT_RED
        line.line.fill.background()

        # Action bullets
        tb2 = slide.shapes.add_textbox(content_x, Inches(2.55), content_w, Inches(4.0))
        tf2 = tb2.text_frame
        tf2.word_wrap = True
        for idx, bullet in enumerate(self._prepare_bullets(slide_data.bullets[:5])):
            bp = tf2.paragraphs[0] if idx == 0 else tf2.add_paragraph()
            bp.text = f"→  {bullet}"
            bp.font.name = FONT_BODY
            bp.font.size = Pt(17)
            bp.font.color.rgb = PPT_WHITE
            bp.space_after = Pt(14)

        # Company footer
        tb3 = slide.shapes.add_textbox(content_x, sh - Inches(0.52), Inches(5.5), Inches(0.3))
        tf3 = tb3.text_frame
        p3 = tf3.paragraphs[0]
        p3.text = f"{COMPANY_NAME}  ·  {CONFIDENTIAL_TEXT}"
        p3.font.name = FONT_BODY
        p3.font.size = Pt(9)
        p3.font.color.rgb = PPT_MID_GREY

        add_ppt_slide_number(slide, prs)

    # ── Shared helpers ──────────────────────────────────────────────────────

    def _draw_header_band(self, slide, prs, title: str, sw: Emu) -> None:
        """Dark header band + red stripe + logo + title (shared by content, metrics, two-column)."""
        # Dark band
        header = slide.shapes.add_shape(1, Emu(0), Emu(0), sw, HEADER_H)
        header.fill.solid()
        header.fill.fore_color.rgb = PPT_HEADER
        header.line.fill.background()

        # Red stripe
        stripe = slide.shapes.add_shape(1, Emu(0), HEADER_H, sw, RED_STRIPE_H)
        stripe.fill.solid()
        stripe.fill.fore_color.rgb = PPT_RED
        stripe.line.fill.background()

        # Logo
        if logo_exists():
            logo_x = sw - LOGO_W - Inches(0.25)
            logo_y = (HEADER_H - Inches(0.72)) // 2
            slide.shapes.add_picture(str(LOGO_PATH), logo_x, logo_y, width=LOGO_W)
            title_w = logo_x - MARGIN_L - Inches(0.1)
        else:
            title_w = sw - MARGIN_L * 2

        # Title in header
        tb = slide.shapes.add_textbox(MARGIN_L, Inches(0.22), title_w, HEADER_H - Inches(0.22))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = self._clean_title(title)
        p.font.name = FONT_HEADING
        p.font.bold = True
        p.font.size = Pt(26)
        p.font.color.rgb = PPT_WHITE

    # ── Utility methods ─────────────────────────────────────────────────────

    def _clear_existing_slides(self, prs: Presentation) -> None:
        slide_id_list = prs.slides._sldIdLst
        for slide_id in list(slide_id_list):
            prs.part.drop_rel(slide_id.rId)
            slide_id_list.remove(slide_id)

    def _blank_layout(self, prs: Presentation):
        for layout in prs.slide_layouts:
            if len(layout.placeholders) == 0:
                return layout
        return prs.slide_layouts[min(6, len(prs.slide_layouts) - 1)]

    def _truncate_slides(self, slides: list[GeneratedSlide], limit: int) -> list[GeneratedSlide]:
        if len(slides) <= limit:
            return slides
        keep = {"closing", "section_divider", "two_column"}
        structural = [(i, s) for i, s in enumerate(slides) if s.slide_type in keep]
        removable  = [(i, s) for i, s in enumerate(slides) if s.slide_type not in keep]
        budget     = limit - len(structural)
        if budget < 0:
            return slides[:limit]
        kept = removable[:budget]
        indices = sorted([i for i, _ in structural] + [i for i, _ in kept])
        return [slides[i] for i in indices]

    def _build_context_blob(self, source_document, retrieval_context: list[str]) -> str:
        """Build a context blob that samples from ALL sections of the document,
        not just the first N characters, so the LLM sees risks/constraints that
        appear late in the document."""
        parts: list[str] = []

        # Section-based extraction: heading + up to 600 chars per section body
        # This gives full document coverage regardless of total length
        if source_document.sections:
            section_chunks: list[str] = []
            for sec in source_document.sections:
                heading = sec.heading.strip() if sec.heading else ""
                body    = sec.body.strip()[:600] if sec.body else ""
                if heading and body:
                    section_chunks.append(f"### {heading}\n{body}")
                elif heading:
                    section_chunks.append(f"### {heading}")
                elif body:
                    section_chunks.append(body)
            if section_chunks:
                parts.append("\n\n".join(section_chunks))

        # Fall back to raw text if no sections (truncate generously)
        if not parts:
            parts.append(source_document.text[:10000])

        # Retrieval context (vector-search results)
        if retrieval_context:
            retrieval = "\n".join(chunk[:600] for chunk in retrieval_context[:5] if chunk.strip())
            if retrieval:
                parts.append(f"--- Additional context ---\n{retrieval}")

        return "\n\n".join(parts)

    def _prepare_bullets(self, bullets: list[str]) -> list[str]:
        seen: list[str] = []
        for b in bullets:
            c = self._clean_bullet(b)
            if c and c not in seen:
                seen.append(c)
        return seen[:6]

    def _clean_bullet(self, text: str) -> str:
        c = re.sub(r"\s+", " ", text).strip()
        c = re.sub(r"^[\d\-\.\)\(▸→•]+\s*", "", c).strip()
        if len(c) > 140:
            c = f"{c[:137].rstrip()}..."
        return c

    def _clean_title(self, title: str) -> str:
        c = re.sub(r"\s+", " ", title).strip()
        if len(c) > 60:
            c = f"{c[:57].rstrip()}..."
        return c

    def _bullet_font_size(self, bullets: list[str]) -> int:
        longest = max((len(b) for b in bullets), default=0)
        if longest > 110 or len(bullets) >= 6:
            return 14
        if longest > 80:
            return 16
        return 18