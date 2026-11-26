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
    system: str,
    user: str,
    *,
    disable_safety: bool = False,
    thinking_level: str | None = None,
    **params,
) -> Completion:
    """params map 1:1 onto GenerateContentConfig (temperature, top_p, max_output_tokens, ...)."""
    config = types.GenerateContentConfig(
        system_instruction=system,
        safety_settings=SAFETY_OFF if disable_safety else None,
        thinking_config=types.ThinkingConfig(thinking_level=thinking_level) if thinking_level else None,
        **{k: v for k, v in params.items() if v is not None},
    )
    contents = [types.Content(role="user", parts=[types.Part(text=user)])]
    try:
        response = await _client(api_key).aio.models.generate_content(
            model=model, contents=contents, config=config
        )
    except errors.APIError as exc:
        raise ProviderError(exc.message or str(exc), exc.code) from None
    except ProviderError:
        raise
    except Exception as exc:  # network errors, SDK validation errors
        raise ProviderError(str(exc) or type(exc).__name__) from None

    try:
        text = response.text or ""
    except (ValueError, AttributeError):
        text = ""
    meta = response.usage_metadata
    usage = Usage(
        getattr(meta, "prompt_token_count", 0) or 0,
        getattr(meta, "candidates_token_count", 0) or 0,
        getattr(meta, "total_token_count", 0) or 0,
    )
    return Completion(text=text, usage=usage, finish_reason=_finish_reason(response))


async def get_model_limits(api_key: str, model_ids: list[str]) -> dict[str, tuple[int, int]]:
    """Fetch (input, output) token limits per alias in parallel; failed aliases are dropped."""
    client = _client(api_key)

    async def one(model_id: str):
        info = await client.aio.models.get(model=model_id)
        return model_id, (info.input_token_limit or 0, info.output_token_limit or 0)

    results = await asyncio.gather(*(one(m) for m in model_ids), return_exceptions=True)
    return {r[0]: r[1] for r in results if not isinstance(r, BaseException)}
