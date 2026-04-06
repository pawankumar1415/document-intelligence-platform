"""
validation_service.py — Generic rubric-based two-layer document validation pipeline.

Adapted from the Sentra NDA Narrative Validation system.  Instead of hardcoded
Good Practice guidelines, validation criteria are defined in user-owned Rubrics
stored in SQLite.

Layer 1: Structure & Quality
  — LLM evaluates the document against each criterion in the selected rubric.
  — Produces a compliance_score (0–10) and a list of specific issues / passed checks.

Layer 2: Internal Consistency
  — LLM scans for internal contradictions: figures cited in two places that differ,
    dates that are inconsistent, claims that contradict each other, etc.

Verdict thresholds:
  PASS              compliance_score >= 8
  PASS_WITH_WARNINGS compliance_score >= 6
  FAIL              compliance_score < 6

RAG context: the existing pgvector store is queried to surface similar documents
that have already been processed, giving the LLM grounding examples.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.services import persistence
from backend.app.services.llm_provider import LLMProvider, generate_json_object, generate_text

logger = logging.getLogger(__name__)

# ── Verdict thresholds ────────────────────────────────────────────────────────
_PASS_THRESHOLD = 8
_WARN_THRESHOLD = 6


# ── Prompt templates ──────────────────────────────────────────────────────────

_LAYER1_SYSTEM = """\
You are a professional document quality analyst. Your task is to evaluate a document \
against a set of rubric criteria and return a structured JSON assessment.

For each criterion, determine whether the document satisfies it, and if not, \
describe the specific issue concisely (under 25 words).

Scoring guide:
- Start at 10. Deduct points based on the severity of unmet criteria:
  - high severity unmet: -2 each
  - medium severity unmet: -1 each
  - low severity unmet: -0.5 each
- Minimum score is 0.

Return ONLY valid JSON matching this exact schema:
{
  "compliance_score": <number 0-10, one decimal place>,
  "issues": ["<specific issue description>", ...],
  "passed": ["<criterion name that was met>", ...]
}
"""

_LAYER1_USER_TEMPLATE = """\
RUBRIC CRITERIA:
{criteria_text}

{rag_context}
DOCUMENT TO EVALUATE:
\"\"\"
{document_text}
\"\"\"
"""

_LAYER2_SYSTEM = """\
You are a document consistency auditor. Your task is to identify any internal \
inconsistencies within a document: figures cited in multiple places that disagree, \
contradictory statements, dates that conflict, or claims that undermine each other.

Do NOT evaluate quality — only flag factual or logical contradictions within the document itself.

Return ONLY valid JSON matching this exact schema:
{
  "consistency_issues": ["<description of inconsistency>", ...],
  "passed": ["<aspect that was internally consistent>", ...]
}

If the document is fully consistent, return empty lists.
"""

_REWRITE_SYSTEM = """\
You are a professional technical writer. Rewrite the following document to fix \
all the identified issues listed below. Preserve all factual content. \
Return ONLY the rewritten document text with no preamble or commentary.
"""

_REWRITE_USER_TEMPLATE = """\
ISSUES TO FIX:
{issues_text}

