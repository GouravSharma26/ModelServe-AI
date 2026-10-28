# Deployment Guide — ModelServe AI

## Supported delivery stages
1. Local virtual environment development.
2. Multi-container Docker Compose deployment (PostgreSQL 16, FastAPI inference, Streamlit dashboard).
3. GitHub Actions CI pipeline.

## Prerequisites
- Git
- Python 3.12 (tested on 3.12.6)
- Docker Desktop / Engine (tested on v29.9.2) and Docker Compose (v5.6.1)

## Local virtual environment setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
```

### Running database migrations locally
```powershell
# Set DATABASE_URL (or use local SQLite for development)
$env:DATABASE_URL = "sqlite:///local_dev.db"
alembic upgrade head
```

### Starting services locally
In separate terminal windows:
```powershell
# 1. Start API (port 8000)
python -m uvicorn modelserve.app:app --host 0.0.0.0 --port 8000

# 2. Start Dashboard (port 8501)
streamlit run src/modelserve/dashboard.py --server.port 8501
```

## Docker Compose deployment

### 1. Configuration
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

### 2. Startup
```powershell
# Build container images and start services in the background
docker compose up -d --build
```

### 3. Verify services and health status
```powershell
docker compose ps
```
All three services should show `healthy`:
- `postgres`: PostgreSQL 16 on port 5432 with named volume `postgres_data`.
- `api`: FastAPI on port 8000 (applies migrations and serves predictions).
- `dashboard`: Streamlit dashboard on port 8501.

### 4. Run automated smoke test
```powershell
python scripts/smoke_test.py --url http://localhost:8000
```

### 5. Accessing interfaces
- API interactive docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health/ready`
- Monitoring dashboard: `http://localhost:8501`

### 6. Teardown
```powershell
docker compose down
# To clean up persisted data volume as well:
docker compose down -v
```

## Operational troubleshooting

| Symptom | Cause | Diagnostic command / Action |
|---|---|---|
| `/health/ready` returns 503 | Model artifact missing or corrupted | Check `docker compose logs api`. Ensure `artifacts/models` contains a valid version directory with matching SHA-256 manifest. |
| Database connection failed | PostgreSQL container starting or unhealthy | Inspect `docker compose logs postgres`. The API will continue serving predictions but log database warnings. |
| `alembic upgrade head` fails | Mismatched database URL or table conflict | Verify `DATABASE_URL` matches PostgreSQL container credentials. |
| Dashboard shows 0 predictions | Clean database state (empty window) | Expected empty state behavior. Send test requests via `/v1/predictions` or the dashboard Playground tab. |
| Port conflict (8000 or 8501) | Port already occupied on host | Override port bindings in `.env` (`MODELSERVE_PORT=8001`) or adjust `docker-compose.yml`. |
