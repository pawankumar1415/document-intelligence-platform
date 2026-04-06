from __future__ import annotations


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 180) -> list[str]:
    clean = (text or "").strip()
    if not clean:
        return []

    chunks: list[str] = []
    start = 0
    length = len(clean)

    while start < length:
        end = min(length, start + max_chars)
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(0, end - overlap)

    return chunks
