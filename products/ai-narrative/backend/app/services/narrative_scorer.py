"""
narrative_scorer.py — Core two-layer narrative scoring engine.

Layer 1: Structural & Quality Compliance
  LLM evaluates the narrative against rubric criteria.
  Returns compliance_score (0-10), issues, and passed checks.

Layer 2: Reference-Based Abnormality Detection
  Retrieves the most similar reference narratives from pgvector.
  LLM compares the input narrative against those references to surface
  abnormalities: missing information, unusual claims, data discrepancies,
  structural deviations, or tone mismatches.

Verdict:
  PASS              — compliance_score >= 8
  PASS_WITH_WARNINGS — compliance_score >= 6
  FAIL              — compliance_score < 6
"""
from __future__ import annotations

import logging
from typing import Any

from backend.app.services import persistence
from backend.app.services.llm_provider import LLMProvider, generate_json_object, generate_text
from backend.app.services.vector_store import query_similar_references, vector_store_status

logger = logging.getLogger(__name__)

_PASS_THRESHOLD = 8.0
_WARN_THRESHOLD = 6.0

# ── Layer 1 Prompts ──────────────────────────────────────────────────────────

_LAYER1_SYSTEM = """\
You are a professional narrative quality analyst. Evaluate the provided narrative \
against the rubric criteria below and return a structured JSON assessment.

Scoring guide (start at 10, deduct for unmet criteria):
  - high severity unmet:   -2 each
  - medium severity unmet: -1 each
  - low severity unmet:    -0.5 each
Minimum score is 0.

Return ONLY valid JSON:
{
  "compliance_score": <number 0-10, one decimal>,
  "issues": ["<specific issue, under 30 words>", ...],
  "passed": ["<criterion name that was met>", ...]
}"""

_LAYER1_USER_TEMPLATE = """\
RUBRIC CRITERIA:
{criteria_text}

NARRATIVE TO EVALUATE:
\"\"\"
{narrative}
\"\"\"
"""

# ── Layer 2 Prompts ──────────────────────────────────────────────────────────

_LAYER2_SYSTEM = """\
You are a narrative abnormality detector. You are given an input narrative and \
a set of similar reference narratives from the same domain.

Your task is to identify abnormalities — places where the input narrative \
significantly deviates from the patterns in the reference set.

Abnormality types:
  - missing_information: Information present in references but absent here
  - unusual_claim:       A claim or figure that references do not support
  - data_discrepancy:    Numeric/date values that conflict with reference patterns
  - structural:          Narrative structure differs significantly from references
  - tone:                Tone or language register differs from references

If no references are available, return empty abnormalities and note this in patterns_followed.

Return ONLY valid JSON:
{
  "abnormalities": [
    {
      "type": "missing_information|unusual_claim|data_discrepancy|structural|tone",
      "description": "<specific description, under 40 words>",
      "severity": "low|medium|high",
      "evidence": "<quote from input or reference supporting this finding>"
    }
  ],
  "reference_quality_score": <0-10>,
  "patterns_followed": ["<pattern this narrative correctly follows>"]
}"""

_LAYER2_USER_TEMPLATE = """\
INPUT NARRATIVE (ID: {unique_id}):
\"\"\"
{narrative}
\"\"\"

SIMILAR REFERENCE NARRATIVES ({ref_count} found):
{references_text}
"""

# ── Rewrite Prompts ──────────────────────────────────────────────────────────

_REWRITE_SYSTEM = """\
You are a senior technical writer specialising in project portfolio narratives. \
Your sole objective is to rewrite a project narrative so that it achieves the \
highest possible quality score against the provided rubric.

Rules you MUST follow:
1. Fix EVERY identified issue — do not leave any unresolved.
2. Satisfy ALL rubric criteria marked HIGH or MEDIUM.
3. Preserve every factual detail: project names, costs, dates, scope, milestones.
4. Do NOT fabricate new facts or figures that are not in the original.
5. Write in a clear, professional, unambiguous style suitable for an executive report.
6. Return ONLY the improved narrative text — no preamble, no labels, no commentary."""

_REWRITE_USER_TEMPLATE = """\
QUALITY RUBRIC (criteria the final narrative must satisfy):
{criteria_text}

SPECIFIC ISSUES TO RESOLVE (all must be fixed):
{issues_text}

ORIGINAL NARRATIVE:
\"\"\"
{narrative}
\"\"\"

Rewrite the narrative above so that every issue is resolved and every rubric \
criterion is met. Preserve all factual content. Output only the rewritten text.
"""


def _build_criteria_text(criteria: list[dict]) -> str:
    severity_labels = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}
    lines = []
    for c in criteria:
        label = severity_labels.get(c.get("severity", "medium"), "[MED]")
        lines.append(f"- {label} {c['name']}: {c.get('description', '')}")
    return "\n".join(lines)


def _build_references_text(references: list) -> str:
    if not references:
        return "No reference narratives available."
    parts = []
    for i, ref in enumerate(references, 1):
        score_pct = int(ref.score * 100)
        parts.append(
            f"--- Reference {i} (similarity {score_pct}%, ID: {ref.unique_id}) ---\n"
            f"{ref.narrative_text}\n"
        )
    return "\n".join(parts)


