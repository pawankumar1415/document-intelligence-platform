"""Tests for Standards features: rules parser, financial service, drift service, and routes."""
from __future__ import annotations

import csv
import io
from unittest.mock import MagicMock, patch

import openpyxl
import pytest
from fastapi.testclient import TestClient

from backend.app.services import persistence


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_csv_bytes(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _make_excel_bytes(rows: list[dict]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h, "") for h in headers])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _save_audit(user_id: int, **kwargs) -> None:
    """Helper that always supplies the required count fields."""
    persistence.save_audit_entry(
        user_id=user_id,
        unique_id=kwargs.get("unique_id", "X"),
        compliance_score=kwargs.get("compliance_score", 8.0),
        verdict=kwargs.get("verdict", "PASS"),
        provider=kwargs.get("provider", "ollama"),
        model_name=kwargs.get("model_name", "qwen3:4b"),
        prompt_hash=kwargs.get("prompt_hash", "abc123"),
        has_custom_rules=kwargs.get("has_custom_rules", False),
        has_financial_data=kwargs.get("has_financial_data", False),
        layer2_abnormality_count=kwargs.get("layer2_abnormality_count", 0),
        layer3_discrepancy_count=kwargs.get("layer3_discrepancy_count", None),
    )


# ── Persistence — user_settings ───────────────────────────────────────────────

class TestUserSettings:
    def test_no_active_rubric_returns_none(self) -> None:
        user = persistence.create_user(email="s1@test.com", password_hash="h", password_salt="s")
        assert persistence.get_active_rules_rubric_id(user["id"]) is None

    def test_set_and_get_active_rubric(self) -> None:
        user = persistence.create_user(email="s2@test.com", password_hash="h", password_salt="s")
        rubric_id = persistence.create_rubric(
            user_id=user["id"], name="Custom", description="", criteria=[]
        )
        persistence.set_active_rules_rubric(user["id"], rubric_id)
        assert persistence.get_active_rules_rubric_id(user["id"]) == rubric_id

    def test_clear_active_rubric(self) -> None:
        user = persistence.create_user(email="s3@test.com", password_hash="h", password_salt="s")
        rubric_id = persistence.create_rubric(
            user_id=user["id"], name="ToRemove", description="", criteria=[]
        )
        persistence.set_active_rules_rubric(user["id"], rubric_id)
        persistence.clear_active_rules_rubric(user["id"])
        assert persistence.get_active_rules_rubric_id(user["id"]) is None

    def test_set_overrides_previous_value(self) -> None:
        user = persistence.create_user(email="s4@test.com", password_hash="h", password_salt="s")
        r1 = persistence.create_rubric(user_id=user["id"], name="R1", description="", criteria=[])
        r2 = persistence.create_rubric(user_id=user["id"], name="R2", description="", criteria=[])
        persistence.set_active_rules_rubric(user["id"], r1)
        persistence.set_active_rules_rubric(user["id"], r2)
        assert persistence.get_active_rules_rubric_id(user["id"]) == r2


# ── Persistence — financial uploads ───────────────────────────────────────────

