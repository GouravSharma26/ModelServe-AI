"""HTTP middleware for request IDs, payload size limits, and access timing."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Callable

from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("modelserve.access")


class PayloadTooLargeError(HTTPException):
    """Raised when request payload exceeds configured byte limit."""

    def __init__(self, message: str = "Payload size exceeded limit") -> None:
        super().__init__(status_code=413, detail=message)


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


class PayloadLimitMiddleware:
    """Enforces maximum incoming request payload size, even when Content-Length is absent, chunked, or incorrect."""

    def __init__(self, app: ASGIApp, max_payload_bytes: int = 65536) -> None:
        self.app = app
        self.max_payload_bytes = max_payload_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length_raw = headers.get(b"content-length")
        if content_length_raw is not None:
            try:
                if int(content_length_raw.decode("latin1")) > self.max_payload_bytes:
                    await self._send_413(scope, send)
                    return
            except ValueError:
                pass

        bytes_received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal bytes_received
            message = await receive()
            if message.get("type") == "http.request":
                chunk = message.get("body", b"")
                bytes_received += len(chunk)
                if bytes_received > self.max_payload_bytes:
                    raise PayloadTooLargeError(
                        f"Payload size exceeded maximum limit of {self.max_payload_bytes} bytes"
                    )
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except PayloadTooLargeError:
            if not response_started:
                await self._send_413(scope, send)

    async def _send_413(self, scope: Scope, send: Send) -> None:
        headers = dict(scope.get("headers", []))
        incoming_id = headers.get(b"x-request-id", b"").decode("latin1").strip()
        request_id = incoming_id if incoming_id else f"req_{uuid.uuid4().hex[:16]}"
        error_body = json.dumps({
            "error": {
                "code": "PAYLOAD_TOO_LARGE",
                "message": f"Payload size exceeds maximum limit of {self.max_payload_bytes} bytes",
                "request_id": request_id,
            }
        }).encode("utf-8")
        response_headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(error_body)).encode("ascii")),
            (b"x-request-id", request_id.encode("ascii")),
        ]
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": response_headers,
        })
        await send({
            "type": "http.response.body",
            "body": error_body,
        })


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
