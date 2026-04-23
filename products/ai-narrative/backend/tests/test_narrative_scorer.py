"""Tests for the narrative scoring engine (mocked LLM)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from backend.app.services import persistence
from backend.app.services.narrative_scorer import (
    _build_criteria_text,
    _build_references_text,
    _enforce_verdict,
)


class TestVerdictLogic:
    def test_pass_at_8(self) -> None:
        assert _enforce_verdict(8.0) == "PASS"

    def test_pass_above_8(self) -> None:
        assert _enforce_verdict(9.5) == "PASS"

    def test_warn_at_6(self) -> None:
        assert _enforce_verdict(6.0) == "PASS_WITH_WARNINGS"

    def test_warn_at_7(self) -> None:
        assert _enforce_verdict(7.9) == "PASS_WITH_WARNINGS"

    def test_fail_below_6(self) -> None:
        assert _enforce_verdict(5.9) == "FAIL"

    def test_fail_at_0(self) -> None:
        assert _enforce_verdict(0.0) == "FAIL"


class TestCriteriaText:
    def test_formats_severity_labels(self) -> None:
        criteria = [
            {"name": "Clarity", "description": "Must be clear.", "severity": "high"},
            {"name": "Tone", "description": "Professional.", "severity": "low"},
        ]
        text = _build_criteria_text(criteria)
        assert "[HIGH]" in text
        assert "[LOW]" in text
        assert "Clarity" in text
        assert "Must be clear." in text

    def test_defaults_to_medium(self) -> None:
        criteria = [{"name": "Test", "description": "Desc"}]
        text = _build_criteria_text(criteria)
        assert "[MED]" in text


class TestReferencesText:
    def test_no_references_message(self) -> None:
        text = _build_references_text([])
        assert "No reference" in text

    def test_formats_references(self) -> None:
        from backend.app.services.vector_store import ReferenceMatch

        refs = [
            ReferenceMatch(unique_id="P001", narrative_text="Reference narrative.", content="", score=0.92),
            ReferenceMatch(unique_id="P002", narrative_text="Another reference.", content="", score=0.85),
        ]
        text = _build_references_text(refs)
        assert "P001" in text
        assert "Reference narrative." in text
        assert "92%" in text
        assert "P002" in text


class TestRunScore:
    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_run_score_pass(
        self,
        mock_vs_status: MagicMock,
        mock_gen_text: MagicMock,
        mock_gen_json: MagicMock,
    ) -> None:
        mock_vs_status.return_value = {"configured": False}
        mock_gen_json.side_effect = [
            # Layer 1 response
            {"compliance_score": 9.0, "issues": [], "passed": ["Clarity", "Tone"]},
            # Layer 2 response
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": ["Good structure"]},
        ]
        mock_gen_text.return_value = ""

        user = persistence.create_user(email="scorer@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        result = run_score(
            narrative="This is a well-written narrative with all required information present.",
            unique_id="TEST-001",
            document_name="Test Project",
            user_id=user["id"],
            provider="openai",
        )

        assert result["overall_verdict"] == "PASS"
        assert result["layer1"]["compliance_score"] == 9.0
        assert result["meta"]["unique_id"] == "TEST-001"

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_run_score_fail(
        self,
        mock_vs_status: MagicMock,
        mock_gen_text: MagicMock,
        mock_gen_json: MagicMock,
    ) -> None:
        mock_vs_status.return_value = {"configured": False}
        mock_gen_json.side_effect = [
            {"compliance_score": 3.0, "issues": ["Missing key information", "Unclear structure"], "passed": []},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_gen_text.return_value = "Rewritten narrative text."

        user = persistence.create_user(email="scorer2@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        result = run_score(
            narrative="Bad narrative.",
            unique_id="TEST-002",
            document_name="Bad Project",
            user_id=user["id"],
            provider="openai",
        )

        assert result["overall_verdict"] == "FAIL"
        assert len(result["layer1"]["issues"]) == 2

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_run_score_persists_result(
        self,
        mock_vs_status: MagicMock,
        mock_gen_text: MagicMock,
        mock_gen_json: MagicMock,
    ) -> None:
        mock_vs_status.return_value = {"configured": False}
        mock_gen_json.side_effect = [
            {"compliance_score": 7.0, "issues": ["Minor issue"], "passed": []},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_gen_text.return_value = ""

        user = persistence.create_user(email="persist@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        run_score(
            narrative="Medium quality narrative.",
            unique_id="TEST-003",
            document_name="Medium Project",
            user_id=user["id"],
            provider="openai",
        )

        results = persistence.list_score_results(user["id"])
        assert len(results) == 1
        assert results[0]["overall_verdict"] == "PASS_WITH_WARNINGS"