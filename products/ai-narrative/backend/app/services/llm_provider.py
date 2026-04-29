from __future__ import annotations

import json
import re
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.app.config import env, env_bool, env_required
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


_THINK_RE = re.compile(r"<think(?:ing)?>\s*[\s\S]*?</think(?:ing)?>", re.IGNORECASE)


def _strip_thinking_tags(text: str) -> str:
    """Remove <think>…</think> and <thinking>…</thinking> blocks that some models emit."""
    return _THINK_RE.sub("", text).strip()


def _generate_json_with_ollama(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
) -> dict:
    timeout_seconds = _env_int("OLLAMA_CHAT_TIMEOUT_SECONDS", 180)
    num_predict = _env_int("OLLAMA_CHAT_NUM_PREDICT", 2048)
    num_ctx = _env_int("OLLAMA_CHAT_NUM_CTX", 4096)
    keep_alive = env("OLLAMA_KEEP_ALIVE", "20m") or "20m"
    disable_think = env_bool("OLLAMA_DISABLE_THINK", True)

    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
            },
            "think": not disable_think,
        }
    ).encode("utf-8")
    request = Request(
        f"{_get_ollama_base_url().rstrip('/')}/api/chat",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Ollama chat request failed with status {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(
            "Could not connect to Ollama or request timed out. Ensure `ollama serve` is running and use a smaller model."
        ) from exc

    message = response_payload.get("message", {})
    content = message.get("content", "") if isinstance(message, dict) else response_payload.get("response", "")
    content_text = str(content).strip()
    if not content_text:
        return {}

    return _extract_json_payload(content_text)


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


def generate_text(
    *,
    provider: LLMProvider,
    messages: list[dict],
    temperature: float = 0.4,
    model: str | None = None,
) -> str:
    """Generate a free-form text response given a list of chat messages."""
    if provider == "openai":
        client = _get_openai_client()
        resolved_model = resolve_chat_model("openai", model)
        response = client.chat.completions.create(
            model=resolved_model,
            temperature=temperature,
            messages=messages,
        )
        return _strip_thinking_tags(response.choices[0].message.content or "")

    if provider == "azure_openai":
        client = _get_azure_client()
        deployment = resolve_chat_model("azure_openai", model or env("AZURE_OPENAI_CHAT_DEPLOYMENT"))
        response = client.chat.completions.create(
            model=deployment,
            temperature=temperature,
            messages=messages,
        )
        return _strip_thinking_tags(response.choices[0].message.content or "")

    if provider == "ollama":
        resolved_model = resolve_chat_model("ollama", model)
        return _generate_text_with_ollama(model=resolved_model, messages=messages, temperature=temperature)

    # Groq
    client = _get_groq_client()
    resolved_model = resolve_chat_model("groq", model)
    response = client.chat.completions.create(
        model=resolved_model,
        temperature=temperature,
        messages=messages,
    )
    return _strip_thinking_tags(response.choices[0].message.content or "")


def _generate_text_with_ollama(*, model: str, messages: list[dict], temperature: float) -> str:
    timeout_seconds = _env_int("OLLAMA_CHAT_TIMEOUT_SECONDS", 180)
    num_predict = _env_int("OLLAMA_CHAT_NUM_PREDICT", 2048)
    num_ctx = _env_int("OLLAMA_CHAT_NUM_CTX", 4096)
    keep_alive = env("OLLAMA_KEEP_ALIVE", "20m") or "20m"
    disable_think = env_bool("OLLAMA_DISABLE_THINK", True)

    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
            },
            "think": not disable_think,
        }
    ).encode("utf-8")
    request = Request(
        f"{_get_ollama_base_url().rstrip('/')}/api/chat",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Ollama chat request failed with status {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(
            "Could not connect to Ollama or request timed out."
        ) from exc

    message = response_payload.get("message", {})
    content = message.get("content", "") if isinstance(message, dict) else response_payload.get("response", "")
    return _strip_thinking_tags(str(content))


def _extract_json_payload(text: str) -> dict:
    # 1. Clean response: strip leading/trailing whitespace and any think-block wrappers
    cleaned = _strip_thinking_tags(text)

    # 2. Try strict parse on the cleaned text
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3. Try to find the outermost {...} block
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 4. Truncated JSON recovery: try to parse with progressively fewer trailing chars
    # until we get a valid object (handles incomplete arrays / strings)
    candidate = match.group(0) if match else cleaned
    for _ in range(min(len(candidate), 512)):
        candidate = candidate.rstrip()
        if not candidate:
            break
        # Close any open string, arrays and the root object
        for suffix in ['"}]}', '"}]', '"}', '"]', '"', "]}", "}", "}"]:
            try:
                result = json.loads(candidate + suffix)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        candidate = candidate[:-1]

    return {"raw": text}


def generate_from_image(
    *,
    provider: LLMProvider,
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """
    Send an image to a vision-capable model and return the text response.

    Supported providers:
      - openai      → gpt-4o-mini (default) or any gpt-4* vision model
      - azure_openai → configured deployment (must be a vision model)
      - groq         → llama-4-scout-17b or llama-3.2-11b-vision-preview
      - ollama       → requires a local vision model (e.g. llava, moondream2)

    The image is sent as a base64 data-URL so no file upload is needed.
    """
    import base64

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64}"

    vision_message = {
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
            {"type": "text", "text": prompt},
        ],
    }

    if provider == "openai":
        client = _get_openai_client()
        vision_model = model or env("OPENAI_VISION_MODEL") or "gpt-4o-mini"
        resp = client.chat.completions.create(
            model=vision_model,
            temperature=temperature,
            messages=[vision_message],
            max_tokens=4096,
        )
        return resp.choices[0].message.content or ""

    if provider == "azure_openai":
        client = _get_azure_client()
        deployment = model or env("AZURE_OPENAI_VISION_DEPLOYMENT") or env("AZURE_OPENAI_CHAT_DEPLOYMENT") or ""
        resp = client.chat.completions.create(
            model=deployment,
            temperature=temperature,
            messages=[vision_message],
            max_tokens=4096,
        )
        return resp.choices[0].message.content or ""

    if provider == "groq":
        client = _get_groq_client()
        # Groq vision models (in order of preference)
        vision_model = model or "meta-llama/llama-4-scout-17b-16e-instruct"
        try:
            resp = client.chat.completions.create(
                model=vision_model,
                temperature=temperature,
                messages=[vision_message],
                max_tokens=4096,
            )
            return resp.choices[0].message.content or ""
        except Exception:
            # Fallback to older vision model
            resp = client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                temperature=temperature,
                messages=[vision_message],
                max_tokens=4096,
            )
            return resp.choices[0].message.content or ""

    if provider == "ollama":
        # Ollama image support: pass images array with base64 content
        resolved_model = resolve_chat_model("ollama", model)
        timeout_seconds = _env_int("OLLAMA_CHAT_TIMEOUT_SECONDS", 180)
        keep_alive = env("OLLAMA_KEEP_ALIVE", "20m") or "20m"
        import base64 as _b64
        payload = json.dumps({
            "model": resolved_model,
            "messages": [{
                "role": "user",
                "content": prompt,
                "images": [_b64.b64encode(image_bytes).decode("utf-8")],
            }],
            "stream": False,
            "keep_alive": keep_alive,
            "options": {"temperature": temperature, "num_predict": 4096},
        }).encode("utf-8")
        request = Request(
            f"{_get_ollama_base_url().rstrip('/')}/api/chat",
            headers={"Content-Type": "application/json"},
            data=payload,
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            msg = data.get("message", {})
            return msg.get("content", "") if isinstance(msg, dict) else ""
        except Exception as exc:
            raise RuntimeError(
                f"Ollama vision request failed. Ensure a vision model (e.g. llava, moondream2) "
                f"is pulled and configured. Error: {exc}"
            ) from exc

    raise ValueError(f"Unsupported provider for vision: {provider}")


def _env_int(name: str, default: int) -> int:
    raw = env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
