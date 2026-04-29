from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.app.config import env


SUPPORTED_EMBEDDING_MODELS: dict[str, dict[str, Any]] = {
    "nomic-ai/nomic-embed-text-v1.5": {
        "label": "Nomic Embed Text v1.5",
        "dimension": 768,
        "document_prefix": "search_document: ",
        "query_prefix": "search_query: ",
        "trust_remote_code": True,
    },
    "BAAI/bge-m3": {
        "label": "BGE-M3",
        "dimension": 1024,
        "document_prefix": "",
        "query_prefix": "",
        "trust_remote_code": False,
    },
    "intfloat/multilingual-e5-large-instruct": {
        "label": "Multilingual E5 Large Instruct",
        "dimension": 1024,
        "document_prefix": "passage: ",
        "query_prefix": "query: ",
        "trust_remote_code": False,
    },
}
OLLAMA_EMBEDDING_FALLBACK_DIMENSIONS: dict[str, int] = {
    "qwen3-embedding:0.6b": 1024,
    "mxbai-embed-large:latest": 1024,
    "mxbai-embed-large": 1024,
    "nomic-embed-text:latest": 768,
    "nomic-embed-text": 768,
}
OLLAMA_EMBEDDING_FALLBACK_MODELS = (
    "qwen3-embedding:0.6b",
    "mxbai-embed-large:latest",
    "nomic-embed-text:latest",
)

SUPPORTED_EMBEDDING_BACKENDS = {"huggingface_local", "ollama"}
_runtime_embedding_backend: str | None = None
_runtime_embedding_model_id: str | None = None


def configured_embedding_backend() -> str:
    if _runtime_embedding_backend:
        return _runtime_embedding_backend
    return env("EMBEDDING_BACKEND", "ollama") or "ollama"


def configured_embedding_model_id() -> str:
    backend = configured_embedding_backend()
    if _runtime_embedding_model_id:
        return _runtime_embedding_model_id
    if backend == "ollama":
        return env("OLLAMA_EMBED_MODEL", "qwen3-embedding:0.6b") or "qwen3-embedding:0.6b"
    return env("EMBEDDING_MODEL_ID", "nomic-ai/nomic-embed-text-v1.5") or "nomic-ai/nomic-embed-text-v1.5"


