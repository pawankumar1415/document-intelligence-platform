"""
excel_parser.py — Excel parsing for batch document validation.

Handles two formats automatically:

FORMAT A — NDA MPPR Multi-row report (ported from reference ingest.py)
  - Sheet is named like '5a)NDA MPPR' or contains 'MPPR'
  - No traditional header row; each project spans 2-3 rows:
      Data row:      col0=empty, col1=project name, col3=RAG status (R/A/G/-)
      Narrative row: col0=project name, col1=narrative paragraph (>40 chars)
      Blank row:     separator
  - Period is extracted from the filename (e.g. 'P07 Exec...') or the sheet

FORMAT B — Generic tabular Excel (simple header-based)
  - First row is a header row
  - Must contain columns for: document name (name/title/document)
                        and: text (text/narrative/content/body)
  - One document per row

Detection: if the file contains a sheet whose name includes 'MPPR', Format A is used.
Otherwise Format B is tried. If Format B fails to find the required columns,
a clear error is raised explaining what columns are expected.

Requires: pandas, openpyxl  (pip install pandas openpyxl)
"""

from __future__ import annotations

import io
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Period extraction (Format A) ───────────────────────────────────────────────
_PERIOD_RE = re.compile(r"\b(P\d{2})\b", re.IGNORECASE)
_RAG_VALUES = {"r", "a", "g", "-", "n/a", "tbd"}


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
    """Scan the first 6 rows × 10 cols for a P## period string."""
    for i in range(min(6, len(df))):
        for j in range(min(10, len(df.columns))):
            cell = _safe(df.iloc[i, j])
            m = _PERIOD_RE.search(cell)
            if m:
                return m.group(1).upper()
    return ""


# ── Format A: NDA MPPR multi-row parser ───────────────────────────────────────

def _parse_mppr_sheet(df: Any, period: str) -> list[dict]:
    """
    Parse the NDA MPPR multi-row format from a pandas DataFrame.
    Returns list of {document_name, text} dicts.
    """
    projects = []

    for i in range(6, len(df)):           # data rows typically start at index 6
        row = df.iloc[i]

        col0 = _safe(row.iloc[0]) if len(row) > 0 else ""
        col1 = _safe(row.iloc[1]) if len(row) > 1 else ""
        col3 = _safe(row.iloc[3]) if len(row) > 3 else ""

        # A project DATA row: col0 empty, col1 = project name, col3 = RAG letter
        is_data_row = (
            col0 == ""
            and col1 != ""
            and len(col1) >= 3
            and col3.lower() in _RAG_VALUES
        )

        if not is_data_row:
            continue

        project_name = col1

        # Find the narrative on the next 1-3 rows
        # Narrative row: col0 matches project name, col1 is a long paragraph
        narrative_text = ""
        for j in range(i + 1, min(i + 4, len(df))):
            nrow = df.iloc[j]
            nc0 = _safe(nrow.iloc[0]) if len(nrow) > 0 else ""
            nc1 = _safe(nrow.iloc[1]) if len(nrow) > 1 else ""
            if nc0 and nc1 and len(nc1) > 40:
                narrative_text = nc1
                break

        if not narrative_text:
            # Still include the project so it shows as SKIPPED in results
            narrative_text = ""

        projects.append({
            "document_name": f"{period} | {project_name}" if period and period != "UNKNOWN" else project_name,
            "text": narrative_text,
        })

    return projects


def _parse_format_a(raw_bytes: bytes, filename: str = "") -> tuple[list[dict], str]:
    """Parse NDA MPPR multi-row format. Returns (items, period)."""
    import pandas as pd

    xl = pd.ExcelFile(io.BytesIO(raw_bytes))

    # Find the MPPR sheet — prefer sheets whose name contains "NDA" (e.g. "5a)NDA MPPR")
    # over period-specific sheets (e.g. "Pd08 MPPR WD9") which use a different layout.
    mppr_sheets = [s for s in xl.sheet_names if "MPPR" in s.upper() or "NDA" in s.upper()]
    if not mppr_sheets:
        raise ValueError(
            f"No MPPR sheet found. Available sheets: {xl.sheet_names}"
        )
    sheet_name = next((s for s in mppr_sheets if "NDA" in s.upper()), mppr_sheets[0])

    df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
    logger.info("MPPR sheet '%s': %d rows × %d cols", sheet_name, len(df), len(df.columns))

    period = _extract_period_from_filename(filename)
    if not period:
        period = _extract_period_from_sheet(df)
    if not period:
        period = "UNKNOWN"
        logger.warning("Could not determine period from filename or sheet content")

    items = _parse_mppr_sheet(df, period)
    logger.info("Parsed %d projects from MPPR sheet (period %s)", len(items), period)
    return items, period


# ── Format B: Generic tabular parser ──────────────────────────────────────────

def _parse_format_b(raw_bytes: bytes) -> list[dict]:
    """
    Parse a generic header-based Excel file.
    Expected columns: one for document name, one for text.
    Column matching is case-insensitive and flexible.
    """
    import pandas as pd

    df = pd.read_excel(io.BytesIO(raw_bytes), header=0)

    # Normalise column names
    col_map: dict[str, str] = {str(c).strip().lower(): str(c) for c in df.columns}

    # Find name column
    name_col = next(
        (col_map[k] for k in col_map if any(kw in k for kw in ("name", "title", "document", "project"))),
        None,
    )
    # Find text column
    text_col = next(
        (col_map[k] for k in col_map if any(kw in k for kw in ("text", "narrative", "content", "body", "description"))),
        None,
    )

    if not name_col or not text_col:
        found = list(col_map.keys())
        raise ValueError(
            f"Could not find required columns. "
            f"Need a column for document name (e.g. 'document_name', 'title', 'project') "
            f"and a column for text (e.g. 'text', 'narrative', 'content'). "
            f"Columns found: {found}"
        )

    items = []
    for _, row in df.iterrows():
        name = _safe(row[name_col])
        text = _safe(row[text_col])
        if name:
            items.append({"document_name": name, "text": text})

    logger.info("Parsed %d rows from generic tabular Excel", len(items))
    return items


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_excel_for_batch(raw_bytes: bytes, filename: str = "") -> list[dict]:
    """
    Auto-detect the Excel format and return a list of {document_name, text} dicts.

    Detection order:
    1. If the file contains a sheet with 'MPPR' or 'NDA' in the name → Format A (multi-row)
    2. Otherwise → Format B (generic tabular with header row)

    Raises ValueError with a descriptive message if neither format can be parsed.
    """
    try:
        import pandas as pd  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "pandas is required for Excel parsing. Run: pip install pandas openpyxl"
        ) from exc

    import pandas as pd

    # Peek at sheet names to decide format
    try:
        xl = pd.ExcelFile(io.BytesIO(raw_bytes))
        sheet_names = xl.sheet_names
    except Exception as exc:
        raise ValueError(f"Could not open Excel file: {exc}") from exc

    is_mppr = any("MPPR" in s.upper() or "NDA" in s.upper() for s in sheet_names)

    if is_mppr:
        logger.info("Detected MPPR multi-row format (sheets: %s)", sheet_names)
        try:
            items, _ = _parse_format_a(raw_bytes, filename=filename)
            return items
        except Exception as exc:
            logger.warning("MPPR parser failed (%s), falling back to generic parser", exc)

    # Generic tabular format
    try:
        return _parse_format_b(raw_bytes)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not parse Excel file: {exc}") from exc


def parse_csv_for_batch(raw_bytes: bytes) -> list[dict]:
    """
    Parse a CSV with a header row containing document name and text columns.
    Matching is case-insensitive and flexible.
    """
    import csv

    text_content = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text_content))

    fieldnames_lower = {(f or "").strip().lower(): (f or "") for f in (reader.fieldnames or [])}

    name_key = next(
        (fieldnames_lower[k] for k in fieldnames_lower if any(kw in k for kw in ("name", "title", "document", "project"))),
        None,
    )
    text_key = next(
        (fieldnames_lower[k] for k in fieldnames_lower if any(kw in k for kw in ("text", "narrative", "content", "body", "description"))),
        None,
    )

    if not name_key or not text_key:
        found = list(fieldnames_lower.keys())
        raise ValueError(
            f"CSV must have a column for document name (e.g. 'document_name', 'title') "
            f"and a column for text (e.g. 'text', 'narrative'). Found: {found}"
        )

    items = []
    for row in reader:
        name = str(row.get(name_key, "") or "").strip()
        text = str(row.get(text_key, "") or "").strip()
        if name:
            items.append({"document_name": name, "text": text})

    return items