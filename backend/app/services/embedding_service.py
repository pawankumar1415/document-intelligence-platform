from __future__ import annotations

from functools import lru_cache
from typing import Any

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


def configured_embedding_backend() -> str:
    return env("EMBEDDING_BACKEND", "huggingface_local") or "huggingface_local"


def configured_embedding_model_id() -> str:
    return env("EMBEDDING_MODEL_ID", "nomic-ai/nomic-embed-text-v1.5") or "nomic-ai/nomic-embed-text-v1.5"


def embedding_configuration() -> dict[str, Any]:
    model_id = configured_embedding_model_id()
    metadata = SUPPORTED_EMBEDDING_MODELS.get(model_id, {})
    return {
        "backend": configured_embedding_backend(),
        "model_id": model_id,
        "dimension": embedding_dimension(model_id),
        "supported_models": [
            {
                "id": supported_model_id,
                "label": details["label"],
                "dimension": details["dimension"],
            }
            for supported_model_id, details in SUPPORTED_EMBEDDING_MODELS.items()
        ],
        "label": metadata.get("label", model_id),
    }


def embedding_dimension(model_id: str | None = None) -> int:
    resolved_model_id = model_id or configured_embedding_model_id()
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
    if configured_embedding_backend() != "huggingface_local":
        raise RuntimeError(
            f"Unsupported embedding backend: {configured_embedding_backend()}. "
            "Only huggingface_local is implemented in this slice."
        )

    model = _load_sentence_transformer(model_id)
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return [[float(value) for value in vector.tolist()] for vector in vectors]


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
