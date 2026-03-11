from __future__ import annotations

from pptx import Presentation

from backend.app.models.schemas import GeneratePptxRequest, GenerateResult, GeneratedSlide
from backend.app.services.file_utils import build_output_path
from backend.app.services.text_utils import build_section_candidates


class PptGenerator:
    def generate(self, request: GeneratePptxRequest) -> GenerateResult:
        slides = self._build_slides(request)
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

    def _build_slides(self, request: GeneratePptxRequest) -> list[GeneratedSlide]:
        candidates = build_section_candidates(request.source_document)

        content_slides = [
            GeneratedSlide(title="Executive Summary", bullets=candidates["Project Overview"][:3]),
            GeneratedSlide(title="Scope Highlights", bullets=candidates["Scope"][:3]),
            GeneratedSlide(title="Deliverables", bullets=candidates["Deliverables"][:3]),
            GeneratedSlide(title="Timeline and Risks", bullets=(candidates["Timeline"] + candidates["Risks"])[:3]),
        ]
        return content_slides[: request.max_content_slides]

    def _write_presentation(self, *, output_path: str, request: GeneratePptxRequest, slides: list[GeneratedSlide]) -> None:
        presentation = Presentation()

        title_layout = presentation.slide_layouts[0]
        title_slide = presentation.slides.add_slide(title_layout)
        title_slide.shapes.title.text = request.deck_title
        subtitle_placeholder = title_slide.placeholders[1]
        subtitle_placeholder.text = request.subtitle or request.source_document.title

        bullet_layout = presentation.slide_layouts[1]
        for slide in slides:
            generated_slide = presentation.slides.add_slide(bullet_layout)
            generated_slide.shapes.title.text = slide.title
            text_frame = generated_slide.placeholders[1].text_frame
            text_frame.clear()

            for index, bullet in enumerate(slide.bullets):
                paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
                paragraph.text = bullet

        presentation.save(output_path)
