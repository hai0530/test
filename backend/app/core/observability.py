"""Small, dependency-free HTTP observability primitives.

The API uses a request identifier to make a request traceable across the
application logs.  Log records are emitted as JSON so they can be ingested by
Docker, a hosted log collector, or a local command-line parser without a
second logging dependency.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
logger = logging.getLogger("app.http")


def _request_id(value: str | None) -> str:
    """Return a safe caller-provided ID or generate one for the request."""

    if value and _REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid.uuid4())


class JsonFormatter(logging.Formatter):
    """Render application log records as one JSON object per line."""

    _extra_fields = (
        "event",
        "request_id",
        "method",
        "path",
        "status_code",
        "duration_ms",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in self._extra_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    """Configure a single JSON handler for application-owned loggers.

    Uvicorn keeps its own access logger.  This handler only owns the ``app``
    namespace, preventing duplicate records when the application is imported
    by tests or by a process that already configured the root logger.
    """

    app_logger = logging.getLogger("app")
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID and emit one structured record per request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = _request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "request failed",
                extra={
                    "event": "http.request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": elapsed_ms,
                },
            )
            raise

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request completed",
            extra={
                "event": "http.request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": elapsed_ms,
            },
        )
        return response
