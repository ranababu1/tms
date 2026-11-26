"""FastAPI entry point: JSON API under /api and the server-rendered pages.

Run:  uvicorn app.main:app --reload
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api.routes import router as api_router
from .pages import PAGES, page_config

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE / "templates")

app = FastAPI(title="Transcreator", docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json")
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    return response


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(request, "landing.html", {})


def _register_tool_page(provider: str, mode: str, path: str) -> None:
    async def page(request: Request):
        cfg = page_config(provider, mode)
        return templates.TemplateResponse(request, "tool.html", {"cfg": cfg})

    page.__name__ = f"page_{provider}_{mode}"
    app.add_api_route(path, page, methods=["GET"], response_class=HTMLResponse)

