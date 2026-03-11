from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi import UploadFile

from backend.app.models.schemas import ParsedDocument, ParsedSection


class DocumentParser:
    async def parse_upload(self, upload_file: UploadFile) -> ParsedDocument:
        suffix = Path(upload_file.filename or "").suffix.lower()
        raw_bytes = await upload_file.read()

        if suffix == ".txt":
            return self._parse_txt(upload_file.filename or "document.txt", raw_bytes)
        if suffix == ".docx":
            return self._parse_docx(upload_file.filename or "document.docx", raw_bytes)

        raise ValueError("Only .txt and .docx files are supported in this first implementation.")

    def _parse_txt(self, filename: str, raw_bytes: bytes) -> ParsedDocument:
        text = raw_bytes.decode("utf-8", errors="ignore").replace("\r\n", "\n")
        paragraphs = [item.strip() for item in text.split("\n\n") if item.strip()]
        sections = [ParsedSection(heading=f"Section {index}", body=paragraph) for index, paragraph in enumerate(paragraphs, start=1)]
        return self._build_document(filename=filename, file_type="txt", title=Path(filename).stem, text=text, sections=sections)

    def _parse_docx(self, filename: str, raw_bytes: bytes) -> ParsedDocument:
        document = Document(BytesIO(raw_bytes))

        sections: list[ParsedSection] = []
        full_paragraphs: list[str] = []
        current_heading = Path(filename).stem
        current_body: list[str] = []

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue

            full_paragraphs.append(text)
            style_name = paragraph.style.name.lower() if paragraph.style and paragraph.style.name else ""

            if style_name.startswith("heading"):
                if current_body:
                    sections.append(ParsedSection(heading=current_heading, body="\n".join(current_body)))
                    current_body = []
                current_heading = text
                continue

            current_body.append(text)

        if current_body:
            sections.append(ParsedSection(heading=current_heading, body="\n".join(current_body)))

        if not sections and full_paragraphs:
            sections = [ParsedSection(heading=Path(filename).stem, body="\n".join(full_paragraphs))]

        return self._build_document(
            filename=filename,
            file_type="docx",
            title=Path(filename).stem,
            text="\n".join(full_paragraphs),
            sections=sections,
        )

    def _build_document(
        self,
        *,
        filename: str,
        file_type: str,
        title: str,
        text: str,
        sections: list[ParsedSection],
    ) -> ParsedDocument:
        paragraph_count = sum(1 for block in text.splitlines() if block.strip())
        word_count = len(text.split())
        return ParsedDocument(
            filename=filename,
            file_type=file_type,
            title=title,
            text=text.strip(),
            sections=sections,
            word_count=word_count,
            paragraph_count=paragraph_count,
        )
