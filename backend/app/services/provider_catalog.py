from __future__ import annotations

import json
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.app.config import env, env_bool, env_json


ProviderName = Literal["openai", "groq", "azure_openai", "ollama"]


OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"
OLLAMA_DEFAULT_MODEL = "qwen3:4b"
OPENAI_FALLBACK_MODELS = (
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
)
GROQ_FALLBACK_MODELS = (
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
)
OLLAMA_FALLBACK_MODELS = (
    "qwen3:4b",
    "llama3.2:3b",
    "gemma3:4b",
)
EXCLUDED_MODEL_TERMS = (
    "embedding",
    "embed",
    "moderation",
    "tts",
    "whisper",
    "transcribe",
    "audio",
    "realtime",
)

def get_provider_catalog() -> list[dict[str, object]]:
    return [
        _build_openai_catalog(),
        _build_groq_catalog(),
        _build_azure_catalog(),
        _build_ollama_catalog(),
    ]


def resolve_chat_model(provider: ProviderName, requested_model: str | None = None) -> str:
    catalog = next((item for item in get_provider_catalog() if item["provider"] == provider), None)
    if not catalog or not bool(catalog["enabled"]):
        raise ValueError(f"Provider {provider} is not enabled.")

    models = [str(model["id"]) for model in catalog["models"]]
    default_model = str(catalog["default_model"] or "")

    if requested_model:
        if requested_model not in models:
            raise ValueError(f"Model {requested_model} is not available for provider {provider}.")
        return requested_model

    if default_model:
        return default_model
    if models:
        return models[0]
    raise ValueError(f"No chat models are configured for provider {provider}.")


def _build_openai_catalog() -> dict[str, object]:
    enabled = _provider_enabled("OPENAI_ENABLED", ("OPENAI_API_KEY",))
    default_model = env("OPENAI_CHAT_MODEL", OPENAI_DEFAULT_MODEL) or OPENAI_DEFAULT_MODEL
    if not enabled:
        return _empty_catalog("openai", "OpenAI", default_model)

    source_message: str | None = None
    try:
        model_ids = _fetch_openai_model_ids()
        source = "live"
    except Exception as exc:
        model_ids = _fallback_model_ids("openai", default_model)
        source = "curated_fallback"
        source_message = str(exc)

    models = _curate_models("openai", model_ids, default_model)
    if not models:
        models = [_model_dict("openai", default_model, default_model, True)]
        source = "curated_fallback"

    return {
        "provider": "openai",
        "display_name": "OpenAI",
        "enabled": True,
        "default_model": _resolve_default_model(default_model, models),
        "models": models,
        "source": source,
        "source_message": source_message,
    }


def _build_groq_catalog() -> dict[str, object]:
    enabled = _provider_enabled("GROQ_ENABLED", ("GROQ_API_KEY",))
    default_model = env("GROQ_CHAT_MODEL", GROQ_DEFAULT_MODEL) or GROQ_DEFAULT_MODEL
    if not enabled:
        return _empty_catalog("groq", "Groq", default_model)

    source_message: str | None = None
    try:
        model_ids = _fetch_groq_model_ids()
        source = "live"
    except Exception as exc:
        model_ids = _fallback_model_ids("groq", default_model)
        source = "curated_fallback"
        source_message = str(exc)

    models = _curate_models("groq", model_ids, default_model)
    if not models:
        models = [_model_dict("groq", default_model, default_model, True)]
        source = "curated_fallback"

    return {
        "provider": "groq",
        "display_name": "Groq",
        "enabled": True,
        "default_model": _resolve_default_model(default_model, models),
        "models": models,
        "source": source,
        "source_message": source_message,
    }


def _build_azure_catalog() -> dict[str, object]:
    enabled = _provider_enabled(
        "AZURE_OPENAI_ENABLED",
        ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"),
    )
    raw_config = env_json("AZURE_OPENAI_CHAT_DEPLOYMENTS_JSON", default=[])
    default_model = env("AZURE_OPENAI_CHAT_DEPLOYMENT", "") or ""
    if not enabled:
        return _empty_catalog("azure_openai", "Azure OpenAI", default_model)

    deployments = []
    if isinstance(raw_config, list):
        deployments = raw_config
    elif raw_config:
        raise RuntimeError("AZURE_OPENAI_CHAT_DEPLOYMENTS_JSON must be a JSON array.")

    models: list[dict[str, object]] = []
    for item in deployments:
        if not isinstance(item, dict):
            continue
        deployment_id = str(item.get("id") or item.get("deployment_name") or "").strip()
        if not deployment_id:
            continue
        label = str(item.get("label") or deployment_id).strip()
        models.append(_model_dict("azure_openai", deployment_id, label, deployment_id == default_model))

    if not models and default_model:
        models.append(_model_dict("azure_openai", default_model, default_model, True))

    return {
        "provider": "azure_openai",
        "display_name": "Azure OpenAI",
        "enabled": enabled,
        "default_model": _resolve_default_model(default_model, models),
        "models": models,
        "source": "config",
        "source_message": None,
    }


