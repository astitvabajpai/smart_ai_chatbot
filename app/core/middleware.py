"""FastAPI middleware for error handling, logging, and rate limiting."""
import json
import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.exceptions import AppException, RateLimitError
from app.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except AppException as exc:
            logger.warning(f"Application exception: {exc.message}", extra={"status_code": exc.status_code})
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.message,
                    "details": exc.details,
                },
            )
        except Exception as exc:
            logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "details": {"message": str(exc)},
                },
            )


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", "")

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
            },
        )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                },
            )
            return response
        except Exception as exc:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "error": str(exc),
                },
                exc_info=True,
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""

    def __init__(self, app, rate_limiter: RateLimiter | None = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.rate_limiter:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path == "/api/health" or request.url.path.startswith("/docs"):
            return await call_next(request)

        client_id = request.client.host if request.client else "unknown"
        if not self.rate_limiter.is_allowed(client_id):
            raise RateLimitError("Too many requests. Please try again later.")

        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size."""

    def __init__(self, app, max_size_bytes: int):
        super().__init__(app)
        self.max_size_bytes = max_size_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_size_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": "Payload too large",
                        "details": {
                            "max_size_mb": self.max_size_bytes / (1024 * 1024),
                        },
                    },
                )
        return await call_next(request)
