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
