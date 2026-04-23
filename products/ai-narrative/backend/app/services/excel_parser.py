"""
excel_parser.py — Flexible Excel/CSV parser for narrative scoring.

Detects three formats automatically:

FORMAT A — NDA MPPR multi-row (legacy compatibility)
  Sheet name contains 'MPPR' or 'NDA'
  Each project spans 2-3 rows; narrative in col1 of the narrative row

FORMAT B — Generic tabular with headers
  First row is a header row.
  Auto-detects columns for:
    unique_id   — "id", "uid", "unique_id", "ref", "reference", "project", "code", "name"
    narrative   — "narrative", "text", "description", "content", "body", "summary", "commentary", "note"
  All other columns are preserved as extra_fields.

FORMAT C — CSV
  Same column detection as Format B.
"""
from __future__ import annotations

import io
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_PERIOD_RE = re.compile(r"\b(P\d{2})\b", re.IGNORECASE)
_RAG_VALUES = {"r", "a", "g", "-", "n/a", "tbd"}

# Column keyword sets for auto-detection
_ID_KEYWORDS = ("id", "uid", "unique_id", "ref", "reference", "project", "code", "identifier", "name", "document")
_TEXT_KEYWORDS = ("narrative", "text", "description", "content", "body", "summary", "commentary", "note", "comment")


def _safe(value: Any, default: str = "") -> str:
    try:
        import pandas as pd
        if pd.isna(value):
            return default
    except (TypeError, ValueError, ImportError):
        pass
    if value is None:
        return default
    return str(value).strip()


def _extract_period_from_filename(filename: str) -> str:
    m = _PERIOD_RE.search(filename or "")
    return m.group(1).upper() if m else ""


def _extract_period_from_sheet(df: Any) -> str:
    for i in range(min(6, len(df))):
        for j in range(min(10, len(df.columns))):
            cell = _safe(df.iloc[i, j])
            m = _PERIOD_RE.search(cell)
            if m:
                return m.group(1).upper()
    return ""


# ── Format A: NDA MPPR ────────────────────────────────────────────────────────

def _parse_mppr_sheet(df: Any, period: str) -> list[dict]:
    records = []
    for i in range(6, len(df)):
        row = df.iloc[i]
        col0 = _safe(row.iloc[0]) if len(row) > 0 else ""
        col1 = _safe(row.iloc[1]) if len(row) > 1 else ""
        col3 = _safe(row.iloc[3]) if len(row) > 3 else ""

        is_data_row = (col0 == "" and col1 != "" and len(col1) >= 3 and col3.lower() in _RAG_VALUES)
        if not is_data_row:
            continue

        project_name = col1
        narrative_text = ""
        for j in range(i + 1, min(i + 4, len(df))):
            nrow = df.iloc[j]
            nc0 = _safe(nrow.iloc[0]) if len(nrow) > 0 else ""
            nc1 = _safe(nrow.iloc[1]) if len(nrow) > 1 else ""
            if nc0 and nc1 and len(nc1) > 40:
                narrative_text = nc1
                break

        uid = f"{period}|{project_name}" if period and period != "UNKNOWN" else project_name
        records.append({
            "unique_id": uid,
            "narrative_text": narrative_text,
            "extra_fields": {"rag_status": col3, "period": period},
        })

    return records


def _parse_format_a(raw_bytes: bytes, filename: str = "") -> tuple[list[dict], str]:
    import pandas as pd

    xl = pd.ExcelFile(io.BytesIO(raw_bytes))
    mppr_sheets = [s for s in xl.sheet_names if "MPPR" in s.upper() or "NDA" in s.upper()]
    sheet_name = next((s for s in mppr_sheets if "NDA" in s.upper()), mppr_sheets[0])
    df = pd.read_excel(xl, sheet_name=sheet_name, header=None)

    period = _extract_period_from_filename(filename) or _extract_period_from_sheet(df) or "UNKNOWN"
    records = _parse_mppr_sheet(df, period)
    logger.info("MPPR: parsed %d records (period %s) from '%s'", len(records), period, sheet_name)
    return records, period


# ── Format B: Generic tabular ────────────────────────────────────────────────

