"""Provider-agnostic operations: translate, godmode, verify, fix, review, models.

Knows nothing about HTTP frameworks. Every function takes the decoded JSON body (a dict)
and returns a JSON-ready dict, or raises ServiceError(status, message) with the exact
user-facing strings from spec Appendix B.7.
"""

import math
from typing import Any

from . import models as M
from . import parsing
from . import prompt_builder as pb
from .cache import get_cached_models
from .languages import language_name
from .providers import claude, gemini
from .providers.base import Completion, ProviderError


class ServiceError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# ---- body helpers ---------------------------------------------------------

def _s(body: dict, key: str) -> str:
    value = body.get(key)
    return value if isinstance(value, str) else ""


def _num(body: dict, key: str, default: float) -> float:
    value = body.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return default
    return float(value)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _key_ok(body: dict) -> bool:
