"""Extended route tests covering new endpoints added in feature/narrative_search."""
from __future__ import annotations

import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _make_csv_bytes(rows: list[dict]) -> bytes:
    import csv
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


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


# ── Chat endpoint ──────────────────────────────────────────────────────────────

class TestChatRoute:
    @patch("backend.app.services.chat_service.generate_text")
    @patch("backend.app.services.chat_service.query_all_narratives")
    @patch("backend.app.services.chat_service.embed_query")
    def test_chat_returns_reply_and_sources(
        self,
        mock_embed: MagicMock,
        mock_query: MagicMock,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        mock_embed.return_value = [0.1] * 768
        match = MagicMock()
        match.unique_id = "P-06 | Security"
        match.narrative_text = "Project remains Amber. Delays in procurement."
        match.score = 0.88
        mock_query.return_value = [match]
        mock_generate.return_value = "The project is Amber status."

        resp = client.post(
            "/api/v1/chat",
            headers=auth_headers,
            json={
                "messages": [{"role": "user", "content": "What is the status?"}],
                "provider": "openai",
                "top_k": 5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] == "The project is Amber status."
        assert len(data["sources"]) == 1
        assert data["sources"][0]["unique_id"] == "P-06 | Security"
        assert "score" in data["sources"][0]

    def test_chat_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "Hello"}], "provider": "openai"},
        )
        assert resp.status_code == 401

    @patch("backend.app.services.chat_service.embed_query")
    def test_chat_retrieval_failure_returns_502(
        self,
        mock_embed: MagicMock,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        mock_embed.side_effect = RuntimeError("pgvector unavailable")

        resp = client.post(
            "/api/v1/chat",
            headers=auth_headers,
            json={"messages": [{"role": "user", "content": "Question"}], "provider": "openai"},
        )
        assert resp.status_code == 502

    @patch("backend.app.services.chat_service.generate_text")
    @patch("backend.app.services.chat_service.query_all_narratives")
    @patch("backend.app.services.chat_service.embed_query")
    def test_chat_invalid_provider_falls_back_to_openai(
        self,
        mock_embed: MagicMock,
        mock_query: MagicMock,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        mock_embed.return_value = [0.1] * 768
        mock_query.return_value = []
        mock_generate.return_value = "Answer."

        resp = client.post(
            "/api/v1/chat",
            headers=auth_headers,
            json={"messages": [{"role": "user", "content": "Q"}], "provider": "invalid_provider"},
        )
        assert resp.status_code == 200


# ── Reference periods endpoint ─────────────────────────────────────────────────

class TestReferencePeriods:
    @patch("backend.app.services.vector_store.get_available_periods")
    def test_periods_returns_sorted_list(
        self,
        mock_periods: MagicMock,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        mock_periods.return_value = ["P-06", "P-07", "P-08"]

        resp = client.get("/api/v1/references/periods", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "periods" in data
        assert data["periods"] == ["P-06", "P-07", "P-08"]

    @patch("backend.app.services.vector_store.get_available_periods")
    def test_periods_returns_empty_when_no_data(
        self,
        mock_periods: MagicMock,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        mock_periods.return_value = []

        resp = client.get("/api/v1/references/periods", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["periods"] == []

    def test_periods_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/references/periods")
        assert resp.status_code == 401

    @patch("backend.app.services.vector_store.get_available_periods")
    def test_periods_exception_returns_empty(
        self,
        mock_periods: MagicMock,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        mock_periods.side_effect = Exception("DB error")

        resp = client.get("/api/v1/references/periods", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["periods"] == []


# ── Score history endpoints ────────────────────────────────────────────────────

class TestScoreHistoryRoutes:
    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_list_scores_after_scoring(
        self,
        mock_vs: MagicMock,
        mock_text: MagicMock,
        mock_json: MagicMock,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        mock_vs.return_value = {"configured": False}
        mock_json.side_effect = [
            {"compliance_score": 9.0, "issues": [], "passed": []},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_text.return_value = ""

        client.post(
            "/api/v1/score",
            headers=auth_headers,
            json={
                "narrative": "Detailed narrative text for testing.",
                "unique_id": "HIST-001",
                "document_name": "History Test",
                "llm_provider": "openai",
            },
        )

        resp = client.get("/api/v1/scores", headers=auth_headers)
        assert resp.status_code == 200
        scores = resp.json()
        assert len(scores) >= 1
        assert any(s["unique_id"] == "HIST-001" for s in scores)

    def test_list_scores_empty_initially(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/api/v1/scores", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_score_not_found(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/api/v1/scores/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_list_scores_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/scores")
        assert resp.status_code == 401


# ── File text extraction endpoint ──────────────────────────────────────────────

class TestFileExtractTextRoute:
    def test_extract_txt_file(self, client: TestClient, auth_headers: dict) -> None:
        content = b"This is a plain text narrative.\nSecond line here."
        resp = client.post(
            "/api/v1/file/extract-text",
            headers=auth_headers,
            files={"file": ("doc.txt", io.BytesIO(content), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "This is a plain text narrative." in data["text"]
        assert data["char_count"] > 0
        assert data["filename"] == "doc.txt"

    def test_extract_unsupported_format_returns_400(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.post(
            "/api/v1/file/extract-text",
            headers=auth_headers,
            files={"file": ("data.xyz", io.BytesIO(b"content"), "application/octet-stream")},
        )
        assert resp.status_code == 400

    def test_extract_text_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/file/extract-text",
            files={"file": ("doc.txt", io.BytesIO(b"text"), "text/plain")},
        )
        assert resp.status_code == 401


# ── File row extraction endpoint ───────────────────────────────────────────────

class TestFileExtractRowsRoute:
    def test_extract_rows_from_csv(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        csv_bytes = _make_csv_bytes([
            {"project_id": "P001", "narrative": "A detailed project narrative text."},
            {"project_id": "P002", "narrative": "Another narrative for scoring test."},
        ])
        resp = client.post(
            "/api/v1/file/extract-rows",
            headers=auth_headers,
            files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "data.csv"
        assert len(data["rows"]) == 2
        assert data["rows"][0]["id"] == "P001"

    def test_extract_rows_from_excel(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        excel_bytes = _make_excel_bytes([
            {"id": "E001", "narrative": "Excel row narrative content."},
        ])
        resp = client.post(
            "/api/v1/file/extract-rows",
            headers=auth_headers,
            files={"file": ("data.xlsx", io.BytesIO(excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["rows"]) == 1

    def test_extract_rows_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/file/extract-rows",
            files={"file": ("data.csv", io.BytesIO(b"id,text\nA,B"), "text/csv")},
        )
        assert resp.status_code == 401


# ── Column detection endpoint ──────────────────────────────────────────────────

class TestColumnDetectRoute:
    def test_detect_columns_from_csv(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        csv_bytes = _make_csv_bytes([
            {"project_code": "P-001", "narrative_text": "Long narrative text content here for detection."},
            {"project_code": "P-002", "narrative_text": "Another longer narrative text for this test case."},
        ])
        resp = client.post(
            "/api/v1/columns/detect",
            headers=auth_headers,
            files={"file": ("cols.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "all_columns" in data
        assert "id_column" in data
        assert "narrative_column" in data
        assert "method" in data
        assert data["method"] in ("heuristic", "llm")

    def test_detect_columns_from_excel(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        excel_bytes = _make_excel_bytes([
            {"ref": "R1", "description": "Detailed description narrative text here."},
            {"ref": "R2", "description": "Another detailed description narrative text."},
        ])
        resp = client.post(
            "/api/v1/columns/detect",
            headers=auth_headers,
            files={"file": ("cols.xlsx", io.BytesIO(excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "ref" in data["all_columns"]
        assert "description" in data["all_columns"]

    def test_detect_columns_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/columns/detect",
            files={"file": ("cols.csv", io.BytesIO(b"a,b\n1,2"), "text/csv")},
        )
        assert resp.status_code == 401


# ── Batch scoring endpoint ─────────────────────────────────────────────────────

class TestBatchScoreRoute:
    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_batch_score_csv(
        self,
        mock_vs: MagicMock,
        mock_text: MagicMock,
        mock_json: MagicMock,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        mock_vs.return_value = {"configured": False}
        mock_json.side_effect = [
            {"compliance_score": 8.0, "issues": [], "passed": ["Clarity"]},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_text.return_value = ""

        csv_bytes = _make_csv_bytes([
            {"id": "B-001", "narrative": "Well written project narrative for batch scoring test."},
        ])

        resp = client.post(
            "/api/v1/score/batch",
            headers=auth_headers,
            files={"file": ("batch.csv", io.BytesIO(csv_bytes), "text/csv")},
            data={"llm_provider": "openai"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["pass_count"] == 1

    def test_batch_score_requires_auth(self, client: TestClient) -> None:
        csv_bytes = _make_csv_bytes([{"id": "X", "narrative": "text"}])
        resp = client.post(
            "/api/v1/score/batch",
            files={"file": ("b.csv", io.BytesIO(csv_bytes), "text/csv")},
            data={"llm_provider": "openai"},
        )
        assert resp.status_code == 401

    def test_batch_score_empty_file_returns_422(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.post(
            "/api/v1/score/batch",
            headers=auth_headers,
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
            data={"llm_provider": "openai"},
        )
        assert resp.status_code == 422


# ── Onboarding endpoint ────────────────────────────────────────────────────────

class TestOnboardingRoute:
    def test_complete_onboarding_returns_ok(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.post("/api/v1/user/complete-onboarding", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_complete_onboarding_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/api/v1/user/complete-onboarding")
        assert resp.status_code == 401


# ── Embedding config endpoint ──────────────────────────────────────────────────

class TestEmbeddingConfigRoute:
    def test_get_embedding_config(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/api/v1/embedding/config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "backend" in data
        assert "model_id" in data
        assert "dimension" in data

    def test_get_embedding_config_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embedding/config")
        assert resp.status_code == 401


# ── References list endpoint ───────────────────────────────────────────────────

class TestReferencesListRoute:
    def test_list_references_empty(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/api/v1/references", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_references_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/references")
        assert resp.status_code == 401


# ── Domain profile endpoints ───────────────────────────────────────────────────

class TestDomainProfileRoute:
    def test_get_profile_empty_when_no_data(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/api/v1/domain/profile", headers=auth_headers)
        assert resp.status_code == 200
        # No profile saved yet — domain_name is null and confidence is 0
        data = resp.json()
        assert data["domain_name"] is None
        assert data["confidence"] == 0.0

    def test_get_profile_returns_saved_profile(
        self, client: TestClient, auth_headers: dict, user_id: int
    ) -> None:
        from backend.app.services import persistence
        persistence.save_domain_profile(
            user_id,
            {
                "domain_name": "Test Domain",
                "period_label": "Period",
                "period_format": "P-XX",
                "status_codes": {},
                "key_terms": {},
                "suggested_questions": ["What is the status?"],
            },
            confidence=0.9,
        )
        resp = client.get("/api/v1/domain/profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["domain_name"] == "Test Domain"
        assert abs(data["confidence"] - 0.9) < 0.001

    def test_get_profile_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/domain/profile")
        assert resp.status_code == 401

    def test_delete_profile_returns_ok(
        self, client: TestClient, auth_headers: dict, user_id: int
    ) -> None:
        from backend.app.services import persistence
        persistence.save_domain_profile(user_id, {"domain_name": "To Delete"}, confidence=0.5)
        resp = client.delete("/api/v1/domain/profile", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        # Confirm it is gone — domain_name should be null after deletion
        resp2 = client.get("/api/v1/domain/profile", headers=auth_headers)
        assert resp2.json()["domain_name"] is None

    def test_delete_profile_requires_auth(self, client: TestClient) -> None:
        resp = client.delete("/api/v1/domain/profile")
        assert resp.status_code == 401