def _enforce_verdict(score: float) -> str:
    if score >= _PASS_THRESHOLD:
        return "PASS"
    if score >= _WARN_THRESHOLD:
        return "PASS_WITH_WARNINGS"
    return "FAIL"


def run_score(
    narrative: str,
    unique_id: str,
    document_name: str,
    user_id: int,
    rubric_id: int | None = None,
    provider: LLMProvider = "openai",
    model: str | None = None,
    top_k_references: int = 5,
) -> dict[str, Any]:
    """
    Run two-layer narrative scoring.

    Returns a dict matching the NarrativeScoreResult schema.
    """
    # ── 1. Resolve rubric ─────────────────────────────────────────────────────
    if rubric_id is None:
        rubric_id = persistence.ensure_default_rubric(user_id)

    rubric = persistence.get_rubric(rubric_id, user_id)
    if not rubric:
        rubric_id = persistence.ensure_default_rubric(user_id)
        rubric = persistence.get_rubric(rubric_id, user_id)

    criteria = rubric["criteria"]
    rubric_name = rubric["name"]

    # ── 2. Retrieve similar reference narratives ──────────────────────────────
    references = []
    if vector_store_status()["configured"]:
        try:
            from backend.app.services.embedding_service import embed_query
            query_embedding = embed_query(narrative[:2000])
            references = query_similar_references(
                user_id=user_id,
                query_embedding=query_embedding,
                limit=top_k_references,
            )
        except Exception as exc:
            logger.warning("Reference retrieval failed: %s", exc)

    # ── 3. Layer 1 — Structural & Quality ────────────────────────────────────
    criteria_text = _build_criteria_text(criteria)
    layer1_user = _LAYER1_USER_TEMPLATE.format(
        criteria_text=criteria_text,
        narrative=narrative[:4000],
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
        logger.error("Layer 1 scoring failed for '%s': %s", document_name, exc, exc_info=True)
        raise RuntimeError(f"Layer 1 scoring failed: {exc}") from exc

    # ── 4. Layer 2 — Reference-Based Abnormality Detection ───────────────────
    references_text = _build_references_text(references)
    layer2_user = _LAYER2_USER_TEMPLATE.format(
        unique_id=unique_id,
        narrative=narrative[:4000],
        ref_count=len(references),
        references_text=references_text,
    )

    try:
        layer2_raw = generate_json_object(
            provider=provider,
            system_prompt=_LAYER2_SYSTEM,
            user_prompt=layer2_user,
            temperature=0.2,
            model=model,
        )
        raw_abnormalities = layer2_raw.get("abnormalities", [])
        abnormalities = []
        for a in raw_abnormalities:
            if isinstance(a, dict):
                abnormalities.append({
                    "type": str(a.get("type", "structural")),
                    "description": str(a.get("description", "")),
                    "severity": str(a.get("severity", "medium")),
                    "evidence": str(a.get("evidence", "")),
                })
        ref_quality_score = float(layer2_raw.get("reference_quality_score", 0.0))
        ref_quality_score = max(0.0, min(10.0, ref_quality_score))
        patterns_followed: list[str] = [str(p) for p in layer2_raw.get("patterns_followed", [])]
    except Exception as exc:
        logger.warning("Layer 2 scoring failed for '%s': %s", document_name, exc)
        abnormalities = []
        ref_quality_score = 0.0
        patterns_followed = []

    # ── 5. AI Rewrite (when issues found) ────────────────────────────────────
    rewritten_narrative = ""
    all_issues = layer1_issues + [a["description"] for a in abnormalities if a.get("severity") in ("high", "medium")]
    if all_issues:
        try:
            issues_text = "\n".join(f"- {i}" for i in all_issues)
            rewrite_user = _REWRITE_USER_TEMPLATE.format(
                criteria_text=_build_criteria_text(criteria),
                issues_text=issues_text,
                narrative=narrative[:4000],
            )
            rewritten_narrative = generate_text(
                provider=provider,
                messages=[
                    {"role": "system", "content": _REWRITE_SYSTEM},
                    {"role": "user", "content": rewrite_user},
                ],
                temperature=0.4,
                model=model,
            )
        except Exception as exc:
            logger.warning("Rewrite generation failed: %s", exc)

    # ── 6. Build result ───────────────────────────────────────────────────────
    verdict = _enforce_verdict(compliance_score)

    result: dict[str, Any] = {
        "overall_verdict": verdict,
        "layer1": {
            "compliance_score": compliance_score,
            "issues": layer1_issues,
            "passed": layer1_passed,
        },
        "layer2": {
            "abnormalities": abnormalities,
            "reference_quality_score": ref_quality_score,
            "patterns_followed": patterns_followed,
            "references_used": len(references),
        },
        "rewritten_narrative": rewritten_narrative,
        "meta": {
            "unique_id": unique_id,
            "document_name": document_name,
            "rubric_id": rubric_id,
            "rubric_name": rubric_name,
            "references_used": len(references),
            "provider": provider,
        },
    }

    # ── 7. Persist ────────────────────────────────────────────────────────────
    try:
        persistence.save_score_result(
            user_id=user_id,
            unique_id=unique_id,
            document_name=document_name,
            overall_verdict=verdict,
            compliance_score=compliance_score,
            result=result,
        )
    except Exception:
        logger.warning("Failed to persist score result for '%s'", document_name, exc_info=True)

    return result