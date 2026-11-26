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
