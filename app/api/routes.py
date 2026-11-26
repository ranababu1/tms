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

