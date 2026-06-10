# app/middleware/logging.py
import time
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

log = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Injects a correlation ID into every request.
    Logs method, path, status, and duration for every request.
    """

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=req_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            ip=request.client.host if request.client else "unknown",
            user_agent=(request.headers.get("user-agent", "")[:100]),
        )

        response.headers["X-Request-ID"] = req_id
        return response
