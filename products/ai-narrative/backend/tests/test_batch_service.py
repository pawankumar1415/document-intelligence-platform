"""Tests for batch_service.py — batch narrative scoring from file upload."""
from __future__ import annotations

import io
import pytest
from unittest.mock import MagicMock, patch

from backend.app.services import persistence


def _make_excel_bytes(rows: list[dict]) -> bytes:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    if rows:
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h, "") for h in headers])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_csv_bytes(rows: list[dict]) -> bytes:
    import csv
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _mock_run_score_with_verdict(verdict: str, score: float):
    """Return a mock that produces a given verdict from run_score."""
    def _run_score(**kwargs):
        return {
            "overall_verdict": verdict,
            "layer1": {"compliance_score": score, "issues": [], "passed": []},
            "layer2": {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": [], "references_used": 0},
            "rewritten_narrative": "",
            "meta": {
                "unique_id": kwargs.get("unique_id", "ID"),
                "document_name": kwargs.get("document_name", "Doc"),
                "rubric_id": kwargs.get("rubric_id", 1),
                "rubric_name": "Default",
                "references_used": 0,
                "provider": kwargs.get("provider", "openai"),
            },
        }
    return _run_score


class TestRunBatchScore:
    @patch("backend.app.services.batch_service.run_score")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_batch_excel_counts_verdicts(
        self,
        mock_vs: MagicMock,
        mock_run_score: MagicMock,
    ) -> None:
        mock_vs.return_value = {"configured": False}
        user = persistence.create_user(email="batch1@test.com", password_hash="h", password_salt="s")

        mock_run_score.side_effect = [
            _mock_run_score_with_verdict("PASS", 9.0)(unique_id="A", document_name="A", rubric_id=1, provider="openai"),
            _mock_run_score_with_verdict("PASS_WITH_WARNINGS", 7.0)(unique_id="B", document_name="B", rubric_id=1, provider="openai"),
            _mock_run_score_with_verdict("FAIL", 3.0)(unique_id="C", document_name="C", rubric_id=1, provider="openai"),
        ]

        raw = _make_excel_bytes([
            {"id": "A", "narrative": "Narrative A content."},
            {"id": "B", "narrative": "Narrative B content."},
            {"id": "C", "narrative": "Narrative C content."},
        ])

        from backend.app.services.batch_service import run_batch_score

        result = run_batch_score(
            raw_bytes=raw,
            filename="batch.xlsx",
            user_id=user["id"],
            provider="openai",
        )

        assert result["total"] == 3
        assert result["pass_count"] == 1
        assert result["warn_count"] == 1
        assert result["fail_count"] == 1
        assert result["skip_count"] == 0

    @patch("backend.app.services.batch_service.run_score")
    def test_batch_skips_empty_narrative_rows(self, mock_run_score: MagicMock) -> None:
        user = persistence.create_user(email="batch2@test.com", password_hash="h", password_salt="s")

        raw = _make_excel_bytes([
            {"id": "VALID", "narrative": "Valid narrative content here."},
            {"id": "EMPTY", "narrative": ""},
            {"id": "SPACES", "narrative": "   "},
        ])

        from backend.app.services.batch_service import run_batch_score

        mock_run_score.return_value = _mock_run_score_with_verdict("PASS", 9.0)(
            unique_id="VALID", document_name="VALID", rubric_id=1, provider="openai"
        )

        result = run_batch_score(
            raw_bytes=raw,
            filename="skip_test.xlsx",
            user_id=user["id"],
        )

        assert result["skip_count"] == 2
        assert result["total"] == 3
        assert mock_run_score.call_count == 1

    @patch("backend.app.services.batch_service.run_score")
    def test_batch_score_exception_produces_error_verdict(
        self, mock_run_score: MagicMock
    ) -> None:
        user = persistence.create_user(email="batch3@test.com", password_hash="h", password_salt="s")
        mock_run_score.side_effect = RuntimeError("LLM API rate limit")

        raw = _make_excel_bytes([
            {"id": "FAIL-ROW", "narrative": "This narrative will error."},
        ])

        from backend.app.services.batch_service import run_batch_score

        result = run_batch_score(
            raw_bytes=raw,
            filename="error_test.xlsx",
            user_id=user["id"],
        )

        assert result["total"] == 1
        assert result["fail_count"] == 1
        assert result["results"][0]["overall_verdict"] == "ERROR"
        assert "LLM API rate limit" in result["results"][0]["layer1"]["issues"][0]

    @patch("backend.app.services.batch_service.run_score")
    def test_batch_csv_input(self, mock_run_score: MagicMock) -> None:
        user = persistence.create_user(email="batch4@test.com", password_hash="h", password_salt="s")
        mock_run_score.return_value = _mock_run_score_with_verdict("PASS", 8.5)(
            unique_id="CSV-1", document_name="CSV-1", rubric_id=1, provider="openai"
        )

        raw = _make_csv_bytes([
            {"project": "CSV-1", "narrative": "CSV narrative content for batch test."},
        ])

        from backend.app.services.batch_service import run_batch_score

        result = run_batch_score(
            raw_bytes=raw,
            filename="batch.csv",
            user_id=user["id"],
        )

        assert result["total"] == 1
        assert result["pass_count"] == 1

    @patch("backend.app.services.batch_service.run_score")
    def test_batch_result_includes_rubric_name(self, mock_run_score: MagicMock) -> None:
        user = persistence.create_user(email="batch5@test.com", password_hash="h", password_salt="s")
        mock_run_score.return_value = _mock_run_score_with_verdict("PASS", 9.0)(
            unique_id="X", document_name="X", rubric_id=1, provider="openai"
        )

        raw = _make_excel_bytes([{"id": "X", "narrative": "Any narrative text."}])

        from backend.app.services.batch_service import run_batch_score

        result = run_batch_score(
            raw_bytes=raw,
            filename="rubric_test.xlsx",
            user_id=user["id"],
        )

        assert "rubric_name" in result
        assert isinstance(result["rubric_name"], str)

    @patch("backend.app.services.batch_service.run_score")
    def test_batch_respects_custom_rubric_id(self, mock_run_score: MagicMock) -> None:
        user = persistence.create_user(email="batch6@test.com", password_hash="h", password_salt="s")
        custom_rubric_id = persistence.create_rubric(
            user_id=user["id"],
            name="Custom Batch Rubric",
            description="Test",
            criteria=[{"name": "Completeness", "description": "Must be complete.", "severity": "high"}],
        )
        mock_run_score.return_value = _mock_run_score_with_verdict("PASS", 9.0)(
            unique_id="X", document_name="X", rubric_id=custom_rubric_id, provider="openai"
        )

        raw = _make_excel_bytes([{"id": "X", "narrative": "Complete narrative text."}])

        from backend.app.services.batch_service import run_batch_score

        run_batch_score(
            raw_bytes=raw,
            filename="custom_rubric.xlsx",
            user_id=user["id"],
            rubric_id=custom_rubric_id,
        )

        call_kwargs = mock_run_score.call_args[1]
        assert call_kwargs["rubric_id"] == custom_rubric_id

    @patch("backend.app.services.batch_service.run_score")
    def test_batch_all_skipped_returns_zero_counts(self, mock_run_score: MagicMock) -> None:
        user = persistence.create_user(email="batch7@test.com", password_hash="h", password_salt="s")

        raw = _make_excel_bytes([
            {"id": "A", "narrative": ""},
            {"id": "B", "narrative": ""},
        ])

        from backend.app.services.batch_service import run_batch_score

        result = run_batch_score(
            raw_bytes=raw,
            filename="all_empty.xlsx",
            user_id=user["id"],
        )

        assert result["total"] == 2
        assert result["skip_count"] == 2
        assert result["pass_count"] == 0
        assert mock_run_score.call_count == 0