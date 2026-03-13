from __future__ import annotations

import json
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.app.config import env, env_required
from backend.app.services.provider_catalog import resolve_chat_model


LLMProvider = Literal["openai", "groq", "azure_openai", "ollama"]


def _get_openai_client():
    from openai import OpenAI

    return OpenAI(api_key=env_required("OPENAI_API_KEY"))


def _get_azure_client():
    from openai import AzureOpenAI

    return AzureOpenAI(
        api_key=env_required("AZURE_OPENAI_API_KEY"),
        azure_endpoint=env_required("AZURE_OPENAI_ENDPOINT"),
        api_version=env("AZURE_OPENAI_API_VERSION", "2024-10-21") or "2024-10-21",
    )


def _get_groq_client():
    from groq import Groq

    return Groq(api_key=env_required("GROQ_API_KEY"))


def _get_ollama_base_url() -> str:
    return env("OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434"


def _generate_json_with_ollama(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
) -> dict:
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }
    ).encode("utf-8")
    request = Request(
        f"{_get_ollama_base_url().rstrip('/')}/api/chat",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    try:
        with urlopen(request, timeout=120) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Ollama chat request failed with status {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("Could not connect to Ollama. Ensure `ollama serve` is running.") from exc

    message = response_payload.get("message", {})
    content = message.get("content", "") if isinstance(message, dict) else response_payload.get("response", "")
    content_text = str(content).strip()
    if not content_text:
        return {}

    try:
        return json.loads(content_text)
    except json.JSONDecodeError:
        # Fall back to safe object to avoid crashing generation on malformed provider output.
        return {"raw": content_text}


def generate_json_object(
    *,
    provider: LLMProvider,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    model: str | None = None,
) -> dict:
    if provider == "openai":
        client = _get_openai_client()
        resolved_model = resolve_chat_model("openai", model)
        response = client.chat.completions.create(
            model=resolved_model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.choices[0].message.content or "{}"
        return json.loads(text)

    if provider == "azure_openai":
        client = _get_azure_client()
        deployment = resolve_chat_model("azure_openai", model or env("AZURE_OPENAI_CHAT_DEPLOYMENT"))
        response = client.chat.completions.create(
            model=deployment,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.choices[0].message.content or "{}"
        return json.loads(text)

    if provider == "ollama":
        resolved_model = resolve_chat_model("ollama", model)
        return _generate_json_with_ollama(
            model=resolved_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )

    client = _get_groq_client()
    resolved_model = resolve_chat_model("groq", model)
    response = client.chat.completions.create(
        model=resolved_model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    text = response.choices[0].message.content or "{}"
    return json.loads(text)
