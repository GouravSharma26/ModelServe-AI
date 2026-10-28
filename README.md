# ModelServe AI

**Project status: Fast Track release implemented & verified locally and in CI.** The repository contains a complete, reproducible ML training/evaluation pipeline, FastAPI inference service, PostgreSQL telemetry persistence, Streamlit monitoring dashboard, Docker Compose multi-service deployment, and GitHub Actions CI.

## Features implemented

- **Reproducible ML training:** Ingestion, validation, 60/20/20 stratified split, and model selection on IBM's public Telco Customer Churn sample (Apache-2.0). Fitted preprocessing and classifier are serialized together as versioned immutable artifacts with SHA-256 manifests.
- **FastAPI inference service:** Single-record prediction endpoint (`POST /v1/predictions`), model metadata endpoint (`GET /v1/model/info`), liveness check (`GET /health/live`), and readiness check (`GET /health/ready`).
- **PostgreSQL telemetry persistence:** SQLAlchemy 2.0 and Alembic migrations storing prediction labels, scores, latencies, and model versions. Excludes raw input features per privacy rules (ADR-008). Telemetry is queried via `GET /v1/monitoring/summary`.
- **Streamlit monitoring dashboard:** Real-time metrics visualization (label distribution, churn rate, latency percentiles p50/p90/p95/p99), training provenance, offline evaluation benchmarks (confusion matrix, PR-AUC, ROC-AUC), and an interactive prediction playground.
- **Docker Compose orchestration:** Multi-container deployment connecting PostgreSQL 16, FastAPI, and Streamlit with volume persistence, health checks, environment-variable configuration, and localhost-isolated port bindings.
- **Trusted artifact loader:** Cryptographic SHA-256 verification against the artifact manifest before loading; tampered or unverified files are rejected.
- **Safety and observability:** X-Request-ID propagation, structured JSON logging with latency metrics, 64 KB payload size guard, and sanitized error envelopes that never expose internal stack traces or raw payload values.

## Quickstart

### Prerequisites
- Python 3.12 (tested on 3.12.6)
- Docker Desktop / Engine and Docker Compose (v5.6.1+)

### Installation
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
```

### Reproducible model preparation
To train candidates and generate verified model artifacts from a clean checkout:
```powershell
python scripts/prepare_model.py --output artifacts/models
```
Outputs a verified model version folder in `artifacts/models/<version>` containing `model.joblib`, `manifest.json`, and `evaluation.json`.

### Multi-container Docker Compose deployment
```powershell
# 1. Prepare configuration
Copy-Item .env.example .env

# 2. Build images and start all containers
docker compose up -d --build

# 3. Verify running containers and health checks
docker compose ps

# 4. Run automated end-to-end smoke test
python scripts/smoke_test.py --url http://127.0.0.1:8000 --dashboard-url http://127.0.0.1:8501
```

### Accessing services
- Interactive API Docs: `http://localhost:8000/docs`
- Health Readiness Probe: `http://localhost:8000/health/ready`
- Streamlit Monitoring Dashboard: `http://localhost:8501`

### Running tests
```powershell
pytest -ra
```
Unit, persistence, schema, and API tests covering data loading, training, model integrity verification, and database telemetry.

## API overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health/live` | Process liveness check (HTTP 200) |
| `GET` | `/health/ready` | Service readiness check (verifies active model and DB connection) |
| `GET` | `/v1/model/info` | Returns active model version, dataset metadata, and evaluation metrics |
| `POST` | `/v1/predictions` | Churn prediction for a single customer observation |
| `GET` | `/v1/monitoring/summary` | Rolling-window prediction counts, label distribution, and latency profile |

See [API_GUIDE.md](API_GUIDE.md) and [DEPLOYMENT.md](DEPLOYMENT.md) for full request/response schemas and deployment details.
