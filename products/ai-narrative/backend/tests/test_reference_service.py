"""Tests for reference_service.py — reference file ingest and management."""
from __future__ import annotations

import io
import pytest
from unittest.mock import MagicMock, patch

from backend.app.services import persistence


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


def _make_csv_bytes(rows: list[dict]) -> bytes:
    import csv
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


class TestIngestReferenceFile:
    @patch("backend.app.services.reference_service.vector_store_status")
    def test_ingest_excel_without_vector_store(
        self, mock_vs: MagicMock
    ) -> None:
        mock_vs.return_value = {"configured": False}
        user = persistence.create_user(email="ingest1@test.com", password_hash="h", password_salt="s")

        raw = _make_excel_bytes([
            {"id": "PROJ-001", "narrative": "Project is on track with green status."},
            {"id": "PROJ-002", "narrative": "Delays reported in phase 2 procurement."},
        ])

        from backend.app.services.reference_service import ingest_reference_file

        result = ingest_reference_file(
            raw_bytes=raw,
            filename="references.xlsx",
            user_id=user["id"],
        )

        assert result["status"] == "ok"
        assert result["record_count"] == 2
        assert result["skipped"] == 0

        # Metadata should be saved in SQLite even without vector store
        files = persistence.list_reference_files(user["id"])
        assert len(files) == 1
        assert files[0]["record_count"] == 2

    @patch("backend.app.services.reference_service.vector_store_status")
    def test_ingest_csv_without_vector_store(
        self, mock_vs: MagicMock
    ) -> None:
        mock_vs.return_value = {"configured": False}
        user = persistence.create_user(email="ingest2@test.com", password_hash="h", password_salt="s")

        raw = _make_csv_bytes([
            {"reference": "REF-A", "narrative": "CSV narrative text here."},
        ])

        from backend.app.services.reference_service import ingest_reference_file

        result = ingest_reference_file(
            raw_bytes=raw,
            filename="refs.csv",
            user_id=user["id"],
        )

        assert result["status"] == "ok"
        assert result["record_count"] == 1

    @patch("backend.app.services.reference_service.vector_store_status")
    def test_ingest_empty_narratives_returns_empty_status(
        self, mock_vs: MagicMock
    ) -> None:
        mock_vs.return_value = {"configured": False}
        user = persistence.create_user(email="ingest3@test.com", password_hash="h", password_salt="s")

        raw = _make_excel_bytes([
            {"id": "PROJ-001", "narrative": ""},
            {"id": "PROJ-002", "narrative": "   "},
        ])

        from backend.app.services.reference_service import ingest_reference_file

        result = ingest_reference_file(
            raw_bytes=raw,
            filename="empty.xlsx",
            user_id=user["id"],
        )

        assert result["status"] == "empty"
        assert result["record_count"] == 0

    @patch("backend.app.services.reference_service.upsert_reference_narratives")
    @patch("backend.app.services.reference_service.embed_documents")
    @patch("backend.app.services.reference_service.vector_store_status")
    def test_ingest_with_vector_store_calls_embed_and_upsert(
        self,
        mock_vs: MagicMock,
        mock_embed: MagicMock,
        mock_upsert: MagicMock,
    ) -> None:
        mock_vs.return_value = {"configured": True}
        mock_embed.return_value = [[0.1] * 768, [0.2] * 768]
        user = persistence.create_user(email="ingest4@test.com", password_hash="h", password_salt="s")

        raw = _make_excel_bytes([
            {"id": "A", "narrative": "Narrative A for embedding test."},
            {"id": "B", "narrative": "Narrative B for embedding test."},
        ])

        from backend.app.services.reference_service import ingest_reference_file

        result = ingest_reference_file(
            raw_bytes=raw,
            filename="embed_test.xlsx",
            user_id=user["id"],
        )

        assert result["status"] == "ok"
        mock_embed.assert_called_once()
        mock_upsert.assert_called_once()

    @patch("backend.app.services.reference_service.embed_documents")
    @patch("backend.app.services.reference_service.vector_store_status")
    def test_ingest_embedding_failure_returns_error_status(
        self,
        mock_vs: MagicMock,
        mock_embed: MagicMock,
    ) -> None:
        mock_vs.return_value = {"configured": True}
        mock_embed.side_effect = RuntimeError("Embedding model unavailable")
        user = persistence.create_user(email="ingest5@test.com", password_hash="h", password_salt="s")

        raw = _make_excel_bytes([
            {"id": "X", "narrative": "A valid narrative that will fail to embed."},
        ])

        from backend.app.services.reference_service import ingest_reference_file

        result = ingest_reference_file(
            raw_bytes=raw,
            filename="fail_embed.xlsx",
            user_id=user["id"],
        )

        assert result["status"] == "error"
        assert "vector indexing failed" in result["message"]

    @patch("backend.app.services.reference_service.vector_store_status")
    def test_skipped_count_reflects_empty_rows(
        self, mock_vs: MagicMock
    ) -> None:
        mock_vs.return_value = {"configured": False}
        user = persistence.create_user(email="ingest6@test.com", password_hash="h", password_salt="s")

        raw = _make_excel_bytes([
            {"id": "VALID-1", "narrative": "Good narrative content here."},
            {"id": "EMPTY-1", "narrative": ""},
            {"id": "VALID-2", "narrative": "Another good narrative."},
        ])

        from backend.app.services.reference_service import ingest_reference_file

        result = ingest_reference_file(
            raw_bytes=raw,
            filename="mixed.xlsx",
            user_id=user["id"],
        )

        assert result["record_count"] == 2
        assert result["skipped"] == 1


