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
        "sourceLang": _s(body, "sourceLang"),
        "targetLang": _s(body, "targetLang"),
        "usage": c.usage.as_dict(),
    }


async def godmode_gemini(body: dict) -> dict:
    text, target, model = _s(body, "text"), _s(body, "targetLang"), _s(body, "model")
    source = _s(body, "sourceLang") or "auto"
    _require(bool(text.strip()), "Text to translate is required.")
    _require(bool(target), "Target language is required.")
    _require(bool(model), "Model selection is required.")
    _check_languages(source, target)
    _require(_key_ok(body), "A valid Gemini API key is required.")

    seed = body.get("seed")
    seed_ok = isinstance(seed, (int, float)) and not isinstance(seed, bool) and math.isfinite(seed)
    level = _s(body, "thinkingLevel").upper()
    params = {
        "temperature": _clamp(_num(body, "temperature", 0.7), 0, 1),
        "top_p": _clamp(_num(body, "topP", 0.95), 0, 1),
        "top_k": round(_clamp(_num(body, "topK", 40), 1, 100)),
        "max_output_tokens": int(_clamp(
            _num(body, "maxOutputTokens", M.GEMINI_DEFAULT_MAX_OUTPUT_TOKENS),
            1, M.GEMINI_GODMODE_MAX_OUTPUT_CAP,
        )),
        "presence_penalty": _clamp(_num(body, "presencePenalty", 0), -2, 2),
        "frequency_penalty": _clamp(_num(body, "frequencyPenalty", 0), -2, 2),
        "seed": round(seed) if seed_ok else None,
    }
    system = pb.build_godmode_system_prompt(_s(body, "systemPrompt"), source, target)
    try:
        c = await gemini.generate(
            _s(body, "apiKey"), model, system, text, disable_safety=True,
            thinking_level=level if level in M.GEMINI_THINKING_LEVELS else None, **params,
        )
    except ProviderError as exc:
        raise ServiceError(500, exc.message) from None
    if c.finish_reason == "safety":
        raise ServiceError(422, "Content blocked by safety filters.")
    if not c.text.strip():
        raise ServiceError(500, "No translation returned. The model may have produced empty output.")
    return _godmode_response(c, body)


async def godmode_claude(body: dict) -> dict:
    text, target, model = _s(body, "text"), _s(body, "targetLang"), _s(body, "model")
    source = _s(body, "sourceLang") or "auto"
    _require(bool(text.strip()), "Text to translate is required.")
    _require(bool(target), "Target language is required.")
    _require(_key_ok(body), "Invalid or missing API key.")
    _require(bool(model), "Model selection is required.")
    _require(M.is_allowed_claude_model(model), "Invalid model selection.")
    _check_languages(source, target)

    max_tokens = int(_clamp(
        _num(body, "maxOutputTokens", M.CLAUDE_DEFAULT_MAX_OUTPUT_TOKENS),
        1, M.CLAUDE_GODMODE_MAX_OUTPUT_CAP,
    ))
    extra = _claude_sampling(
        model,
        _clamp(_num(body, "temperature", 0.7), 0, 1),
        round(_clamp(_num(body, "topK", 40), 1, 500)),
    )
    effort = _s(body, "effort").lower()
    if M.supports_effort(model) and effort in M.CLAUDE_EFFORT_LEVELS:
        extra["effort"] = effort
    system = pb.build_godmode_system_prompt(_s(body, "systemPrompt"), source, target)
    try:
        c = await claude.create_message(_s(body, "apiKey"), model, system, text, max_tokens, **extra)
    except ProviderError as exc:
        raise _claude_godmode_error(exc, model) from None
    except Exception:
        raise ServiceError(500, "An unexpected error occurred.") from None
    if not c.text.strip():
        raise ServiceError(500, "No translation returned. The model may have produced empty output.")
    return _godmode_response(c, body)


# ---- verification and fix -------------------------------------------------

_PROVIDER_KEY_MSG = {
    "gemini": "A valid Gemini API key is required.",
    "claude": "A valid Anthropic API key is required.",
}


