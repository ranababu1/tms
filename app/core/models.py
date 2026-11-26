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

