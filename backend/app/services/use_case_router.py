from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.app.models.schemas import DocumentInput, ParsedDocument


SUPPORTED_USE_CASES = {
    "sow_generation": (
        "statement of work",
        "sow",
        "scope",
        "deliverables",
        "timeline",
        "assumptions",
        "project plan",
        "proposal",
        "engagement",
        "work package",
    ),
    "presentation_generation": (
        "presentation",
        "slide",
        "deck",
        "executive summary",
        "roadmap",
        "business case",
        "stakeholder",
        "milestone",
    ),
    "requirement_extraction": (
        "requirements",
        "acceptance criteria",
        "functional requirement",
        "non-functional",
        "user story",
        "business requirement",
        "specification",
        "compliance requirement",
    ),
}

UNSUPPORTED_PATTERNS = (
    "screening questions",
    "interview process",
    "candidate",
    "expected salary",
    "notice period",
    "job offer",
    "doj",
    "immediate joiner",
    "work timings",
    "is this acceptable to you",
)


@dataclass
class UseCaseScreeningResult:
    is_supported: bool
    matched_use_cases: list[str]
    confidence: float
    reasons: list[str]


def screen_document_for_supported_use_cases(document: ParsedDocument | DocumentInput) -> UseCaseScreeningResult:
    text = f"{document.title}\n{document.text}".lower()

    matched_use_cases: list[str] = []
    total_positive_hits = 0
    for use_case, keywords in SUPPORTED_USE_CASES.items():
        hits = _count_keyword_hits(text, keywords)
        if hits > 0:
            matched_use_cases.append(use_case)
        total_positive_hits += hits

    unsupported_hits = _count_keyword_hits(text, UNSUPPORTED_PATTERNS)
    word_count = _word_count(document.text)

    reasons: list[str] = []
    if unsupported_hits > 0:
        reasons.append(
            "The document appears to be recruitment/interview content, which is outside supported use cases."
        )
    if total_positive_hits == 0:
        reasons.append(
            "No strong indicators found for SOW generation, presentation generation, or requirement extraction."
        )
    if word_count < 40:
        reasons.append("Document content is too short for reliable SOW/PPT/requirement generation.")

    confidence = _calculate_confidence(total_positive_hits, unsupported_hits, word_count)
    has_enough_signal = total_positive_hits >= 2 or word_count >= 40
    is_supported = unsupported_hits == 0 and total_positive_hits > 0 and has_enough_signal
    if not is_supported and not reasons:
        reasons.append("Document does not match the current product use-case boundaries.")

    return UseCaseScreeningResult(
        is_supported=is_supported,
        matched_use_cases=matched_use_cases,
        confidence=confidence,
        reasons=reasons,
    )


def _count_keyword_hits(text: str, keywords: Iterable[str]) -> int:
    hits = 0
    for keyword in keywords:
        if keyword in text:
            hits += 1
    return hits


def _word_count(text: str) -> int:
    return len([token for token in text.split() if token.strip()])


def _calculate_confidence(positive_hits: int, unsupported_hits: int, word_count: int) -> float:
    base = min(positive_hits * 0.18, 0.9)
    penalty = min(unsupported_hits * 0.22, 0.9)
    length_bonus = 0.08 if word_count >= 200 else 0.0
    score = base + length_bonus - penalty
    return max(0.0, min(1.0, round(score, 2)))
