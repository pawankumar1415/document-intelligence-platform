"""
batch_service.py — Batch narrative scoring from Excel/CSV upload.

Parses the uploaded file, runs narrative_scorer.run_score for each record,
and aggregates results into a BatchScoreResponse-shaped dict.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.app.services.excel_parser import (
    parse_csv_for_scoring,
    parse_docx_for_scoring,
    parse_excel_for_scoring,
    parse_pdf_for_scoring,
)
from backend.app.services.llm_provider import LLMProvider
from backend.app.services.narrative_scorer import run_score
from backend.app.services import persistence

logger = logging.getLogger(__name__)


def run_batch_score(
    raw_bytes: bytes,
    filename: str,
    user_id: int,
    rubric_id: int | None = None,
    provider: LLMProvider = "openai",
    model: str | None = None,
    top_k_references: int = 5,
    id_column: str | None = None,
    narrative_column: str | None = None,
) -> dict[str, Any]:
    """
    Parse an Excel/CSV file and score every narrative row.

    Returns a BatchScoreResponse-shaped dict.
    """
    # 1. Parse file
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "csv":
        records = parse_csv_for_scoring(raw_bytes, id_column=id_column, narrative_column=narrative_column)
    elif ext == "docx":
        records = parse_docx_for_scoring(raw_bytes, id_column=id_column, narrative_column=narrative_column)
    elif ext == "pdf":
        records = parse_pdf_for_scoring(raw_bytes, id_column=id_column, narrative_column=narrative_column)
    else:
        records = parse_excel_for_scoring(raw_bytes, filename=filename, id_column=id_column, narrative_column=narrative_column)

    # 2. Resolve rubric name for response
    if rubric_id is None:
        rubric_id = persistence.ensure_default_rubric(user_id)
    rubric = persistence.get_rubric(rubric_id, user_id)
    rubric_name = rubric["name"] if rubric else "Default"

    # 3. Score each record
    results: list[dict[str, Any]] = []
    pass_count = warn_count = fail_count = skip_count = 0

    for record in records:
        uid = record.get("unique_id", "UNKNOWN")
        narrative = record.get("narrative_text", "").strip()

        if not narrative:
            skip_count += 1
            results.append({
                "overall_verdict": "SKIPPED",
                "layer1": {"compliance_score": 0.0, "issues": [], "passed": []},
                "layer2": {
                    "abnormalities": [],
                    "reference_quality_score": 0.0,
                    "patterns_followed": [],
                    "references_used": 0,
                },
                "rewritten_narrative": "",
                "meta": {
                    "unique_id": uid,
                    "document_name": uid,
                    "rubric_id": rubric_id,
                    "rubric_name": rubric_name,
                    "references_used": 0,
                    "provider": provider,
                },
            })
            continue

        try:
            result = run_score(
                narrative=narrative,
                unique_id=uid,
                document_name=uid,
                user_id=user_id,
                rubric_id=rubric_id,
                provider=provider,
                model=model,
                top_k_references=top_k_references,
            )
            verdict = result["overall_verdict"]
            if verdict == "PASS":
                pass_count += 1
            elif verdict == "PASS_WITH_WARNINGS":
                warn_count += 1
            else:
                fail_count += 1
            results.append(result)

        except Exception as exc:
            logger.error("Batch scoring error for ID '%s': %s", uid, exc)
            fail_count += 1
            results.append({
                "overall_verdict": "ERROR",
                "layer1": {"compliance_score": 0.0, "issues": [str(exc)], "passed": []},
                "layer2": {
                    "abnormalities": [],
                    "reference_quality_score": 0.0,
                    "patterns_followed": [],
                    "references_used": 0,
                },
                "rewritten_narrative": "",
                "meta": {
                    "unique_id": uid,
                    "document_name": uid,
                    "rubric_id": rubric_id,
                    "rubric_name": rubric_name,
                    "references_used": 0,
                    "provider": provider,
                },
            })

    return {
        "total": len(results),
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "skip_count": skip_count,
        "rubric_name": rubric_name,
        "results": results,
    }