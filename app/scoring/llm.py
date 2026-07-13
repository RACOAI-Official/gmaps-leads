"""Vendor-neutral LLM client for scoring/explain and the settings test console.

Two wire formats are supported, selected by ``settings.llm_api_format``:
  * ``anthropic`` — Z.ai coding-plan key served at ``api.z.ai/api/anthropic``
    (Anthropic Messages format, ``POST {base_url}/v1/messages``).
  * ``openai``    — any OpenAI-compatible Chat Completions server, including a
    self-hosted vLLM instance running Qwen (``POST {base_url}/chat/completions``).

No SDK dependency: plain ``httpx`` (already in requirements.txt). No hardcoded
vendor — everything comes from config per the CLAUDE.md rule. When the key or
endpoint is unset, every call degrades to a no-op (returns ``None`` / reports
``ok=False``) so the rest of the pipeline keeps working without an LLM.
"""

from __future__ import annotations

import logging
import time

import httpx

from app.config import settings

log = logging.getLogger(__name__)

_VALID_FORMATS = {"anthropic", "openai"}
_DEFAULT_TIMEOUT = 60.0


class LLMError(Exception):
    """Raised when an LLM call is attempted but cannot be made."""


def _format() -> str:
    fmt = (settings.llm_api_format or "").strip().lower()
    if fmt and fmt not in _VALID_FORMATS:
        log.warning("unknown LLM_API_FORMAT=%r, falling back to 'anthropic'", fmt)
    return fmt or "anthropic"


def is_configured() -> bool:
    return bool(settings.llm_base_url and settings.llm_api_key and settings.llm_model)


def _trim_base(url: str) -> str:
    return url.rstrip("/")


def _call_anthropic(messages: list[dict], max_tokens: int) -> tuple[str, dict]:
    """Anthropic Messages format. Auth via x-api-key header (Z.ai plan)."""
    url = f"{_trim_base(settings.llm_base_url)}/v1/messages"
    # Anthropic expects the system prompt split out; pull a leading system role
    # out of the messages list if present.
    system = ""
    user_msgs: list[dict] = []
    for m in messages:
        if m["role"] == "system":
            system += (system and "\n") + m["content"]
        else:
            user_msgs.append(m)

    payload: dict = {
        "model": settings.llm_model,
        "max_tokens": max_tokens,
        "messages": user_msgs,
    }
    if system:
        payload["system"] = system
    headers = {
        "x-api-key": settings.llm_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    t0 = time.time()
    resp = httpx.post(url, json=payload, headers=headers, timeout=_DEFAULT_TIMEOUT)
    latency = (time.time() - t0) * 1000
    if resp.status_code != 200:
        raise LLMError(f"anthropic HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    text = "".join(b.get("text", "") for b in data.get("content", []))
    usage = data.get("usage", {})
    return text, {
        "model": data.get("model", settings.llm_model),
        "latency_ms": round(latency),
        "usage": {
            "input": usage.get("input_tokens"),
            "output": usage.get("output_tokens"),
        },
    }


def _call_openai(messages: list[dict], max_tokens: int) -> tuple[str, dict]:
    """OpenAI Chat Completions format (vLLM / any compat server)."""
    base = _trim_base(settings.llm_base_url)
    # Accept base URLs with or without /v1 already on them.
    path = "/chat/completions" if base.endswith("/v1") else "/v1/chat/completions"
    url = f"{base}{path}"
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "content-type": "application/json",
    }
    t0 = time.time()
    resp = httpx.post(url, json=payload, headers=headers, timeout=_DEFAULT_TIMEOUT)
    latency = (time.time() - t0) * 1000
    if resp.status_code != 200:
        raise LLMError(f"openai HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    choices = data.get("choices") or []
    text = choices[0]["message"]["content"] if choices else ""
    usage = data.get("usage", {})
    return text, {
        "model": data.get("model", settings.llm_model),
        "latency_ms": round(latency),
        "usage": {
            "input": usage.get("prompt_tokens"),
            "output": usage.get("completion_tokens"),
        },
    }


def chat(messages: list[dict], max_tokens: int = 600) -> tuple[str, dict]:
    """Send a chat-style message list. Returns (text, meta).

    Raises LLMError if not configured or the upstream call fails.
    """
    if not is_configured():
        raise LLMError("LLM not configured (LLM_BASE_URL/API_KEY/MODEL required)")
    fmt = _format()
    if fmt == "openai":
        return _call_openai(messages, max_tokens)
    return _call_anthropic(messages, max_tokens)


def complete(prompt: str, *, system: str | None = None, max_tokens: int = 600) -> str | None:
    """One-shot completion. Returns the text, or None if unconfigured.

    Errors are logged (not raised) so callers in the worker loop never crash a
    whole scoring run over a single bad LLM call.
    """
    if not is_configured():
        log.info("LLM not configured; skipping completion")
        return None
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        text, _meta = chat(messages, max_tokens=max_tokens)
        return text.strip()
    except LLMError as e:
        log.warning("LLM complete failed: %s", e)
        return None


def ping(prompt: str = "Reply with the single word OK.") -> dict:
    """Connectivity test used by the Settings → LLM console.

    Returns ``{ok, format, model, latency_ms, reply}`` or
    ``{ok: False, error}``. Never raises.
    """
    if not is_configured():
        return {
            "ok": False,
            "error": "LLM not configured (set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL)",
            "format": _format(),
        }
    try:
        text, meta = chat([{"role": "user", "content": prompt}], max_tokens=64)
        return {
            "ok": True,
            "format": _format(),
            "model": meta["model"],
            "latency_ms": meta["latency_ms"],
            "usage": meta["usage"],
            "reply": text.strip(),
        }
    except LLMError as e:
        return {"ok": False, "error": str(e), "format": _format()}