def _find_column(col_map: dict[str, str], keywords: tuple[str, ...]) -> str | None:
    # Phase 1: column name exactly equals a keyword
    for key, original in col_map.items():
        if key in keywords:
            return original
    # Phase 2: the LAST word in the column name (split by _ / - / space) is a keyword
    # e.g. "document_name" → last word "name" matches; "project_end_p50" → "p50" does not
    for key, original in col_map.items():
        parts = re.split(r"[^a-z0-9]", key)
        if parts and parts[-1] in keywords:
            return original
    return None


def _parse_format_b(
    raw_bytes: bytes,
    id_column: str | None = None,
    narrative_column: str | None = None,
) -> list[dict]:
    import pandas as pd

    df = pd.read_excel(io.BytesIO(raw_bytes), header=0)
    col_map = {str(c).strip().lower(): str(c) for c in df.columns}

    # Use user-confirmed columns if supplied, otherwise auto-detect
    id_col = id_column if id_column and id_column in df.columns else _find_column(col_map, _ID_KEYWORDS)
    text_col = narrative_column if narrative_column and narrative_column in df.columns else _find_column(col_map, _TEXT_KEYWORDS)

    if not id_col or not text_col:
        raise ValueError(
            f"Could not identify required columns. "
            f"Need a unique ID column (e.g. 'id', 'project', 'reference') "
            f"and a narrative column (e.g. 'narrative', 'text', 'description'). "
            f"Columns found: {list(col_map.keys())}"
        )

    records = []
    for _, row in df.iterrows():
        uid = _safe(row[id_col])
        narrative = _safe(row[text_col])
        if not uid:
            continue
        extra = {c: _safe(row[c]) for c in df.columns if c not in (id_col, text_col)}
        records.append({"unique_id": uid, "narrative_text": narrative, "extra_fields": extra})

    logger.info("Generic tabular: parsed %d records", len(records))
    return records


# ── Format C: CSV ─────────────────────────────────────────────────────────────

def _parse_csv(
    raw_bytes: bytes,
    id_column: str | None = None,
    narrative_column: str | None = None,
) -> list[dict]:
    import csv

    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    all_fields = list(reader.fieldnames or [])
    fieldnames_lower = {(f or "").strip().lower(): (f or "") for f in all_fields}

    id_key = id_column if id_column and id_column in all_fields else _find_column(fieldnames_lower, _ID_KEYWORDS)
    text_key = narrative_column if narrative_column and narrative_column in all_fields else _find_column(fieldnames_lower, _TEXT_KEYWORDS)

    if not id_key or not text_key:
        raise ValueError(
            f"CSV must have a unique ID column and a narrative text column. "
            f"Found: {list(fieldnames_lower.keys())}"
        )

    records = []
    for row in reader:
        uid = str(row.get(id_key, "") or "").strip()
        narrative = str(row.get(text_key, "") or "").strip()
        if not uid:
            continue
        extra = {k: str(v or "").strip() for k, v in row.items() if k not in (id_key, text_key)}
        records.append({"unique_id": uid, "narrative_text": narrative, "extra_fields": extra})

    logger.info("CSV: parsed %d records", len(records))
    return records


# ── Format D: DOCX table ─────────────────────────────────────────────────────

def _parse_docx(
    raw_bytes: bytes,
    id_column: str | None = None,
    narrative_column: str | None = None,
) -> list[dict]:
    from docx import Document  # type: ignore

    doc = Document(io.BytesIO(raw_bytes))
    if not doc.tables:
        raise ValueError("No tables found in the .docx file.")

    table = doc.tables[0]
    headers = [cell.text.strip() for cell in table.rows[0].cells]
    col_map = {h.strip().lower(): h for h in headers}

    id_col = id_column if id_column and id_column in headers else _find_column(col_map, _ID_KEYWORDS)
    text_col = narrative_column if narrative_column and narrative_column in headers else _find_column(col_map, _TEXT_KEYWORDS)

    if not id_col or not text_col:
        raise ValueError(
            f"Could not identify required columns in .docx table. "
            f"Columns found: {headers}"
        )

    records = []
    for row in table.rows[1:]:
        row_data = {headers[i]: cell.text.strip() for i, cell in enumerate(row.cells) if i < len(headers)}
        uid = row_data.get(id_col, "").strip()
        narrative = row_data.get(text_col, "").strip()
        if not uid:
            continue
        extra = {k: v for k, v in row_data.items() if k not in (id_col, text_col)}
        records.append({"unique_id": uid, "narrative_text": narrative, "extra_fields": extra})

    logger.info("DOCX: parsed %d records", len(records))
    return records