def _build_ollama_catalog() -> dict[str, object]:
    enabled = _ollama_provider_enabled()
    default_model = env("OLLAMA_CHAT_MODEL", OLLAMA_DEFAULT_MODEL) or OLLAMA_DEFAULT_MODEL
    if not enabled:
        return _empty_catalog("ollama", "Ollama", default_model)

    source_message: str | None = None
    try:
        model_ids = _fetch_ollama_model_ids()
        source = "live"
    except Exception as exc:
        model_ids = _fallback_model_ids("ollama", default_model)
        source = "curated_fallback"
        source_message = str(exc)

    models = _curate_models("ollama", model_ids, default_model)
    if not models:
        models = [_model_dict("ollama", default_model, default_model, True)]
        source = "curated_fallback"

    return {
        "provider": "ollama",
        "display_name": "Ollama",
        "enabled": True,
        "default_model": _resolve_default_model(default_model, models),
        "models": models,
        "source": source,
        "source_message": source_message,
    }


def _provider_enabled(flag_name: str, key_names: tuple[str, ...]) -> bool:
    if env(flag_name) is not None:
        return env_bool(flag_name, False)
    return all(bool(env(key_name)) for key_name in key_names)


def _ollama_provider_enabled() -> bool:
    if env("OLLAMA_ENABLED") is not None:
        return env_bool("OLLAMA_ENABLED", True)
    return True


def _empty_catalog(provider: ProviderName, display_name: str, default_model: str) -> dict[str, object]:
    return {
        "provider": provider,
        "display_name": display_name,
        "enabled": False,
        "default_model": default_model,
        "models": [],
        "source": "disabled",
        "source_message": None,
    }


def _fetch_openai_model_ids() -> list[str]:
    from openai import OpenAI

    client = OpenAI(api_key=env("OPENAI_API_KEY"))
    response = client.models.list()
    return [item.id for item in response.data]


def _fetch_groq_model_ids() -> list[str]:
    api_key = env("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    model_ids_from_sdk: list[str] = []
    sdk_error: str | None = None
    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        response = client.models.list()
        model_ids_from_sdk = [str(item.id).strip() for item in response.data if str(item.id).strip()]
    except Exception as exc:
        sdk_error = str(exc)

    if model_ids_from_sdk:
        return model_ids_from_sdk

    request = Request(
        "https://api.groq.com/openai/v1/models",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        sdk_context = f" SDK error: {sdk_error}." if sdk_error else ""
        raise RuntimeError(f"Could not fetch Groq models.{sdk_context}") from exc

    return [str(item.get("id", "")).strip() for item in payload.get("data", []) if str(item.get("id", "")).strip()]


def _fetch_ollama_model_ids() -> list[str]:
    base_url = env("OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434"
    request = Request(
        f"{base_url.rstrip('/')}/api/tags",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError("Could not fetch Ollama models. Ensure `ollama serve` is running.") from exc

    models: list[dict[str, Any]] = payload.get("models", [])
    return [str(item.get("name", "")).strip() for item in models if str(item.get("name", "")).strip()]


def _curate_models(provider: ProviderName, model_ids: list[str], default_model: str) -> list[dict[str, object]]:
    explicit_allowlist = env(f"{provider.upper()}_MODEL_ALLOWLIST", "")
    allowed_ids = {item.strip() for item in explicit_allowlist.split(",") if item.strip()}

    filtered_ids: list[str] = []
    seen: set[str] = set()
    for model_id in model_ids:
        if model_id in seen:
            continue
        seen.add(model_id)
        lowered = model_id.lower()
        if allowed_ids and model_id not in allowed_ids:
            continue
        if any(term in lowered for term in EXCLUDED_MODEL_TERMS):
            continue
        filtered_ids.append(model_id)

    if default_model and default_model not in filtered_ids:
        filtered_ids.insert(0, default_model)

    deduped_ids: list[str] = []
    for model_id in filtered_ids:
        if model_id not in deduped_ids:
            deduped_ids.append(model_id)

    return [_model_dict(provider, model_id, model_id, model_id == default_model) for model_id in deduped_ids]


def _resolve_default_model(default_model: str, models: list[dict[str, object]]) -> str:
    if default_model and any(str(model["id"]) == default_model for model in models):
        return default_model
    if models:
        return str(models[0]["id"])
    return default_model


def _model_dict(provider: ProviderName, model_id: str, label: str, is_default: bool) -> dict[str, object]:
    return {
        "id": model_id,
        "label": label,
        "provider": provider,
        "is_default": is_default,
    }


def _fallback_model_ids(provider: ProviderName, default_model: str) -> list[str]:
    if provider == "openai":
        curated = list(OPENAI_FALLBACK_MODELS)
    elif provider == "groq":
        curated = list(GROQ_FALLBACK_MODELS)
    elif provider == "ollama":
        curated = list(OLLAMA_FALLBACK_MODELS)
    else:
        curated = []

    if default_model and default_model not in curated:
        curated.insert(0, default_model)
    return curated or ([default_model] if default_model else [])
