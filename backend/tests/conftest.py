"""
conftest.py — shared pytest fixtures for all test layers.

Isolation strategy:
  - Each test gets its own temporary SQLite file via `isolated_db`.
  - `persistence.DB_PATH` and `persistence.DATA_DIR` are monkeypatched so
    no test ever touches the real app.db.
  - The FastAPI TestClient fires the startup event (which calls init_db),
    so the patching must happen BEFORE the client is constructed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ── Database isolation ────────────────────────────────────────────────────────

@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """
    Patch persistence to use an isolated temp SQLite file and initialise it.
    Returns the Path to the test DB (rarely needed directly).
    """
    import backend.app.services.persistence as p

    test_db = tmp_path / "test.db"
    monkeypatch.setattr(p, "DB_PATH", test_db)
    monkeypatch.setattr(p, "DATA_DIR", tmp_path)
    p.init_db()
    return test_db


# ── FastAPI test client ───────────────────────────────────────────────────────

@pytest.fixture()
def client(isolated_db):
    """
    A TestClient backed by an isolated DB.
    The startup event fires inside the `with` block, re-running init_db
    against the already-patched DB_PATH — safe to call twice (IF NOT EXISTS).
    """
    from backend.app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── Auth helpers ──────────────────────────────────────────────────────────────

TEST_EMAIL    = "tester@bsbi.test"
TEST_PASSWORD = "TestPass123!"


@pytest.fixture()
def registered_user(client):
    """Register a test user and return the full auth response dict."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def auth_token(registered_user) -> str:
    """Bearer token for the registered test user."""
    return registered_user["access_token"]


@pytest.fixture()
def auth_headers(auth_token) -> dict[str, str]:
    """Auth header dict, ready to pass as `headers=` to TestClient calls."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture()
def user_id(registered_user) -> int:
    return int(registered_user["user"]["id"])


# ── Seeded project + artifact ─────────────────────────────────────────────────

@pytest.fixture()
def project(client, auth_headers):
    """A project owned by the test user."""
    resp = client.post(
        "/api/v1/projects",
        json={"name": "Test Engagement"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def artifact_id(isolated_db, user_id, project):
    """
    Insert a minimal artifact row directly via persistence so tests that need
    an artifact_id don't have to run the full LLM generation pipeline.
    """
    import backend.app.services.persistence as p

    aid = p.save_artifact(
        user_id=user_id,
        project_id=int(project["id"]),
        artifact_payload={
            "artifact_type": "sow",
            "artifact_name": "Test_SOW.docx",
            "file_path": "/tmp/test_sow.docx",
            "download_url": "/api/v1/download/Test_SOW.docx",
            "summary": "A test statement of work.",
            "sections": [],
            "slides": [],
        },
    )
    return aid