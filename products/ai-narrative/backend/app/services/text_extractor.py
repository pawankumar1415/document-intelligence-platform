"""text_extractor.py — Extract plain text from uploaded files (DOCX, PDF, TXT)."""
from __future__ import annotations

from pathlib import Path


def extract_text(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        return content.decode("utf-8", errors="replace").strip()

    if ext == ".docx":
        try:
            import docx
            from io import BytesIO
            doc = docx.Document(BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)
        except ImportError as exc:
            raise RuntimeError(
                "python-docx is not installed. Run: pip install python-docx"
            ) from exc

    if ext == ".pdf":
        from io import BytesIO
        try:
            import pdfplumber
            with pdfplumber.open(BytesIO(content)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages).strip()
        except ImportError:
            pass
        try:
            import pypdf
            reader = pypdf.PdfReader(BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages).strip()
        except ImportError as exc:
            raise RuntimeError(
                "No PDF library found. Run: pip install pdfplumber  or  pip install pypdf"
            ) from exc

    raise ValueError(
        f"Unsupported file type '{ext}'. Accepted: .txt, .docx, .pdf"
    )