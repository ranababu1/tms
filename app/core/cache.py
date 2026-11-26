"""7-day model-catalog cache: module-level memory plus a JSON file under .cache/ (spec §7).

On refresh failure a stale entry is served; with no entry at all the error propagates.
"""

import json
import time
from pathlib import Path
from typing import Awaitable, Callable

CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache"

_memory: dict[str, dict] = {}

