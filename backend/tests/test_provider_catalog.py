import pytest

from backend.app.services.embedding_service import embedding_configuration
from backend.app.services.provider_catalog import _build_azure_catalog, resolve_chat_model


def test_embedding_configuration_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_BACKEND", "huggingface_local")
    monkeypatch.setenv("EMBEDDING_MODEL_ID", "nomic-ai/nomic-embed-text-v1.5")

    config = embedding_configuration()

    assert config["backend"] == "huggingface_local"
    assert config["model_id"] == "nomic-ai/nomic-embed-text-v1.5"
    assert config["dimension"] == 768


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
