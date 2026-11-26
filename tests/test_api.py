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
        "systemPrompt": "From {sourceLang} to {targetLang}", "temperature": 5, "topP": -1, "topK": 400.6,
        "maxOutputTokens": 10**9, "presencePenalty": 9, "frequencyPenalty": -9, "seed": 4.6,
        "thinkingLevel": "bogus",
    })
    assert r.status_code == 200 and r.json()["translatedText"] == "out"
    c = calls[0]
    assert c["args"][2].startswith("From English to German\nCODE/MARKUP RULES")
    kw = c["kwargs"]
    assert (kw["temperature"], kw["top_p"], kw["top_k"]) == (1, 0, 100)
    assert kw["max_output_tokens"] == 65536 and kw["presence_penalty"] == 2 and kw["frequency_penalty"] == -2
    assert kw["seed"] == 5 and kw["thinking_level"] is None


def test_claude_godmode_gates(monkeypatch):
    calls = []
    monkeypatch.setattr(services.claude, "create_message", fake("ok", calls=calls))
    body = {"text": "x", "targetLang": "de", "apiKey": KEY, "systemPrompt": "p",
            "temperature": 0.4, "topK": 900, "maxOutputTokens": 0, "effort": "max"}
    post("/api/godmode-claude", {**body, "model": "claude-opus-5-5"})
    assert calls[0]["args"][4] == 1 and calls[0]["kwargs"] == {"effort": "max"}
    calls.clear()
    post("/api/godmode-claude", {**body, "model": "claude-haiku-4-5"})
    assert calls[0]["kwargs"] == {"temperature": 0.4, "top_k": 500}
    r = post("/api/godmode-claude", {**body, "apiKey": "x", "model": "claude-haiku-4-5"})
    assert r.json()["error"] == "Invalid or missing API key."


# ---- verify / fix / review ------------------------------------------------

VERIFY_BODY = {"originalText": "o", "translatedText": "t", "targetLang": "de", "model": "claude-haiku-4-5", "apiKey": KEY}


def test_verify_success_and_parse_failure(monkeypatch):
    monkeypatch.setattr(services.claude, "create_message",
                        fake('```json\n{"results":[{"item":1,"pass":true,"note":"ok"}],"allPassed":false}\n```'))
    data = post("/api/verify-translation-claude", VERIFY_BODY).json()
    assert len(data["checklist"]) == 15 and data["results"][0]["pass"] is True and data["allPassed"] is False
    monkeypatch.setattr(services.claude, "create_message", fake("I cannot comply"))
    r = post("/api/verify-translation-claude", VERIFY_BODY)
    assert r.status_code == 502 and r.json()["error"] == "Verification response could not be parsed. Please try again."
    monkeypatch.setattr(services.claude, "create_message", fake("", finish="max_tokens"))
    assert "ran out of output budget" in post("/api/verify-translation-claude", VERIFY_BODY).json()["error"]
    monkeypatch.setattr(services.claude, "create_message", fake(raises=ProviderError("busy", 529)))
    assert post("/api/verify-translation-claude", VERIFY_BODY).status_code == 529


def test_verify_validation():
    r = post("/api/verify-translation", {**VERIFY_BODY, "apiKey": ""})
    assert r.json()["error"] == "A valid Gemini API key is required."
    r = post("/api/verify-translation-claude", {**VERIFY_BODY, "model": "nope"})
    assert r.json()["error"] == "Invalid model selection."


def test_fix(monkeypatch):
    body = {"originalText": "o", "currentTranslation": "c", "targetLang": "tr", "model": "m", "apiKey": KEY}
    r = post("/api/fix-translation", {**body, "failingChecks": []})
    assert r.status_code == 400 and r.json()["error"] == "At least one failing check is required."
    calls = []
    monkeypatch.setattr(services.gemini, "generate", fake("  fixed  ", calls=calls))
    r = post("/api/fix-translation", {**body, "failingChecks": [{"description": "d", "note": "n"}]})
    assert r.json()["translatedText"] == "fixed"
    assert "1. d — Reviewer note: n" in calls[0]["args"][2]
    assert calls[0]["kwargs"]["temperature"] == 0.5


def test_review(monkeypatch):
    calls = []
    monkeypatch.setattr(services.gemini, "generate",
                        fake('{"hasIssues": true, "issues": ["a"], "correctedTranslation": "better"}', calls=calls))
    body = {"originalText": "o", "translatedText": "t", "targetLang": "Turkish", "model": "m", "apiKey": KEY}
    data = post("/api/review-translation", body).json()
    assert data["hasIssues"] and data["issues"] == ["a"] and data["correctedTranslation"] == "better"
    assert "native Turkish speaker" in calls[0]["args"][2]
    monkeypatch.setattr(services.gemini, "generate", fake("{oops"))
    data = post("/api/review-translation", body).json()
    assert data["issues"] == ["Review parsing failed. Raw review returned."]


# ---- model catalogs -------------------------------------------------------

def test_models_fallback_on_provider_error(monkeypatch):
    async def boom(*a, **k):
        raise ProviderError("bad key", 401)
    monkeypatch.setattr(services.claude, "list_models", boom)
    r = post("/api/claude-models", {"apiKey": KEY})
    assert r.status_code == 200
    data = r.json()
    assert data["fallback"] is True and data["fetchedAt"] is None
    assert [m["id"] for m in data["models"]] == ["claude-opus-5-5", "claude-sonnet-5", "claude-haiku-4-5"]
    assert post("/api/models", {"apiKey": "x"}).status_code == 400