def configured_ollama_base_url() -> str:
    return env("OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434"


def get_runtime_embedding_override() -> tuple[str | None, str | None]:
    return (_runtime_embedding_backend, _runtime_embedding_model_id)


def set_runtime_embedding_override(backend: str | None, model_id: str | None) -> None:
    global _runtime_embedding_backend
    global _runtime_embedding_model_id
    _runtime_embedding_backend = backend
    _runtime_embedding_model_id = model_id
    _ollama_embedding_dimension.cache_clear()


def set_runtime_embedding_config(*, backend: str, model_id: str) -> None:
    normalized_backend = backend.strip()
    normalized_model = model_id.strip()
    if normalized_backend not in SUPPORTED_EMBEDDING_BACKENDS:
        supported = ", ".join(sorted(SUPPORTED_EMBEDDING_BACKENDS))
        raise RuntimeError(f"Unsupported embedding backend: {normalized_backend}. Supported: {supported}.")
    if not normalized_model:
        raise RuntimeError("Embedding model id is required.")

    set_runtime_embedding_override(normalized_backend, normalized_model)


def embedding_configuration() -> dict[str, Any]:
    backend = configured_embedding_backend()
    model_id = configured_embedding_model_id()
    metadata = SUPPORTED_EMBEDDING_MODELS.get(model_id, {})
    dimension = embedding_dimension(model_id)
    return {
        "backend": backend,
        "model_id": model_id,
        "dimension": dimension,
        "supported_models": _supported_models_for_backend(backend, model_id, dimension),
        "label": metadata.get("label", model_id),
    }


def embedding_dimension(model_id: str | None = None) -> int:
    backend = configured_embedding_backend()
    resolved_model_id = model_id or configured_embedding_model_id()
    if backend == "ollama":
        try:
            return _ollama_embedding_dimension(resolved_model_id)
        except Exception:
            fallback = OLLAMA_EMBEDDING_FALLBACK_DIMENSIONS.get(resolved_model_id)
            if fallback is not None:
                return fallback
            raise

    metadata = SUPPORTED_EMBEDDING_MODELS.get(resolved_model_id)
    if metadata:
        return int(metadata["dimension"])

    model = _load_sentence_transformer(resolved_model_id)
    dimension = model.get_sentence_embedding_dimension()
    if dimension is None:
        raise RuntimeError(f"Could not determine embedding dimension for model {resolved_model_id}.")
    return int(dimension)


def embed_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model_id = configured_embedding_model_id()
    prepared_texts = [_prepare_document_text(model_id, text) for text in texts]
    return _encode(model_id, prepared_texts)


def embed_query(text: str) -> list[float]:
    model_id = configured_embedding_model_id()
    prepared_text = _prepare_query_text(model_id, text)
    embeddings = _encode(model_id, [prepared_text])
    if not embeddings:
        raise RuntimeError("No embedding was produced for the query text.")
    return embeddings[0]


def _prepare_document_text(model_id: str, text: str) -> str:
    metadata = SUPPORTED_EMBEDDING_MODELS.get(model_id, {})
    prefix = str(metadata.get("document_prefix", ""))
    return f"{prefix}{text.strip()}"


def _prepare_query_text(model_id: str, text: str) -> str:
    metadata = SUPPORTED_EMBEDDING_MODELS.get(model_id, {})
    prefix = str(metadata.get("query_prefix", ""))
    return f"{prefix}{text.strip()}"


def _encode(model_id: str, texts: list[str]) -> list[list[float]]:
    backend = configured_embedding_backend()
    if backend == "huggingface_local":
        model = _load_sentence_transformer(model_id)
        vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return [[float(value) for value in vector.tolist()] for vector in vectors]

    if backend == "ollama":
        return _encode_ollama(model_id, texts)

    raise RuntimeError(
        f"Unsupported embedding backend: {backend}. "
        "Supported values are huggingface_local or ollama."
    )


@lru_cache(maxsize=4)
def _load_sentence_transformer(model_id: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency-level failure
        raise RuntimeError(
            "sentence-transformers is not installed. Install requirements.txt dependencies."
        ) from exc

    metadata = SUPPORTED_EMBEDDING_MODELS.get(model_id, {})
    trust_remote_code = bool(metadata.get("trust_remote_code", False))
    return SentenceTransformer(model_id, trust_remote_code=trust_remote_code)


def _supported_models_for_backend(backend: str, model_id: str, dimension: int) -> list[dict[str, Any]]:
    if backend == "ollama":
        return _build_ollama_supported_models(model_id, dimension)

    return [
        {
            "id": supported_model_id,
            "label": details["label"],
            "dimension": details["dimension"],
        }
        for supported_model_id, details in SUPPORTED_EMBEDDING_MODELS.items()
    ]


def _encode_ollama(model_id: str, texts: list[str]) -> list[list[float]]:
    base_url = configured_ollama_base_url().rstrip("/")

    # Try the modern batch endpoint first (Ollama >= 0.3.6)
    payload = json.dumps({"model": model_id, "input": texts}).encode("utf-8")
    request = Request(
        f"{base_url}/api/embed",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    try:
        with urlopen(request, timeout=90) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        vectors = _extract_ollama_embeddings(response_payload)
        if len(vectors) != len(texts):
            raise RuntimeError("Ollama embedding response length mismatch.")
        return [_normalize_vector(vector) for vector in vectors]
    except HTTPError as exc:
        if exc.code != 404:
            raise RuntimeError(f"Ollama embed request failed with status {exc.code}.") from exc
        # 404 means /api/embed doesn't exist — fall back to legacy /api/embeddings endpoint
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("Could not connect to Ollama. Ensure `ollama serve` is running.") from exc

    # Legacy endpoint (Ollama < 0.3.6): single prompt per request
    vectors: list[list[float]] = []
    for text in texts:
        legacy_payload = json.dumps({"model": model_id, "prompt": text}).encode("utf-8")
        legacy_request = Request(
            f"{base_url}/api/embeddings",
            headers={"Content-Type": "application/json"},
            data=legacy_payload,
        )
        try:
            with urlopen(legacy_request, timeout=90) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Ollama embed request failed with status {exc.code}.") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError("Could not connect to Ollama. Ensure `ollama serve` is running.") from exc
        embedding = response_payload.get("embedding")
        if not isinstance(embedding, list):
            raise RuntimeError("Ollama legacy embeddings response did not include an embedding vector.")
        vectors.append(_normalize_vector([float(v) for v in embedding]))
    return vectors


@lru_cache(maxsize=8)
def _ollama_embedding_dimension(model_id: str) -> int:
    vectors = _encode_ollama(model_id, ["dimension probe"])
    if not vectors or not vectors[0]:
        raise RuntimeError("Could not determine embedding dimension from Ollama response.")
    return len(vectors[0])


def _extract_ollama_embeddings(response_payload: dict[str, Any]) -> list[list[float]]:
    embeddings = response_payload.get("embeddings")
    if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
        return [[float(value) for value in vector] for vector in embeddings]

    single = response_payload.get("embedding")
    if isinstance(single, list):
        return [[float(value) for value in single]]

    raise RuntimeError("Ollama embedding response did not include embedding vectors.")


def _normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0:
        return vector
    return [value / norm for value in vector]


def _build_ollama_supported_models(active_model_id: str, active_dimension: int) -> list[dict[str, Any]]:
    allowlist = _embedding_allowlist("OLLAMA_EMBED_MODEL_ALLOWLIST")

    discovered: list[str] = []
    if allowlist:
        discovered = list(allowlist)
    else:
        try:
            discovered = _fetch_ollama_embedding_model_ids()
        except Exception:
            discovered = list(OLLAMA_EMBEDDING_FALLBACK_MODELS)

    ordered_ids: list[str] = []
    for candidate in [active_model_id, *discovered]:
        if candidate and candidate not in ordered_ids:
            ordered_ids.append(candidate)

    models: list[dict[str, Any]] = []
    for candidate in ordered_ids:
        candidate_dimension = _resolve_ollama_embedding_dimension(
            candidate,
            active_model_id=active_model_id,
            active_dimension=active_dimension,
        )
        models.append(
            {
                "id": candidate,
                "label": candidate,
                "dimension": candidate_dimension,
            }
        )

    return models


def _fetch_ollama_embedding_model_ids() -> list[str]:
    request = Request(
        f"{configured_ollama_base_url().rstrip('/')}/api/tags",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError("Could not fetch Ollama model list.") from exc

    models: list[dict[str, Any]] = payload.get("models", [])
    filtered: list[str] = []
    for item in models:
        model_id = str(item.get("name", "")).strip()
        if not model_id:
            continue
        lowered = model_id.lower()
        if "embed" in lowered or "embedding" in lowered:
            filtered.append(model_id)
    return filtered


def _resolve_ollama_embedding_dimension(candidate: str, *, active_model_id: str, active_dimension: int) -> int:
    if candidate == active_model_id:
        return active_dimension
    try:
        return _ollama_embedding_dimension(candidate)
    except Exception:
        return OLLAMA_EMBEDDING_FALLBACK_DIMENSIONS.get(candidate, active_dimension)


def _embedding_allowlist(env_key: str) -> list[str]:
    raw = env(env_key, "") or ""
    return [item.strip() for item in raw.split(",") if item.strip()]
