from __future__ import annotations

import re
from collections import OrderedDict

from backend.app.models.schemas import DocumentInput


KEYWORD_GROUPS = OrderedDict(
    {
        "Project Overview": ("overview", "summary", "background", "objective", "goal"),
        "Scope": ("scope", "service", "solution", "approach", "workstream"),
        "Deliverables": ("deliverable", "output", "artifact", "report", "dashboard"),
        "Timeline": ("timeline", "schedule", "phase", "week", "milestone"),
        "Risks": ("risk", "dependency", "constraint", "assumption", "issue"),
    }
)


def normalize_sentences(text: str) -> list[str]:
    collapsed = re.sub(r"\s+", " ", text.strip())
    if not collapsed:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", collapsed)
    return [sentence.strip() for sentence in sentences if len(sentence.strip()) > 20]


def collect_candidate_lines(source_document: DocumentInput) -> list[str]:
    lines: list[str] = []

    for section in source_document.sections:
        if section.heading.strip():
            lines.append(section.heading.strip())
        lines.extend(line.strip() for line in section.body.splitlines() if line.strip())

    if not lines:
        lines.extend(sentence.strip() for sentence in source_document.text.splitlines() if sentence.strip())

    deduped = list(dict.fromkeys(lines))
    return deduped


def pick_sentences_by_keywords(sentences: list[str], keywords: tuple[str, ...], limit: int) -> list[str]:
    chosen: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            chosen.append(sentence)
        if len(chosen) >= limit:
            return chosen

    for sentence in sentences:
        if sentence not in chosen:
            chosen.append(sentence)
        if len(chosen) >= limit:
            return chosen

    return chosen


def build_section_candidates(source_document: DocumentInput) -> dict[str, list[str]]:
    sentences = normalize_sentences(source_document.text)
    if not sentences:
        sentences = collect_candidate_lines(source_document)

    return {
        name: pick_sentences_by_keywords(sentences, keywords, limit=3)
        for name, keywords in KEYWORD_GROUPS.items()
    }
