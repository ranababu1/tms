"""Tag parsing for simple mode and tolerant JSON parsing for verify/review (spec §5.2, §5.3)."""

import json
import re
from typing import Any

_FLAGS = re.IGNORECASE | re.DOTALL
_DRAFT_RE = re.compile(r"<draft>(.*?)</draft>", _FLAGS)
_CRITIQUE_RE = re.compile(r"<critique>(.*?)</critique>", _FLAGS)
_FINAL_RE = re.compile(r"<final>(.*?)</final>", _FLAGS)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_tags(raw: str) -> dict[str, str | None]:
    """Split a draft/critique/final response. Missing <final> returns the raw text unstripped."""
    draft = _DRAFT_RE.search(raw)
    critique = _CRITIQUE_RE.search(raw)
    final = _FINAL_RE.search(raw)
    return {
        "translatedText": final.group(1).strip() if final else raw,
        "draftText": draft.group(1).strip() if draft else None,
        "critiqueText": critique.group(1).strip() if critique else None,
    }


def parse_json_tolerant(raw: str) -> Any | None:
    """Fenced block, then whole text, then the first greedy {...}. None when nothing parses."""
    text = raw.strip()
    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    match = _OBJECT_RE.search(text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except (ValueError, TypeError):
        return None