def _validate_model(provider: str, model: str) -> None:
    if provider == "gemini":
        _require(bool(model), "Model selection is required.")
    else:
        _require(M.is_allowed_claude_model(model), "Invalid model selection.")


async def _complete(provider: str, body: dict, system: str, user: str,
                    *, temperature: float, max_tokens: int) -> Completion:
    model = _s(body, "model")
    try:
        if provider == "gemini":
            return await gemini.generate(
                _s(body, "apiKey"), model, system, user,
                temperature=temperature, top_p=0.95, max_output_tokens=max_tokens,
            )
        return await claude.create_message(
            _s(body, "apiKey"), model, system, user, max_tokens,
            **_claude_sampling(model, temperature),
        )
    except ProviderError as exc:
        # Claude verify/fix forward the provider status; Gemini errors are 500s.
        status = exc.status if provider == "claude" and exc.status else 500
        raise ServiceError(status, exc.message) from None


async def verify(provider: str, body: dict) -> dict:
    original, translated = _s(body, "originalText"), _s(body, "translatedText")
    target, model = _s(body, "targetLang"), _s(body, "model")
    _require(bool(original.strip()), "Original text is required.")
    _require(bool(translated.strip()), "Translated text is required.")
    _require(bool(target), "Target language is required.")
    _require(_key_ok(body), _PROVIDER_KEY_MSG[provider])
    _validate_model(provider, model)

    checklist = pb.get_verification_checklist(target)
    c = await _complete(
        provider, body, pb.build_verification_prompt(target),
        pb.build_verification_user_message(original, translated),
        temperature=0.2, max_tokens=8192,
    )
    if not c.text.strip():
        if c.finish_reason == "max_tokens":
            raise ServiceError(500, "Verification ran out of output budget before writing a response. Try again.")
        raise ServiceError(500, "No verification response was returned by the model.")
    result = parsing.normalize_verification(parsing.parse_json_tolerant(c.text), checklist)
    if not result["results"]:
        raise ServiceError(502, "Verification response could not be parsed. Please try again.")
    return {"checklist": checklist, **result, "usage": c.usage.as_dict()}


async def fix(provider: str, body: dict) -> dict:
    original, current = _s(body, "originalText"), _s(body, "currentTranslation")
    target, model = _s(body, "targetLang"), _s(body, "model")
    _require(bool(original.strip()), "Original text is required.")
    _require(bool(current.strip()), "Current translation is required.")
    _require(bool(target), "Target language is required.")
    _require(_key_ok(body), _PROVIDER_KEY_MSG[provider])
    _validate_model(provider, model)
    raw_checks = body.get("failingChecks")
    checks = [
        {"description": str(c.get("description", "")), "note": str(c.get("note") or "")}
        for c in (raw_checks if isinstance(raw_checks, list) else [])
        if isinstance(c, dict)
    ]
    _require(bool(checks), "At least one failing check is required.")

    c = await _complete(
        provider, body, pb.build_fix_prompt(target, checks),
        pb.build_fix_user_message(original, current),
        temperature=0.5,
        max_tokens=8192 if provider == "gemini" else M.CLAUDE_DEFAULT_MAX_OUTPUT_TOKENS,
    )
    if not c.text.strip():
        raise ServiceError(500, "No fix response was returned by the model.")
    return {"translatedText": c.text.strip(), "usage": c.usage.as_dict()}


# ---- review (Gemini only) -------------------------------------------------

async def review_gemini(body: dict) -> dict:
    original, translated = _s(body, "originalText"), _s(body, "translatedText")
    target, model = _s(body, "targetLang"), _s(body, "model")
    _require(bool(original.strip()), "Original text is required.")
    _require(bool(translated.strip()), "Translated text is required.")
    _require(bool(target), "Target language is required.")
    _require(bool(model), "Model selection is required.")
    _require(_key_ok(body), "A valid Gemini API key is required.")

    # Accept a code or a name; the original contract sends the name.
    target_name = language_name(target)
    system, user = pb.build_review_prompts(original, translated, target_name)
    try:
