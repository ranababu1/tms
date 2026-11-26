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
