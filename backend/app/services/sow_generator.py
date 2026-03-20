from __future__ import annotations

import re
from datetime import datetime, timezone

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from backend.app.models.schemas import GenerateResult, GenerateSowRequest, GeneratedSection
from backend.app.services.branding import (
    BSBI_DARK_GREY,
    BSBI_MID_GREY,
    BSBI_RED,
    FONT_FAMILY,
    LOGO_PATH,
    add_header_footer,
    add_horizontal_rule,
    add_styled_table,
    apply_docx_styles,
    logo_exists,
)
from backend.app.services.file_utils import build_output_path
from backend.app.services.llm_provider import generate_json_object
from backend.app.services.text_utils import build_section_candidates


# ── Prompt templates ───────────────────────────────────────────────────────

SOW_SYSTEM_PROMPT = """\
You are a senior management consultant at a Big-4 firm drafting a Statement of Work.

Rules:
- Write in a professional, confident, and concise consulting tone.
- Every paragraph MUST be 2-3 sentences. No filler. No generic platitudes.
- Bullets MUST be actionable, specific, and under 20 words each.
- Ground every claim in the source material provided. If information is missing, write "To be confirmed during discovery" — never invent facts.
- Return ONLY valid JSON. No markdown, no commentary outside JSON.
"""

SOW_USER_PROMPT_TEMPLATE = """\
Return ONLY JSON matching this schema exactly:
{{
  "meta": {{
    "prepared_by": "BSBI Consulting",
    "date": "{today}",
    "version": "Draft 1.0"
  }},
  "sections": [
    {{
      "title": "string",
      "paragraphs": ["string"],
      "bullets": ["string"],
      "table_rows": [["col1", "col2", "col3"]]
    }}
  ]
}}

Generate 8 sections in this order:
1. Executive Summary — 2 paragraphs, no bullets
2. Project Objectives — 1 paragraph, 4-6 bullets listing measurable objectives
3. Scope of Work — 1 paragraph defining boundaries, 4-6 bullets for in-scope items
4. Solution Approach — 2 paragraphs on methodology and architecture, 3-4 bullets
5. Deliverables — 1 paragraph, then table_rows with columns ["Deliverable", "Description"] for 4-6 deliverables
6. Timeline and Milestones — 1 paragraph, then table_rows with columns ["Phase", "Activities", "Duration"] for 3-5 phases
7. Assumptions and Dependencies — no paragraphs, 5-8 bullets
8. Governance and Success Criteria — 1 paragraph on governance, 3-5 bullets on success metrics

Client: {client_name}
Project: {project_name}
Assumptions provided: {assumptions}

Source content:
{context_blob}
"""


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

    # ── Section building ───────────────────────────────────────────────────

    def _build_sections(self, request: GenerateSowRequest, retrieval_context: list[str]) -> list[GeneratedSection]:
        llm_sections = self._build_sections_from_llm(request, retrieval_context)
        if llm_sections:
            return llm_sections

        # Fallback: keyword-heuristic path
        candidates = build_section_candidates(request.source_document)

        sections = [
            GeneratedSection(
                title="Executive Summary",
                paragraphs=[
                    f"This Statement of Work outlines the engagement between BSBI Consulting and {request.client_name} for the {request.project_name} initiative.",
                    *self._prepare_lines(candidates["Project Overview"][:3], limit=3, char_limit=320),
                ],
            ),
            GeneratedSection(
                title="Project Objectives",
                paragraphs=[
                    f"The following objectives have been identified for {request.project_name} based on initial discovery and stakeholder input.",
                ],
                bullets=self._prepare_lines(candidates["Project Overview"][:5], limit=5, char_limit=180),
            ),
            GeneratedSection(
                title="Scope of Work",
                paragraphs=[
                    "The scope of this engagement covers the following workstreams and deliverables.",
                ],
                bullets=self._prepare_lines(candidates["Scope"][:5], limit=5, char_limit=180),
            ),
            GeneratedSection(
                title="Solution Approach",
                paragraphs=self._prepare_lines(candidates["Scope"][:3], limit=3, char_limit=320),
                bullets=self._prepare_lines(candidates["Deliverables"][:4], limit=4, char_limit=180),
            ),
            GeneratedSection(
                title="Deliverables",
                paragraphs=[
                    "The table below summarises the key deliverables for this engagement.",
                ],
                bullets=self._prepare_lines(candidates["Deliverables"][:5], limit=5, char_limit=180),
                table_rows=[
                    [d, "To be confirmed during project planning."]
                    for d in self._prepare_lines(candidates["Deliverables"][:4], limit=4, char_limit=80)
                ],
            ),
            GeneratedSection(
                title="Timeline and Milestones",
                paragraphs=[
                    "The indicative timeline below outlines the major phases of delivery.",
                ],
                bullets=self._prepare_lines(candidates["Timeline"][:4], limit=4, char_limit=180)
                or ["Timeline to be confirmed during project planning."],
                table_rows=[
                    [f"Phase {i+1}", t, "TBC"]
                    for i, t in enumerate(self._prepare_lines(candidates["Timeline"][:4], limit=4, char_limit=80))
                ] or [["Phase 1", "Discovery and planning", "TBC"]],
            ),
            GeneratedSection(
                title="Assumptions and Dependencies",
                bullets=self._prepare_lines(
                    (request.assumptions or []) + candidates["Risks"][:5],
                    limit=7,
                    char_limit=180,
                )
                or ["Dependencies and assumptions will be validated during discovery."],
            ),
            GeneratedSection(
                title="Governance and Success Criteria",
                paragraphs=[
                    "Governance checkpoints, quality criteria, and stakeholder approvals will be agreed at project kickoff.",
                ],
                bullets=self._prepare_lines(candidates["Risks"][:4], limit=4, char_limit=180)
                or ["Success metrics to be defined during discovery phase."],
            ),
        ]
        return sections

    def _build_sections_from_llm(
        self,
        request: GenerateSowRequest,
        retrieval_context: list[str],
    ) -> list[GeneratedSection] | None:
        context_blob = self._build_context_blob(request.source_document.text, retrieval_context)
        today = datetime.now(timezone.utc).strftime("%d %B %Y")

        user_prompt = SOW_USER_PROMPT_TEMPLATE.format(
            today=today,
            client_name=request.client_name,
            project_name=request.project_name,
            assumptions="; ".join(request.assumptions) if request.assumptions else "None provided",
            context_blob=context_blob,
        )

        try:
            payload = generate_json_object(
                provider=request.llm_provider,
                model=request.llm_model,
                system_prompt=SOW_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
            )
            sections_payload = payload.get("sections", [])
            sections: list[GeneratedSection] = []
            for item in sections_payload:
                title = str(item.get("title", "")).strip()
                if not title:
                    continue
                paragraphs = self._prepare_lines(
                    [str(p).strip() for p in item.get("paragraphs", []) if str(p).strip()],
                    limit=4,
                    char_limit=400,
                )
                bullets = self._prepare_lines(
                    [str(b).strip() for b in item.get("bullets", []) if str(b).strip()],
                    limit=8,
                    char_limit=200,
                )
                table_rows = [
                    [str(cell).strip() for cell in row]
                    for row in item.get("table_rows", [])
                    if isinstance(row, list) and any(str(c).strip() for c in row)
                ]
                sections.append(
                    GeneratedSection(
                        title=self._clean_title(title),
                        paragraphs=paragraphs,
                        bullets=bullets,
                        table_rows=table_rows,
                    )
                )
            return sections or None
        except Exception:
            return None

    # ── DOCX writing ───────────────────────────────────────────────────────

    def _write_docx(self, *, output_path: str, request: GenerateSowRequest, sections: list[GeneratedSection]) -> None:
        document = Document()
        apply_docx_styles(document)
        add_header_footer(document)

        # ── Cover page ─────────────────────────────────────────────────────
        self._write_cover_page(document, request)

        # ── Table of Contents placeholder ──────────────────────────────────
        self._insert_toc(document)

        # ── Document metadata block ────────────────────────────────────────
        self._write_metadata_block(document, request)

        # ── Sections ───────────────────────────────────────────────────────
        for section in sections:
            heading = document.add_heading(section.title, level=1)
            heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_horizontal_rule(document)

            for paragraph_text in section.paragraphs:
                p = document.add_paragraph(paragraph_text)
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            for bullet in section.bullets:
                document.add_paragraph(bullet, style="List Bullet")

            # Tables
            if section.table_rows:
                table_title = section.title.lower()
                if "deliverable" in table_title:
                    add_styled_table(document, ["Deliverable", "Description"], section.table_rows)
                elif "timeline" in table_title or "milestone" in table_title:
                    add_styled_table(document, ["Phase", "Activities", "Duration"], section.table_rows)
                else:
                    headers = [f"Column {i+1}" for i in range(len(section.table_rows[0]))]
                    add_styled_table(document, headers, section.table_rows)

        # ── Sign-off block ─────────────────────────────────────────────────
        self._write_signoff_block(document)

        document.save(output_path)

    def _write_cover_page(self, document: Document, request: GenerateSowRequest) -> None:
        """Build a branded cover page with logo, title, client, date, and confidentiality."""
        # Spacing before logo
        for _ in range(3):
            document.add_paragraph("")

        # Logo
        if logo_exists():
            logo_para = document.add_paragraph()
            logo_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = logo_para.add_run()
            run.add_picture(str(LOGO_PATH), width=Inches(2.2))

        document.add_paragraph("")

        # Title
        title_para = document.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_para.add_run("Statement of Work")
        run.font.name = FONT_FAMILY
        run.font.size = Pt(28)
        run.font.bold = True
        run.font.color.rgb = BSBI_RED

        # Project name
        proj_para = document.add_paragraph()
        proj_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = proj_para.add_run(request.project_name)
        run.font.name = FONT_FAMILY
        run.font.size = Pt(18)
        run.font.color.rgb = BSBI_DARK_GREY

        # Client
        client_para = document.add_paragraph()
        client_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = client_para.add_run(f"Prepared for: {request.client_name}")
        run.font.name = FONT_FAMILY
        run.font.size = Pt(13)
        run.font.color.rgb = BSBI_MID_GREY

        # Date
        date_para = document.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = date_para.add_run(datetime.now(timezone.utc).strftime("%d %B %Y"))
        run.font.name = FONT_FAMILY
        run.font.size = Pt(12)
        run.font.color.rgb = BSBI_MID_GREY

        # Spacer
        for _ in range(4):
            document.add_paragraph("")

        # Confidentiality notice
        conf_para = document.add_paragraph()
        conf_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = conf_para.add_run(
            "CONFIDENTIAL — This document contains proprietary information intended solely for the named recipient. "
            "Unauthorised distribution is prohibited."
        )
        run.font.name = FONT_FAMILY
        run.font.size = Pt(9)
        run.font.italic = True
        run.font.color.rgb = BSBI_MID_GREY

        # Page break after cover
        document.add_page_break()

    def _insert_toc(self, document: Document) -> None:
        """Insert a Table of Contents field that Word will populate on open."""
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        toc_heading = document.add_heading("Table of Contents", level=1)
        toc_heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
        add_horizontal_rule(document)

        paragraph = document.add_paragraph()
        run = paragraph.add_run()
        fld_char_begin = OxmlElement("w:fldChar")
        fld_char_begin.set(qn("w:fldCharType"), "begin")
        run._r.append(fld_char_begin)

        instr_text = OxmlElement("w:instrText")
        instr_text.set(qn("xml:space"), "preserve")
        instr_text.text = ' TOC \\o "1-2" \\h \\z \\u '
        run._r.append(instr_text)

        fld_char_separate = OxmlElement("w:fldChar")
        fld_char_separate.set(qn("w:fldCharType"), "separate")
        run._r.append(fld_char_separate)

        # Placeholder text shown before TOC is updated
        placeholder_run = paragraph.add_run("Right-click and select 'Update Field' to populate this table of contents.")
        placeholder_run.font.size = Pt(10)
        placeholder_run.font.color.rgb = BSBI_MID_GREY
        placeholder_run.font.name = FONT_FAMILY

        fld_char_end = OxmlElement("w:fldChar")
        fld_char_end.set(qn("w:fldCharType"), "end")
        placeholder_run._r.append(fld_char_end)

        document.add_page_break()

    def _write_metadata_block(self, document: Document, request: GenerateSowRequest) -> None:
        """Add a document information table at the start of the body."""
        today = datetime.now(timezone.utc).strftime("%d %B %Y")
        add_styled_table(
            document,
            ["Field", "Detail"],
            [
                ["Document Title", f"Statement of Work — {request.project_name}"],
                ["Client", request.client_name],
                ["Prepared By", "BSBI Consulting"],
                ["Date", today],
                ["Version", "Draft 1.0"],
                ["Classification", "Confidential"],
            ],
        )

    def _write_signoff_block(self, document: Document) -> None:
        """Add a sign-off / approval table at the end of the document."""
        document.add_heading("Approval and Sign-Off", level=1)
        add_horizontal_rule(document)
        document.add_paragraph(
            "This Statement of Work is approved by the undersigned representatives of both parties."
        )
        add_styled_table(
            document,
            ["Role", "Name", "Signature", "Date"],
            [
                ["Client Representative", "", "", ""],
                ["BSBI Engagement Lead", "", "", ""],
                ["BSBI Delivery Lead", "", "", ""],
            ],
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    def _build_context_blob(self, source_text: str, retrieval_context: list[str]) -> str:
        source = source_text[:8000]
        retrieval = "\n".join(chunk[:800] for chunk in retrieval_context[:5] if chunk.strip())
        return "\n\n".join(part for part in [source, retrieval] if part)

    def _prepare_lines(self, lines: list[str], *, limit: int, char_limit: int) -> list[str]:
        prepared: list[str] = []
        for line in lines:
            cleaned = re.sub(r"\s+", " ", line).strip()
            cleaned = re.sub(r"^[\d\-\.\)\(]+\s*", "", cleaned)
            cleaned = cleaned.replace("•", " ").strip(" -")
            if len(cleaned) > char_limit:
                cleaned = f"{cleaned[: char_limit - 3].rstrip()}..."
            if cleaned and cleaned not in prepared:
                prepared.append(cleaned)
            if len(prepared) >= limit:
                break
        return prepared

    def _clean_title(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if len(cleaned) > 70:
            return f"{cleaned[:67].rstrip()}..."
        return cleaned
