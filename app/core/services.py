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