ORIGINAL DOCUMENT:
\"\"\"
{document_text}
\"\"\"
"""


def _build_criteria_text(criteria: list[dict]) -> str:
    lines = []
    for c in criteria:
        severity_label = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}.get(c.get("severity", "medium"), "[MED]")
        lines.append(f"- {severity_label} {c['name']}: {c.get('description', '')}")
    return "\n".join(lines)


def _get_rag_context(text: str, user_id: int, project_id: int | None) -> str:
    """Retrieve similar documents from pgvector for grounding context."""
    try:
        from backend.app.services.embedding_service import embed_query
        from backend.app.services.vector_store import _connect, _ensure_vector_literal, ChunkMatch

        query_embedding = embed_query(text[:1500])
        vec_literal = _ensure_vector_literal(query_embedding)

        with _connect() as connection:
            with connection.cursor() as cursor:
                if project_id:
                    cursor.execute(
                        """
                        SELECT content, 1 - (embedding <=> %s::vector) AS score
                        FROM document_chunks
                        WHERE user_id = %s AND project_id = %s
                        ORDER BY embedding <=> %s::vector LIMIT 3
                        """,
                        (vec_literal, user_id, project_id, vec_literal),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT content, 1 - (embedding <=> %s::vector) AS score
                        FROM document_chunks
                        WHERE user_id = %s
                        ORDER BY embedding <=> %s::vector LIMIT 3
                        """,
                        (vec_literal, user_id, vec_literal),
                    )
                rows = cursor.fetchall()

        if not rows:
            return ""
        context = "SIMILAR DOCUMENTS FOR REFERENCE:\n"
        for i, row in enumerate(rows, 1):
            context += f"--- Reference {i} [similarity {float(row[1]):.2f}] ---\n{row[0]}\n\n"
        return context
    except Exception:
        logger.debug("RAG context retrieval skipped (vector store unavailable)", exc_info=True)
        return ""


def _enforce_verdict(score: float) -> str:
    if score >= _PASS_THRESHOLD:
        return "PASS"
    if score >= _WARN_THRESHOLD:
        return "PASS_WITH_WARNINGS"
    return "FAIL"


def run_validation(
    text: str,
    document_name: str,
    user_id: int,
    rubric_id: int | None = None,
    project_id: int | None = None,
    provider: LLMProvider = "openai",
    model: str | None = None,
) -> dict[str, Any]:
    """
    Run two-layer validation on a document text.

    Returns a dict matching the ValidationResult schema.
    """
    # ── 1. Resolve rubric ─────────────────────────────────────────────────────
    if rubric_id is None:
        rubric_id = persistence.ensure_default_rubric(user_id)

    rubric = persistence.get_rubric(rubric_id, user_id)
    if not rubric:
        rubric_id = persistence.ensure_default_rubric(user_id)
        rubric = persistence.get_rubric(rubric_id, user_id)

    criteria = rubric["criteria"]  # type: ignore[index]
    rubric_name = rubric["name"]  # type: ignore[index]

    # ── 2. Fetch RAG context ──────────────────────────────────────────────────
    rag_context = _get_rag_context(text, user_id=user_id, project_id=project_id)
    chunks_used = rag_context.count("--- Reference")

    # ── 3. Layer 1 — Structure & Quality ─────────────────────────────────────
    criteria_text = _build_criteria_text(criteria)
    layer1_user = _LAYER1_USER_TEMPLATE.format(
        criteria_text=criteria_text,
        rag_context=rag_context,
        document_text=text[:4000],
    )

    try:
        layer1_raw = generate_json_object(
            provider=provider,
            system_prompt=_LAYER1_SYSTEM,
            user_prompt=layer1_user,
            temperature=0.2,
            model=model,
        )
        compliance_score = float(layer1_raw.get("compliance_score", 5.0))
        compliance_score = max(0.0, min(10.0, compliance_score))
        layer1_issues: list[str] = [str(i) for i in layer1_raw.get("issues", [])]
        layer1_passed: list[str] = [str(p) for p in layer1_raw.get("passed", [])]
    except Exception as exc:
        logger.error("Layer 1 validation failed for '%s': %s", document_name, exc, exc_info=True)
        raise RuntimeError(f"Layer 1 validation failed: {exc}") from exc

    # ── 4. Layer 2 — Internal Consistency ────────────────────────────────────
    try:
        layer2_raw = generate_json_object(
            provider=provider,
            system_prompt=_LAYER2_SYSTEM,
            user_prompt=f'DOCUMENT:\n"""\n{text[:4000]}\n"""',
            temperature=0.1,
            model=model,
        )
        layer2_issues: list[str] = [str(i) for i in layer2_raw.get("consistency_issues", [])]
        layer2_passed: list[str] = [str(p) for p in layer2_raw.get("passed", [])]
    except Exception as exc:
        logger.warning("Layer 2 validation failed for '%s': %s", document_name, exc)
        layer2_issues = []
        layer2_passed = []

    # ── 5. AI Rewrite (only when issues found) ────────────────────────────────
    rewritten_text = ""
    all_issues = layer1_issues + layer2_issues
    if all_issues:
        try:
            issues_text = "\n".join(f"- {i}" for i in all_issues)
            rewrite_prompt = _REWRITE_USER_TEMPLATE.format(
                issues_text=issues_text,
                document_text=text[:4000],
            )
            rewritten_text = generate_text(
                provider=provider,
                messages=[
                    {"role": "system", "content": _REWRITE_SYSTEM},
                    {"role": "user", "content": rewrite_prompt},
                ],
                temperature=0.4,
                model=model,
            )
        except Exception as exc:
            logger.warning("Rewrite generation failed: %s", exc)

    # ── 6. Determine verdict ──────────────────────────────────────────────────
    verdict = _enforce_verdict(compliance_score)

    result: dict[str, Any] = {
        "overall_verdict": verdict,
        "layer1": {
            "compliance_score": compliance_score,
            "issues": layer1_issues,
            "passed": layer1_passed,
        },
        "layer2": {
            "consistency_issues": layer2_issues,
            "passed": layer2_passed,
        },
        "rewritten_text": rewritten_text,
        "meta": {
            "document_name": document_name,
            "rubric_id": rubric_id,
            "rubric_name": rubric_name,
            "chunks_used": chunks_used,
        },
    }

    # ── 7. Persist result ─────────────────────────────────────────────────────
    try:
        persistence.save_validation_result(
            user_id=user_id,
            rubric_id=rubric_id,
            document_name=document_name,
            verdict=verdict,
            score=compliance_score,
            result=result,
        )
    except Exception:
        logger.warning("Failed to persist validation result for '%s'", document_name, exc_info=True)

    return result


