"""Google Gemini via the google-genai SDK (async client). The key is never logged."""

import asyncio

from google import genai
from google.genai import errors, types

from .base import PROVIDER_TIMEOUT_SECONDS, Completion, ProviderError, Usage

SAFETY_OFF = [
    types.SafetySetting(category=c, threshold=types.HarmBlockThreshold.BLOCK_NONE)
    for c in (
        types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    )
]


def _client(api_key: str) -> genai.Client:
    key = api_key.strip()
    if len(key) < 10:
        raise ProviderError("A valid Gemini API key is required.", 400)
    return genai.Client(
        api_key=key, http_options=types.HttpOptions(timeout=PROVIDER_TIMEOUT_SECONDS * 1000)
    )


def _finish_reason(response) -> str | None:
    try:
        reason = response.candidates[0].finish_reason
    except (AttributeError, IndexError, TypeError):
        return None
    name = getattr(reason, "name", str(reason) if reason else None)
    if name == "SAFETY":
        return "safety"
    if name == "MAX_TOKENS":
        return "max_tokens"
    return name


async def generate(
    api_key: str,
    model: str,
