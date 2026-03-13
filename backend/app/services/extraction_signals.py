from __future__ import annotations

import re

from backend.app.models.schemas import ExtractionSignal


SIGNAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "regulatory_compliance": (
        "office for nuclear regulation",
        "onr",
        "nsr19",
        "regulatory",
        "compliance inspection",
        "fundamental safeguards expectations",
        "licence condition",
        "assurance",
    ),
    "governance_audit": (
        "audit",
        "committee",
        "treasury",
        "national audit office",
        "compliance",
        "assurance",
        "inspection",
        "governance",
    ),
    "project_controls": (
        "milestone",
        "timeline",
        "schedule",
        "baseline",
        "forecast",
        "eac",
        "variance",
        "sanction",
        "delivery",
        "status",
        "rag",
    ),
    "requirements_tracking": (
        "requirement",
        "functional",
        "non-functional",
        "acceptance criteria",
        "user story",
        "tracker",
        "backlog",
        "specification",
    ),
    "financial_contracts": (
        "budget",
        "cost",
        "variance",
        "contract",
        "framework",
        "procurement",
        "supply chain",
        "value for money",
        "funding",
    ),
    "project_commercials": (
        "business case",
        "capital value",
        "lot",
        "supplier",
        "project controls",
        "commercial management",
        "programme and project partners",
    ),
    "regulatory_safety": (
        "safety",
        "safeguards",
        "emergency",
        "licence",
        "regulatory",
        "public accounts",
        "risk reduction",
        "hazard",
    ),
    "environmental_waste": (
        "decommission",
        "waste",
        "contaminated",
        "groundwater",
        "restoration",
        "environmental",
        "silo",
        "pond",
        "retrieval",
        "magnox",
    ),
}


def extract_signals(text: str) -> list[ExtractionSignal]:
    lowered_text = text.lower()
    sentences = _split_sentences(text)

    signals: list[ExtractionSignal] = []
    for signal_name, keywords in SIGNAL_KEYWORDS.items():
        keyword_hits = {keyword: _keyword_count(lowered_text, keyword) for keyword in keywords}
        total_hits = sum(keyword_hits.values())
        if total_hits <= 0:
            continue
        unique_hits = sum(1 for count in keyword_hits.values() if count > 0)
        evidence = _find_evidence(sentences, keywords, limit=3)
        coverage = unique_hits / max(1, len(keywords))
        density = min(1.0, total_hits / 10.0)
        score = round(min(1.0, (0.7 * coverage) + (0.3 * density)), 2)
        signals.append(ExtractionSignal(name=signal_name, score=score, evidence=evidence))

    return sorted(signals, key=lambda signal: signal.score, reverse=True)


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _find_evidence(sentences: list[str], keywords: tuple[str, ...], limit: int) -> list[str]:
    evidence: list[str] = []
    for sentence in sentences:
        lowered_sentence = sentence.lower()
        if any(keyword in lowered_sentence for keyword in keywords):
            evidence.append(sentence[:220])
            if len(evidence) >= limit:
                break
    return evidence


def _keyword_count(text: str, keyword: str) -> int:
    if " " in keyword:
        return text.count(keyword)
    pattern = rf"\b{re.escape(keyword)}\b"
    return len(re.findall(pattern, text))
