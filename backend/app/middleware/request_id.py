"""
Request ID middleware: generates or propagates correlation IDs across the request lifecycle.
"""

import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

# Context variable accessible across async tasks for structured logging
request_id_ctx: ContextVar[str] = ContextVar("request_id_ctx", default="")


def get_request_id() -> str:
    """Retrieve the correlation ID of the current active request context."""
    return request_id_ctx.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that reads or assigns an X-Request-ID header,
    binds it to the async context, and echoes it in the response headers.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Extract incoming header or generate a new UUID4
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)

        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            request_id_ctx.reset(token)
