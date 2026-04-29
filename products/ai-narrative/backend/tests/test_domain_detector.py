"""Tests for the automatic domain detection service."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.app.services.domain_detector import _fallback_profile, _normalise, detect_domain


# ── _normalise ────────────────────────────────────────────────────────────────

class TestNormalise:
    def test_full_valid_profile(self) -> None:
        raw = {
            "domain_name": "Nuclear Decommissioning Authority",
            "period_label": "Period",
            "period_format": "P-XX (e.g. P-06, P-07)",
            "status_codes": {"R": "Red — off-track", "A": "Amber — at risk", "G": "Green — on-track"},
            "key_terms": {"DCA": "Delivery Confidence Assessment", "EAC": "Estimate At Complete"},
            "suggested_questions": ["Which projects are Red?", "What is the P80 cost?"],
            "confidence": 0.92,
        }
        result = _normalise(raw)
        assert result["domain_name"] == "Nuclear Decommissioning Authority"
        assert result["period_label"] == "Period"
        assert result["period_format"] == "P-XX (e.g. P-06, P-07)"
        assert result["status_codes"]["R"] == "Red — off-track"
        assert result["key_terms"]["DCA"] == "Delivery Confidence Assessment"
        assert len(result["suggested_questions"]) == 2
        assert abs(result["confidence"] - 0.92) < 0.001

    def test_missing_optional_fields_get_defaults(self) -> None:
        result = _normalise({})
        assert result["domain_name"] is None
        assert result["period_label"] == "Period"
        assert result["period_format"] is None
        assert result["status_codes"] == {}
        assert result["key_terms"] == {}
        assert result["suggested_questions"] == []
        assert result["confidence"] == 0.0

    def test_invalid_status_codes_becomes_empty_dict(self) -> None:
        result = _normalise({"status_codes": ["R", "A", "G"]})
        assert result["status_codes"] == {}

    def test_suggested_questions_capped_at_8(self) -> None:
        raw = {"suggested_questions": [f"Q{i}?" for i in range(12)]}
        result = _normalise(raw)
        assert len(result["suggested_questions"]) == 8

    def test_null_suggested_questions_returns_empty_list(self) -> None:
        result = _normalise({"suggested_questions": None})
        assert result["suggested_questions"] == []

    def test_confidence_coerced_to_float(self) -> None:
        result = _normalise({"confidence": "0.85"})
        assert isinstance(result["confidence"], float)
        assert abs(result["confidence"] - 0.85) < 0.001


# ── _fallback_profile ─────────────────────────────────────────────────────────

class TestFallbackProfile:
    def test_returns_safe_defaults(self) -> None:
        p = _fallback_profile()
        assert p["domain_name"] is None
        assert p["period_label"] == "Period"
        assert p["confidence"] == 0.0
        assert isinstance(p["suggested_questions"], list)
        assert isinstance(p["status_codes"], dict)


# ── detect_domain ─────────────────────────────────────────────────────────────

class TestDetectDomain:
    def test_empty_sample_returns_fallback(self) -> None:
        result = detect_domain(sample_records=[])
        assert result == _fallback_profile()

    def test_blank_narratives_returns_fallback(self) -> None:
        records = [{"unique_id": "X", "narrative_text": "   "} for _ in range(5)]
        result = detect_domain(sample_records=records)
        assert result == _fallback_profile()

    @patch("backend.app.services.domain_detector.generate_json_object")
    def test_successful_detection(self, mock_gen) -> None:
        mock_gen.return_value = {
            "domain_name": "Central Government Portfolio Office",
            "period_label": "Quarter",
            "period_format": "Q1–Q4",
            "status_codes": {"G": "On Track", "A": "At Risk", "R": "Off Track"},
            "key_terms": {"SRO": "Senior Responsible Owner"},
            "suggested_questions": ["Which programmes are amber?"],
            "confidence": 0.88,
        }
        records = [
            {"unique_id": "P001", "narrative_text": "The programme remains on track this quarter."},
            {"unique_id": "P002", "narrative_text": "Costs are above baseline due to contractor delays."},
        ]
        result = detect_domain(sample_records=records)
        assert result["domain_name"] == "Central Government Portfolio Office"
        assert result["period_label"] == "Quarter"
        assert result["confidence"] == 0.88
        mock_gen.assert_called_once()

    @patch("backend.app.services.domain_detector.generate_json_object")
    def test_only_first_10_samples_used(self, mock_gen) -> None:
        mock_gen.return_value = {"confidence": 0.5}
        records = [
            {"unique_id": f"ID-{i}", "narrative_text": f"Narrative text for project {i}."}
            for i in range(15)
        ]
        detect_domain(sample_records=records)
        call_args = mock_gen.call_args
        # The user prompt contains sample text; check it only has 10 records
        user_prompt = call_args.kwargs.get("user_prompt") or call_args.args[1]
        assert "Record 10" in user_prompt
        assert "Record 11" not in user_prompt

    @patch("backend.app.services.domain_detector.generate_json_object")
    def test_llm_failure_returns_fallback(self, mock_gen) -> None:
        mock_gen.side_effect = RuntimeError("LLM unavailable")
        records = [{"unique_id": "P1", "narrative_text": "Some narrative text here."}]
        result = detect_domain(sample_records=records)
        assert result == _fallback_profile()

    @patch("backend.app.services.domain_detector.generate_json_object")
    def test_nda_portfolio_data_detected_correctly(self, mock_gen) -> None:
        """Simulate detection on the NDA portfolio narrative style."""
        mock_gen.return_value = {
            "domain_name": "Nuclear Decommissioning Authority",
            "period_label": "Period",
            "period_format": "P-XX (e.g. P-06, P-07)",
            "status_codes": {
                "R": "Red — forecast end date outside P80",
                "A": "Amber — at risk but manageable",
                "G": "Green — within P80 tolerances",
            },
            "key_terms": {
                "DCA": "Delivery Confidence Assessment",
                "EAC": "Estimate At Complete",
                "CCR": "Change Control Request",
                "P50": "50th percentile cost estimate",
                "P80": "80th percentile cost estimate",
            },
            "suggested_questions": [
                "Which projects are Red DCA this period?",
                "Summarise projects where EAC exceeds P80 sanction.",
            ],
            "confidence": 0.95,
        }
        # Use real NDA-style narrative content
        records = [
            {
                "unique_id": "P06 | Enhanced CNC Airwave System",
                "narrative_text": (
                    "The Delivery Confidence Assessment remains Red, since the forecast end date "
                    "is outside of the Business Case P80 date due to the project currently being "
                    "on hold pending a future scope delivery decision."
                ),
            },
            {
                "unique_id": "P06 | SEP Solid Waste Storage Retrievals",
                "narrative_text": (
                    "The Delivery Confidence Assessment remains amber in light of challenges to "
                    "the SEP1 commissioning schedule. The lifecycle EAC remains within released "
                    "sanction, however the lifecycle impacts of prolongation of SEP1 have been "
                    "incorporated into EAC which resulted in a lifecycle increase."
                ),
            },
        ]
        result = detect_domain(sample_records=records)
        assert result["domain_name"] == "Nuclear Decommissioning Authority"
        assert "DCA" in result["key_terms"]
        assert "P80" in result["key_terms"]
        assert result["confidence"] >= 0.9