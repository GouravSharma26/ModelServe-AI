# ModelServe AI

**Project status: Phase 2 complete; Fast Track MVP in progress.** The repository contains the reproducible training/evaluation pipeline and the FastAPI inference service. PostgreSQL persistence, Streamlit dashboard, Docker Compose, CI, and public deployment remain subsequent planned phases.

## Features implemented

- **Reproducible ML training:** Ingestion, validation, 60/20/20 stratified split, and model selection on IBM's public Telco Customer Churn sample (Apache-2.0). Fitted preprocessing and classifier are serialized together as versioned immutable artifacts with SHA-256 manifests.
- **FastAPI inference service:** Single-record prediction endpoint (`POST /v1/predictions`), model metadata endpoint (`GET /v1/model/info`), liveness check (`GET /health/live`), and readiness check (`GET /health/ready`).
- **Pydantic schema validation:** All 19 customer features validated with strict type and categorical bounds; unexpected extra fields are forbidden (`extra = "forbid"`).
- **Trusted artifact loader:** Cryptographic SHA-256 verification against the artifact manifest before loading; tampered or unverified files are rejected.
- **Observability and safety:** X-Request-ID propagation, structured JSON logging with latency metrics, 64 KB payload size guard, and sanitized error envelopes that never expose internal stack traces.

## Quickstart

### Prerequisites
- Python 3.12 (tested on 3.12.6)

### Installation
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
```

### Running the training pipeline
```powershell
modelserve-train --output artifacts/models
```
Outputs a versioned model folder in `artifacts/models/<version>` containing `model.joblib`, `manifest.json`, and `evaluation.json`.

### Starting the inference API
```powershell
modelserve-api
# Alternatively: python -m uvicorn modelserve.app:app --host 0.0.0.0 --port 8000
```
Interactive OpenAPI documentation is available locally at `http://localhost:8000/docs`.

### Running tests
```powershell
pytest -q
```
34 unit, integration, schema, and API tests covering data loading, training, model integrity verification, and API behavior.

## API overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health/live` | Process liveness check (HTTP 200) |
| `GET` | `/health/ready` | Service readiness check (verifies active model is loaded) |
| `GET` | `/v1/model/info` | Returns active model version, dataset metadata, and evaluation metrics |
| `POST` | `/v1/predictions` | Churn prediction for a single customer observation |

See [API_GUIDE.md](API_GUIDE.md) for full request/response schemas and examples.

## Current scope and next phase

- **Completed:** Phase 0 (Reconnaissance & design), Phase 1 (ML training pipeline), Phase 2 (FastAPI inference vertical slice).
- **Next:** Phase 3 — PostgreSQL persistence (Alembic migrations, prediction event telemetry, model version records).
- **Resume readiness:** NOT READY until Phase 5 verification criteria pass. See [FAST_TRACK_PLAN.md](FAST_TRACK_PLAN.md) and [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md).
