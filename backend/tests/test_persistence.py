"""
test_persistence.py — unit tests for every CRUD function in persistence.py.

All tests use the `isolated_db` fixture so they never touch the real app.db.
No LLM calls, no network — these run in milliseconds.
"""

from __future__ import annotations

import pytest


# ── Users ─────────────────────────────────────────────────────────────────────

def test_create_and_get_user(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("alice@test.com", "hash123", "salt456")
    assert user["email"] == "alice@test.com"
    assert int(user["id"]) > 0

    fetched = p.get_user_by_email("alice@test.com")
    assert fetched is not None
    assert fetched["email"] == "alice@test.com"


def test_duplicate_user_raises(isolated_db):
    from backend.app.services import persistence as p

    p.create_user("dup@test.com", "h", "s")
    with pytest.raises(ValueError, match="already exists"):
        p.create_user("dup@test.com", "h2", "s2")


def test_get_user_by_id(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("bob@test.com", "hash", "salt")
    fetched = p.get_user_by_id(int(user["id"]))
    assert fetched is not None
    assert fetched["email"] == "bob@test.com"


def test_get_nonexistent_user_returns_none(isolated_db):
    from backend.app.services import persistence as p

    assert p.get_user_by_email("nobody@test.com") is None
    assert p.get_user_by_id(99999) is None


# ── Sessions ──────────────────────────────────────────────────────────────────

def test_create_and_lookup_session(isolated_db):
    from backend.app.services import persistence as p
    from datetime import datetime, timezone, timedelta

    user = p.create_user("sess@test.com", "h", "s")
    expires = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
    p.create_session(token="tok123", user_id=int(user["id"]), expires_at=expires)

    found = p.get_user_by_session_token("tok123")
    assert found is not None
    assert found["email"] == "sess@test.com"


def test_expired_session_not_returned(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("exp@test.com", "h", "s")
    past = "2000-01-01T00:00:00+00:00"
    p.create_session(token="oldtok", user_id=int(user["id"]), expires_at=past)

    assert p.get_user_by_session_token("oldtok") is None


# ── Projects ──────────────────────────────────────────────────────────────────

def test_create_and_list_projects(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("proj@test.com", "h", "s")
    uid = int(user["id"])

    p1 = p.create_project(uid, "Engagement Alpha")
    p2 = p.create_project(uid, "Engagement Beta")

    projects = p.list_projects(uid)
    names = [pr["name"] for pr in projects]
    assert "Engagement Alpha" in names
    assert "Engagement Beta" in names
    assert len(projects) == 2


def test_project_isolation_between_users(isolated_db):
    from backend.app.services import persistence as p

    u1 = p.create_user("user1@test.com", "h", "s")
    u2 = p.create_user("user2@test.com", "h", "s")
    p.create_project(int(u1["id"]), "User1 Project")

    assert p.list_projects(int(u2["id"])) == []


# ── Artifacts ─────────────────────────────────────────────────────────────────

def test_save_and_get_artifact(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("art@test.com", "h", "s")
    uid = int(user["id"])
    proj = p.create_project(uid, "Art Project")
    pid = int(proj["id"])

    artifact_id = p.save_artifact(uid, pid, {
        "artifact_type": "sow",
        "artifact_name": "SOW_Test.docx",
        "file_path": "/tmp/sow.docx",
        "download_url": "/api/v1/download/SOW_Test.docx",
        "summary": "A statement of work.",
        "sections": [{"title": "Scope", "paragraphs": ["Do the work."], "bullets": []}],
        "slides": [],
    })

    assert artifact_id > 0
    art = p.get_artifact_by_id(artifact_id, uid)
    assert art is not None
    assert art["artifact_name"] == "SOW_Test.docx"
    assert art["artifact_type"] == "sow"


def test_artifact_not_visible_to_other_user(isolated_db):
    from backend.app.services import persistence as p

    u1 = p.create_user("owner@test.com", "h", "s")
    u2 = p.create_user("other@test.com", "h", "s")
    proj = p.create_project(int(u1["id"]), "P")
    aid = p.save_artifact(int(u1["id"]), int(proj["id"]), {
        "artifact_type": "sow", "artifact_name": "Private.docx",
        "file_path": "/x", "download_url": "/y", "summary": "s",
        "sections": [], "slides": [],
    })

    assert p.get_artifact_by_id(aid, int(u2["id"])) is None


# ── Templates ─────────────────────────────────────────────────────────────────

def test_create_and_list_templates(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("tpl@test.com", "h", "s")
    uid = int(user["id"])

    tpl = p.create_template(uid, "Custom SOW", "A custom SOW template", "sow", {"tone": "formal"})
    assert tpl["name"] == "Custom SOW"
    assert tpl["template_type"] == "sow"

    templates = p.list_templates(uid)
    assert any(t["name"] == "Custom SOW" for t in templates)


def test_list_templates_filters_by_type(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("tplfilter@test.com", "h", "s")
    uid = int(user["id"])
    p.create_template(uid, "SOW Tpl", "", "sow", {})
    p.create_template(uid, "PPT Tpl", "", "pptx", {})

    sow_only = p.list_templates(uid, template_type="sow")
    assert all(t["template_type"] == "sow" for t in sow_only)
    assert any(t["name"] == "SOW Tpl" for t in sow_only)


def test_default_templates_seeded(isolated_db):
    """_ensure_default_templates seeds exactly 4 defaults (one per type)."""
    from backend.app.services import persistence as p

    user = p.create_user("defaults@test.com", "h", "s")
    uid = int(user["id"])
    p._ensure_default_templates(uid)

    all_tpls = p.list_templates(uid)
    defaults = [t for t in all_tpls if t["is_default"]]
    types_covered = {t["template_type"] for t in defaults}

    assert len(defaults) == 4
    assert types_covered == {"sow", "pptx", "bid", "case_study"}


def test_delete_template(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("del@test.com", "h", "s")
    uid = int(user["id"])
    tpl = p.create_template(uid, "Temp", "", "sow", {})
    tid = int(tpl["id"])

    deleted = p.delete_template(tid, uid)
    assert deleted is True
    assert p.get_template(tid, uid) is None


def test_cannot_delete_default_template(isolated_db):
    """Default templates should be protected from deletion."""
    from backend.app.services import persistence as p

    user = p.create_user("nodelete@test.com", "h", "s")
    uid = int(user["id"])
    p._ensure_default_templates(uid)

    defaults = [t for t in p.list_templates(uid) if t["is_default"]]
    default_id = int(defaults[0]["id"])

    deleted = p.delete_template(default_id, uid)
    assert deleted is False


# ── Share Links ───────────────────────────────────────────────────────────────

def test_create_and_get_share_link(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("share@test.com", "h", "s")
    uid = int(user["id"])
    proj = p.create_project(uid, "Share Project")
    aid = p.save_artifact(uid, int(proj["id"]), {
        "artifact_type": "sow", "artifact_name": "Share.docx",
        "file_path": "/x", "download_url": "/y", "summary": "s",
        "sections": [], "slides": [],
    })

    link = p.create_share_link(aid, uid, expires_at=None)
    assert len(link["token"]) >= 20

    fetched = p.get_share_link(link["token"])
    assert fetched is not None
    assert fetched["artifact_id"] == aid
    assert fetched["artifact_name"] == "Share.docx"


def test_expired_share_link_not_returned(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("exp_share@test.com", "h", "s")
    uid = int(user["id"])
    proj = p.create_project(uid, "P")
    aid = p.save_artifact(uid, int(proj["id"]), {
        "artifact_type": "sow", "artifact_name": "X.docx",
        "file_path": "/x", "download_url": "/y", "summary": "",
        "sections": [], "slides": [],
    })

    past = "2000-01-01T00:00:00+00:00"
    link = p.create_share_link(aid, uid, expires_at=past)
    assert p.get_share_link(link["token"]) is None


def test_revoke_share_link(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("revoke@test.com", "h", "s")
    uid = int(user["id"])
    proj = p.create_project(uid, "P")
    aid = p.save_artifact(uid, int(proj["id"]), {
        "artifact_type": "sow", "artifact_name": "R.docx",
        "file_path": "/x", "download_url": "/y", "summary": "",
        "sections": [], "slides": [],
    })

    link = p.create_share_link(aid, uid, expires_at=None)
    p.delete_share_link(link["token"], uid)
    assert p.get_share_link(link["token"]) is None


# ── Artifact Feedback ─────────────────────────────────────────────────────────

def test_save_and_list_feedback(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("fb@test.com", "h", "s")
    uid = int(user["id"])
    proj = p.create_project(uid, "P")
    aid = p.save_artifact(uid, int(proj["id"]), {
        "artifact_type": "bid", "artifact_name": "Bid.docx",
        "file_path": "/x", "download_url": "/y", "summary": "",
        "sections": [], "slides": [],
    })

    p.save_feedback(aid, uid, section_title="Executive Summary", rating=1, note="Excellent section")
    p.save_feedback(aid, uid, section_title="Approach", rating=-1, note="Needs more detail")

    items = p.list_feedback(aid, uid)
    assert len(items) == 2
    ratings = {item["section_title"]: item["rating"] for item in items}
    assert ratings["Executive Summary"] == 1
    assert ratings["Approach"] == -1


# ── Project Overview ──────────────────────────────────────────────────────────

def test_project_overview_aggregates_correctly(isolated_db):
    from backend.app.services import persistence as p

    user = p.create_user("overview@test.com", "h", "s")
    uid = int(user["id"])
    proj = p.create_project(uid, "NHS Digital Programme")
    pid = int(proj["id"])

    # Add 2 documents
    for i in range(2):
        p.save_parsed_document(uid, pid, {
            "filename": f"doc{i}.txt", "file_type": "txt",
            "title": f"Document {i}", "text": "content " * 100,
            "word_count": 100, "paragraph_count": 5,
            "sections": [], "extraction_signals": [],
        })

    # Add 1 artifact
    p.save_artifact(uid, pid, {
        "artifact_type": "sow", "artifact_name": "SOW.docx",
        "file_path": "/x", "download_url": "/y", "summary": "SOW summary",
        "sections": [], "slides": [],
    })

    overview = p.get_project_overview(pid, uid)
    assert overview is not None
    assert overview["name"] == "NHS Digital Programme"
    assert len(overview["documents"]) == 2
    assert len(overview["artifacts"]) == 1