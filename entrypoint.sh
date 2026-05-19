#!/bin/sh
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head
echo "[entrypoint] Migrations complete."

echo "[entrypoint] Starting application..."
exec uvicorn app.main:create_app \
    --factory \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --limit-max-requests 10000 \
    --timeout-keep-alive 5
