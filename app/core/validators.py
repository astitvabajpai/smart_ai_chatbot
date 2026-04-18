"""Input validation utilities."""
import re
from pathlib import Path

from app.core.exceptions import ValidationError


class Validator:
    """Common input validation methods."""

    # Password must have at least 8 chars, 1 uppercase, 1 lowercase, 1 digit
    PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$")
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format."""
        email = email.strip().lower()
        if not email:
            raise ValidationError("Email is required")
        if len(email) > 254:
            raise ValidationError("Email is too long")
        if not Validator.EMAIL_PATTERN.match(email):
            raise ValidationError("Invalid email format")
        return email

    @staticmethod
    def validate_password(password: str, min_length: int = 8) -> str:
        """Validate password strength."""
        if not password:
            raise ValidationError("Password is required")
        if len(password) < min_length:
            raise ValidationError(f"Password must be at least {min_length} characters")
        if len(password) > 128:
            raise ValidationError("Password is too long")
        return password

    @staticmethod
    def validate_full_name(name: str) -> str:
        """Validate full name."""
        name = name.strip()
        if not name:
            raise ValidationError("Full name is required")
        if len(name) < 2:
            raise ValidationError("Full name must be at least 2 characters")
        if len(name) > 100:
            raise ValidationError("Full name is too long")
        # Allow letters, spaces, hyphens, apostrophes
        if not re.match(r"^[a-zA-Z\s\-']{2,100}$", name):
            raise ValidationError("Full name contains invalid characters")
        return name

    @staticmethod
    def validate_question(question: str, min_length: int = 3, max_length: int = 5000) -> str:
        """Validate question/query."""
        question = question.strip()
        if not question:
            raise ValidationError("Question is required")
        if len(question) < min_length:
            raise ValidationError(f"Question must be at least {min_length} characters")
        if len(question) > max_length:
            raise ValidationError(f"Question must be less than {max_length} characters")
        return question

    @staticmethod
    def validate_filename(filename: str) -> str:
        """Validate uploaded filename."""
        if not filename:
            raise ValidationError("Filename is required")

        # Get just the filename, remove any path traversal attempts
        filename = Path(filename).name
        if not filename:
            raise ValidationError("Invalid filename")

        # Only allow PDF files
        if not filename.lower().endswith(".pdf"):
            raise ValidationError("Only PDF files are supported")

        # Max filename length
        if len(filename) > 255:
            raise ValidationError("Filename too long")

        return filename

    @staticmethod
    def validate_top_k(top_k: int | None) -> int | None:
        """Validate top_k parameter."""
        if top_k is None:
            return None
        if not isinstance(top_k, int):
            raise ValidationError("top_k must be an integer")
        if top_k < 1:
            raise ValidationError("top_k must be at least 1")
        if top_k > 50:
            raise ValidationError("top_k must be at most 50")
        return top_k

    @staticmethod
    def validate_chunk_size(size: int) -> int:
        """Validate chunk size."""
        if size < 100:
            raise ValidationError("Chunk size must be at least 100")
        if size > 10000:
            raise ValidationError("Chunk size must be at most 10000")
        return size

    @staticmethod
    def validate_url(url: str) -> str:
        """Validate URL format."""
        url = url.strip()
        if not url:
            raise ValidationError("URL is required")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValidationError("URL must start with http:// or https://")
        if len(url) > 2048:
            raise ValidationError("URL is too long")
        return url
