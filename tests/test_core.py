"""Unit tests for the pure core: prompts, parsing, capability gates, pricing."""

from app.core import models as M
from app.core import parsing, pricing
from app.core import prompt_builder as pb
from app.core.prompts import de


# ---- prompt builder -------------------------------------------------------

def test_checklist_has_15_items_per_language():
    for lang in ("de", "tr", "vi", "es", "xx"):
        assert len(pb.get_verification_checklist(lang)) == 15
    assert pb.get_verification_checklist("de")[0] == "No passive voice?"
    assert pb.get_verification_checklist("es") == pb.get_verification_checklist("de")


def test_dedicated_prompt_replaces_source_once_and_appends_format():
    prompt = pb.build_translation_system_prompt("auto", "tr")
    assert "Auto-detect the source language of the content." in prompt
    assert "{sourceLang}" not in prompt
    assert "Target language: Turkish." in prompt
    assert "<critique>" in prompt
    assert prompt.endswith("</final>\n\nTranslate the following content:")


def test_named_source_sentence():
    prompt = pb.build_translation_system_prompt("en", "de")
    assert "The source language is English." in prompt


def test_fallback_prompt_overrides_target():
    prompt = pb.build_translation_system_prompt("en", "es")
    assert prompt.startswith("## TARGET LANGUAGE OVERRIDE (read first)\nThe target language is Spanish, NOT German.")
    assert "Output ONLY Spanish.\n\nYou are a senior German copywriter" in prompt


def test_god_template_seed():
    assert pb.get_prompt_template_for_lang("vi").startswith("You are a senior Vietnamese copywriter")
    assert "REQUIRED OUTPUT FORMAT" not in pb.get_prompt_template_for_lang("de")
    assert pb.get_prompt_template_for_lang("ja").startswith("No predefined prompt for Japanese yet.")


def test_godmode_interpolation_is_global_and_appends_rules():
    out = pb.build_godmode_system_prompt("{sourceLang}->{targetLang} {sourceLang}", "auto", "fr")
    assert out.startswith("auto-detected->French auto-detected\nCODE/MARKUP RULES (non-negotiable):")
    assert out.endswith("10. Do NOT wrap output in markdown code blocks or any other formatting.")


def test_verification_prompt_note_only_for_fallback():
    assert "this checklist was written for German" not in pb.build_verification_prompt("de")
    es = pb.build_verification_prompt("es")
    assert "checking a Spanish marketing translation" in es
    assert "judge the Spanish equivalent instead." in es
    assert "1. No passive voice?\n2." in es


def test_fix_prompt():
    checks = [{"description": "No passive voice?", "note": "Sentence 2 is passive"},
              {"description": "CTA natural?", "note": ""}]
    out = pb.build_fix_prompt("de", checks)
    assert out.startswith(de.PROMPT_TEMPLATE)  # {sourceLang} left unreplaced
    assert "1. No passive voice? — Reviewer note: Sentence 2 is passive\n2. CTA natural?\n" in out
    fallback = pb.build_fix_prompt("pt", checks)
    assert fallback.startswith("## TARGET LANGUAGE OVERRIDE")
    assert "{sourceLang}" not in fallback


# ---- parsing --------------------------------------------------------------

def test_parse_tags_full_and_missing_final():
    raw = "<DRAFT> d </draft>\n<critique>\n1. PASS\n</critique><final>\n f \n</final>"
    assert parsing.parse_tags(raw) == {"translatedText": "f", "draftText": "d", "critiqueText": "1. PASS"}
    raw2 = "  just text  "
    assert parsing.parse_tags(raw2) == {"translatedText": raw2, "draftText": None, "critiqueText": None}
