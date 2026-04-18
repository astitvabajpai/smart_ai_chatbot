import logging
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import ErrorHandlingMiddleware, LoggingMiddleware, RequestSizeLimitMiddleware
from app.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure logging
configure_logging(log_level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle: startup and shutdown."""
    logger.info("Application starting up...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Vector backend: {settings.vector_backend}")
    logger.info(f"Embedding provider: {settings.embedding_provider}")

    yield

    logger.info("Application shutting down...")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Production-grade Document Chatbot with RAG",
    lifespan=lifespan,
)

# Add security middleware first
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# Add request size limit middleware
max_upload_bytes = settings.max_upload_size_mb * 1024 * 1024
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_size_bytes=max_upload_bytes,
)

# Add rate limiting if enabled
if settings.enable_rate_limiting:
    rate_limiter = RateLimiter(
        requests=settings.rate_limit_requests,
        period_seconds=settings.rate_limit_period_seconds,
    )
    from app.core.middleware import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

# Add logging and error handling middleware (order matters - applies in reverse)
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

# Include routes
app.include_router(router, prefix="/api")


# Graceful shutdown handlers
def signal_handler(signum, frame):
    """Handle termination signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
