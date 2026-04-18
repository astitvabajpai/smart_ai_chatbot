#!/usr/bin/env bash
# Production startup script for Document Chatbot
set -euo pipefail

export PYTHONUNBUFFERED=1

# Create required directories
mkdir -p logs storage/{uploads,chroma}

# Log startup info
echo "🚀 Starting Document Chatbot API..."
echo "   Environment: ${APP_ENV:-development}"
echo "   Workers: ${API_WORKERS:-4}"
echo "   Port: ${API_PORT:-8000}"
echo "   Vector Backend: ${VECTOR_BACKEND:-chroma}"

# Start Gunicorn with Uvicorn workers
exec gunicorn \
    -k uvicorn.workers.UvicornWorker \
    -w "${API_WORKERS:-4}" \
    -b "${API_HOST:-0.0.0.0}:${API_PORT:-8000}" \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level "${LOG_LEVEL:-info}" \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    app.main:app
