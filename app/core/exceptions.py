"""Custom exception classes for the application."""
from typing import Any


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 500, details: dict[str, Any] | None = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Invalid input data."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=400, details=details)


class AuthenticationError(AppException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationError(AppException):
    """User not authorized for this resource."""

    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, status_code=403)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status_code=404)


class ConflictError(AppException):
    """Resource already exists."""

    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class RateLimitError(AppException):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Too many requests"):
        super().__init__(message, status_code=429)


class ProcessingError(AppException):
    """Error during processing."""

    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class ExternalServiceError(AppException):
    """External service unavailable."""

    def __init__(self, service: str):
        super().__init__(f"{service} service unavailable", status_code=503)
