from __future__ import annotations

import json
from typing import Literal

from backend.app.config import env, env_required
from backend.app.services.provider_catalog import resolve_chat_model


LLMProvider = Literal["openai", "groq", "azure_openai"]


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
