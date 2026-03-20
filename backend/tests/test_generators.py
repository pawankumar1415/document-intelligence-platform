from pathlib import Path

import pytest

from backend.app.models.schemas import (
    DocumentInput,
    GeneratePptxRequest,
    GenerateSowRequest,
    ParsedSection,
)
from backend.app.services.document_parser import DocumentParser
from backend.app.services.ppt_generator import PptGenerator
from backend.app.services.sow_generator import SowGenerator


def sample_document() -> DocumentInput:
    return DocumentInput(
        title="Sample Discovery Notes",
        text=(
            "Project overview: Build a document intelligence platform for internal teams. "
            "The scope includes docx and txt parsing, SOW generation, and PPT deck creation. "
            "Deliverables include an API, editable documents, and a presentation draft. "
            "The timeline is a two-week prototype followed by iterative hardening. "
            "A key risk is inconsistent source document structure."
        ),
        sections=[
            ParsedSection(heading="Overview", body="Build a document intelligence platform for internal teams."),
            ParsedSection(heading="Scope", body="Support docx and txt parsing, SOW generation, and PPT deck creation."),
        ],
    )


def test_txt_parser_creates_sections() -> None:
    parser = DocumentParser()
    parsed = parser._parse_txt("notes.txt", b"Alpha paragraph.\n\nBeta paragraph.")

    assert parsed.file_type == "txt"
    assert len(parsed.sections) == 2
    assert parsed.sections[0].heading == "Section 1"


def test_docx_parser_rejects_invalid_docx() -> None:
    parser = DocumentParser()
    with pytest.raises(ValueError, match="invalid or corrupted"):
        parser._parse_docx("broken.docx", b"this-is-not-a-valid-docx")


def test_sow_generator_writes_docx() -> None:
    generator = SowGenerator()
    result = generator.generate(
        GenerateSowRequest(
            client_name="Acme Corp",
            project_name="Document Intelligence Pilot",
            source_document=sample_document(),
            assumptions=["Client will provide sample documents before kickoff."],
        )
    )

    output_path = Path(result.file_path)
    assert output_path.exists()
    assert result.sections
    titles = {section.title for section in result.sections}
    # New structure has 8 sections + sign-off added in docx (sign-off is docx-only, not in sections list)
    assert "Executive Summary" in titles
    assert "Scope of Work" in titles
    assert "Deliverables" in titles
    assert "Timeline and Milestones" in titles
    assert "Assumptions and Dependencies" in titles
    assert len(result.sections) >= 8

    # Verify docx contains tables (deliverables + timeline + metadata + sign-off)
    from docx import Document
    doc = Document(str(output_path))
    assert len(doc.tables) >= 2, f"Expected at least 2 tables, got {len(doc.tables)}"


def test_ppt_generator_writes_pptx() -> None:
    generator = PptGenerator()
    result = generator.generate(
        GeneratePptxRequest(
            deck_title="Document Intelligence Pilot",
            subtitle="Kickoff Summary",
            source_document=sample_document(),
        )
    )

    output_path = Path(result.file_path)
    assert output_path.exists()
    assert result.slides
    # First slide from data should be the section divider
    assert result.slides[0].slide_type == "section_divider"
    assert result.slides[0].title == "Executive Overview"
    # Should have a closing slide
    closing_slides = [s for s in result.slides if s.slide_type == "closing"]
    assert len(closing_slides) >= 1
    # Should have at least one two-column slide
    two_col_slides = [s for s in result.slides if s.slide_type == "two_column"]
    assert len(two_col_slides) >= 1


def test_ppt_generator_has_accent_shapes() -> None:
    """Verify pptx output has accent bar shapes on content slides."""
    from pptx import Presentation

    generator = PptGenerator()
    result = generator.generate(
        GeneratePptxRequest(
            deck_title="Test Deck",
            subtitle="Accent Bar Test",
            source_document=sample_document(),
            max_content_slides=4,
        )
    )

    prs = Presentation(result.file_path)
    # At least some slides should have shapes (accent bars, text boxes)
    total_shapes = sum(len(slide.shapes) for slide in prs.slides)
    # Each slide has at minimum: logo + accent bar + title textbox = 3 shapes
    assert total_shapes >= len(prs.slides) * 2
