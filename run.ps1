# Creates the venv on first run, installs deps, and starts the server.
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python -m pip install -q -r requirements.txt
& .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000 --timeout-keep-alive 620
