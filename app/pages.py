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
        "name": "Claude",
        "keyStorage": "claude_translator_api_key",
        "verifyStorage": "claude_translator_verify_enabled",
        "targetStorage": "claude_translator_target_lang",
        "keyLink": "https://console.anthropic.com/settings/keys",
        "keyPlaceholder": "Paste your Anthropic API key",
        "noKeyError": "Please enter your Anthropic API key.",
        "modelsEndpoint": "/api/claude-models",
        "fallbackModels": M.claude_fallback_models,
    },
}

PAGES = {
    ("gemini", "simple"): {"path": "/translate", "accent": "cyan", "title": "Gemini Translator",
                           "translate": "/api/translate", "verify": "/api/verify-translation",
                           "fix": "/api/fix-translation", "review": "/api/review-translation",
                           "defaultModel": "gemini-flash-lite-latest"},
    ("claude", "simple"): {"path": "/translate/claude", "accent": "violet", "title": "Claude Translator",
                           "translate": "/api/translate-claude", "verify": "/api/verify-translation-claude",
                           "fix": "/api/fix-translation-claude", "review": None,
                           "defaultModel": "claude-sonnet-5"},
    ("gemini", "god"): {"path": "/godmode", "accent": "amber", "title": "God Mode · Gemini",
                        "translate": "/api/godmode", "verify": None, "fix": None,
                        "review": "/api/review-translation", "defaultModel": "gemini-flash-latest"},
    ("claude", "god"): {"path": "/godmode/claude", "accent": "amber", "title": "God Mode · Claude",
                        "translate": "/api/godmode-claude", "verify": None, "fix": None,
                        "review": None, "defaultModel": "claude-sonnet-5"},
}


def page_config(provider: str, mode: str) -> dict:
    prov = PROVIDERS[provider]
    page = PAGES[(provider, mode)]
    other = "claude" if provider == "gemini" else "gemini"
    loading = GEMINI_LOADING if provider == "gemini" else CLAUDE_LOADING
    if mode == "god" and provider == "gemini":
        loading = [m if m != "Retaining output structure" else "Aligning output structure" for m in loading]
    if mode == "god" and provider == "claude":
        loading = [m for m in loading if m != "Retaining output structure"]

    return {
        "provider": provider,
        "mode": mode,
        "providerName": prov["name"],
        "accent": page["accent"],
