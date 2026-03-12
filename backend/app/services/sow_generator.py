from __future__ import annotations

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from backend.app.models.schemas import GenerateResult, GenerateSowRequest, GeneratedSection
from backend.app.services.branding import LOGO_PATH, logo_exists
from backend.app.services.file_utils import build_output_path
from backend.app.services.llm_provider import generate_json_object
from backend.app.services.text_utils import build_section_candidates


class SowGenerator:
    def generate(self, request: GenerateSowRequest, retrieval_context: list[str] | None = None) -> GenerateResult:
        sections = self._build_sections(request, retrieval_context=retrieval_context or [])
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

    def _build_sections(self, request: GenerateSowRequest, retrieval_context: list[str]) -> list[GeneratedSection]:
        llm_sections = self._build_sections_from_llm(request, retrieval_context)
        if llm_sections:
            return llm_sections

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

    def _build_sections_from_llm(
        self,
        request: GenerateSowRequest,
        retrieval_context: list[str],
    ) -> list[GeneratedSection] | None:
        context_blob = "\n\n".join(
            [request.source_document.text[:6000], *retrieval_context[:5]]
        )

        system_prompt = (
            "You are a senior consulting proposal writer. "
            "Generate concise, professional SOW content in strict JSON."
        )
        user_prompt = (
            "Return ONLY JSON in this shape: "
            '{"sections":[{"title":"string","paragraphs":["string"],"bullets":["string"]}]}. '
            "Create sections for: Project Overview, Scope of Work, Deliverables, Indicative Timeline, "
            "Assumptions and Risks. Use no markdown.\n\n"
            f"Client: {request.client_name}\n"
            f"Project: {request.project_name}\n"
            f"Assumptions: {request.assumptions}\n\n"
            f"Source content:\n{context_blob}"
        )

        try:
            payload = generate_json_object(
                provider=request.llm_provider,
                model=request.llm_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
            )
            sections_payload = payload.get("sections", [])
            sections: list[GeneratedSection] = []
            for item in sections_payload:
                title = str(item.get("title", "")).strip()
                if not title:
                    continue
                paragraphs = [str(p).strip() for p in item.get("paragraphs", []) if str(p).strip()]
                bullets = [str(b).strip() for b in item.get("bullets", []) if str(b).strip()]
                sections.append(GeneratedSection(title=title, paragraphs=paragraphs, bullets=bullets))
            return sections or None
        except Exception:
            return None

    def _write_docx(self, *, output_path: str, request: GenerateSowRequest, sections: list[GeneratedSection]) -> None:
        document = Document()
        self._apply_branding(document)

        if logo_exists():
            logo_para = document.add_paragraph()
            logo_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            run = logo_para.add_run()
            run.add_picture(str(LOGO_PATH), width=Inches(1.7))

        title = document.add_heading(f"Statement of Work - {request.project_name}", level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.LEFT
        subtitle = document.add_paragraph(f"Client: {request.client_name}")
        subtitle.runs[0].font.size = Pt(11)
        subtitle.runs[0].font.color.rgb = RGBColor(74, 74, 74)

        source_info = document.add_paragraph(f"Source Document: {request.source_document.title}")
        source_info.runs[0].font.size = Pt(10)
        source_info.runs[0].font.color.rgb = RGBColor(120, 120, 120)
        document.add_paragraph("")

        for section in sections:
            document.add_heading(section.title, level=1)
            for paragraph in section.paragraphs:
                document.add_paragraph(paragraph)
            for bullet in section.bullets:
                document.add_paragraph(bullet, style="List Bullet")

        document.save(output_path)

    def _apply_branding(self, document: Document) -> None:
        normal_style = document.styles["Normal"]
        normal_style.font.name = "Calibri"
        normal_style.font.size = Pt(11)

        heading_one = document.styles["Heading 1"]
        heading_one.font.name = "Calibri"
        heading_one.font.size = Pt(16)
        heading_one.font.bold = True
        heading_one.font.color.rgb = RGBColor(177, 18, 35)
