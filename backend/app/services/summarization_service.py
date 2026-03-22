from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

from backend.app.models.schemas import (
    ExtractionSignal,
    SummarizeRequest,
    SummarizeResponse,
    SummaryGroup,
    SummaryInsight,
)
from backend.app.services.llm_provider import generate_json_object


SummaryMode = Literal["executive_summary", "bullet_points", "narrative_rewrite", "key_insights"]

_DOC_CONTEXT_MAP: dict[str, str] = {
    "project_requirements": "a project requirements or specification document",
    "solution_architecture": "a technical architecture or system design document",
    "delivery_planning": "a project delivery plan or programme roadmap",
    "data_ai_stack": "an AI, data engineering, or machine learning technical document",
    "governance_risk": "a risk management, assumptions, or governance document",
    "commercial_value": "a business case, commercial proposal, or value justification document",
    "regulatory_compliance": "a regulatory compliance, audit, or licensing document",
    "decommissioning_environment": "a nuclear decommissioning or environmental hazard management document",
}

_MODE_SCHEMA: dict[str, str] = {
    "executive_summary": """\
Generate a 3-4 paragraph executive summary.
Cover: (1) Context & Purpose, (2) Key Scope or Findings, (3) Recommended Actions or Outcomes, (4) Risks or Dependencies.
Return JSON exactly:
{"title": "Executive Summary", "paragraphs": ["...", "...", "..."], "key_points": ["bullet 1", "bullet 2", "bullet 3"]}
""",
    "bullet_points": """\
Extract and group the most important information as structured bullet points.
Produce 3-5 thematic headings, each with 3-6 concise bullets (under 25 words each).
Return JSON exactly:
{"title": "Key Points", "groups": [{"heading": "...", "bullets": ["...", "..."]}], "summary_line": "one sentence overview of the whole document"}
""",
    "narrative_rewrite": """\
Rewrite the source content as a clean, flowing professional narrative.
Preserve all key facts but restructure into clear readable prose. Cut jargon. Aim for 200-350 words.
Return JSON exactly:
{"title": "Narrative Summary", "paragraphs": ["...", "...", "..."], "summary_line": "one sentence essence of the document"}
""",
    "key_insights": """\
Extract the 5-8 most important insights, decisions, or findings.
Each insight must be standalone (understandable without the source) and 1-2 sentences.
Rate each as high / medium / low significance.
Return JSON exactly:
{"title": "Key Insights", "insights": [{"insight": "...", "significance": "high"}], "summary_line": "one sentence overview"}
""",
}


def _infer_doc_context(signals: list[ExtractionSignal]) -> str:
    if not signals:
        return "a professional business document"
    top = signals[0].name
    return _DOC_CONTEXT_MAP.get(top, "a professional business document")


def _build_system_prompt(doc_context: str, signals: list[ExtractionSignal]) -> str:
    signal_names = [s.name.replace("_", " ") for s in signals[:4]]
    signal_line = f"Key themes detected in this document: {', '.join(signal_names)}." if signal_names else ""
    return f"""\
You are a senior business analyst and technical writer. You are summarising {doc_context}.
{signal_line}

Rules:
- Be precise and evidence-based. Never invent facts not present in the source.
- Use professional, clear language appropriate for executive or technical stakeholders.
- Do not include preambles like "Here is a summary" or "This document discusses".
- Keep every paragraph 2-4 sentences. Every bullet under 25 words.
- Return ONLY valid JSON matching the requested schema. No markdown, no text outside JSON.
"""


def _build_user_prompt(mode: SummaryMode, title: str, text: str) -> str:
    instructions = _MODE_SCHEMA[mode]
    # Truncate to avoid hitting context limits while preserving meaningful content
    truncated_text = text[:5000] if len(text) > 5000 else text
    return f"""Document title: {title}

{instructions}

Source document content:
{truncated_text}
"""


def _parse_response(mode: SummaryMode, raw: dict, doc_context: str) -> SummarizeResponse:
    title = str(raw.get("title", "Summary"))
    paragraphs: list[str] = [str(p) for p in raw.get("paragraphs", []) if p]
    key_points: list[str] = [str(b) for b in raw.get("key_points", []) if b]
    summary_line: str = str(raw.get("summary_line", ""))

    groups: list[SummaryGroup] = []
    for g in raw.get("groups", []):
        if isinstance(g, dict):
            groups.append(SummaryGroup(
                heading=str(g.get("heading", "")),
                bullets=[str(b) for b in g.get("bullets", []) if b],
            ))

    insights: list[SummaryInsight] = []
    for item in raw.get("insights", []):
        if isinstance(item, dict):
            insights.append(SummaryInsight(
                insight=str(item.get("insight", "")),
                significance=str(item.get("significance", "medium")),
            ))

    return SummarizeResponse(
        mode=mode,
        doc_context=doc_context,
        title=title,
        paragraphs=paragraphs,
        key_points=key_points,
        groups=groups,
        insights=insights,
        summary_line=summary_line,
    )


def summarize_document(request: SummarizeRequest) -> SummarizeResponse:
    signals = list(request.extraction_signals or [])
    doc_context = _infer_doc_context(signals)
    system_prompt = _build_system_prompt(doc_context, signals)
    user_prompt = _build_user_prompt(request.mode, request.title, request.source_text)

    raw = generate_json_object(
        provider=request.llm_provider,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=request.llm_model,
        temperature=0.25,
    )

    print(f"[summarize] mode={request.mode} provider={request.llm_provider} raw_keys={list(raw.keys())}")
    print(f"[summarize] raw={raw}")

    return _parse_response(request.mode, raw, doc_context)