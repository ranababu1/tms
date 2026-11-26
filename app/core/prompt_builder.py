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
