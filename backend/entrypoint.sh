#!/usr/bin/env bash
set -e

echo "=== Kerdostat Backend Starting ==="
echo "Environment: ${ENVIRONMENT:-production}"

# Run database migrations if alembic configuration exists
if [ -f "alembic.ini" ]; then
    echo "Running Alembic database migrations..."
    alembic upgrade head || echo "Warning: Alembic migrations encountered an issue or database is up to date."
else
    echo "No alembic.ini found in current working directory, skipping explicit migrations."
fi

# Launch server process
if [ "${ENVIRONMENT}" = "development" ]; then
    echo "Starting Uvicorn in development mode..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    WORKERS="${WORKERS:-4}"
    LOG_LEVEL="${LOG_LEVEL:-info}"
    echo "Starting Gunicorn in production mode with ${WORKERS} workers..."
    exec gunicorn app.main:app \
        --workers "${WORKERS}" \
        --worker-class uvicorn.workers.UvicornWorker \
        --ws wsproto \
        --bind 0.0.0.0:8000 \
        --log-level "${LOG_LEVEL}" \
        --access-logfile - \
        --error-logfile -
fi