class TestDeleteReferenceFile:
    @patch("backend.app.services.reference_service.vector_store_status")
    def test_delete_existing_file_returns_true(
        self, mock_vs: MagicMock
    ) -> None:
        mock_vs.return_value = {"configured": False}
        user = persistence.create_user(email="del1@test.com", password_hash="h", password_salt="s")
        file_id = persistence.save_reference_file(
            user_id=user["id"], filename="to_delete.xlsx",
            description="", record_count=5,
        )

        from backend.app.services.reference_service import delete_reference_file

        result = delete_reference_file(file_id, user["id"])
        assert result is True
        assert persistence.list_reference_files(user["id"]) == []

    @patch("backend.app.services.reference_service.vector_store_status")
    def test_delete_nonexistent_file_returns_false(
        self, mock_vs: MagicMock
    ) -> None:
        mock_vs.return_value = {"configured": False}
        user = persistence.create_user(email="del2@test.com", password_hash="h", password_salt="s")

        from backend.app.services.reference_service import delete_reference_file

        result = delete_reference_file(9999, user["id"])
        assert result is False

    @patch("backend.app.services.reference_service.delete_reference_file_vectors")
    @patch("backend.app.services.reference_service.vector_store_status")
    def test_delete_with_vector_store_calls_vector_cleanup(
        self,
        mock_vs: MagicMock,
        mock_del_vectors: MagicMock,
    ) -> None:
        mock_vs.return_value = {"configured": True}
        user = persistence.create_user(email="del3@test.com", password_hash="h", password_salt="s")
        file_id = persistence.save_reference_file(
            user_id=user["id"], filename="with_vectors.xlsx",
            description="", record_count=3,
        )

        from backend.app.services.reference_service import delete_reference_file

        delete_reference_file(file_id, user["id"])
        mock_del_vectors.assert_called_once_with(file_id)


class TestListReferenceFiles:
    @patch("backend.app.services.reference_service.vector_store_status")
    def test_list_returns_user_files_only(self, mock_vs: MagicMock) -> None:
        mock_vs.return_value = {"configured": False}
        user1 = persistence.create_user(email="list1@test.com", password_hash="h", password_salt="s")
        user2 = persistence.create_user(email="list2@test.com", password_hash="h", password_salt="s")

        persistence.save_reference_file(
            user_id=user1["id"], filename="u1.xlsx", description="", record_count=1
        )
        persistence.save_reference_file(
            user_id=user2["id"], filename="u2.xlsx", description="", record_count=2
        )

        from backend.app.services.reference_service import list_reference_files

        files = list_reference_files(user1["id"])
        assert len(files) == 1
        assert files[0]["filename"] == "u1.xlsx"