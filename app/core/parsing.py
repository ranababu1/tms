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


def normalize_verification(parsed: Any, checklist: list[str]) -> dict:
    """Shape a verifier reply into {results, allPassed}; results sliced to the checklist."""
    if not isinstance(parsed, dict) or not isinstance(parsed.get("results"), list):
        return {"results": [], "allPassed": False}
    results = []
    for idx, r in enumerate(parsed["results"][: len(checklist)]):
        r = r if isinstance(r, dict) else {}
        note = r.get("note")
        results.append({
            "item": r.get("item", idx + 1),
            "pass": bool(r.get("pass")),
            "note": note if isinstance(note, str) else "",
        })
    model_flag = parsed.get("allPassed")
    if isinstance(model_flag, bool):
        all_passed = model_flag
    else:
        all_passed = len(results) > 0 and all(r["pass"] for r in results)
    return {"results": results, "allPassed": all_passed}


REVIEW_PARSE_FAILED = {
    "hasIssues": False,
    "issues": ["Review parsing failed. Raw review returned."],
    "correctedTranslation": None,
}


def normalize_review(parsed: Any) -> dict:
    if not isinstance(parsed, dict):
        return dict(REVIEW_PARSE_FAILED)
    issues = parsed.get("issues")
    issues = [i for i in issues if isinstance(i, str)][:8] if isinstance(issues, list) else []
    corrected = parsed.get("correctedTranslation")
    corrected = corrected if isinstance(corrected, str) and corrected.strip() else None
    return {
        "hasIssues": bool(parsed.get("hasIssues")),
        "issues": issues,
        "correctedTranslation": corrected,
    }
