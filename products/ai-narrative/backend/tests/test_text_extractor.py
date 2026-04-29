"""Tests for text_extractor.py — plain text extraction from uploaded files."""
from __future__ import annotations

import io
import pytest

from backend.app.services.text_extractor import extract_text


class TestExtractTxt:
    def test_basic_utf8(self) -> None:
        content = "Hello, world!\nSecond line.".encode("utf-8")
        result = extract_text("file.txt", content)
        assert result == "Hello, world!\nSecond line."

    def test_strips_leading_trailing_whitespace(self) -> None:
        content = "   Some text.   ".encode("utf-8")
        result = extract_text("notes.txt", content)
        assert result == "Some text."

    def test_handles_invalid_utf8_gracefully(self) -> None:
        content = b"Valid text \xff\xfe and more."
        result = extract_text("bad_encoding.txt", content)
        assert "Valid text" in result

    def test_empty_txt_returns_empty_string(self) -> None:
        result = extract_text("empty.txt", b"")
        assert result == ""


class TestExtractDocx:
    def _make_docx(self, paragraphs: list[str]) -> bytes:
        from docx import Document
        doc = Document()
        for para in paragraphs:
            doc.add_paragraph(para)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def test_extracts_paragraphs(self) -> None:
        content = self._make_docx(["First paragraph.", "Second paragraph."])
        result = extract_text("document.docx", content)
        assert "First paragraph." in result
        assert "Second paragraph." in result

    def test_skips_empty_paragraphs(self) -> None:
        content = self._make_docx(["Real content.", "", "More content."])
        result = extract_text("doc.docx", content)
        # Should not contain two consecutive newlines from empty paragraphs
        assert "Real content." in result
        assert "More content." in result

    def test_paragraphs_joined_with_newlines(self) -> None:
        content = self._make_docx(["Line one.", "Line two."])
        result = extract_text("joined.docx", content)
        assert "\n" in result


class TestExtractUnsupported:
    def test_unsupported_extension_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text("data.xlsx", b"fake content")

    def test_csv_extension_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text("data.csv", b"col1,col2\nval1,val2")

    def test_no_extension_raises(self) -> None:
        with pytest.raises(ValueError):
            extract_text("filename_without_ext", b"some content")

    def test_unknown_extension_error_message_includes_extension(self) -> None:
        with pytest.raises(ValueError, match=r"\.xyz"):
            extract_text("file.xyz", b"content")