# ── Format E: PDF table ──────────────────────────────────────────────────────

def _parse_pdf(
    raw_bytes: bytes,
    id_column: str | None = None,
    narrative_column: str | None = None,
) -> list[dict]:
    import pdfplumber  # type: ignore

    def _clean(val: str) -> str:
        return " ".join(val.split())

    all_rows: list[list[str]] = []
    with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for tbl in tables:
                for row in tbl:
                    all_rows.append([_clean(str(cell or "")) for cell in row])

    if not all_rows:
        raise ValueError("No tables found in the PDF file.")

    headers = all_rows[0]
    col_map = {h.strip().lower(): h for h in headers}

    id_col = id_column if id_column and id_column in headers else _find_column(col_map, _ID_KEYWORDS)
    text_col = narrative_column if narrative_column and narrative_column in headers else _find_column(col_map, _TEXT_KEYWORDS)

    if not id_col or not text_col:
        raise ValueError(
            f"Could not identify required columns in PDF table. "
            f"Columns found: {headers}"
        )

    id_idx = headers.index(id_col)
    text_idx = headers.index(text_col)

    records = []
    for row in all_rows[1:]:
        if len(row) <= max(id_idx, text_idx):
            continue
        uid = row[id_idx].strip()
        narrative = row[text_idx].strip()
        if not uid:
            continue
        extra = {headers[i]: row[i] for i in range(len(headers)) if i not in (id_idx, text_idx) and i < len(row)}
        records.append({"unique_id": uid, "narrative_text": narrative, "extra_fields": extra})

    logger.info("PDF: parsed %d records", len(records))
    return records


# ── Public API ────────────────────────────────────────────────────────────────

def parse_excel_for_scoring(
    raw_bytes: bytes,
    filename: str = "",
    id_column: str | None = None,
    narrative_column: str | None = None,
) -> list[dict]:
    """
    Auto-detect Excel format and return a list of:
      { unique_id: str, narrative_text: str, extra_fields: dict }

    Detection priority:
      1. Sheet name contains 'MPPR' or 'NDA' → Format A (NDA multi-row)
      2. Otherwise → Format B (generic header-based)
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required: pip install pandas openpyxl") from exc

    try:
        xl = pd.ExcelFile(io.BytesIO(raw_bytes))
        sheet_names = xl.sheet_names
    except Exception as exc:
        raise ValueError(f"Could not open Excel file: {exc}") from exc

    is_mppr = any("MPPR" in s.upper() or "NDA" in s.upper() for s in sheet_names)

    if is_mppr and not id_column and not narrative_column:
        try:
            records, _ = _parse_format_a(raw_bytes, filename=filename)
            return records
        except Exception as exc:
            logger.warning("MPPR parser failed (%s), falling back to generic parser", exc)

    return _parse_format_b(raw_bytes, id_column=id_column, narrative_column=narrative_column)


def parse_csv_for_scoring(
    raw_bytes: bytes,
    id_column: str | None = None,
    narrative_column: str | None = None,
) -> list[dict]:
    """Parse a CSV file. Returns same format as parse_excel_for_scoring."""
    return _parse_csv(raw_bytes, id_column=id_column, narrative_column=narrative_column)


def parse_docx_for_scoring(
    raw_bytes: bytes,
    id_column: str | None = None,
    narrative_column: str | None = None,
) -> list[dict]:
    """Parse the first table in a .docx file. Returns same format as parse_excel_for_scoring."""
    return _parse_docx(raw_bytes, id_column=id_column, narrative_column=narrative_column)


def parse_pdf_for_scoring(
    raw_bytes: bytes,
    id_column: str | None = None,
    narrative_column: str | None = None,
) -> list[dict]:
    """Parse tables from a PDF file. Returns same format as parse_excel_for_scoring."""
    return _parse_pdf(raw_bytes, id_column=id_column, narrative_column=narrative_column)


def build_content_string(record: dict) -> str:
    """Build a concatenated content string for embedding from a record dict."""
    uid = record.get("unique_id", "")
    narrative = record.get("narrative_text", "")
    extras = record.get("extra_fields", {})

    parts = [f"ID: {uid}", f"Narrative: {narrative}"]
    for key, value in extras.items():
        if value and str(value).strip():
            parts.append(f"{key}: {value}")

    return " | ".join(parts)