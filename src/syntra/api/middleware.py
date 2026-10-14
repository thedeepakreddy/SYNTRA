"""HTTP middleware for security, correlation IDs, and request size boundaries."""

from typing import Any

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from syntra.api.errors import create_problem_response
from syntra.core.config import get_settings


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforce strict upper bound on incoming request body payloads (default: 10MB)."""

    def __init__(self, app: Any, max_bytes: int | None = None) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes or get_settings().max_request_body_bytes

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        content_length_header = request.headers.get("content-length")
        if content_length_header:
            try:
                content_length = int(content_length_header)
                if content_length > self.max_bytes:
                    return create_problem_response(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        title="Payload Too Large",
                        detail=f"Request body of {content_length} bytes exceeds maximum allowed size of {self.max_bytes} bytes.",
                        instance=request.url.path,
                        problem_type="https://api.syntra.io/errors/payload-too-large",
                    )
            except ValueError:
                pass

        response: Response = await call_next(request)
        return response
