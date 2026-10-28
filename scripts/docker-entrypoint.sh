#!/bin/sh
set -e

# Run database schema migrations if DATABASE_URL is configured
if [ -n "$DATABASE_URL" ]; then
    echo "Applying database schema migrations..."
    alembic upgrade head || echo "Alembic migration notice: schema bootstrap handled by app lifespan."
fi

# Ensure model artifacts exist; generate if missing
if [ ! -d "/app/artifacts/models" ] || [ -z "$(ls -A /app/artifacts/models 2>/dev/null)" ]; then
    echo "No model artifacts found in /app/artifacts/models. Generating artifact..."
    python -m modelserve.model_preparation --output /app/artifacts/models || echo "Warning: model preparation encountered an issue."
fi

PORT="${PORT:-8000}"
echo "Starting ModelServe AI on 0.0.0.0:$PORT..."
exec python -m uvicorn modelserve.app:app --host 0.0.0.0 --port "$PORT"

