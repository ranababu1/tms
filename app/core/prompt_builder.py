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
    """Simple-mode prompt: dedicated de/tr/vi, otherwise override + German prompt."""
    if target_lang in TEMPLATES:
        return _dedicated_system_prompt(target_lang, source_lang)
    return _fallback_override(target_lang) + _dedicated_system_prompt("de", source_lang)


def get_prompt_template_for_lang(lang: str) -> str:
    """God Mode seed text (no output-format block)."""
    if lang in TEMPLATES:
        return TEMPLATES[lang].PROMPT_TEMPLATE
    return common.GODMODE_PLACEHOLDER.replace("{LangName}", language_name(lang))


def get_verification_checklist(lang: str) -> list[str]:
    """Numbered critique items — the single source of truth for verify and fix."""
    mod = TEMPLATES.get(lang, TEMPLATES["de"])
    match = _CRITIQUE_RE.search(mod.TWO_PHASE_OUTPUT_FORMAT)
    if not match:
        return []
    return [item.strip() for item in _ITEM_RE.findall(match.group(1))]


def build_verification_prompt(lang: str) -> str:
    checklist = get_verification_checklist(lang)
    checklist_text = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(checklist))
    name = language_name(lang)
    note = "" if lang in TEMPLATES else common.CHECKLIST_NOTE.replace("{LangName}", name)
    return (
        common.VERIFY_PROMPT.replace("{LangName}", name)
        .replace("{checklistText}", checklist_text)
        .replace("{checklistNote}", note)
    )


def build_verification_user_message(original: str, translated: str) -> str:
    return f"ORIGINAL:\n{original}\n\nFINAL TRANSLATION:\n{translated}"


def build_fix_prompt(lang: str, failing_checks: list[dict]) -> str:
    if lang in TEMPLATES:
        base = TEMPLATES[lang].PROMPT_TEMPLATE
    else:
        base = _fallback_override(lang) + TEMPLATES["de"].PROMPT_TEMPLATE.replace("{sourceLang}", "")
    lines = []
    for i, check in enumerate(failing_checks):
        line = f"{i + 1}. {check.get('description', '')}"
        note = (check.get("note") or "").strip()
        if note:
            line += f" — Reviewer note: {note}"
        lines.append(line)
    return base + common.FIX_REQUEST.replace("{issues}", "\n".join(lines))


def build_fix_user_message(original: str, current: str) -> str:
    return f"ORIGINAL SOURCE:\n{original}\n\nCURRENT TRANSLATION (to fix):\n{current}"


def build_godmode_system_prompt(system_prompt: str, source_lang: str, target_lang: str) -> str:
    src_name = "auto-detected" if source_lang == "auto" else language_name(source_lang)
    prompt = system_prompt.replace("{sourceLang}", src_name)
    prompt = prompt.replace("{targetLang}", language_name(target_lang))
    return prompt + common.GODMODE_HARDCODED_RULES


def build_review_prompts(original: str, translated: str, target_name: str) -> tuple[str, str]:
    system = common.REVIEW_SYSTEM.replace("{targetLangName}", target_name)
    user = (
        common.REVIEW_USER.replace("{originalText}", original)
        .replace("{targetLangName}", target_name)
        .replace("{translatedText}", translated)
    )
    return system, user