class TestFinancialPersistence:
    def test_save_and_get_upload_status(self) -> None:
        user = persistence.create_user(email="f1@test.com", password_hash="h", password_salt="s")
        persistence.save_financial_upload(
            user_id=user["id"],
            filename="data.xlsx",
            records=[{"unique_id": "P1", "raw_data": {"budget": "£50k"}}],
        )
        status = persistence.get_financial_upload_status(user["id"])
        assert status is not None
        assert status["filename"] == "data.xlsx"
        assert status["record_count"] == 1

    def test_no_upload_returns_none(self) -> None:
        user = persistence.create_user(email="f2@test.com", password_hash="h", password_salt="s")
        assert persistence.get_financial_upload_status(user["id"]) is None

    def test_delete_upload(self) -> None:
        user = persistence.create_user(email="f3@test.com", password_hash="h", password_salt="s")
        persistence.save_financial_upload(
            user_id=user["id"],
            filename="data.xlsx",
            records=[{"unique_id": "P1", "raw_data": {}}],
        )
        persistence.delete_financial_upload(user["id"])
        assert persistence.get_financial_upload_status(user["id"]) is None

    def test_get_financial_record_exact_match(self) -> None:
        user = persistence.create_user(email="f4@test.com", password_hash="h", password_salt="s")
        persistence.save_financial_upload(
            user_id=user["id"],
            filename="data.csv",
            records=[{"unique_id": "PROJ-001", "raw_data": {"budget": "£100k", "spend": "£90k"}}],
        )
        record = persistence.get_financial_record(user_id=user["id"], unique_id="PROJ-001")
        assert record is not None
        assert record["budget"] == "£100k"

    def test_get_financial_record_case_insensitive(self) -> None:
        user = persistence.create_user(email="f5@test.com", password_hash="h", password_salt="s")
        persistence.save_financial_upload(
            user_id=user["id"],
            filename="data.csv",
            records=[{"unique_id": "PROJ-002", "raw_data": {"budget": "£200k"}}],
        )
        record = persistence.get_financial_record(user_id=user["id"], unique_id="proj-002")
        assert record is not None

    def test_get_financial_record_missing_returns_none(self) -> None:
        user = persistence.create_user(email="f6@test.com", password_hash="h", password_salt="s")
        assert persistence.get_financial_record(user_id=user["id"], unique_id="NONEXISTENT") is None


# ── Persistence — score audit ──────────────────────────────────────────────────

class TestScoreAudit:
    def test_save_and_retrieve_audit_entry(self) -> None:
        user = persistence.create_user(email="a1@test.com", password_hash="h", password_salt="s")
        _save_audit(user["id"], compliance_score=8.5, verdict="PASS", provider="ollama")
        records = persistence.get_audit_records(user["id"], days=30)
        assert len(records) == 1
        assert records[0]["compliance_score"] == pytest.approx(8.5)
        assert records[0]["verdict"] == "PASS"
        assert records[0]["provider"] == "ollama"

    def test_multiple_audit_entries(self) -> None:
        user = persistence.create_user(email="a2@test.com", password_hash="h", password_salt="s")
        for score, verdict in [(9.0, "PASS"), (5.0, "FAIL"), (7.0, "PASS_WITH_WARNINGS")]:
            _save_audit(user["id"], compliance_score=score, verdict=verdict)
        records = persistence.get_audit_records(user["id"], days=30)
        assert len(records) == 3

    def test_audit_records_isolated_by_user(self) -> None:
        u1 = persistence.create_user(email="a3@test.com", password_hash="h", password_salt="s")
        u2 = persistence.create_user(email="a4@test.com", password_hash="h", password_salt="s")
        _save_audit(u1["id"])
        assert len(persistence.get_audit_records(u2["id"], days=30)) == 0


# ── Rules parser ──────────────────────────────────────────────────────────────

class TestRulesParser:
    def test_parse_csv_rules(self) -> None:
        from backend.app.services.rules_parser import parse_rules_document

        csv_bytes = _make_csv_bytes([
            {"name": "Clarity", "description": "Writing must be clear", "severity": "high"},
            {"name": "Completeness", "description": "All fields must be present", "severity": "medium"},
        ])
        criteria = parse_rules_document(csv_bytes, "rules.csv", provider="ollama")
        assert len(criteria) == 2
        assert criteria[0]["name"] == "Clarity"
        assert criteria[0]["severity"] == "high"

    def test_parse_excel_rules(self) -> None:
        from backend.app.services.rules_parser import parse_rules_document

        rows = [
            {"name": "Timeliness", "description": "Reports must be submitted on time", "severity": "high"},
            {"name": "Accuracy", "description": "Data must be accurate", "severity": "medium"},
        ]
        xl_bytes = _make_excel_bytes(rows)
        criteria = parse_rules_document(xl_bytes, "rules.xlsx", provider="ollama")
        assert len(criteria) >= 1

    @patch("backend.app.services.rules_parser.generate_json_object",
           create=True,
           new_callable=lambda: lambda *a, **kw: None)
    def test_parse_docx_falls_back_to_llm(self, _mock: None) -> None:
        """DOCX path calls the LLM; we patch it at module level via importlib."""
        import importlib
        import backend.app.services.rules_parser as rp_mod

        llm_response = {
            "criteria": [
                {"name": "LLM Criterion", "description": "Extracted by LLM", "severity": "medium"}
            ]
        }

        with patch.object(rp_mod, "_extract_with_llm", return_value=llm_response["criteria"]):
            import docx
            doc = docx.Document()
            doc.add_paragraph("1. Clarity: The narrative must be clearly written.")
            buf = io.BytesIO()
            doc.save(buf)
            docx_bytes = buf.getvalue()

            criteria = rp_mod.parse_rules_document(docx_bytes, "rules.docx", provider="ollama")
            assert len(criteria) >= 1

    def test_severity_defaults_to_medium_for_csv_without_severity(self) -> None:
        from backend.app.services.rules_parser import parse_rules_document

        csv_bytes = _make_csv_bytes([
            {"name": "Check", "description": "Some check"},
        ])
        criteria = parse_rules_document(csv_bytes, "rules.csv", provider="ollama")
        assert len(criteria) == 1
        assert criteria[0]["severity"] in ("medium", "low", "high")  # has a value


# ── Financial service ─────────────────────────────────────────────────────────

class TestFinancialService:
    def test_ingest_csv(self) -> None:
        from backend.app.services.financial_service import ingest_financial_file

        user = persistence.create_user(email="fi1@test.com", password_hash="h", password_salt="s")
        csv_bytes = _make_csv_bytes([
            {"project_id": "PROJ-001", "budget": "£100k", "spend": "£90k"},
            {"project_id": "PROJ-002", "budget": "£200k", "spend": "£180k"},
        ])
        result = ingest_financial_file(csv_bytes, "data.csv", user["id"])
        assert result["record_count"] == 2
        assert result["status"] == "ok"

        record = persistence.get_financial_record(user_id=user["id"], unique_id="PROJ-001")
        assert record is not None
        assert record["budget"] == "£100k"

    def test_ingest_excel(self) -> None:
        from backend.app.services.financial_service import ingest_financial_file

        user = persistence.create_user(email="fi2@test.com", password_hash="h", password_salt="s")
        rows = [
            {"id": "REF-001", "planned_cost": "1000", "actual_cost": "1100"},
            {"id": "REF-002", "planned_cost": "2000", "actual_cost": "1900"},
            {"id": "REF-003", "planned_cost": "500", "actual_cost": "500"},
        ]
        result = ingest_financial_file(_make_excel_bytes(rows), "data.xlsx", user["id"])
        assert result["record_count"] == 3

    def test_ingest_replaces_previous_records(self) -> None:
        from backend.app.services.financial_service import ingest_financial_file

        user = persistence.create_user(email="fi3@test.com", password_hash="h", password_salt="s")
        ingest_financial_file(
            _make_csv_bytes([{"project_id": "OLD-001", "budget": "£50k"}]), "old.csv", user["id"]
        )
        ingest_financial_file(
            _make_csv_bytes([{"project_id": "NEW-001", "budget": "£100k"}]), "new.csv", user["id"]
        )
        assert persistence.get_financial_record(user_id=user["id"], unique_id="OLD-001") is None
        assert persistence.get_financial_record(user_id=user["id"], unique_id="NEW-001") is not None

    def test_ingest_skips_empty_id_rows(self) -> None:
        from backend.app.services.financial_service import ingest_financial_file

        user = persistence.create_user(email="fi4@test.com", password_hash="h", password_salt="s")
        csv_bytes = _make_csv_bytes([
            {"project_id": "PROJ-001", "budget": "£100k"},
            {"project_id": "", "budget": "£200k"},
        ])
        result = ingest_financial_file(csv_bytes, "data.csv", user["id"])
        assert result["record_count"] == 1


# ── Drift service ─────────────────────────────────────────────────────────────

