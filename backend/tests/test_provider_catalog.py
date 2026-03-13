import pytest

from backend.app.services.embedding_service import (
    _extract_ollama_embeddings,
    embedding_configuration,
)
from backend.app.services.provider_catalog import (
    _build_azure_catalog,
    _build_groq_catalog,
    _build_ollama_catalog,
    resolve_chat_model,
)


def test_embedding_configuration_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_BACKEND", "huggingface_local")
    monkeypatch.setenv("EMBEDDING_MODEL_ID", "nomic-ai/nomic-embed-text-v1.5")

    config = embedding_configuration()

    assert config["backend"] == "huggingface_local"
    assert config["model_id"] == "nomic-ai/nomic-embed-text-v1.5"
    assert config["dimension"] == 768


def test_embedding_configuration_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "qwen3-embedding:4b")
    monkeypatch.setattr(
        "backend.app.services.embedding_service._ollama_embedding_dimension",
        lambda _model_id: 2560,
    )

    config = embedding_configuration()

    assert config["backend"] == "ollama"
    assert config["model_id"] == "qwen3-embedding:4b"
    assert config["dimension"] == 2560
    assert config["supported_models"][0]["id"] == "qwen3-embedding:4b"


def test_extract_ollama_embeddings_supports_single_and_batch() -> None:
    batch_payload = {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}
    single_payload = {"embedding": [0.5, 0.6]}

    assert _extract_ollama_embeddings(batch_payload) == [[0.1, 0.2], [0.3, 0.4]]
    assert _extract_ollama_embeddings(single_payload) == [[0.5, 0.6]]


def test_resolve_chat_model_rejects_invalid_requested_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.provider_catalog.get_provider_catalog",
        lambda: [
            {
                "provider": "openai",
                "display_name": "OpenAI",
                "enabled": True,
                "default_model": "gpt-4o-mini",
                "models": [{"id": "gpt-4o-mini", "label": "gpt-4o-mini", "provider": "openai", "is_default": True}],
                "source": "test",
            }
        ],
    )

    with pytest.raises(ValueError, match="not available"):
        resolve_chat_model("openai", "gpt-9-unknown")


def test_azure_catalog_uses_deployment_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENABLED", "true")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv(
        "AZURE_OPENAI_CHAT_DEPLOYMENTS_JSON",
        '[{"id":"bsbi-gpt-4o-mini","label":"BSBI GPT-4o Mini"}]',
    )
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "bsbi-gpt-4o-mini")

    catalog = _build_azure_catalog()

    assert catalog["enabled"] is True
    assert catalog["default_model"] == "bsbi-gpt-4o-mini"
    assert catalog["models"][0]["id"] == "bsbi-gpt-4o-mini"


def test_ollama_catalog_reads_live_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_ENABLED", "true")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_CHAT_MODEL", "qwen3:4b")
    monkeypatch.setattr(
        "backend.app.services.provider_catalog._fetch_ollama_model_ids",
        lambda: ["qwen3:4b", "gemma3:4b", "qwen3-embedding:4b"],
    )

    catalog = _build_ollama_catalog()

    assert catalog["enabled"] is True
    assert catalog["source"] == "live"
    assert "qwen3:4b" in [model["id"] for model in catalog["models"]]
    # embedding-only models should not appear in chat model selector
    assert "qwen3-embedding:4b" not in [model["id"] for model in catalog["models"]]


def test_ollama_catalog_is_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_ENABLED", raising=False)
    monkeypatch.setenv("OLLAMA_CHAT_MODEL", "qwen3:4b")
    monkeypatch.setattr(
        "backend.app.services.provider_catalog._fetch_ollama_model_ids",
        lambda: ["qwen3:4b"],
    )

    catalog = _build_ollama_catalog()

    assert catalog["enabled"] is True
    assert catalog["default_model"] == "qwen3:4b"


def test_groq_catalog_uses_curated_fallback_on_fetch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_ENABLED", "true")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setattr(
        "backend.app.services.provider_catalog._fetch_groq_model_ids",
        lambda: (_ for _ in ()).throw(RuntimeError("network down")),
    )

    catalog = _build_groq_catalog()
    model_ids = [model["id"] for model in catalog["models"]]

    assert catalog["enabled"] is True
    assert catalog["source"] == "curated_fallback"
    assert "llama-3.3-70b-versatile" in model_ids
    assert len(model_ids) >= 2
