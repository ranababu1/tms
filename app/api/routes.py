"""The /api/* JSON contract from spec §5. All POST; errors are {"error": "..."}."""

import json
import logging
from typing import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..core import services
from ..core.services import ServiceError

log = logging.getLogger("tms.api")
router = APIRouter(prefix="/api")

Handler = Callable[[dict], Awaitable[dict]]


def error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


async def _run(request: Request, handler: Handler) -> JSONResponse:
    try:
        body = await request.json()
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return error(400, "Invalid request body.")
    if not isinstance(body, dict):
        return error(400, "Invalid request body.")
    try:
        return JSONResponse(await handler(body))
    except ServiceError as exc:
        return error(exc.status, exc.message)
    except Exception as exc:  # never log the body: it contains the API key
        log.error("Unhandled error in %s: %s", request.url.path, type(exc).__name__)
        return error(500, "An unexpected error occurred. Please try again.")


def _route(path: str, handler: Handler) -> None:
    async def endpoint(request: Request) -> JSONResponse:
        return await _run(request, handler)

    endpoint.__name__ = "api_" + path.strip("/").replace("-", "_")
    router.add_api_route(path, endpoint, methods=["POST"])

