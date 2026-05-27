"""
reference_service.py — Upload, embed, and manage reference narrative files.

Reference files are Excel/CSV files containing "gold standard" narratives
that the scoring engine uses for comparison during abnormality detection.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.app.services import persistence
from backend.app.services.embedding_service import embed_documents
from backend.app.services.excel_parser import (
    build_content_string,
    parse_csv_for_scoring,
    parse_docx_for_scoring,
    parse_excel_for_scoring,
    parse_pdf_for_scoring,
)
from backend.app.services.vector_store import (
    delete_reference_file_vectors,
    upsert_reference_narratives,
    vector_store_status,
)

logger = logging.getLogger(__name__)

_DETECTION_SAMPLE_SIZE = 10


def _trigger_domain_detection(records: list[dict], user_id: int) -> None:
    """Run domain detection on a sample of records and persist the profile. Non-blocking."""
    try:
        from backend.app.services.domain_detector import detect_domain
        from backend.app.services import persistence

        sample = [r for r in records if r.get("narrative_text", "").strip()][:_DETECTION_SAMPLE_SIZE]
        if not sample:
            return

        profile = detect_domain(sample_records=sample)
        persistence.save_domain_profile(user_id, profile, confidence=profile.get("confidence", 0.0))
        logger.info(
            "Domain detected for user %d: '%s' (confidence %.2f)",
            user_id,
            profile.get("domain_name") or "unknown",
            profile.get("confidence", 0.0),
        )
    except Exception as exc:
        logger.warning("Domain detection skipped for user %d: %s", user_id, exc)


def ingest_reference_file(
    raw_bytes: bytes,
    filename: str,
    user_id: int,
    description: str = "",
) -> dict[str, Any]:
    """
    Parse an Excel/CSV file of reference narratives, embed them, and store in pgvector.

    Returns:
        { status, filename, record_count, skipped, message }
    """
    # 1. Parse file
    fname_lower = filename.lower()
    if fname_lower.endswith(".csv"):
        records = parse_csv_for_scoring(raw_bytes)
    elif fname_lower.endswith(".docx"):
        records = parse_docx_for_scoring(raw_bytes)
    elif fname_lower.endswith(".pdf"):
        records = parse_pdf_for_scoring(raw_bytes)
    else:
        records = parse_excel_for_scoring(raw_bytes, filename=filename)

    total = len(records)
    valid_records = [r for r in records if r.get("narrative_text", "").strip()]
    skipped = total - len(valid_records)

    if not valid_records:
        return {
            "status": "empty",
            "filename": filename,
            "record_count": 0,
            "skipped": skipped,
            "message": "No narrative text found in the uploaded file.",
        }

    # 2. Save metadata to SQLite first (get file_id)
    file_id = persistence.save_reference_file(
        user_id=user_id,
        filename=filename,
        description=description,
        record_count=len(valid_records),
    )

    # 3. Build content strings for embedding
    for record in valid_records:
        record["content"] = build_content_string(record)

    # 4. Embed (batch)
    if vector_store_status()["configured"]:
        contents = [r["content"] for r in valid_records]
        try:
            embeddings = embed_documents(contents)
            upsert_reference_narratives(
                file_id=file_id,
                user_id=user_id,
                records=valid_records,
                embeddings=embeddings,
            )
            logger.info("Indexed %d reference narratives (file_id=%d)", len(valid_records), file_id)
        except Exception as exc:
            logger.error("Failed to index reference narratives: %s", exc, exc_info=True)
            return {
                "status": "error",
                "filename": filename,
                "record_count": len(valid_records),
                "skipped": skipped,
                "message": f"File saved but vector indexing failed: {exc}",
            }
    else:
        logger.warning("pgvector not configured — reference file saved without embeddings.")

    # 5. Trigger domain detection (non-blocking — errors are logged, not raised)
    _trigger_domain_detection(valid_records, user_id)

    return {
        "status": "ok",
        "filename": filename,
        "record_count": len(valid_records),
        "skipped": skipped,
        "message": f"Successfully indexed {len(valid_records)} reference narratives.",
    }


def list_reference_files(user_id: int) -> list[dict[str, Any]]:
    return persistence.list_reference_files(user_id)


def delete_reference_file(file_id: int, user_id: int) -> bool:
    """Delete reference file metadata and its vector embeddings."""
    ref = persistence.get_reference_file(file_id, user_id)
    if not ref:
        return False

    # Remove vectors first
    if vector_store_status()["configured"]:
        try:
            delete_reference_file_vectors(file_id)
        except Exception as exc:
            logger.warning("Could not delete vectors for file_id=%d: %s", file_id, exc)

    # Remove SQLite record
    return persistence.delete_reference_file(file_id, user_id)