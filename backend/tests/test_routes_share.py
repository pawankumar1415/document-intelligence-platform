"""
test_routes_share.py — API route tests for Share Links and Artifact Feedback.

Covers: create share link, public get, revoke, expiry, feedback thumbs up/down.
No LLM calls.
"""

from __future__ import annotations


# ── Create share link ─────────────────────────────────────────────────────────

def test_create_share_link(client, auth_headers, artifact_id):
    resp = client.post(
        f"/api/v1/artifacts/{artifact_id}/share",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert len(data["token"]) >= 20
    assert data["artifact_id"] == artifact_id
    assert data["expires_at"] is None


def test_create_share_link_with_expiry(client, auth_headers, artifact_id):
    resp = client.post(
        f"/api/v1/artifacts/{artifact_id}/share",
        json={"expires_in_days": 7},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["expires_at"] is not None  # ISO timestamp set


def test_create_share_link_requires_auth(client, artifact_id):
    resp = client.post(f"/api/v1/artifacts/{artifact_id}/share", json={})
    assert resp.status_code == 401


def test_create_share_link_unknown_artifact(client, auth_headers):
    resp = client.post("/api/v1/artifacts/99999/share", json={}, headers=auth_headers)
    assert resp.status_code == 404


# ── Public get (no auth) ──────────────────────────────────────────────────────

def test_public_get_share_link(client, auth_headers, artifact_id):
    create_resp = client.post(
        f"/api/v1/artifacts/{artifact_id}/share",
        json={},
        headers=auth_headers,
    )
    token = create_resp.json()["token"]

    # Call the public endpoint — NO auth headers
    public_resp = client.get(f"/api/v1/share/{token}")
    assert public_resp.status_code == 200
    data = public_resp.json()
    assert data["token"] == token
    assert data["artifact_name"] == "Test_SOW.docx"


def test_public_get_nonexistent_token_returns_404(client):
    resp = client.get("/api/v1/share/this-token-does-not-exist")
    assert resp.status_code == 404


def test_public_get_expired_link_returns_404(client, auth_headers, artifact_id):
    """Share link with past expiry should not be accessible publicly."""
    # We can't easily set expiry to past via the API (it only accepts future days)
    # so we use persistence directly to insert an expired link
    from datetime import datetime, timezone, timedelta
    import backend.app.services.persistence as p

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    link = p.create_share_link(artifact_id, artifact_id, expires_at=past)
    # Note: using artifact_id as a stand-in user_id here just to get a token
    # The important thing is get_share_link() filters out expired ones
    resp = client.get(f"/api/v1/share/{link['token']}")
    assert resp.status_code == 404


# ── List share links ──────────────────────────────────────────────────────────

def test_list_share_links(client, auth_headers, artifact_id):
    # Create two share links
    client.post(f"/api/v1/artifacts/{artifact_id}/share", json={}, headers=auth_headers)
    client.post(f"/api/v1/artifacts/{artifact_id}/share", json={}, headers=auth_headers)

    resp = client.get(f"/api/v1/artifacts/{artifact_id}/share", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert all(item["artifact_id"] == artifact_id for item in data)


# ── Revoke share link ─────────────────────────────────────────────────────────

def test_revoke_share_link(client, auth_headers, artifact_id):
    create_resp = client.post(
        f"/api/v1/artifacts/{artifact_id}/share",
        json={},
        headers=auth_headers,
    )
    token = create_resp.json()["token"]

    # Revoke
    del_resp = client.delete(f"/api/v1/share/{token}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Public get should now 404
    public_resp = client.get(f"/api/v1/share/{token}")
    assert public_resp.status_code == 404


def test_revoke_requires_auth(client, auth_headers, artifact_id):
    create_resp = client.post(
        f"/api/v1/artifacts/{artifact_id}/share",
        json={},
        headers=auth_headers,
    )
    token = create_resp.json()["token"]

    resp = client.delete(f"/api/v1/share/{token}")  # no auth
    assert resp.status_code == 401


# ── Artifact Feedback ─────────────────────────────────────────────────────────

def test_submit_thumbs_up(client, auth_headers, artifact_id):
    resp = client.post(
        f"/api/v1/artifacts/{artifact_id}/feedback",
        json={"rating": 1, "section_title": "Executive Summary", "note": "Great section"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rating"] == 1
    assert data["artifact_id"] == artifact_id
    assert data["section_title"] == "Executive Summary"


def test_submit_thumbs_down(client, auth_headers, artifact_id):
    resp = client.post(
        f"/api/v1/artifacts/{artifact_id}/feedback",
        json={"rating": -1, "section_title": "Scope", "note": "Needs more detail"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["rating"] == -1


def test_submit_feedback_invalid_rating(client, auth_headers, artifact_id):
    resp = client.post(
        f"/api/v1/artifacts/{artifact_id}/feedback",
        json={"rating": 0},  # 0 is not valid, must be 1 or -1
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_get_feedback(client, auth_headers, artifact_id):
    client.post(
        f"/api/v1/artifacts/{artifact_id}/feedback",
        json={"rating": 1, "section_title": "S1", "note": ""},
        headers=auth_headers,
    )
    client.post(
        f"/api/v1/artifacts/{artifact_id}/feedback",
        json={"rating": -1, "section_title": "S2", "note": "Weak"},
        headers=auth_headers,
    )

    resp = client.get(f"/api/v1/artifacts/{artifact_id}/feedback", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    sections = {item["section_title"] for item in data}
    assert sections == {"S1", "S2"}


def test_feedback_requires_auth(client, artifact_id):
    resp = client.post(
        f"/api/v1/artifacts/{artifact_id}/feedback",
        json={"rating": 1},
    )
    assert resp.status_code == 401


def test_feedback_unknown_artifact_returns_404(client, auth_headers):
    resp = client.post(
        "/api/v1/artifacts/99999/feedback",
        json={"rating": 1, "section_title": "", "note": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── Project overview route ────────────────────────────────────────────────────

def test_project_overview_route(client, auth_headers, project):
    project_id = project["id"]
    resp = client.get(f"/api/v1/projects/{project_id}/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == project_id
    assert data["name"] == "Test Engagement"
    assert isinstance(data["documents"], list)
    assert isinstance(data["artifacts"], list)
    assert isinstance(data["recent_validations"], list)
    assert isinstance(data["clause_count"], int)


def test_project_overview_wrong_user_returns_404(client, auth_headers, project):
    """User B cannot see User A's project overview."""
    b_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "userb_ov@test.com", "password": "Pass123!"},
    )
    b_headers = {"Authorization": f"Bearer {b_resp.json()['access_token']}"}

    resp = client.get(
        f"/api/v1/projects/{project['id']}/overview",
        headers=b_headers,
    )
    assert resp.status_code == 404