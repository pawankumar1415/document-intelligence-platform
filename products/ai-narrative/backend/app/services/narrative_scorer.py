"""
narrative_scorer.py — Core three-layer narrative scoring engine.

Layer 1: Structural & Quality Compliance
  LLM evaluates the narrative against rubric criteria (custom uploaded rules
  override the default rubric when present).

Layer 2: Reference-Based Abnormality Detection
  Retrieves the most similar reference narratives from pgvector.
  LLM surfaces abnormalities vs reference patterns.

Layer 3: Financial Discrepancy Check  (only when financial data is uploaded)
  Retrieves the financial record matching this narrative's unique_id.
  LLM checks the narrative's monetary/schedule claims against the data.

Verdict:
  PASS              — compliance_score >= 8
  PASS_WITH_WARNINGS — compliance_score >= 6
  FAIL              — compliance_score < 6
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from backend.app.config import default_llm_provider
from backend.app.services import persistence
from backend.app.services.llm_provider import LLMProvider, generate_json_object, generate_text
from backend.app.services.vector_store import query_similar_references, upsert_scored_narrative, vector_store_status

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

# ── Layer 3 Prompts ──────────────────────────────────────────────────────────

_LAYER3_SYSTEM = """\
You are a financial accuracy auditor. Given a project narrative and its official
financial record, identify discrepancies between what the narrative states and
what the data shows.

Discrepancy types:
  - cost_overrun:      Narrative reports a cost higher than the financial data
  - cost_underrun:     Narrative cost is lower than financial data (possible understatement)
  - schedule_slip:     Narrative dates or milestones differ from financial data
  - data_conflict:     Any numeric figure in the narrative contradicts the data
  - missing_reference: Key financial value exists in data but absent from narrative

Return ONLY valid JSON:
{
  "discrepancies": [
    {
      "type": "cost_overrun|cost_underrun|schedule_slip|data_conflict|missing_reference",
      "description": "<specific description under 40 words>",
      "severity": "low|medium|high",
      "narrative_claim": "<exact quote or paraphrase from narrative>",
      "data_value": "<value from the financial record>"
    }
  ],
  "financial_alignment_score": <0-10, 10=perfect>,
  "aligned_items": ["<financial item correctly referenced in narrative>"]
}"""

_LAYER3_USER_TEMPLATE = """\
PROJECT NARRATIVE (ID: {unique_id}):
\"\"\"{narrative}\"\"\"

FINANCIAL REFERENCE DATA:
{financial_data}
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


