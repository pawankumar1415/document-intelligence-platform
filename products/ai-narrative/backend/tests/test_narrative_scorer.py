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

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_run_score_boundary_exactly_8_is_pass(
        self,
        mock_vs_status: MagicMock,
        mock_gen_text: MagicMock,
        mock_gen_json: MagicMock,
    ) -> None:
        mock_vs_status.return_value = {"configured": False}
        mock_gen_json.side_effect = [
            {"compliance_score": 8.0, "issues": [], "passed": ["Clarity"]},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_gen_text.return_value = ""
        user = persistence.create_user(email="boundary8@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        result = run_score(narrative="Good.", unique_id="B8", document_name="B8", user_id=user["id"])
        assert result["overall_verdict"] == "PASS"

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_run_score_boundary_exactly_6_is_warn(
        self,
        mock_vs_status: MagicMock,
        mock_gen_text: MagicMock,
        mock_gen_json: MagicMock,
    ) -> None:
        mock_vs_status.return_value = {"configured": False}
        mock_gen_json.side_effect = [
            {"compliance_score": 6.0, "issues": ["Minor issue"], "passed": []},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_gen_text.return_value = "Rewrite."
        user = persistence.create_user(email="boundary6@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        result = run_score(narrative="Ok.", unique_id="B6", document_name="B6", user_id=user["id"])
        assert result["overall_verdict"] == "PASS_WITH_WARNINGS"

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_run_score_abnormalities_trigger_rewrite(
        self,
        mock_vs_status: MagicMock,
        mock_gen_text: MagicMock,
        mock_gen_json: MagicMock,
    ) -> None:
        mock_vs_status.return_value = {"configured": False}
        mock_gen_json.side_effect = [
            {"compliance_score": 8.5, "issues": [], "passed": ["Clarity"]},
            {
                "abnormalities": [
                    {"type": "missing_information", "description": "Missing cost data.", "severity": "high", "evidence": ""},
                ],
                "reference_quality_score": 7.0,
                "patterns_followed": [],
            },
        ]
        mock_gen_text.return_value = "Rewritten with cost data included."
        user = persistence.create_user(email="abnorm@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        result = run_score(narrative="Narrative missing cost data.", unique_id="ABN-001", document_name="ABN", user_id=user["id"])
        assert len(result["layer2"]["abnormalities"]) == 1
        assert result["rewritten_narrative"] == "Rewritten with cost data included."
        mock_gen_text.assert_called_once()

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_run_score_layer2_failure_is_non_fatal(
        self,
        mock_vs_status: MagicMock,
        mock_gen_text: MagicMock,
        mock_gen_json: MagicMock,
    ) -> None:
        mock_vs_status.return_value = {"configured": False}
        mock_gen_json.side_effect = [
            {"compliance_score": 9.0, "issues": [], "passed": ["Clarity"]},
            RuntimeError("Layer 2 LLM error"),
        ]
        mock_gen_text.return_value = ""
        user = persistence.create_user(email="layer2fail@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        result = run_score(narrative="Good narrative.", unique_id="L2F-001", document_name="L2F", user_id=user["id"])
        # Should still produce a valid result despite layer 2 failure
        assert result["overall_verdict"] == "PASS"
        assert result["layer2"]["abnormalities"] == []

    @patch("backend.app.services.narrative_scorer.upsert_scored_narrative")
    @patch("backend.app.services.embedding_service.embed_query")
    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_run_score_indexes_narrative_when_vs_configured(
        self,
        mock_vs_status: MagicMock,
        mock_gen_text: MagicMock,
        mock_gen_json: MagicMock,
        mock_embed: MagicMock,
        mock_upsert: MagicMock,
    ) -> None:
        mock_vs_status.return_value = {"configured": True}
        mock_gen_json.side_effect = [
            {"compliance_score": 9.0, "issues": [], "passed": []},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_gen_text.return_value = ""
        mock_embed.return_value = [0.1] * 768
        user = persistence.create_user(email="index@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        run_score(narrative="Indexed narrative.", unique_id="IDX-001", document_name="IDX", user_id=user["id"])

        mock_upsert.assert_called_once()
        call_kwargs = mock_upsert.call_args[1]
        assert call_kwargs["unique_id"] == "IDX-001"
        assert call_kwargs["user_id"] == user["id"]

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_run_score_clamps_score_above_10(
        self,
        mock_vs_status: MagicMock,
        mock_gen_text: MagicMock,
        mock_gen_json: MagicMock,
    ) -> None:
        mock_vs_status.return_value = {"configured": False}
        mock_gen_json.side_effect = [
            {"compliance_score": 15.0, "issues": [], "passed": []},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_gen_text.return_value = ""
        user = persistence.create_user(email="clamp10@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        result = run_score(narrative="Great.", unique_id="C10", document_name="C10", user_id=user["id"])
        assert result["layer1"]["compliance_score"] <= 10.0

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_run_score_clamps_score_below_0(
        self,
        mock_vs_status: MagicMock,
        mock_gen_text: MagicMock,
        mock_gen_json: MagicMock,
    ) -> None:
        mock_vs_status.return_value = {"configured": False}
        mock_gen_json.side_effect = [
            {"compliance_score": -5.0, "issues": ["Very bad"], "passed": []},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_gen_text.return_value = "Rewrite."
        user = persistence.create_user(email="clamp0@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        result = run_score(narrative="Terrible.", unique_id="C0", document_name="C0", user_id=user["id"])
        assert result["layer1"]["compliance_score"] >= 0.0