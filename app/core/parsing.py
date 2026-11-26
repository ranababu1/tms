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
