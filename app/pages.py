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
