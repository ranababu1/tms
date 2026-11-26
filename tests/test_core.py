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
