from __future__ import annotations

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import PP_PLACEHOLDER
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
            "Generate concise slide titles and max 3 bullets each.\n\n"
            f"Deck title: {request.deck_title}\n"
            f"Subtitle: {request.subtitle or ''}\n"
            f"Source:\n{context_blob}"
        )

        try:
            payload = generate_json_object(
                provider=request.llm_provider,
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
                slides.append(GeneratedSlide(title=title, bullets=bullets[:3]))
            return slides or None
        except Exception:
            return None

    def _write_presentation(self, *, output_path: str, request: GeneratePptxRequest, slides: list[GeneratedSlide]) -> None:
        presentation = Presentation(str(PPT_TEMPLATE_PATH)) if ppt_template_exists() else Presentation()

        title_layout = presentation.slide_layouts[0]
        title_slide = presentation.slides.add_slide(title_layout)
        title_slide.shapes.title.text = request.deck_title
        subtitle = request.subtitle or request.source_document.title
        for shape in title_slide.placeholders:
            if shape.is_placeholder and shape.placeholder_format.type == PP_PLACEHOLDER.SUBTITLE:
                shape.text = subtitle
                break
        self._style_title_slide(title_slide)
        self._add_logo(title_slide)

        bullet_layout = presentation.slide_layouts[1]
        for slide in slides:
            generated_slide = presentation.slides.add_slide(bullet_layout)
            generated_slide.shapes.title.text = slide.title
            body_placeholder = None
            for shape in generated_slide.placeholders:
                if shape.is_placeholder and shape.placeholder_format.type == PP_PLACEHOLDER.BODY:
                    body_placeholder = shape
                    break
            if body_placeholder is None:
                textbox = generated_slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.5), Inches(4.6))
                text_frame = textbox.text_frame
            else:
                text_frame = body_placeholder.text_frame
            text_frame.clear()

            for index, bullet in enumerate(slide.bullets):
                paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
                paragraph.text = bullet
                paragraph.font.size = Pt(20)
                paragraph.font.name = "Calibri"
                paragraph.font.color.rgb = RGBColor(50, 50, 50)
            self._style_content_slide(generated_slide)
            self._add_logo(generated_slide)

        presentation.save(output_path)

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
        title_shape = slide.shapes.title
        if title_shape and title_shape.has_text_frame:
            for paragraph in title_shape.text_frame.paragraphs:
                paragraph.font.name = "Calibri"
                paragraph.font.bold = True
                paragraph.font.size = Pt(34)
                paragraph.font.color.rgb = RGBColor(177, 18, 35)
