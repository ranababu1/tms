# Transcreator

Bring-your-own-key marketing translation built on Google Gemini and Anthropic Claude.
The backend is Python (FastAPI). The frontend is plain HTML, CSS and JavaScript served by the same process, with no Node build step.

## Features

- **Simple mode** (`/translate`, `/translate/claude`): hand-written prompts for German, Turkish and Vietnamese. Each answer comes back as a draft, a 15-point self-critique and a final version. Other target languages use the German prompt with a target-language override (shown in violet in the selector).
- **Verification loop** (opt-in in the key dialog): an independent reviewer grades the result. Failing checks are fixed, and the loop runs up to 5 rounds. Each attempt gets its own tab.
- **Translate and Review** (Gemini): a second QA pass that can offer a corrected version.
- **God Mode** (`/godmode`, `/godmode/claude`): you can edit the system prompt and every sampling parameter. Code and markup preservation rules are always appended. Claude controls that the selected model does not support are shown greyed out.
- Live model catalogs, cached for 7 days. If a fetch fails, the app falls back to a static list. Token limits and USD/INR pricing are shown in the model-info modal, and per-request and per-session cost is tracked.

## Run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000 --timeout-keep-alive 620
```

Open http://127.0.0.1:8000 and click **Set API Key**. No server environment variables are needed.

## Privacy

Your key is stored in this tab's `sessionStorage`. It is sent in the body of each request to this app's `/api/*` routes, which forward it to the provider. The server never stores or logs it.

## Tests

