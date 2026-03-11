from __future__ import annotations

import json
from typing import Literal

from backend.app.config import env, env_required


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
) -> dict:
    if provider == "openai":
        client = _get_openai_client()
        model = env("OPENAI_CHAT_MODEL", "gpt-4o-mini") or "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model,
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
        deployment = env_required("AZURE_OPENAI_CHAT_DEPLOYMENT")
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
    model = env("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile") or "llama-3.3-70b-versatile"
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    text = response.choices[0].message.content or "{}"
    return json.loads(text)


def embed_texts(provider: LLMProvider, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    embedding_provider = provider
    if provider == "groq":
        embedding_provider = (env("EMBEDDING_PROVIDER", "openai") or "openai")  # groq has no embedding API

    if embedding_provider == "openai":
        client = _get_openai_client()
        model = env("OPENAI_EMBED_MODEL", "text-embedding-3-small") or "text-embedding-3-small"
        response = client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in response.data]

    if embedding_provider == "azure_openai":
        client = _get_azure_client()
        deployment = env_required("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        response = client.embeddings.create(model=deployment, input=texts)
        return [item.embedding for item in response.data]

    raise RuntimeError(f"Unsupported embedding provider: {embedding_provider}")
