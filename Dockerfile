# Dockerfile for ModelServe AI FastAPI inference service
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -m -s /bin/bash appuser

WORKDIR /app

# Install pinned Python dependencies
COPY requirements.lock /app/
RUN pip install --no-cache-dir -r requirements.lock

# Copy application source, migrations, scripts, and project configuration
COPY pyproject.toml alembic.ini /app/
COPY alembic /app/alembic
COPY src /app/src
COPY scripts /app/scripts

RUN pip install --no-cache-dir --no-deps -e .

# Prepare model artifact during build for self-contained deployment
RUN python -m modelserve.model_preparation --output /app/artifacts/models

# Set entrypoint permissions and ownership
RUN chmod +x /app/scripts/docker-entrypoint.sh && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health/live || exit 1

ENTRYPOINT ["/bin/sh", "/app/scripts/docker-entrypoint.sh"]

