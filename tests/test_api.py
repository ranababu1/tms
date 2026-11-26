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
