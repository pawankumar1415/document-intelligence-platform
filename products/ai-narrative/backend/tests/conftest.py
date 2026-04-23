"""Pytest fixtures for AI Narrative Search tests."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """Give each test its own SQLite database."""
    db_file = tmp_path / "test_narrative.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))

    # Patch the persistence module's DB_PATH and DATA_DIR
    import backend.app.services.persistence as pers
    monkeypatch.setattr(pers, "DB_PATH", db_file)
    monkeypatch.setattr(pers, "DATA_DIR", tmp_path)
    pers.init_db()
    yield db_file


@pytest.fixture
def client() -> TestClient:
    from backend.app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def registered_user(client: TestClient) -> dict:
    resp = client.post("/api/v1/auth/register", json={"email": "test@example.com", "password": "TestPass123"})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture
def auth_token(registered_user: dict) -> str:
    return registered_user["access_token"]


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def user_id(registered_user: dict) -> int:
    return registered_user["user"]["id"]


# ── Sample data ───────────────────────────────────────────────────────────────

SAMPLE_NARRATIVE_GOOD = """
The project DCA remains Amber due to ongoing procurement delays in Phase 2.
The first delivery milestone is at risk due to supplier lead times extending beyond
the original schedule. Cost position has been maintained in period with no material
variance. Action is being taken to expedite procurement through alternative suppliers.
Schedule has deteriorated by 15 days due to the procurement delays described above.
The implications to contingency are minor; the project team is actively managing
risk and pursuing three opportunities to recover schedule.
"""

SAMPLE_NARRATIVE_BAD = """
Project delayed. Things are bad. Numbers are off. See attached.
"""

SAMPLE_NARRATIVE_MEDIUM = """
The project status has changed due to some issues in the delivery phase.
Costs have increased but we are working on it. The schedule has slipped.
We are taking action to resolve the problems identified in previous periods.
The team is aware of the risks and is monitoring the situation closely.
"""