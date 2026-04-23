"""Tests for the persistence layer (SQLite CRUD)."""
from __future__ import annotations

import pytest
from backend.app.services import persistence


class TestUsers:
    def test_create_user_first_is_admin(self) -> None:
        user = persistence.create_user(
            email="admin@test.com",
            password_hash="hash",
            password_salt="salt",
        )
        assert user["id"] is not None
        assert user["is_admin"] is True

    def test_create_user_second_is_not_admin(self) -> None:
        persistence.create_user(email="first@test.com", password_hash="h", password_salt="s")
        user2 = persistence.create_user(email="second@test.com", password_hash="h2", password_salt="s2")
        assert user2["is_admin"] is False

    def test_get_user_by_email(self) -> None:
        persistence.create_user(email="find@test.com", password_hash="h", password_salt="s")
        user = persistence.get_user_by_email("find@test.com")
        assert user is not None
        assert user["email"] == "find@test.com"

    def test_get_user_by_email_missing(self) -> None:
        assert persistence.get_user_by_email("nobody@test.com") is None

    def test_session_create_and_lookup(self) -> None:
        user = persistence.create_user(email="session@test.com", password_hash="h", password_salt="s")
        persistence.create_session(
            token="tok123",
            user_id=user["id"],
            expires_at="2099-01-01T00:00:00+00:00",
        )
        found = persistence.get_user_by_session_token("tok123")
        assert found is not None
        assert found["email"] == "session@test.com"

    def test_session_expired_not_returned(self) -> None:
        user = persistence.create_user(email="exp@test.com", password_hash="h", password_salt="s")
        persistence.create_session(
            token="old_tok",
            user_id=user["id"],
            expires_at="2000-01-01T00:00:00+00:00",
        )
        assert persistence.get_user_by_session_token("old_tok") is None


class TestRubrics:
    def test_ensure_default_rubric_created(self) -> None:
        user = persistence.create_user(email="rubric@test.com", password_hash="h", password_salt="s")
        rubric_id = persistence.ensure_default_rubric(user["id"])
        assert rubric_id > 0

    def test_ensure_default_rubric_idempotent(self) -> None:
        user = persistence.create_user(email="rubric2@test.com", password_hash="h", password_salt="s")
        id1 = persistence.ensure_default_rubric(user["id"])
        id2 = persistence.ensure_default_rubric(user["id"])
        assert id1 == id2

    def test_get_rubric(self) -> None:
        user = persistence.create_user(email="getru@test.com", password_hash="h", password_salt="s")
        rubric_id = persistence.ensure_default_rubric(user["id"])
        rubric = persistence.get_rubric(rubric_id, user["id"])
        assert rubric is not None
        assert rubric["name"] == "Default Narrative Rubric"
        assert isinstance(rubric["criteria"], list)
        assert len(rubric["criteria"]) > 0

    def test_create_custom_rubric(self) -> None:
        user = persistence.create_user(email="custom@test.com", password_hash="h", password_salt="s")
        rid = persistence.create_rubric(
            user_id=user["id"],
            name="My Rubric",
            description="Test",
            criteria=[{"name": "Test", "description": "desc", "severity": "high"}],
        )
        rubric = persistence.get_rubric(rid, user["id"])
        assert rubric["name"] == "My Rubric"
        assert rubric["criteria"][0]["name"] == "Test"

    def test_delete_rubric(self) -> None:
        user = persistence.create_user(email="delru@test.com", password_hash="h", password_salt="s")
        rid = persistence.create_rubric(
            user_id=user["id"],
            name="To Delete",
            description="",
            criteria=[],
        )
        persistence.delete_rubric(rid, user["id"])
        assert persistence.get_rubric(rid, user["id"]) is None


class TestReferenceFiles:
    def test_save_and_list(self) -> None:
        user = persistence.create_user(email="ref@test.com", password_hash="h", password_salt="s")
        fid = persistence.save_reference_file(
            user_id=user["id"],
            filename="refs.xlsx",
            description="test refs",
            record_count=42,
        )
        assert fid > 0
        files = persistence.list_reference_files(user["id"])
        assert len(files) == 1
        assert files[0]["filename"] == "refs.xlsx"
        assert files[0]["record_count"] == 42

    def test_delete_reference_file(self) -> None:
        user = persistence.create_user(email="delref@test.com", password_hash="h", password_salt="s")
        fid = persistence.save_reference_file(
            user_id=user["id"],
            filename="del.xlsx",
            description="",
            record_count=5,
        )
        deleted = persistence.delete_reference_file(fid, user["id"])
        assert deleted is True
        assert persistence.list_reference_files(user["id"]) == []

    def test_delete_wrong_user_fails(self) -> None:
        user1 = persistence.create_user(email="u1@test.com", password_hash="h", password_salt="s")
        user2 = persistence.create_user(email="u2@test.com", password_hash="h", password_salt="s")
        fid = persistence.save_reference_file(
            user_id=user1["id"], filename="f.xlsx", description="", record_count=1
        )
        deleted = persistence.delete_reference_file(fid, user2["id"])
        assert deleted is False


class TestScoreResults:
    def test_save_and_list(self) -> None:
        user = persistence.create_user(email="score@test.com", password_hash="h", password_salt="s")
        sid = persistence.save_score_result(
            user_id=user["id"],
            unique_id="PROJ-001",
            document_name="Project Alpha",
            overall_verdict="PASS",
            compliance_score=8.5,
            result={"layer1": {}, "layer2": {}},
        )
        assert sid > 0
        results = persistence.list_score_results(user["id"])
        assert len(results) == 1
        assert results[0]["unique_id"] == "PROJ-001"
        assert results[0]["overall_verdict"] == "PASS"

    def test_analytics_overview(self) -> None:
        user = persistence.create_user(email="analytics@test.com", password_hash="h", password_salt="s")
        persistence.save_score_result(
            user_id=user["id"], unique_id="A", document_name="A",
            overall_verdict="PASS", compliance_score=9.0, result={}
        )
        persistence.save_score_result(
            user_id=user["id"], unique_id="B", document_name="B",
            overall_verdict="FAIL", compliance_score=4.0, result={}
        )
        overview = persistence.get_analytics_overview(user["id"])
        assert overview["total_scored"] == 2
        assert overview["pass_count"] == 1
        assert overview["fail_count"] == 1
        assert overview["avg_compliance_score"] == pytest.approx(6.5, rel=0.01)