"""API contract tests (spec §5, B.7) with provider calls mocked — no network, no keys."""

import pytest
from fastapi.testclient import TestClient

from app.core import cache, services
from app.core.providers.base import Completion, ProviderError, Usage
from app.main import app

client = TestClient(app)
KEY = "k" * 20


def fake(text="", finish=None, usage=(10, 5, 15), raises=None, calls=None):
    async def _fn(*args, **kwargs):
        if calls is not None:
            calls.append({"args": args, "kwargs": kwargs})
        if raises:
            raise raises
        return Completion(text=text, usage=Usage(*usage), finish_reason=finish)
    return _fn


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.clear_memory_cache()
    yield
    cache.clear_memory_cache()

