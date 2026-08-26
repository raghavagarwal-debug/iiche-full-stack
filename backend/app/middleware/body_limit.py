"""
Request body size limit middleware.
Per Section 12: request size limits to prevent memory exhaustion attacks.

Implemented as pure ASGI middleware for performance.
"""

import logging

from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


class RequestBodyLimitMiddleware:
    """
    Pure ASGI middleware that rejects requests with Content-Length exceeding the configured limit.
    Also tracks actual bytes received to catch chunked-transfer attacks that omit Content-Length.
    """

    def __init__(self, app):
        self.app = app
        self.max_bytes = settings.max_request_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Quick check via Content-Length header (if present)
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large"},
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass

        # Wrap receive to track actual bytes for chunked transfers
        bytes_received = 0

        async def limited_receive():
            nonlocal bytes_received
            message = await receive()
            if message.get("type") == "http.request":
                body = message.get("body", b"")
                bytes_received += len(body)
                if bytes_received > self.max_bytes:
                    raise RequestTooLarge()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLarge:
            response = JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"},
            )
            await response(scope, receive, send)


class RequestTooLarge(Exception):
    """Raised when the request body exceeds the configured limit."""
    pass
