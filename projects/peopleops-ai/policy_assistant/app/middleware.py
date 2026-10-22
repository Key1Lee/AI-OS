from starlette.responses import JSONResponse


class RequestSizeLimit:
    """Bound actual request bytes, including requests without Content-Length."""

    def __init__(self, app, max_bytes):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            return await self.app(scope, receive, send)
        parts, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            part = message.get("body", b"")
            size += len(part)
            if size > self.max_bytes:
                return await JSONResponse({"detail": "Request too large"}, status_code=413)(scope, receive, send)
            parts.append(part)
            if not message.get("more_body", False):
                break
        body = b"".join(parts)
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
