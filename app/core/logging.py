import json
import logging
import logging.handlers
import sys
from pathlib import Path


def configure_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """Configure application logging with file and console handlers."""
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers = []

    # Formatter with structured logging
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (app.log)
    app_log_file = log_dir_path / "app.log"
    file_handler = logging.handlers.RotatingFileHandler(
        app_log_file,
        maxBytes=10485760,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Error file handler
    error_log_file = log_dir_path / "error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10485760,  # 10MB
        backupCount=5,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Suppress verbose libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info(f"Logging configured at level: {log_level}")
