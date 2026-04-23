"""Integration tests for API routes."""
from __future__ import annotations

import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


class TestAuthRoutes:
    def test_register_success(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "new@test.com", "password": "StrongPass1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "new@test.com"

    def test_register_duplicate_email(self, client: TestClient) -> None:
        client.post("/api/v1/auth/register", json={"email": "dup@test.com", "password": "Pass1234"})
        resp = client.post("/api/v1/auth/register", json={"email": "dup@test.com", "password": "Pass1234"})
        assert resp.status_code == 409

    def test_register_short_password(self, client: TestClient) -> None:
        resp = client.post("/api/v1/auth/register", json={"email": "pw@test.com", "password": "short"})
        assert resp.status_code == 422

    def test_login_success(self, client: TestClient, registered_user: dict) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "TestPass123"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client: TestClient, registered_user: dict) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "WrongPass"},
        )
        assert resp.status_code == 401

    def test_protected_route_without_token(self, client: TestClient) -> None:
        resp = client.get("/api/v1/references")
        assert resp.status_code == 401


class TestHealth:
    def test_health_ok(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["product"] == "AI Narrative Search"


class TestRubricRoutes:
    def test_list_rubrics_creates_default(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/rubrics", headers=auth_headers)
        assert resp.status_code == 200
        rubrics = resp.json()
        assert len(rubrics) >= 1
        assert any(r["is_default"] for r in rubrics)

    def test_create_rubric(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/rubrics",
            headers=auth_headers,
            json={
                "name": "Custom Rubric",
                "description": "Test",
                "criteria": [
                    {"name": "Clarity", "description": "Must be clear.", "severity": "high"}
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Custom Rubric"
        assert len(data["criteria"]) == 1

    def test_delete_rubric(self, client: TestClient, auth_headers: dict) -> None:
        create_resp = client.post(
            "/api/v1/rubrics",
            headers=auth_headers,
            json={"name": "To Delete", "description": "", "criteria": []},
        )
        rubric_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/v1/rubrics/{rubric_id}", headers=auth_headers)
        assert del_resp.status_code == 200


class TestScoreRoutes:
    @patch("backend.app.services.narrative_scorer.generate_json_object")
    @patch("backend.app.services.narrative_scorer.generate_text")
    @patch("backend.app.services.narrative_scorer.vector_store_status")
    def test_score_narrative_pass(
        self,
        mock_vs: MagicMock,
        mock_text: MagicMock,
        mock_json: MagicMock,
        client: TestClient,
        auth_headers: dict,
    ) -> None:
        mock_vs.return_value = {"configured": False}
        mock_json.side_effect = [
            {"compliance_score": 8.5, "issues": [], "passed": ["Clarity"]},
            {"abnormalities": [], "reference_quality_score": 0.0, "patterns_followed": []},
        ]
        mock_text.return_value = ""

        resp = client.post(
            "/api/v1/score",
            headers=auth_headers,
            json={
                "narrative": "This is a well-written narrative that covers all required topics.",
                "unique_id": "PROJ-001",
                "document_name": "Test Project",
                "llm_provider": "openai",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_verdict"] == "PASS"
        assert data["layer1"]["compliance_score"] == 8.5

    def test_score_narrative_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/score",
            json={
                "narrative": "Test narrative.",
                "unique_id": "X",
                "document_name": "X",
                "llm_provider": "openai",
            },
        )
        assert resp.status_code == 401


class TestAnalyticsRoutes:
    def test_analytics_empty(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/analytics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overview"]["total_scored"] == 0
        assert data["overview"]["reference_files_count"] == 0
        assert data["recent_scores"] == []


class TestAdminRoutes:
    def test_non_admin_cannot_access(self, client: TestClient) -> None:
        client.post("/api/v1/auth/register", json={"email": "r1@test.com", "password": "Pass1234"})
        login = client.post("/api/v1/auth/login", json={"email": "r1@test.com", "password": "Pass1234"})
        client.post("/api/v1/auth/register", json={"email": "r2@test.com", "password": "Pass1234"})
        login2 = client.post("/api/v1/auth/login", json={"email": "r2@test.com", "password": "Pass1234"})
        token2 = login2.json()["access_token"]
        resp = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 403

    def test_admin_can_list_users(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/admin/users", headers=auth_headers)
        assert resp.status_code == 200
        users = resp.json()
        assert len(users) >= 1
        assert any(u["is_admin"] for u in users)