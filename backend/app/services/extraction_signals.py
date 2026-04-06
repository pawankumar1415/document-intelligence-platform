from __future__ import annotations

import re

from backend.app.models.schemas import ExtractionSignal


SIGNAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "project_requirements": (
        "requirements",
        "functional requirement",
        "non-functional",
        "acceptance criteria",
        "user story",
        "must",
        "should",
        "scope",
    ),
    "solution_architecture": (
        "architecture",
        "component",
        "layer",
        "api",
        "integration",
        "pipeline",
        "module",
        "service",
    ),
    "delivery_planning": (
        "timeline",
        "milestone",
        "phase",
        "roadmap",
        "delivery",
        "implementation",
        "plan",
        "schedule",
    ),
    "data_ai_stack": (
        "embedding",
        "vector",
        "retrieval",
        "llm",
        "ocr",
        "semantic",
        "model",
        "inference",
    ),
    "governance_risk": (
        "risk",
        "assumption",
        "dependency",
        "compliance",
        "governance",
        "security",
        "control",
        "policy",
    ),
    "commercial_value": (
        "business case",
        "cost",
        "budget",
        "value",
        "benefit",
        "roi",
        "efficiency",
        "productivity",
    ),
    "regulatory_compliance": (
        "office for nuclear regulation",
        "onr",
        "nsr19",
        "safeguards",
        "licence condition",
        "inspection",
        "regulatory",
    ),
    "decommissioning_environment": (
        "decommission",
        "waste",
        "silo",
        "pond",
        "hazard",
        "retrieval",
        "environmental",
        "contaminated",
    ),
}

MIN_SIGNAL_SCORE = 0.24
MIN_TOTAL_HITS = 2
MAX_SIGNALS = 6


def extract_signals(text: str) -> list[ExtractionSignal]:
    lowered_text = text.lower()
    sentences = _split_sentences(text)

    signals: list[ExtractionSignal] = []
    for signal_name, keywords in SIGNAL_KEYWORDS.items():
        keyword_hits = {keyword: _keyword_count(lowered_text, keyword) for keyword in keywords}
        total_hits = sum(keyword_hits.values())
        unique_hits = sum(1 for count in keyword_hits.values() if count > 0)
        if total_hits < MIN_TOTAL_HITS or unique_hits < 2:
            continue

        evidence = _find_evidence(sentences, keywords, limit=2)
        coverage = unique_hits / len(keywords)
        density = min(1.0, total_hits / 8.0)
        score = round(min(1.0, (0.55 * coverage) + (0.45 * density)), 2)
        if score < MIN_SIGNAL_SCORE:
            continue
        signals.append(ExtractionSignal(name=signal_name, score=score, evidence=evidence))

    return sorted(signals, key=lambda signal: signal.score, reverse=True)[:MAX_SIGNALS]


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    cleaned: list[str] = []
    for chunk in chunks:
        line = re.sub(r"\s+", " ", chunk).strip()
        if len(line) < 18:
            continue
        cleaned.append(line)
    return cleaned


def _find_evidence(sentences: list[str], keywords: tuple[str, ...], limit: int) -> list[str]:
    ranked: list[tuple[int, str]] = []
    for sentence in sentences:
        lowered_sentence = sentence.lower()
        hits = sum(1 for keyword in keywords if keyword in lowered_sentence)
        if hits > 0:
            ranked.append((hits, sentence[:220]))

    ranked.sort(key=lambda item: item[0], reverse=True)
    evidence: list[str] = []
    for _, sentence in ranked:
        if sentence not in evidence:
            evidence.append(sentence)
        if len(evidence) >= limit:
            break
    return evidence


def _keyword_count(text: str, keyword: str) -> int:
    if " " in keyword:
        return text.count(keyword)
    pattern = rf"\b{re.escape(keyword)}\b"
    return len(re.findall(pattern, text))
