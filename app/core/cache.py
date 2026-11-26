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


def _path(name: str) -> Path:
    return CACHE_DIR / f"{name}-models.json"


def _load(name: str) -> dict | None:
    if name in _memory:
        return _memory[name]
    try:
        entry = json.loads(_path(name).read_text(encoding="utf-8"))
        if isinstance(entry.get("models"), list) and isinstance(entry.get("fetchedAt"), (int, float)):
            _memory[name] = entry
            return entry
    except (OSError, ValueError, AttributeError):
        pass
    return None


def _store(name: str, models: list[dict]) -> dict:
    entry = {"models": models, "fetchedAt": time.time()}
    _memory[name] = entry
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        _path(name).write_text(json.dumps(entry), encoding="utf-8")
    except OSError:
        pass  # memory cache still works
    return entry


async def get_cached_models(name: str, fetch: Callable[[], Awaitable[list[dict]]]) -> dict:
    """Return {"models", "fetchedAt"} — fresh cache, else refetch, else stale cache."""
    entry = _load(name)
    if entry and time.time() - entry["fetchedAt"] < CACHE_TTL_SECONDS:
        return entry
    try:
        models = await fetch()
        if not models:
            raise ValueError("Provider returned no models.")
        return _store(name, models)
    except Exception:
        if entry:
            return entry
        raise


def clear_memory_cache() -> None:
    _memory.clear()
