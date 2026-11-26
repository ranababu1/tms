"""Anthropic Messages/Models over raw HTTP (spec §5.1). The key is never logged."""

import httpx

from ..models import ANTHROPIC_VERSION
from .base import PROVIDER_TIMEOUT_SECONDS, Completion, ProviderError, Usage

API_BASE = "https://api.anthropic.com/v1"


def _headers(api_key: str) -> dict:
    return {
        "x-api-key": api_key.strip(),
        "anthropic-version": ANTHROPIC_VERSION,
        "Content-Type": "application/json",
    }


def _error_message(response: httpx.Response) -> str:
    try:
        msg = response.json().get("error", {}).get("message")
        if msg:
            return msg
    except (ValueError, AttributeError):
        pass
    return f"Anthropic API error: {response.status_code}"


async def _request(method: str, path: str, api_key: str, **kwargs) -> dict:
    try:
        async with httpx.AsyncClient(timeout=PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.request(method, API_BASE + path, headers=_headers(api_key), **kwargs)
    except httpx.HTTPError as exc:
        raise ProviderError(f"Could not reach Anthropic: {type(exc).__name__}") from None
    if response.status_code >= 400:
        raise ProviderError(_error_message(response), response.status_code)
    return response.json()


async def create_message(
    api_key: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float | None = None,
    top_k: int | None = None,
    effort: str | None = None,
) -> Completion:
    body: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    if temperature is not None:
        body["temperature"] = temperature
    if top_k is not None:
        body["top_k"] = top_k
    if effort is not None:
        body["output_config"] = {"effort": effort}

    data = await _request("POST", "/messages", api_key, json=body)
    text = next(
        (b.get("text", "") for b in data.get("content") or [] if b.get("type") == "text"), ""
    )
    usage = data.get("usage") or {}
    inp, out = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
    stop = data.get("stop_reason")
    return Completion(
        text=text,
        usage=Usage(inp, out, inp + out),
        finish_reason="max_tokens" if stop == "max_tokens" else stop,
    )


async def list_models(api_key: str) -> list[dict]:
    data = await _request("GET", "/models", api_key, params={"limit": 1000})
    return data.get("data") or []
