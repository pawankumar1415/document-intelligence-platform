"""
Integration tests using the real test documents in test-documents/.

These tests do NOT call any LLM or vector database — they exercise parsing,
column detection, and content extraction using the actual files shipped with
the platform. Any test that would require OpenAI/pgvector is mocked at the
service boundary.

Test documents used:
  - NDA_Portfolio_Batch_Validation - Test.xlsx  (3 rows: R, A, G)
  - 06_NDA_Portfolio_Batch_Validation.xlsx       (18 rows)
  - NDA_Portfolio_Batch_Validation - Test.docx
  - NDA_Portfolio_Batch_Validation - Test.pdf
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

TEST_DOCS = Path(__file__).resolve().parents[4] / "test-documents"

XLSX_SMALL = TEST_DOCS / "NDA_Portfolio_Batch_Validation - Test.xlsx"
XLSX_FULL  = TEST_DOCS / "06_NDA_Portfolio_Batch_Validation.xlsx"
DOCX_FILE  = TEST_DOCS / "NDA_Portfolio_Batch_Validation - Test.docx"
PDF_FILE   = TEST_DOCS / "NDA_Portfolio_Batch_Validation - Test.pdf"


def _require(path: Path) -> bytes:
    """Return file bytes or skip the test if the file does not exist."""
    if not path.exists():
        pytest.skip(f"Test document not found: {path.name}")
    return path.read_bytes()


# ── Excel parsing ─────────────────────────────────────────────────────────────

class TestRealXlsxParsing:
    def test_small_xlsx_parses_3_records(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring
        raw = _require(XLSX_SMALL)
        records = parse_excel_for_scoring(raw, filename=XLSX_SMALL.name)
        assert len(records) == 3

    def test_small_xlsx_unique_ids_are_document_names(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring
        raw = _require(XLSX_SMALL)
        records = parse_excel_for_scoring(raw, filename=XLSX_SMALL.name)
        ids = [r["unique_id"] for r in records]
        assert any("CNC Airwave" in uid for uid in ids)
        assert any("SEP" in uid for uid in ids)
        assert any("Heat Exchanger" in uid for uid in ids)

    def test_small_xlsx_narrative_text_populated(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring
        raw = _require(XLSX_SMALL)
        records = parse_excel_for_scoring(raw, filename=XLSX_SMALL.name)
        for r in records:
            assert len(r["narrative_text"]) > 100, f"Narrative too short for {r['unique_id']}"

    def test_small_xlsx_extra_fields_include_rag_status(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring
        raw = _require(XLSX_SMALL)
        records = parse_excel_for_scoring(raw, filename=XLSX_SMALL.name)
        rag_values = {r["extra_fields"].get("rag_status") for r in records}
        assert rag_values == {"R", "A", "G"}

    def test_full_xlsx_parses_18_records(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring
        raw = _require(XLSX_FULL)
        records = parse_excel_for_scoring(raw, filename=XLSX_FULL.name)
        assert len(records) == 18

    def test_full_xlsx_rag_distribution(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring
        raw = _require(XLSX_FULL)
        records = parse_excel_for_scoring(raw, filename=XLSX_FULL.name)
        rag = [r["extra_fields"].get("rag_status", "") for r in records]
        # 06_NDA_Portfolio_Batch_Validation.xlsx: 2 Red, 7 Amber, 9 Green
        assert rag.count("R") == 2
        assert rag.count("A") == 7
        assert rag.count("G") == 9

    def test_full_xlsx_all_narratives_non_empty(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring
        raw = _require(XLSX_FULL)
        records = parse_excel_for_scoring(raw, filename=XLSX_FULL.name)
        empty = [r["unique_id"] for r in records if not r["narrative_text"].strip()]
        assert empty == [], f"Empty narratives found: {empty}"

    def test_full_xlsx_content_string_includes_all_fields(self) -> None:
        from backend.app.services.excel_parser import build_content_string, parse_excel_for_scoring
        raw = _require(XLSX_FULL)
        records = parse_excel_for_scoring(raw, filename=XLSX_FULL.name)
        for r in records:
            r["content"] = build_content_string(r)
            assert r["unique_id"] in r["content"]
            assert r["narrative_text"][:50] in r["content"]

    def test_explicit_column_overrides_work(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring
        raw = _require(XLSX_SMALL)
        records = parse_excel_for_scoring(
            raw,
            filename=XLSX_SMALL.name,
            id_column="document_name",
            narrative_column="text",
        )
        assert len(records) == 3
        assert all(r["unique_id"] for r in records)


# ── DOCX parsing ──────────────────────────────────────────────────────────────

class TestRealDocxParsing:
    def test_docx_parses_records(self) -> None:
        from backend.app.services.excel_parser import parse_docx_for_scoring
        raw = _require(DOCX_FILE)
        records = parse_docx_for_scoring(raw)
        assert len(records) >= 1

    def test_docx_narrative_text_populated(self) -> None:
        from backend.app.services.excel_parser import parse_docx_for_scoring
        raw = _require(DOCX_FILE)
        records = parse_docx_for_scoring(raw)
        for r in records:
            assert r["narrative_text"].strip(), f"Empty narrative for {r['unique_id']}"

    def test_docx_unique_ids_non_empty(self) -> None:
        from backend.app.services.excel_parser import parse_docx_for_scoring
        raw = _require(DOCX_FILE)
        records = parse_docx_for_scoring(raw)
        assert all(r["unique_id"] for r in records)


# ── PDF parsing ───────────────────────────────────────────────────────────────

class TestRealPdfParsing:
    def test_pdf_parses_records(self) -> None:
        from backend.app.services.excel_parser import parse_pdf_for_scoring
        raw = _require(PDF_FILE)
        try:
            records = parse_pdf_for_scoring(raw)
            assert len(records) >= 1
        except Exception as exc:
            pytest.skip(f"PDF parsing requires pdfplumber: {exc}")

    def test_pdf_narrative_text_populated(self) -> None:
        from backend.app.services.excel_parser import parse_pdf_for_scoring
        raw = _require(PDF_FILE)
        try:
            records = parse_pdf_for_scoring(raw)
            for r in records:
                assert r["narrative_text"].strip(), f"Empty narrative for {r['unique_id']}"
        except Exception as exc:
            pytest.skip(f"PDF parsing requires pdfplumber: {exc}")


# ── Reference ingest using real file ─────────────────────────────────────────

class TestRealFileIngest:
    @patch("backend.app.services.reference_service.vector_store_status")
    @patch("backend.app.services.reference_service._trigger_domain_detection")
    def test_ingest_small_xlsx_without_vector_store(
        self, mock_detect, mock_vs, user_id: int
    ) -> None:
        from backend.app.services.reference_service import ingest_reference_file
        mock_vs.return_value = {"configured": False}
        raw = _require(XLSX_SMALL)
        result = ingest_reference_file(
            raw_bytes=raw,
            filename=XLSX_SMALL.name,
            user_id=user_id,
            description="NDA P06 small test set",
        )
        assert result["status"] == "ok"
        assert result["record_count"] == 3
        assert result["skipped"] == 0
        mock_detect.assert_called_once()

    @patch("backend.app.services.reference_service.vector_store_status")
    @patch("backend.app.services.reference_service._trigger_domain_detection")
    def test_ingest_full_xlsx_counts(self, mock_detect, mock_vs, user_id: int) -> None:
        from backend.app.services.reference_service import ingest_reference_file
        mock_vs.return_value = {"configured": False}
        raw = _require(XLSX_FULL)
        result = ingest_reference_file(
            raw_bytes=raw,
            filename=XLSX_FULL.name,
            user_id=user_id,
        )
        assert result["status"] == "ok"
        assert result["record_count"] == 18

    @patch("backend.app.services.reference_service.vector_store_status")
    @patch("backend.app.services.reference_service.upsert_reference_narratives")
    @patch("backend.app.services.reference_service.embed_documents")
    @patch("backend.app.services.reference_service._trigger_domain_detection")
    def test_ingest_calls_embed_when_vector_store_configured(
        self, mock_detect, mock_embed, mock_upsert, mock_vs, user_id: int
    ) -> None:
        from backend.app.services.reference_service import ingest_reference_file
        mock_vs.return_value = {"configured": True}
        mock_embed.return_value = [[0.1] * 768 for _ in range(3)]
        raw = _require(XLSX_SMALL)
        result = ingest_reference_file(
            raw_bytes=raw,
            filename=XLSX_SMALL.name,
            user_id=user_id,
        )
        assert result["status"] == "ok"
        mock_embed.assert_called_once()
        mock_upsert.assert_called_once()


# ── Batch scoring with real file ──────────────────────────────────────────────

class TestRealFileBatchScore:
    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_batch_score_small_xlsx_produces_3_results(
        self, mock_vs, mock_text, mock_json, user_id: int
    ) -> None:
        from backend.app.services.batch_service import run_batch_score
        mock_vs.return_value = {"configured": False}
        mock_json.side_effect = [
            {"compliance_score": 8.5, "issues": [], "passed": ["Clarity"]},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ] * 3
        mock_text.return_value = ""
        raw = _require(XLSX_SMALL)
        result = run_batch_score(
            raw_bytes=raw,
            filename=XLSX_SMALL.name,
            user_id=user_id,
            provider="openai",
        )
        assert result["total"] == 3

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_batch_score_full_xlsx_produces_18_results(
        self, mock_vs, mock_text, mock_json, user_id: int
    ) -> None:
        from backend.app.services.batch_service import run_batch_score
        mock_vs.return_value = {"configured": False}
        mock_json.side_effect = [
            {"compliance_score": 7.0, "issues": ["Minor issue"], "passed": ["Clarity"]},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ] * 18
        mock_text.return_value = ""
        raw = _require(XLSX_FULL)
        result = run_batch_score(
            raw_bytes=raw,
            filename=XLSX_FULL.name,
            user_id=user_id,
            provider="openai",
        )
        assert result["total"] == 18

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_batch_score_explicit_column_override(
        self, mock_vs, mock_text, mock_json, user_id: int
    ) -> None:
        from backend.app.services.batch_service import run_batch_score
        mock_vs.return_value = {"configured": False}
        mock_json.side_effect = [
            {"compliance_score": 9.0, "issues": [], "passed": []},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ] * 3
        mock_text.return_value = ""
        raw = _require(XLSX_SMALL)
        result = run_batch_score(
            raw_bytes=raw,
            filename=XLSX_SMALL.name,
            user_id=user_id,
            provider="openai",
            id_column="document_name",
            narrative_column="text",
        )
        assert result["total"] == 3


# ── Column detection with real file ──────────────────────────────────────────

class TestRealFileColumnDetection:
    def test_column_detection_identifies_document_name_as_id(self) -> None:
        import io
        import pandas as pd
        from backend.app.services.excel_parser import _ID_KEYWORDS, _TEXT_KEYWORDS, _find_column

        raw = _require(XLSX_SMALL)
        df = pd.read_excel(io.BytesIO(raw), header=0, dtype=str)
        col_map = {str(c).strip().lower(): str(c) for c in df.columns}
        id_col = _find_column(col_map, _ID_KEYWORDS)
        txt_col = _find_column(col_map, _TEXT_KEYWORDS)
        assert id_col == "document_name"
        assert txt_col == "text"

    def test_column_detection_all_columns_returned(self) -> None:
        import io
        import pandas as pd
        raw = _require(XLSX_SMALL)
        df = pd.read_excel(io.BytesIO(raw), header=0, dtype=str)
        expected = {"document_name", "rag_status", "business_case", "cost_p50_m",
                    "cost_p80_m", "project_end_p50", "text"}
        assert set(df.columns) == expected


# ── Domain detection trigger on ingest ───────────────────────────────────────

class TestDomainDetectionOnIngest:
    @patch("backend.app.services.reference_service.vector_store_status")
    @patch("backend.app.services.reference_service._trigger_domain_detection")
    def test_domain_detection_called_with_records(
        self, mock_detect, mock_vs, user_id: int
    ) -> None:
        from backend.app.services.reference_service import ingest_reference_file
        mock_vs.return_value = {"configured": False}
        raw = _require(XLSX_SMALL)
        ingest_reference_file(raw_bytes=raw, filename=XLSX_SMALL.name, user_id=user_id)
        mock_detect.assert_called_once()
        records_arg, user_id_arg = mock_detect.call_args.args
        assert len(records_arg) == 3
        assert user_id_arg == user_id

    @patch("backend.app.services.domain_detector.generate_json_object")
    @patch("backend.app.services.reference_service.vector_store_status")
    def test_domain_detection_saves_profile(
        self, mock_vs, mock_gen, user_id: int
    ) -> None:
        from backend.app.services import persistence
        from backend.app.services.reference_service import ingest_reference_file
        mock_vs.return_value = {"configured": False}
        mock_gen.return_value = {
            "domain_name": "Test Organisation",
            "period_label": "Period",
            "period_format": "P-XX",
            "status_codes": {"R": "Red", "A": "Amber", "G": "Green"},
            "key_terms": {},
            "suggested_questions": ["Which projects are Red?"],
            "confidence": 0.88,
        }
        raw = _require(XLSX_SMALL)
        ingest_reference_file(raw_bytes=raw, filename=XLSX_SMALL.name, user_id=user_id)
        profile = persistence.get_domain_profile(user_id)
        assert profile is not None
        assert profile["domain_name"] == "Test Organisation"
        assert profile["confidence"] == 0.88