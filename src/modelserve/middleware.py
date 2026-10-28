"""HTTP middleware for request IDs, payload size limits, and access timing."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("modelserve.access")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns or propagates an X-Request-ID for every incoming request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming_id = request.headers.get("X-Request-ID", "").strip()
        if incoming_id and len(incoming_id) <= 128 and incoming_id.replace("-", "").replace("_", "").isalnum():
            request_id = incoming_id
        else:
            request_id = f"req_{uuid.uuid4().hex[:16]}"

        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class PayloadLimitMiddleware(BaseHTTPMiddleware):
    """Enforces maximum incoming request payload size."""

    def __init__(self, app, max_payload_bytes: int = 65536) -> None:
        super().__init__(app)
        self.max_payload_bytes = max_payload_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("Content-Length")
        request_id = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:16]}")

        if content_length is not None:
            try:
                length = int(content_length)
                if length > self.max_payload_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Payload size {length} bytes exceeds maximum limit of {self.max_payload_bytes} bytes",
                                "request_id": request_id,
                            }
                        },
                        headers={"X-Request-ID": request_id},
                    )
            except ValueError:
                pass

        return await call_next(request)


class AccessLoggingMiddleware(BaseHTTPMiddleware):
    """Emits structured access logs with request IDs and execution latencies."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        request_id = getattr(request.state, "request_id", "-")

        logger.info(
            f"{request.method} {request.url.path} {response.status_code} in {latency_ms}ms",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response

