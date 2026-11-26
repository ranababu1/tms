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
