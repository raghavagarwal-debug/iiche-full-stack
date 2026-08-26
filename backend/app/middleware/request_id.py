"""
Request ID middleware — adds a unique X-Request-ID header to every request/response.
Per Section 13: structured logs with request IDs.

Implemented as pure ASGI middleware instead of BaseHTTPMiddleware for better
performance under high concurrency (avoids the extra task creation overhead).
"""

import uuid


class RequestIDMiddleware:
    """Pure ASGI middleware — avoids the per-request task overhead of BaseHTTPMiddleware."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Extract or generate request ID
        headers = dict(scope.get("headers", []))
        supplied_request_id = headers.get(b"x-request-id", b"").decode("utf-8", errors="ignore")
        try:
            request_id = str(uuid.UUID(supplied_request_id))
        except (ValueError, AttributeError):
            request_id = str(uuid.uuid4())

        # Store in scope state for downstream access
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = request_id

        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("utf-8")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_request_id)
