#!/bin/sh
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head
echo "[entrypoint] Migrations complete."

if [ "$#" -gt 0 ]; then
    # A command was passed (e.g. celery worker) — run it
    echo "[entrypoint] Starting: $*"
    exec "$@"
else
    # No command → default to API server
    echo "[entrypoint] Starting API server..."
    exec uvicorn app.main:create_app \
        --factory \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 4 \
        --limit-max-requests 10000 \
        --timeout-keep-alive 5
fi
