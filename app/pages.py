"""Per-page configuration for the four tool pages (provider x mode), handed to the JS app."""

from .core import models as M
from .core.languages import LANGUAGES_WITH_PROMPT, UI_LANGUAGES
from .core.prompt_builder import get_prompt_template_for_lang

GEMINI_LOADING = [
    "Powered by Google AI",
    "Inference pipeline initialized",
    "Optimizing translation quality",
    "Retaining output structure",
    "Preserving context and tone",
    "Formatting output for quick use",
    "Cutting hours of manual effort",
]
CLAUDE_LOADING = ["Powered by Anthropic Models", *GEMINI_LOADING[1:]]

PROVIDERS = {
    "gemini": {
        "name": "Gemini",
        "keyStorage": "gemini_translator_api_key",
        "verifyStorage": "gemini_translator_verify_enabled",
        "targetStorage": "gemini_translator_target_lang",
        "keyLink": "https://aistudio.google.com/apikey",
        "keyPlaceholder": "Paste your Google AI Studio API key",
        "noKeyError": "Please set your Gemini API key using the button in the top navigation.",
        "modelsEndpoint": "/api/models",
        "fallbackModels": M.gemini_fallback_models,
    },
    "claude": {
