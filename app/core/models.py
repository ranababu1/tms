"""Model catalogs, pricing, limits and Claude capability gates (spec §5.1, §7, §13)."""

import re

from .pricing import pricing_summary

# ---- Gemini ---------------------------------------------------------------
GEMINI_DEFAULT_MAX_OUTPUT_TOKENS = 8192
GEMINI_GODMODE_MAX_OUTPUT_CAP = 65536
GEMINI_THINKING_LEVELS = ("MINIMAL", "LOW", "MEDIUM", "HIGH")

GEMINI_ALIASES = [
    {"id": "gemini-pro-latest", "label": "Gemini 3.1 Pro", "isPro": True},
    {"id": "gemini-flash-latest", "label": "Gemini 3.8 Flash", "isPro": False},
    {"id": "gemini-flash-lite-latest", "label": "Gemini 3.5 Flash Lite", "isPro": False},
]
GEMINI_PRICING = {
    "gemini-pro-latest": {"inputPer1M": 1.25, "outputPer1M": 10.0},
    "gemini-flash-latest": {"inputPer1M": 0.30, "outputPer1M": 2.50},
    "gemini-flash-lite-latest": {"inputPer1M": 0.10, "outputPer1M": 0.40},
}
GEMINI_FALLBACK_LIMITS = {"inputTokenLimit": 1_048_576, "outputTokenLimit": 65_536}


def gemini_pricing(model_id: str) -> dict:
    if model_id in GEMINI_PRICING:
        return GEMINI_PRICING[model_id]
    key = "gemini-pro-latest" if "pro" in model_id.lower() else "gemini-flash-latest"
    return GEMINI_PRICING[key]


def gemini_model(alias: dict, input_limit: int, output_limit: int) -> dict:
    pricing = gemini_pricing(alias["id"])
    return {
        "id": alias["id"],
        "label": alias["label"],
        "badge": "Pro" if alias["isPro"] else None,
        "isPro": alias["isPro"],
        "inputTokenLimit": input_limit,
        "outputTokenLimit": output_limit,
        "pricing": pricing_summary(pricing),
    }


def gemini_fallback_models() -> list[dict]:
    lim = GEMINI_FALLBACK_LIMITS
    return [gemini_model(a, lim["inputTokenLimit"], lim["outputTokenLimit"]) for a in GEMINI_ALIASES]


# ---- Claude ---------------------------------------------------------------
CLAUDE_DEFAULT_MAX_OUTPUT_TOKENS = 64000
CLAUDE_GODMODE_MAX_OUTPUT_CAP = 128000
CLAUDE_EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
ANTHROPIC_VERSION = "2023-06-01"
CLAUDE_FAMILY_ORDER = ("opus", "sonnet", "haiku")

CLAUDE_FAMILY_LIMITS = {
    "opus": {"inputTokenLimit": 1_000_000, "outputTokenLimit": 128_000},
    "sonnet": {"inputTokenLimit": 1_000_000, "outputTokenLimit": 128_000},
    "haiku": {"inputTokenLimit": 200_000, "outputTokenLimit": 64_000},
}
CLAUDE_EXACT_PRICING = {
    "claude-opus-5-5": {"inputPer1M": 4.0, "outputPer1M": 20.0},
    "claude-sonnet-5": {"inputPer1M": 2.0, "outputPer1M": 10.0},
    "claude-haiku-4-5": {"inputPer1M": 1.0, "outputPer1M": 5.0},
}
CLAUDE_FAMILY_PRICING = {
    "opus": {"inputPer1M": 4.0, "outputPer1M": 20.0},
    "sonnet": {"inputPer1M": 2.0, "outputPer1M": 10.0},
    "haiku": {"inputPer1M": 1.0, "outputPer1M": 5.0},
}
CLAUDE_FALLBACK = [
    ("claude-opus-5-5", "Claude Opus 5.5"),
    ("claude-sonnet-5", "Claude Sonnet 5"),
    ("claude-haiku-4-5", "Claude Haiku 4.5"),
]

_ALLOWED_RE = re.compile(r"^claude-(opus|sonnet|haiku)-\d", re.IGNORECASE)
_GEN5_RE = re.compile(r"^claude-(opus|sonnet)-5", re.IGNORECASE)
_FAMILY_RE = re.compile(r"opus|sonnet|haiku", re.IGNORECASE)


def is_allowed_claude_model(model_id: str) -> bool:
    return bool(_ALLOWED_RE.match(model_id or ""))


def supports_sampling_params(model_id: str) -> bool:
    """Opus/Sonnet 5.x reject temperature/top_k."""
    return not _GEN5_RE.match(model_id or "")


def supports_effort(model_id: str) -> bool:
    return bool(_GEN5_RE.match(model_id or ""))


def claude_family(model_id: str) -> str | None:
    m = _FAMILY_RE.search(model_id or "")
    return m.group(0).lower() if m else None


def title_case_id(model_id: str) -> str:
    return " ".join(part.capitalize() for part in model_id.split("-"))


def claude_model(model_id: str, label: str | None = None) -> dict:
    family = claude_family(model_id) or "sonnet"
    pricing = CLAUDE_EXACT_PRICING.get(model_id) or CLAUDE_FAMILY_PRICING[family]
    return {
        "id": model_id,
        "label": label or title_case_id(model_id),
        "badge": family.capitalize(),
        "isPro": family == "opus",
        **CLAUDE_FAMILY_LIMITS[family],
        "supportsSampling": supports_sampling_params(model_id),
        "supportsEffort": supports_effort(model_id),
        "pricing": pricing_summary(pricing),
    }


def claude_fallback_models() -> list[dict]:
    return [claude_model(mid, label) for mid, label in CLAUDE_FALLBACK]


def pick_latest_claude_models(raw: list[dict]) -> list[dict]:
    """Newest model per family from /v1/models data, ordered Opus, Sonnet, Haiku."""
    best: dict[str, dict] = {}
    for m in raw:
        mid = m.get("id", "")
        family = claude_family(mid)
        if not mid.startswith("claude-") or not family:
            continue
        if family not in best or m.get("created_at", "") > best[family].get("created_at", ""):
            best[family] = m
    return [
        claude_model(best[f]["id"], best[f].get("display_name"))