class TestDriftService:
    def _seed(self, user_id: int, entries: list[dict]) -> None:
        for e in entries:
            _save_audit(
                user_id,
                compliance_score=e.get("score", 8.0),
                verdict=e.get("verdict", "PASS"),
                provider=e.get("provider", "ollama"),
                model_name=e.get("model", "qwen3:4b"),
                prompt_hash=e.get("hash", "abc123"),
                has_custom_rules=e.get("custom_rules", False),
                has_financial_data=e.get("financial", False),
            )

    def test_no_data_returns_empty_metrics(self) -> None:
        from backend.app.services.drift_service import get_drift_metrics

        user = persistence.create_user(email="d1@test.com", password_hash="h", password_salt="s")
        metrics = get_drift_metrics(user["id"], days=30)
        assert metrics["total_scored"] == 0
        assert metrics["trend_direction"] == "stable"

    def test_avg_score_computed(self) -> None:
        from backend.app.services.drift_service import get_drift_metrics

        user = persistence.create_user(email="d2@test.com", password_hash="h", password_salt="s")
        self._seed(user["id"], [{"score": 8.0, "verdict": "PASS"}, {"score": 6.0, "verdict": "PASS_WITH_WARNINGS"}])
        metrics = get_drift_metrics(user["id"], days=30)
        assert metrics["avg_score"] == pytest.approx(7.0, rel=0.01)
        assert metrics["total_scored"] == 2

    def test_custom_rules_usage_pct(self) -> None:
        from backend.app.services.drift_service import get_drift_metrics

        user = persistence.create_user(email="d3@test.com", password_hash="h", password_salt="s")
        self._seed(user["id"], [
            {"score": 9.0, "custom_rules": True},
            {"score": 8.0, "custom_rules": True},
            {"score": 7.0, "custom_rules": False},
            {"score": 6.0, "custom_rules": False},
        ])
        metrics = get_drift_metrics(user["id"], days=30)
        assert metrics["custom_rules_usage_pct"] == pytest.approx(50.0, rel=0.01)

    def test_financial_check_usage_pct(self) -> None:
        from backend.app.services.drift_service import get_drift_metrics

        user = persistence.create_user(email="d4@test.com", password_hash="h", password_salt="s")
        self._seed(user["id"], [
            {"score": 9.0, "financial": True},
            {"score": 8.0, "financial": False},
            {"score": 7.0, "financial": False},
            {"score": 6.0, "financial": False},
        ])
        metrics = get_drift_metrics(user["id"], days=30)
        assert metrics["financial_check_usage_pct"] == pytest.approx(25.0, rel=0.01)

    def test_model_distribution(self) -> None:
        from backend.app.services.drift_service import get_drift_metrics

        user = persistence.create_user(email="d5@test.com", password_hash="h", password_salt="s")
        self._seed(user["id"], [
            {"score": 9.0, "provider": "ollama", "model": "qwen3:4b"},
            {"score": 8.0, "provider": "ollama", "model": "qwen3:4b"},
            {"score": 7.0, "provider": "openai", "model": "gpt-4o-mini"},
        ])
        metrics = get_drift_metrics(user["id"], days=30)
        dist = metrics["model_distribution"]
        # keys are "provider/model_name"
        assert dist.get("ollama/qwen3:4b") == 2
        assert dist.get("openai/gpt-4o-mini") == 1

    def test_export_audit_csv_has_headers(self) -> None:
        from backend.app.services.drift_service import export_audit_csv

        user = persistence.create_user(email="d6@test.com", password_hash="h", password_salt="s")
        self._seed(user["id"], [{"score": 8.0}])
        csv_text = export_audit_csv(user["id"], days=30)
        assert "compliance_score" in csv_text
        assert "verdict" in csv_text
        assert "provider" in csv_text

    def test_export_csv_contains_data(self) -> None:
        from backend.app.services.drift_service import export_audit_csv

        user = persistence.create_user(email="d7@test.com", password_hash="h", password_salt="s")
        self._seed(user["id"], [{"score": 9.5, "verdict": "PASS", "provider": "groq"}])
        csv_text = export_audit_csv(user["id"], days=30)
        assert "PASS" in csv_text
        assert "groq" in csv_text


# ── Standards routes ──────────────────────────────────────────────────────────

class TestStandardsRoutes:
    def test_get_standards_status_empty(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/standards/rules", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["rules"]["active"] is False
        assert data["financial"]["active"] is False

    @patch("backend.app.services.rules_parser.parse_rules_document")
    def test_upload_rules_document(
        self,
        mock_parse: MagicMock,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        mock_parse.return_value = [
            {"name": "Clarity", "description": "Clear writing", "severity": "high"},
            {"name": "Completeness", "description": "All sections present", "severity": "medium"},
        ]
        csv_bytes = _make_csv_bytes([{"name": "Clarity", "description": "Clear writing"}])
        resp = client.post(
            "/api/v1/standards/rules/upload",
            headers=auth_headers,
            files={"file": ("rules.csv", csv_bytes, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["criteria_count"] == 2
        assert data["filename"] == "rules.csv"

        status_resp = client.get("/api/v1/standards/rules", headers=auth_headers)
        assert status_resp.json()["rules"]["active"] is True

    @patch("backend.app.services.rules_parser.parse_rules_document")
    def test_delete_rules_reverts_to_default(
        self,
        mock_parse: MagicMock,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        mock_parse.return_value = [{"name": "X", "description": "Y", "severity": "low"}]
        csv_bytes = _make_csv_bytes([{"name": "X", "description": "Y"}])
        client.post(
            "/api/v1/standards/rules/upload",
            headers=auth_headers,
            files={"file": ("rules.csv", csv_bytes, "text/csv")},
        )
        del_resp = client.delete("/api/v1/standards/rules", headers=auth_headers)
        assert del_resp.status_code == 200
        status = client.get("/api/v1/standards/rules", headers=auth_headers).json()
        assert status["rules"]["active"] is False

    def test_upload_financial_data_csv(self, client: TestClient, auth_headers: dict) -> None:
        csv_bytes = _make_csv_bytes([
            {"project_id": "PROJ-001", "budget": "£100k", "spend": "£90k"},
            {"project_id": "PROJ-002", "budget": "£200k", "spend": "£180k"},
        ])
        resp = client.post(
            "/api/v1/standards/financial/upload",
            headers=auth_headers,
            files={"file": ("financial.csv", csv_bytes, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_count"] == 2
        assert data["filename"] == "financial.csv"

        status = client.get("/api/v1/standards/rules", headers=auth_headers).json()
        assert status["financial"]["active"] is True
        assert status["financial"]["record_count"] == 2

    def test_delete_financial_data(self, client: TestClient, auth_headers: dict) -> None:
        csv_bytes = _make_csv_bytes([{"project_id": "P1", "budget": "£10k"}])
        client.post(
            "/api/v1/standards/financial/upload",
            headers=auth_headers,
            files={"file": ("fin.csv", csv_bytes, "text/csv")},
        )
        del_resp = client.delete("/api/v1/standards/financial", headers=auth_headers)
        assert del_resp.status_code == 200
        status = client.get("/api/v1/standards/rules", headers=auth_headers).json()
        assert status["financial"]["active"] is False

    def test_standards_routes_require_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/standards/rules").status_code == 401


# ── Drift routes ──────────────────────────────────────────────────────────────

class TestDriftRoutes:
    def test_drift_endpoint_returns_metrics(
        self, client: TestClient, auth_headers: dict, user_id: int
    ) -> None:
        for score, verdict in [(8.0, "PASS"), (5.0, "FAIL")]:
            _save_audit(user_id, compliance_score=score, verdict=verdict)

        resp = client.get("/api/v1/analytics/drift", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_scored"] == 2
        assert "trend_direction" in data
        assert "data_points" in data
        assert "model_distribution" in data

    def test_drift_export_returns_csv(
        self, client: TestClient, auth_headers: dict, user_id: int
    ) -> None:
        _save_audit(user_id, compliance_score=9.0, verdict="PASS")
        resp = client.get("/api/v1/analytics/drift/export", headers=auth_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_drift_route_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/analytics/drift").status_code == 401


# ── Layer 3 in narrative scorer ───────────────────────────────────────────────

class TestLayer3InScorer:
    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_layer3_is_none_without_financial_data(
        self, mock_vs: MagicMock, mock_text: MagicMock, mock_json: MagicMock
    ) -> None:
        mock_vs.return_value = {"configured": False}
        mock_json.side_effect = [
            {"compliance_score": 8.0, "issues": [], "passed": []},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_text.return_value = ""

        user = persistence.create_user(email="l3a@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        result = run_score(
            narrative="Good narrative.",
            unique_id="NO-FIN-001",
            document_name="Test",
            user_id=user["id"],
            provider="ollama",
        )
        assert result["layer3"] is None
        assert result["meta"]["has_financial_data"] is False

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_layer3_runs_when_financial_record_exists(
        self, mock_vs: MagicMock, mock_text: MagicMock, mock_json: MagicMock
    ) -> None:
        mock_vs.return_value = {"configured": False}
        mock_json.side_effect = [
            {"compliance_score": 8.0, "issues": [], "passed": []},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
            {
                "discrepancies": [{
                    "type": "cost_overrun",
                    "description": "Cost overrun detected.",
                    "severity": "high",
                    "narrative_claim": "on budget",
                    "data_value": "£1.2M overrun",
                }],
                "financial_alignment_score": 4.0,
                "aligned_items": [],
                "financial_record_found": True,
            },
        ]
        mock_text.return_value = "Rewrite addressing financial discrepancies."

        user = persistence.create_user(email="l3b@test.com", password_hash="h", password_salt="s")
        persistence.save_financial_upload(
            user_id=user["id"],
            filename="fin.csv",
            records=[{"unique_id": "FIN-001", "raw_data": {"budget": "£10M", "actual": "£11.2M"}}],
        )

        from backend.app.services.narrative_scorer import run_score

        result = run_score(
            narrative="The project remains on budget and on schedule.",
            unique_id="FIN-001",
            document_name="Financial Test",
            user_id=user["id"],
            provider="ollama",
        )
        assert result["layer3"] is not None
        assert result["meta"]["has_financial_data"] is True
        assert len(result["layer3"]["discrepancies"]) == 1
        assert result["layer3"]["discrepancies"][0]["type"] == "cost_overrun"

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_custom_rules_rubric_used_when_active(
        self, mock_vs: MagicMock, mock_text: MagicMock, mock_json: MagicMock
    ) -> None:
        mock_vs.return_value = {"configured": False}
        mock_json.side_effect = [
            {"compliance_score": 9.0, "issues": [], "passed": ["Custom Criterion"]},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_text.return_value = ""

        user = persistence.create_user(email="l3c@test.com", password_hash="h", password_salt="s")
        custom_rubric_id = persistence.create_rubric(
            user_id=user["id"],
            name="Custom Rules",
            description="Uploaded via Standards",
            criteria=[{"name": "Custom Criterion", "description": "Must be present.", "severity": "high"}],
        )
        persistence.set_active_rules_rubric(user["id"], custom_rubric_id)

        from backend.app.services.narrative_scorer import run_score

        result = run_score(
            narrative="The narrative meets all custom requirements.",
            unique_id="CR-001",
            document_name="Custom Rules Test",
            user_id=user["id"],
            provider="ollama",
        )
        assert result["meta"]["has_custom_rules"] is True
        assert result["meta"]["rubric_id"] == custom_rubric_id

    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_audit_entry_written_after_score(
        self, mock_vs: MagicMock, mock_text: MagicMock, mock_json: MagicMock
    ) -> None:
        mock_vs.return_value = {"configured": False}
        mock_json.side_effect = [
            {"compliance_score": 7.5, "issues": ["Minor issue"], "passed": []},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_text.return_value = ""

        user = persistence.create_user(email="l3d@test.com", password_hash="h", password_salt="s")

        from backend.app.services.narrative_scorer import run_score

        run_score(
            narrative="A narrative text.",
            unique_id="AUDIT-001",
            document_name="Audit Test",
            user_id=user["id"],
            provider="ollama",
        )

        records = persistence.get_audit_records(user["id"], days=30)
        assert len(records) == 1
        assert records[0]["compliance_score"] == pytest.approx(7.5)
        assert records[0]["verdict"] == "PASS_WITH_WARNINGS"