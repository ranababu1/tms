"""Builds every system prompt from the verbatim prompt sources (spec §6, Appendix B)."""

import re

from .languages import language_name
from .prompts import common
from .prompts.common import TEMPLATES

TRANSLATE_SUFFIX = "\n\nTranslate the following content:"
_CRITIQUE_RE = re.compile(r"<critique>(.*?)</critique>", re.DOTALL)
_ITEM_RE = re.compile(r"^\d+\.\s*(.+)$", re.MULTILINE)


def source_instruction(source_lang: str) -> str:
    if source_lang == "auto":
        return "Auto-detect the source language of the content."
    return f"The source language is {language_name(source_lang)}."


def _fallback_override(target_lang: str) -> str:
    return common.FALLBACK_OVERRIDE.replace("{LangName}", language_name(target_lang))


def _dedicated_system_prompt(lang: str, source_lang: str) -> str:
    mod = TEMPLATES[lang]
    template = mod.PROMPT_TEMPLATE.replace("{sourceLang}", source_instruction(source_lang), 1)
    return template + mod.TWO_PHASE_OUTPUT_FORMAT + TRANSLATE_SUFFIX


def build_translation_system_prompt(source_lang: str, target_lang: str) -> str:
