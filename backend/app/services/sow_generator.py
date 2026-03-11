from __future__ import annotations

from docx import Document

from backend.app.models.schemas import GenerateResult, GenerateSowRequest, GeneratedSection
from backend.app.services.file_utils import build_output_path
from backend.app.services.text_utils import build_section_candidates


class SowGenerator:
    def generate(self, request: GenerateSowRequest) -> GenerateResult:
        sections = self._build_sections(request)
        output_path = build_output_path("sow", "docx")
        self._write_docx(output_path=str(output_path), request=request, sections=sections)
        artifact_name = output_path.name

        summary = f"SOW draft generated for {request.client_name} / {request.project_name}"
        return GenerateResult(
            artifact_type="sow",
            file_path=str(output_path),
            artifact_name=artifact_name,
            download_url=f"/api/v1/artifacts/{artifact_name}",
            summary=summary,
            sections=sections,
        )

    def _build_sections(self, request: GenerateSowRequest) -> list[GeneratedSection]:
        candidates = build_section_candidates(request.source_document)

        sections = [
            GeneratedSection(
                title="Project Overview",
                paragraphs=[
                    f"This Statement of Work outlines the engagement for {request.project_name} for {request.client_name}.",
                    *candidates["Project Overview"][:2],
                ],
            ),
            GeneratedSection(
                title="Scope of Work",
                bullets=candidates["Scope"][:3],
            ),
            GeneratedSection(
                title="Deliverables",
                bullets=candidates["Deliverables"][:3],
            ),
            GeneratedSection(
                title="Indicative Timeline",
                bullets=candidates["Timeline"][:3] or ["Timeline to be confirmed during project planning."],
            ),
            GeneratedSection(
                title="Assumptions and Risks",
                bullets=(request.assumptions or []) + candidates["Risks"][:3] or ["Dependencies and assumptions will be validated during discovery."],
            ),
        ]
        return sections

    def _write_docx(self, *, output_path: str, request: GenerateSowRequest, sections: list[GeneratedSection]) -> None:
        document = Document()
        document.add_heading(f"Statement of Work - {request.project_name}", level=0)
        document.add_paragraph(f"Client: {request.client_name}")
        document.add_paragraph(f"Source Document: {request.source_document.title}")

        for section in sections:
            document.add_heading(section.title, level=1)
            for paragraph in section.paragraphs:
                document.add_paragraph(paragraph)
            for bullet in section.bullets:
                document.add_paragraph(bullet, style="List Bullet")

        document.save(output_path)
