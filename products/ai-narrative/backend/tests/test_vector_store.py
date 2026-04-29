"""Tests for vector_store.py — mocked psycopg connections."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call

from backend.app.services.vector_store import (
    ReferenceMatch,
    _ensure_vector_literal,
    vector_store_status,
)


class TestEnsureVectorLiteral:
    def test_formats_float_list(self) -> None:
        result = _ensure_vector_literal([0.1, 0.2, 0.3])
        assert result == "[0.10000000,0.20000000,0.30000000]"

    def test_empty_list(self) -> None:
        result = _ensure_vector_literal([])
        assert result == "[]"

    def test_negative_values(self) -> None:
        result = _ensure_vector_literal([-0.5, 0.5])
        assert result.startswith("[-0.")
        assert "0.50000000" in result

    def test_precision_is_8_decimal_places(self) -> None:
        result = _ensure_vector_literal([1.0 / 3.0])
        # 1/3 to 8 dp = 0.33333333
        assert "0.33333333" in result


class TestVectorStoreStatus:
    def test_not_configured_when_no_dsn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "backend.app.services.vector_store.PGVECTOR_DSN", ""
        )
        status = vector_store_status()
        assert status["configured"] is False

    def test_configured_when_dsn_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "backend.app.services.vector_store.PGVECTOR_DSN",
            "postgresql://user:pass@localhost/testdb",
        )
        status = vector_store_status()
        assert status["configured"] is True

    def test_status_includes_embedding_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "backend.app.services.vector_store.PGVECTOR_DSN", ""
        )
        status = vector_store_status()
        assert "embedding_dim" in status
        assert "embedding_backend" in status
        assert "embedding_model_id" in status


class TestQuerySimilarReferences:
    @patch("backend.app.services.vector_store._connect")
    def test_returns_reference_matches(self, mock_connect: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            ("PROJ-001", "Narrative text A.", "Content A.", 0.92),
            ("PROJ-002", "Narrative text B.", "Content B.", 0.85),
        ]

        from backend.app.services.vector_store import query_similar_references

        results = query_similar_references(
            user_id=1,
            query_embedding=[0.1] * 768,
            limit=5,
        )

        assert len(results) == 2
        assert isinstance(results[0], ReferenceMatch)
        assert results[0].unique_id == "PROJ-001"
        assert results[0].score == pytest.approx(0.92)
        assert results[1].unique_id == "PROJ-002"

    @patch("backend.app.services.vector_store._connect")
    def test_returns_empty_list_when_no_matches(self, mock_connect: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        from backend.app.services.vector_store import query_similar_references

        results = query_similar_references(user_id=1, query_embedding=[0.1] * 768)
        assert results == []


class TestQueryAllNarratives:
    @patch("backend.app.services.vector_store._connect")
    def test_deduplicates_by_unique_id(self, mock_connect: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # Same unique_id appears in both reference and scored tables
        mock_cursor.fetchall.return_value = [
            ("PROJ-001", "Text A", "Text A", 0.95, "reference"),
            ("PROJ-001", "Text A", "Text A", 0.93, "scored"),
            ("PROJ-002", "Text B", "Text B", 0.88, "reference"),
        ]

        from backend.app.services.vector_store import query_all_narratives

        results = query_all_narratives(user_id=1, query_embedding=[0.1] * 768)

        # PROJ-001 should only appear once (highest score kept via ORDER BY first)
        unique_ids = [r.unique_id for r in results]
        assert unique_ids.count("PROJ-001") == 1
        assert "PROJ-002" in unique_ids

    @patch("backend.app.services.vector_store._connect")
    def test_respects_limit(self, mock_connect: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            (f"PROJ-{i:03d}", f"Text {i}", f"Text {i}", 0.9 - i * 0.01, "reference")
            for i in range(10)
        ]

        from backend.app.services.vector_store import query_all_narratives

        results = query_all_narratives(user_id=1, query_embedding=[0.1] * 768, limit=3)
        assert len(results) <= 3


class TestUpsertScoredNarrative:
    @patch("backend.app.services.vector_store._connect")
    def test_executes_upsert_query(self, mock_connect: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from backend.app.services.vector_store import upsert_scored_narrative

        upsert_scored_narrative(
            user_id=1,
            unique_id="PROJ-999",
            narrative_text="Scored narrative text.",
            embedding=[0.1] * 768,
        )

        mock_cursor.execute.assert_called_once()
        sql_called = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO scored_narratives" in sql_called
        assert "ON CONFLICT" in sql_called
        mock_conn.commit.assert_called_once()


class TestGetAvailablePeriods:
    @patch("backend.app.services.vector_store._connect")
    def test_extracts_periods_from_unique_ids(self, mock_connect: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            ("P-06 | Security Systems",),
            ("P-07 | Infrastructure",),
            ("P-06 | Civil Works",),
        ]

        from backend.app.services.vector_store import get_available_periods

        periods = get_available_periods(user_id=1)

        assert "P-06" in periods
        assert "P-07" in periods
        assert periods == sorted(periods)
        # P-06 should not be duplicated
        assert periods.count("P-06") == 1

    @patch("backend.app.services.vector_store._connect")
    def test_returns_empty_when_no_periods(self, mock_connect: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [("PROJ-001",), ("PROJ-002",)]

        from backend.app.services.vector_store import get_available_periods

        periods = get_available_periods(user_id=1)
        assert periods == []