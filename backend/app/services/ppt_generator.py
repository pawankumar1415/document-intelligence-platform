from __future__ import annotations

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

from backend.app.models.schemas import GeneratePptxRequest, GenerateResult, GeneratedSlide
from backend.app.services.branding import LOGO_PATH, PPT_TEMPLATE_PATH, logo_exists, ppt_template_exists
from backend.app.services.file_utils import build_output_path
from backend.app.services.llm_provider import generate_json_object
from backend.app.services.text_utils import build_section_candidates


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

    def _build_slides(self, request: GeneratePptxRequest, retrieval_context: list[str]) -> list[GeneratedSlide]:
        llm_slides = self._build_slides_from_llm(request, retrieval_context)
        if llm_slides:
            return llm_slides[: request.max_content_slides]

        candidates = build_section_candidates(request.source_document)

        content_slides = [
            GeneratedSlide(title="Executive Summary", bullets=candidates["Project Overview"][:3]),
            GeneratedSlide(title="Scope Highlights", bullets=candidates["Scope"][:3]),
            GeneratedSlide(title="Deliverables", bullets=candidates["Deliverables"][:3]),
            GeneratedSlide(title="Timeline and Risks", bullets=(candidates["Timeline"] + candidates["Risks"])[:3]),
        ]
        return content_slides[: request.max_content_slides]

    def _build_slides_from_llm(
        self,
        request: GeneratePptxRequest,
        retrieval_context: list[str],
    ) -> list[GeneratedSlide] | None:
        context_blob = "\n\n".join(
            [request.source_document.text[:6000], *retrieval_context[:5]]
        )
        system_prompt = (
            "You are a management consultant preparing a board-ready presentation outline. "
            "Return strict JSON only."
        )
        user_prompt = (
            "Return ONLY JSON in this shape: "
            '{"slides":[{"title":"string","bullets":["string","string","string"]}]}. '
            "Generate concise slide titles and max 4 bullets each. "
            "Use ONLY information grounded in the provided source. "
            "If data is missing, write 'To be confirmed' instead of inventing facts.\n\n"
            f"Deck title: {request.deck_title}\n"
            f"Subtitle: {request.subtitle or ''}\n"
            f"Source:\n{context_blob}"
        )

        try:
            payload = generate_json_object(
                provider=request.llm_provider,
                model=request.llm_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
            )
            slides_payload = payload.get("slides", [])
            slides: list[GeneratedSlide] = []
            for item in slides_payload:
                title = str(item.get("title", "")).strip()
                if not title:
                    continue
                bullets = [str(b).strip() for b in item.get("bullets", []) if str(b).strip()]
                slides.append(GeneratedSlide(title=title, bullets=bullets[:4]))
            return slides or None
        except Exception:
            return None

    def _write_presentation(self, *, output_path: str, request: GeneratePptxRequest, slides: list[GeneratedSlide]) -> None:
        presentation = Presentation(str(PPT_TEMPLATE_PATH)) if ppt_template_exists() else Presentation()
        self._clear_existing_slides(presentation)
        blank_layout = self._resolve_blank_layout(presentation)

        title_slide = presentation.slides.add_slide(blank_layout)
        self._write_title_slide_content(
            title_slide=title_slide,
            title_text=request.deck_title,
            subtitle_text=request.subtitle or request.source_document.title,
        )
        self._style_title_slide(title_slide)
        self._add_logo(title_slide)

        for slide in slides:
            generated_slide = presentation.slides.add_slide(blank_layout)
            self._write_content_slide_content(generated_slide=generated_slide, slide=slide)
            self._style_content_slide(generated_slide)
            self._add_logo(generated_slide)

        presentation.save(output_path)

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

    def _write_title_slide_content(self, *, title_slide, title_text: str, subtitle_text: str) -> None:
        title_box = title_slide.shapes.add_textbox(Inches(0.9), Inches(0.85), Inches(11.0), Inches(1.1))
        title_frame = title_box.text_frame
        title_frame.clear()
        title_paragraph = title_frame.paragraphs[0]
        title_paragraph.text = title_text
        title_paragraph.font.name = "Calibri"
        title_paragraph.font.bold = True
        title_paragraph.font.size = Pt(44)
        title_paragraph.font.color.rgb = RGBColor(177, 18, 35)

        subtitle_box = title_slide.shapes.add_textbox(Inches(0.95), Inches(2.05), Inches(10.5), Inches(1.0))
        subtitle_frame = subtitle_box.text_frame
        subtitle_frame.clear()
        subtitle_paragraph = subtitle_frame.paragraphs[0]
        subtitle_paragraph.text = subtitle_text
        subtitle_paragraph.font.name = "Calibri"
        subtitle_paragraph.font.size = Pt(22)
        subtitle_paragraph.font.color.rgb = RGBColor(60, 60, 60)

    def _write_content_slide_content(self, *, generated_slide, slide: GeneratedSlide) -> None:
        title_box = generated_slide.shapes.add_textbox(Inches(0.75), Inches(0.55), Inches(11.4), Inches(0.95))
        title_frame = title_box.text_frame
        title_frame.clear()
        title_paragraph = title_frame.paragraphs[0]
        title_paragraph.text = slide.title
        title_paragraph.font.name = "Calibri"
        title_paragraph.font.bold = True
        title_paragraph.font.size = Pt(36)
        title_paragraph.font.color.rgb = RGBColor(177, 18, 35)

        body_box = generated_slide.shapes.add_textbox(Inches(0.9), Inches(1.65), Inches(11.1), Inches(4.7))
        text_frame = body_box.text_frame
        text_frame.clear()
        for index, bullet in enumerate(slide.bullets[:6]):
            paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
            paragraph.text = bullet
            paragraph.level = 0
            paragraph.font.size = Pt(22)
            paragraph.font.name = "Calibri"
            paragraph.font.color.rgb = RGBColor(50, 50, 50)

    def _add_logo(self, slide) -> None:
        if logo_exists():
            slide.shapes.add_picture(str(LOGO_PATH), Inches(10.9), Inches(0.2), width=Inches(1.5))

    def _style_title_slide(self, slide) -> None:
        title_shape = slide.shapes.title
        if title_shape and title_shape.has_text_frame:
            for paragraph in title_shape.text_frame.paragraphs:
                paragraph.font.name = "Calibri"
                paragraph.font.bold = True
                paragraph.font.size = Pt(42)
                paragraph.font.color.rgb = RGBColor(177, 18, 35)

    def _style_content_slide(self, slide) -> None:
        _ = slide
