"""Provider-agnostic operations: translate, godmode, verify, fix, review, models.

Knows nothing about HTTP frameworks. Every function takes the decoded JSON body (a dict)
and returns a JSON-ready dict, or raises ServiceError(status, message) with the exact
user-facing strings from spec Appendix B.7.
"""

import math
from typing import Any

from . import models as M
from . import parsing
from . import prompt_builder as pb
from .cache import get_cached_models
from .languages import language_name
from .providers import claude, gemini
from .providers.base import Completion, ProviderError


class ServiceError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# ---- body helpers ---------------------------------------------------------

def _s(body: dict, key: str) -> str:
    value = body.get(key)
    return value if isinstance(value, str) else ""


def _num(body: dict, key: str, default: float) -> float:
    value = body.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return default
    return float(value)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _key_ok(body: dict) -> bool:
    return len(_s(body, "apiKey").strip()) >= 10


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ServiceError(400, message)


def _check_languages(source: str, target: str) -> None:
    if source and source != "auto" and source == target:
        raise ServiceError(400, "Source and target languages must be different.")


# ---- Claude error mapping -------------------------------------------------

def _claude_translate_error(exc: ProviderError, model: str) -> ServiceError:
    mapped = {
        401: "Invalid API key. Please check your Anthropic API key.",
        403: "Access denied. Check your Anthropic API key and account permissions.",
        429: "Rate limit exceeded. Please wait a moment and try again.",
        404: f'Model "{model}" not found. It may not be available for your account yet.',
    }
    if exc.status in mapped:
        return ServiceError(exc.status, mapped[exc.status])
    return ServiceError(500, exc.message or f"Anthropic API error: {exc.status}")


def _claude_godmode_error(exc: ProviderError, model: str) -> ServiceError:
    mapped = {
        401: "Invalid API key.",
        429: "Rate limit exceeded. Please wait and try again.",
        404: f'Model "{model}" not found.',
    }
    if exc.status in mapped:
        return ServiceError(exc.status, mapped[exc.status])
    return ServiceError(500, exc.message or f"Anthropic API error: {exc.status}")


def _claude_sampling(model: str, temperature: float, top_k: int | None = None) -> dict:
    if not M.supports_sampling_params(model):
        return {}
    params: dict[str, Any] = {"temperature": temperature}
    if top_k is not None:
        params["top_k"] = top_k
    return params


def _translate_response(c: Completion, body: dict, parsed: dict) -> dict:
    return {
        **parsed,
        "model": _s(body, "model"),
        "sourceLang": _s(body, "sourceLang"),
        "targetLang": _s(body, "targetLang"),
        "usage": c.usage.as_dict(),
    }


# ---- simple translate -----------------------------------------------------

async def translate_gemini(body: dict) -> dict:
    text, target, model = _s(body, "text"), _s(body, "targetLang"), _s(body, "model")
    source = _s(body, "sourceLang") or "auto"
    _require(bool(text.strip()), "Text to translate is required.")
    _require(bool(target), "Target language is required.")
    _require(bool(model), "Model selection is required.")
    _check_languages(source, target)
    _require(_key_ok(body), "A valid Gemini API key is required.")

    requested = int(_num(body, "maxOutputTokens", 0))
    try:
        c = await gemini.generate(
            _s(body, "apiKey"), model, pb.build_translation_system_prompt(source, target), text,
            disable_safety=True, temperature=0.7, top_p=0.95,
            max_output_tokens=requested if requested > 0 else M.GEMINI_DEFAULT_MAX_OUTPUT_TOKENS,
        )
    except ProviderError as exc:
        raise ServiceError(500, exc.message) from None
    if c.finish_reason == "safety":
        raise ServiceError(422, "Content was blocked by safety filters. Try rephrasing.")
    if not c.text.strip():
        raise ServiceError(500, "No translation was returned. The model may have produced empty output.")
    return _translate_response(c, body, parsing.parse_tags(c.text))


async def translate_claude(body: dict) -> dict:
    text, target, model = _s(body, "text"), _s(body, "targetLang"), _s(body, "model")
    source = _s(body, "sourceLang") or "auto"
    _require(bool(text.strip()), "Text to translate is required.")
    _require(bool(target), "Target language is required.")
    _require(bool(_s(body, "apiKey").strip()), "API key is required.")
    _require(bool(model), "Model selection is required.")
    _require(M.is_allowed_claude_model(model), "Invalid model selection.")
    _require(_key_ok(body), "Invalid API key format.")
    _check_languages(source, target)

    requested = int(_num(body, "maxOutputTokens", 0))
    max_tokens = (
        min(requested, M.CLAUDE_GODMODE_MAX_OUTPUT_CAP) if requested > 0
        else M.CLAUDE_DEFAULT_MAX_OUTPUT_TOKENS
    )
    try:
        c = await claude.create_message(
            _s(body, "apiKey"), model, pb.build_translation_system_prompt(source, target), text,
            max_tokens, **_claude_sampling(model, 0.7, 100),
        )
    except ProviderError as exc:
        raise _claude_translate_error(exc, model) from None
    except Exception:
        raise ServiceError(500, "An unexpected error occurred. Please try again.") from None
    if not c.text.strip():
        raise ServiceError(500, "No translation was returned. The model may have produced empty output.")
    return _translate_response(c, body, parsing.parse_tags(c.text))


# ---- God Mode -------------------------------------------------------------

def _godmode_response(c: Completion, body: dict) -> dict:
    return {
        "translatedText": c.text.strip(),
        "model": _s(body, "model"),
