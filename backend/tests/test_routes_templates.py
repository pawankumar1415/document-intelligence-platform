"""
test_routes_templates.py — API route tests for the Template Library.

These test the full HTTP layer with a TestClient backed by an isolated DB.
No LLM calls are made.
"""

from __future__ import annotations


# ── List templates ─────────────────────────────────────────────────────────────

def test_list_templates_requires_auth(client):
    resp = client.get("/api/v1/templates")
    assert resp.status_code == 401


def test_list_templates_empty_for_new_user(client, auth_headers):
    resp = client.get("/api/v1/templates", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_templates_seeds_defaults_on_first_call(client, auth_headers):
    """
    The GET /templates route triggers _ensure_default_templates, so a new user
    should see exactly 4 default templates (one per document type) after first call.
    """
    resp = client.get("/api/v1/templates", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    defaults = [t for t in data if t["is_default"]]
    types = {t["template_type"] for t in defaults}
    assert len(defaults) == 4
    assert types == {"sow", "pptx", "bid", "case_study"}


def test_list_templates_filter_by_type(client, auth_headers):
    resp = client.get("/api/v1/templates?template_type=sow", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert all(t["template_type"] == "sow" for t in data)


# ── Create template ────────────────────────────────────────────────────────────

def test_create_template(client, auth_headers):
    payload = {
        "name": "Housing Sector SOW",
        "description": "Tailored for housing association engagements",
        "template_type": "sow",
        "config": {"tone": "formal", "include_assumptions": True},
    }
    resp = client.post("/api/v1/templates", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Housing Sector SOW"
    assert data["template_type"] == "sow"
    assert data["is_default"] is False
    assert "id" in data
    assert data["config"]["tone"] == "formal"


def test_create_template_requires_auth(client):
    payload = {"name": "x", "description": "", "template_type": "sow", "config": {}}
    resp = client.post("/api/v1/templates", json=payload)
    assert resp.status_code == 401


def test_create_template_invalid_type(client, auth_headers):
    payload = {"name": "x", "description": "", "template_type": "invalid_type", "config": {}}
    resp = client.post("/api/v1/templates", json=payload, headers=auth_headers)
    assert resp.status_code == 422  # Pydantic validation error


# ── Get single template ────────────────────────────────────────────────────────

def test_get_template(client, auth_headers):
    create_resp = client.post(
        "/api/v1/templates",
        json={"name": "My Template", "description": "", "template_type": "bid", "config": {}},
        headers=auth_headers,
    )
    template_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/templates/{template_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "My Template"


def test_get_nonexistent_template_returns_404(client, auth_headers):
    resp = client.get("/api/v1/templates/99999", headers=auth_headers)
    assert resp.status_code == 404


# ── Delete template ────────────────────────────────────────────────────────────

def test_delete_custom_template(client, auth_headers):
    create_resp = client.post(
        "/api/v1/templates",
        json={"name": "Delete Me", "description": "", "template_type": "pptx", "config": {}},
        headers=auth_headers,
    )
    template_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/v1/templates/{template_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/v1/templates/{template_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_cannot_delete_default_template(client, auth_headers):
    """Default templates return 404 on delete (protected)."""
    templates_resp = client.get("/api/v1/templates", headers=auth_headers)
    defaults = [t for t in templates_resp.json() if t["is_default"]]
    assert defaults, "No default templates found — seeding may have failed"

    default_id = defaults[0]["id"]
    resp = client.delete(f"/api/v1/templates/{default_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_template_isolated_between_users(client, auth_headers):
    """A template created by user A is not visible to user B."""
    # Create a template as user A
    client.post(
        "/api/v1/templates",
        json={"name": "User A Template", "description": "", "template_type": "sow", "config": {}},
        headers=auth_headers,
    )

    # Register user B
    b_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "userb@test.com", "password": "Pass123!"},
    )
    b_headers = {"Authorization": f"Bearer {b_resp.json()['access_token']}"}

    b_templates = client.get("/api/v1/templates", headers=b_headers).json()
    names = [t["name"] for t in b_templates]
    assert "User A Template" not in names