# Prompt version hash — changes automatically when system prompts are edited
_PROMPT_HASH = hashlib.sha256(
    (_LAYER1_SYSTEM + _LAYER2_SYSTEM + _LAYER3_SYSTEM).encode()
).hexdigest()[:12]


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
    provider: LLMProvider | None = None,
    model: str | None = None,
    top_k_references: int = 5,
) -> dict[str, Any]:
    """
    Run two-layer narrative scoring.

    Returns a dict matching the NarrativeScoreResult schema.
    """
    provider = provider or default_llm_provider()  # type: ignore[assignment]
    # ── 1. Resolve rubric ─────────────────────────────────────────────────────
    # Priority: explicit rubric_id > user's uploaded rules rubric > default rubric
    has_custom_rules = False
    if rubric_id is None:
        custom_rubric_id = persistence.get_active_rules_rubric_id(user_id)
        if custom_rubric_id:
            rubric_id = custom_rubric_id
            has_custom_rules = True
        else:
            rubric_id = persistence.ensure_default_rubric(user_id)

    rubric = persistence.get_rubric(rubric_id, user_id)
    if not rubric:
        rubric_id = persistence.ensure_default_rubric(user_id)
        rubric = persistence.get_rubric(rubric_id, user_id)
        has_custom_rules = False

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

    # ── 5. Layer 3 — Financial Discrepancy Check ─────────────────────────────
    layer3_result: dict[str, Any] | None = None
    has_financial_data = False
    try:
        from backend.app.services.financial_service import get_financial_record
        fin_record = get_financial_record(user_id=user_id, unique_id=unique_id)
        if fin_record:
            has_financial_data = True
            import json as _json
            financial_data_str = _json.dumps(fin_record, indent=2)
            layer3_user = _LAYER3_USER_TEMPLATE.format(
                unique_id=unique_id,
                narrative=narrative[:3000],
                financial_data=financial_data_str[:2000],
            )
            layer3_raw = generate_json_object(
                provider=provider,
                system_prompt=_LAYER3_SYSTEM,
                user_prompt=layer3_user,
                temperature=0.2,
                model=model,
            )
            raw_discrepancies = layer3_raw.get("discrepancies", [])
            discrepancies = []
            for d in raw_discrepancies:
                if isinstance(d, dict):
                    discrepancies.append({
                        "type": str(d.get("type", "data_conflict")),
                        "description": str(d.get("description", "")),
                        "severity": str(d.get("severity", "medium")),
                        "narrative_claim": str(d.get("narrative_claim", "")),
                        "data_value": str(d.get("data_value", "")),
                    })
            layer3_result = {
                "discrepancies": discrepancies,
                "financial_alignment_score": float(layer3_raw.get("financial_alignment_score", 0.0)),
                "aligned_items": [str(a) for a in layer3_raw.get("aligned_items", [])],
                "financial_record_found": True,
            }
    except Exception as exc:
        logger.warning("Layer 3 financial check failed for '%s': %s", document_name, exc)

    # ── 6. AI Rewrite (when issues found) ────────────────────────────────────
    rewritten_narrative = ""
    layer3_issues = (
        [d["description"] for d in layer3_result["discrepancies"] if d.get("severity") in ("high", "medium")]
        if layer3_result else []
    )
    all_issues = layer1_issues + [a["description"] for a in abnormalities if a.get("severity") in ("high", "medium")] + layer3_issues
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

    # ── 7. Build result ───────────────────────────────────────────────────────
    verdict = _enforce_verdict(compliance_score)

    # Resolve the actual model name used (best-effort)
    try:
        from backend.app.services.provider_catalog import resolve_chat_model
        model_name = resolve_chat_model(provider, model)  # type: ignore[arg-type]
    except Exception:
        model_name = model or ""

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
        "layer3": layer3_result,
        "rewritten_narrative": rewritten_narrative,
        "meta": {
            "unique_id": unique_id,
            "document_name": document_name,
            "rubric_id": rubric_id,
            "rubric_name": rubric_name,
            "references_used": len(references),
            "provider": provider,
            "model_name": model_name,
            "has_custom_rules": has_custom_rules,
            "has_financial_data": has_financial_data,
            "prompt_hash": _PROMPT_HASH,
            "narrative_text": narrative,
        },
    }

    # ── 8. Persist to SQLite ──────────────────────────────────────────────────
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

    # ── 9. Write audit entry ─────────────────────────────────────────────────
    try:
        persistence.save_audit_entry(
            user_id=user_id,
            unique_id=unique_id,
            provider=str(provider),
            model_name=model_name,
            prompt_hash=_PROMPT_HASH,
            compliance_score=compliance_score,
            layer2_abnormality_count=len(abnormalities),
            layer3_discrepancy_count=len(layer3_result["discrepancies"]) if layer3_result else None,
            verdict=verdict,
            has_custom_rules=has_custom_rules,
            has_financial_data=has_financial_data,
        )
    except Exception:
        logger.warning("Failed to write audit entry for '%s'", unique_id, exc_info=True)

    # ── 10. Index into pgvector for chat searchability ────────────────────────
    if vector_store_status()["configured"]:
        try:
            from backend.app.services.embedding_service import embed_query
            embedding = embed_query(narrative[:2000])
            upsert_scored_narrative(
                user_id=user_id,
                unique_id=unique_id,
                narrative_text=narrative,
                embedding=embedding,
            )
            logger.info("Indexed scored narrative '%s' into pgvector for user %s", unique_id, user_id)
        except Exception as exc:
            logger.warning("Failed to index scored narrative '%s' into pgvector: %s", unique_id, exc)

    return result