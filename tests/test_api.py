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


def post(path, body):
    return client.post(path, json=body)


# ---- pages ----------------------------------------------------------------

@pytest.mark.parametrize("path", ["/", "/translate", "/translate/claude", "/godmode", "/godmode/claude"])
def test_pages_render(path):
    r = client.get(path)
    assert r.status_code == 200 and "<html" in r.text
    if path != "/":
        assert 'id="page-config"' in r.text


def test_static_assets():
    for path in ("/static/css/app.css", "/static/js/tool.js", "/static/js/constellation.js"):
        assert client.get(path).status_code == 200


# ---- common errors --------------------------------------------------------

def test_invalid_json_body():
    r = client.post("/api/translate", content=b"{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400 and r.json() == {"error": "Invalid request body."}


@pytest.mark.parametrize("body,msg", [
    ({}, "Text to translate is required."),
    ({"text": "hi"}, "Target language is required."),
    ({"text": "hi", "targetLang": "de"}, "Model selection is required."),
    ({"text": "hi", "targetLang": "de", "sourceLang": "de", "model": "m"}, "Source and target languages must be different."),
    ({"text": "hi", "targetLang": "de", "model": "m", "apiKey": " short "}, "A valid Gemini API key is required."),
])
def test_gemini_translate_validation(body, msg):
    r = post("/api/translate", body)
    assert r.status_code == 400 and r.json() == {"error": msg}


def test_claude_translate_validation():
    base = {"text": "hi", "targetLang": "de"}
    assert post("/api/translate-claude", base).json()["error"] == "API key is required."
    r = post("/api/translate-claude", {**base, "apiKey": KEY, "model": "gpt-4"})
    assert r.json()["error"] == "Invalid model selection."
    r = post("/api/translate-claude", {**base, "apiKey": "short", "model": "claude-sonnet-5"})
    assert r.json()["error"] == "Invalid API key format."


# ---- translate ------------------------------------------------------------

def test_gemini_translate_success(monkeypatch):
    calls = []
    monkeypatch.setattr(services.gemini, "generate", fake("<draft>D</draft><critique>C</critique><final> F </final>", calls=calls))
    r = post("/api/translate", {"text": "Hello", "sourceLang": "auto", "targetLang": "tr",
                                "model": "gemini-flash-latest", "apiKey": KEY})
    assert r.status_code == 200
    data = r.json()
    assert data["translatedText"] == "F" and data["draftText"] == "D" and data["critiqueText"] == "C"
    assert data["usage"] == {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15}
    kw = calls[0]["kwargs"]
    assert kw["temperature"] == 0.7 and kw["top_p"] == 0.95 and kw["max_output_tokens"] == 8192
    assert kw["disable_safety"] is True


def test_gemini_translate_safety_and_empty(monkeypatch):
    body = {"text": "x", "targetLang": "de", "model": "m", "apiKey": KEY}
    monkeypatch.setattr(services.gemini, "generate", fake("", finish="safety"))
    r = post("/api/translate", body)
    assert r.status_code == 422 and r.json()["error"] == "Content was blocked by safety filters. Try rephrasing."
    monkeypatch.setattr(services.gemini, "generate", fake("   "))
    assert post("/api/translate", body).status_code == 500
    monkeypatch.setattr(services.gemini, "generate", fake(raises=ProviderError("quota exceeded", 429)))
    r = post("/api/translate", body)
    assert r.status_code == 500 and r.json()["error"] == "quota exceeded"


def test_claude_translate_params_and_error_mapping(monkeypatch):
    calls = []
    monkeypatch.setattr(services.claude, "create_message", fake("no tags here", calls=calls))
    body = {"text": "x", "targetLang": "de", "model": "claude-haiku-4-5", "apiKey": KEY, "maxOutputTokens": 999999}
    r = post("/api/translate-claude", body)
    assert r.json()["translatedText"] == "no tags here" and r.json()["draftText"] is None
    args, kw = calls[0]["args"], calls[0]["kwargs"]
    assert args[4] == 128000 and kw == {"temperature": 0.7, "top_k": 100}

    calls.clear()
    post("/api/translate-claude", {**body, "model": "claude-sonnet-5", "maxOutputTokens": 0})
    assert calls[0]["args"][4] == 64000 and calls[0]["kwargs"] == {}

    for status, fragment in [(401, "Invalid API key"), (403, "Access denied"), (429, "Rate limit"), (404, "not found")]:
        monkeypatch.setattr(services.claude, "create_message", fake(raises=ProviderError("x", status)))
        r = post("/api/translate-claude", body)
        assert r.status_code == status and fragment in r.json()["error"]
    monkeypatch.setattr(services.claude, "create_message", fake(raises=ProviderError("overloaded", 529)))
    r = post("/api/translate-claude", body)
    assert r.status_code == 500 and r.json()["error"] == "overloaded"


# ---- God Mode -------------------------------------------------------------

def test_gemini_godmode_clamps(monkeypatch):
    calls = []
    monkeypatch.setattr(services.gemini, "generate", fake(" out ", calls=calls))
    r = post("/api/godmode", {
        "text": "x", "sourceLang": "en", "targetLang": "de", "model": "m", "apiKey": KEY,
