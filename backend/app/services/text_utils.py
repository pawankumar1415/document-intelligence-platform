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

MAX_LINE_LENGTH = 150
MIN_LINE_LENGTH = 18


def normalize_sentences(text: str) -> list[str]:
    if not text.strip():
        return []
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    cleaned = [_clean_line(chunk) for chunk in chunks]
    return [item for item in cleaned if len(item) >= MIN_LINE_LENGTH]


def collect_candidate_lines(source_document: DocumentInput) -> list[str]:
    lines: list[str] = []

    for section in source_document.sections:
        heading = _clean_line(section.heading)
        if heading:
            lines.append(heading)
        for line in section.body.splitlines():
            lines.extend(_expand_line_candidates(line))

    if not lines:
        for line in source_document.text.splitlines():
            lines.extend(_expand_line_candidates(line))

    deduped = list(dict.fromkeys(line for line in lines if len(line) >= MIN_LINE_LENGTH))
    return deduped


def pick_sentences_by_keywords(sentences: list[str], keywords: tuple[str, ...], limit: int) -> list[str]:
    ranked: list[tuple[int, str]] = []
    for sentence in sentences:
        lowered = sentence.lower()
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > 0:
            ranked.append((score, sentence))

    ranked.sort(key=lambda item: (item[0], -len(item[1])), reverse=True)
    chosen: list[str] = []
    for _, sentence in ranked:
        compact = _shorten(sentence, MAX_LINE_LENGTH)
        if compact not in chosen:
            chosen.append(compact)
        if len(chosen) >= limit:
            return chosen

    for sentence in sentences:
        compact = _shorten(sentence, MAX_LINE_LENGTH)
        if compact not in chosen:
            chosen.append(compact)
        if len(chosen) >= limit:
            return chosen
    return chosen


def build_section_candidates(source_document: DocumentInput) -> dict[str, list[str]]:
    sentences = collect_candidate_lines(source_document)
    sentences.extend(normalize_sentences(source_document.text))
    sentences = list(dict.fromkeys(sentences))

    return {
        name: pick_sentences_by_keywords(sentences, keywords, limit=5)
        for name, keywords in KEYWORD_GROUPS.items()
    }


def _expand_line_candidates(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped:
        return []

    parts = re.split(r"[•\u2022]+|\s+-\s+", stripped)
    candidates = [_clean_line(part) for part in parts]
    return [item for item in candidates if item]


def _clean_line(line: str) -> str:
    normalized = re.sub(r"\s+", " ", line).strip()
    normalized = re.sub(r"^[\d\-\.\)\(]+\s*", "", normalized)
    normalized = normalized.replace("In Scope:", "").replace("Out of Scope:", "")
    normalized = normalized.replace("•", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip(" .:-")
    return _shorten(normalized, MAX_LINE_LENGTH)


def _shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    candidate = text[: limit - 3].rstrip()
    return f"{candidate}..."
