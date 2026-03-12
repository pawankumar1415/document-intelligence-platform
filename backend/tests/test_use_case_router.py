from backend.app.models.schemas import DocumentInput, ParsedDocument
from backend.app.services.use_case_router import screen_document_for_supported_use_cases


def test_screening_questions_document_is_rejected() -> None:
    document = ParsedDocument(
        filename="screening_questions.docx",
        file_type="docx",
        title="Screening Questions - Python for Machine Learning",
        text=(
            "Q1. Can you describe your machine learning experience? "
            "Q2. Is this position acceptable to you? "
            "Q3. Expected salary and notice period."
        ),
        sections=[],
        word_count=44,
        paragraph_count=3,
    )

    result = screen_document_for_supported_use_cases(document)

    assert result.is_supported is False
    assert any("recruitment/interview" in reason for reason in result.reasons)


def test_project_scope_document_is_supported() -> None:
    document = DocumentInput(
        title="Statement of Work Draft Notes",
        text=(
            "This project scope includes deliverables, timeline, and assumptions. "
            "The statement of work will define milestones, reporting, and acceptance criteria. "
            "Business requirements include data migration, analytics dashboard, and governance checks."
        ),
        sections=[],
    )

    result = screen_document_for_supported_use_cases(document)

    assert result.is_supported is True
    assert "sow_generation" in result.matched_use_cases
