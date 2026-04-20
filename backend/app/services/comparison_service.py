from __future__ import annotations

import logging

from backend.app.models.schemas import CompareRequest, ComparisonChange, ComparisonResult
from backend.app.services.llm_provider import generate_json_object

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a senior document analyst. You will be given two versions of a document (Doc A and Doc B).
Your job is to produce a structured comparison that identifies what has changed, improved, or regressed.

Rules:
- Be specific. Reference actual content, not just "the document is better".
- Do not invent content that is not present in either document.
- Score each document 0-10 for overall quality, specificity, structure, and completeness.
- Return ONLY valid JSON — no markdown, no commentary outside the JSON.
"""

_USER_PROMPT = """\
Compare these two documents and return JSON matching this schema exactly:
{{
  "summary": "2-3 sentence overview of the comparison",
  "overall_sentiment": "improved | regressed | neutral",
  "doc_a_score": 0.0,
  "doc_b_score": 0.0,
  "key_improvements": ["string"],
  "key_regressions": ["string"],
  "changes": [
    {{
      "section": "string — topic or section name",
      "change_type": "added | removed | improved | regressed | unchanged",
      "details": "1-2 sentences describing the change"
    }}
  ]
}}

Rules:
- overall_sentiment: "improved" if doc_b_score > doc_a_score, "regressed" if lower, "neutral" if equal.
- key_improvements: list up to 5 specific things Doc B does better than Doc A.
- key_regressions: list up to 5 specific things Doc A does better than Doc B (regressions in Doc B).
- changes: 5-10 entries covering the most significant differences.
- If the documents are nearly identical, still identify at least 3 meaningful observations.

Doc A — "{doc_a_name}":
{doc_a_text}

Doc B — "{doc_b_name}":
{doc_b_text}
"""


def compare_documents(request: CompareRequest) -> ComparisonResult:
    doc_a_snippet = request.doc_a_text[:4000]
    doc_b_snippet = request.doc_b_text[:4000]

    prompt = _USER_PROMPT.format(
        doc_a_name=request.doc_a_name,
        doc_a_text=doc_a_snippet,
        doc_b_name=request.doc_b_name,
        doc_b_text=doc_b_snippet,
    )

    try:
        raw = generate_json_object(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=prompt,
            provider=request.llm_provider,
            model=request.llm_model,
        )
    except Exception as exc:
        logger.warning("LLM comparison failed: %s", exc)
        raw = {}

    changes = [
        ComparisonChange(
            section=c.get("section", "Unknown"),
            change_type=c.get("change_type", "unchanged"),
            details=c.get("details", ""),
        )
        for c in raw.get("changes", [])
        if isinstance(c, dict)
    ]

    return ComparisonResult(
        summary=raw.get("summary", "Comparison could not be completed."),
        overall_sentiment=raw.get("overall_sentiment", "neutral"),
        doc_a_score=float(raw.get("doc_a_score", 0)),
        doc_b_score=float(raw.get("doc_b_score", 0)),
        key_improvements=raw.get("key_improvements", []),
        key_regressions=raw.get("key_regressions", []),
        changes=changes,
        doc_a_name=request.doc_a_name,
        doc_b_name=request.doc_b_name,
    )