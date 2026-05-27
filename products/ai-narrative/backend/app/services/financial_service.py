"""
financial_service.py — Financial reference data for Layer 3 discrepancy checking.

Upload an Excel/CSV with monetary/schedule data keyed by the same unique_id
used in narratives. Layer 3 retrieves the matching row and asks the LLM to
identify discrepancies between the narrative's claims and the financial data.
"""
from __future__ import annotations

import io
import logging
from typing import Any

from backend.app.services import persistence

logger = logging.getLogger(__name__)


def ingest_financial_file(
    raw_bytes: bytes,
    filename: str,
    user_id: int,
) -> dict[str, Any]:
    """
    Parse a financial data file and store records per user.
    Replaces any previously uploaded financial data for this user.
    """
    import pandas as pd

    ext = filename.lower().rsplit(".", 1)[-1]
    try:
        df = pd.read_csv(io.BytesIO(raw_bytes), dtype=str) if ext == "csv" \
            else pd.read_excel(io.BytesIO(raw_bytes), dtype=str)
    except Exception as exc:
        raise RuntimeError(f"Could not parse financial file: {exc}") from exc

    df.fillna("", inplace=True)

    # Auto-detect the unique_id column (must match narrative unique_ids)
    col_lower = {c.lower().strip(): c for c in df.columns}
    uid_col = next(
        (col_lower[k] for k in (
            "unique_id", "document_name", "project_id", "project_name", "id", "name"
        ) if k in col_lower),
        df.columns[0] if len(df.columns) > 0 else None,
    )
    if not uid_col:
        raise RuntimeError("Could not identify a unique ID column in the financial file.")

    records: list[dict] = []
    for _, row in df.iterrows():
        uid = str(row[uid_col]).strip()
        if not uid or uid.lower() in ("nan", "none", ""):
            continue
        raw_data = {
            str(col): str(val)
            for col, val in row.items()
            if str(val).strip() not in ("", "nan", "None")
        }
        records.append({"unique_id": uid, "raw_data": raw_data})

    if not records:
        raise RuntimeError("No valid records found in the financial file.")

    persistence.save_financial_upload(
        user_id=user_id,
        filename=filename,
        records=records,
    )

    return {
        "status": "ok",
        "filename": filename,
        "record_count": len(records),
        "message": f"{len(records)} project financial records indexed.",
    }


def get_financial_record(user_id: int, unique_id: str) -> dict[str, Any] | None:
    """Retrieve the financial data dict for a given project unique_id."""
    return persistence.get_financial_record(user_id=user_id, unique_id=unique_id)