def run_batch_validation(
    items: list[dict[str, str]],
    user_id: int,
    rubric_id: int | None = None,
    project_id: int | None = None,
    provider: LLMProvider = "openai",
    model: str | None = None,
) -> dict[str, Any]:
    """
    Validate multiple documents.

    items: list of {"document_name": str, "text": str}
    Returns a BatchValidateResponse-shaped dict.
    """
    if rubric_id is None:
        rubric_id = persistence.ensure_default_rubric(user_id)

    rubric = persistence.get_rubric(rubric_id, user_id)
    rubric_name = rubric["name"] if rubric else "Unknown Rubric"  # type: ignore[index]

    results = []
    for item in items:
        name = item.get("document_name", "Untitled")
        text = item.get("text", "").strip()

        if not text:
            results.append({
                "overall_verdict": "SKIPPED",
                "layer1": {"compliance_score": 0, "issues": [], "passed": []},
                "layer2": {"consistency_issues": [], "passed": []},
                "rewritten_text": "",
                "meta": {"document_name": name, "rubric_id": rubric_id, "rubric_name": rubric_name, "chunks_used": 0},
            })
            continue

        try:
            result = run_validation(
                text=text,
                document_name=name,
                user_id=user_id,
                rubric_id=rubric_id,
                project_id=project_id,
                provider=provider,
                model=model,
            )
            results.append(result)
        except Exception as exc:
            logger.error("Batch validation error for '%s': %s", name, exc)
            results.append({
                "overall_verdict": "ERROR",
                "layer1": {"compliance_score": 0, "issues": [str(exc)], "passed": []},
                "layer2": {"consistency_issues": [], "passed": []},
                "rewritten_text": "",
                "meta": {"document_name": name, "rubric_id": rubric_id, "rubric_name": rubric_name, "chunks_used": 0},
            })

    return {
        "total": len(results),
        "rubric_name": rubric_name,
        "results": results,
    }