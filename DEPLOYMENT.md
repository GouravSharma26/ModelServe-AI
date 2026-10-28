# Deployment Guide — ModelServe AI

## Supported delivery stages
1. Local virtual environment development.
2. Multi-container Docker Compose deployment (PostgreSQL 16, FastAPI inference, Streamlit dashboard).
3. GitHub Actions CI pipeline with automated container builds and smoke testing.

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

### Reproducible model preparation
Before starting inference services or Docker Compose from a clean checkout, prepare the verified model artifact:
```powershell
python scripts/prepare_model.py --output artifacts/models
```
This runs the validated training pipeline, computes cryptographic SHA-256 digests, and generates `model.joblib`, `manifest.json`, and `evaluation.json` in `artifacts/models/<version>`.

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
Key configuration parameters:
- `POSTGRES_USER`: PostgreSQL username (default: `modelserve_user`).
- `POSTGRES_PASSWORD`: PostgreSQL password (configure a strong non-default secret for non-local deployments).
- `POSTGRES_DB`: Database name (default: `modelserve_db`).
- `POSTGRES_PORT_BINDING`: Host bind address (default `127.0.0.1:5432` prevents exposing the database externally).
- `API_PORT_BINDING`: API host bind address (default `127.0.0.1:8000`).
- `DASHBOARD_PORT_BINDING`: Dashboard host bind address (default `127.0.0.1:8501`).

### 2. Model artifact preparation
Ensure the model artifact is generated in the mounted `artifacts/models` folder before starting the stack:
```powershell
python scripts/prepare_model.py --output artifacts/models
```

### 3. Startup
```powershell
# Build container images and start services in the background
docker compose up -d --build
```

### 4. Health probes: Liveness vs Readiness
- **Liveness probe (`/health/live`):** Verifies that the FastAPI process is responsive. Used by Docker Compose to ensure the container is functioning.
- **Readiness probe (`/health/ready`):** Verifies that a cryptographically verified model artifact is actively loaded in memory and confirms PostgreSQL connectivity. If model artifacts are missing or unverified, `/health/ready` returns HTTP 503 while `/health/live` remains HTTP 200.
- **Streamlit dashboard probe (`/_stcore/health`):** Verifies that the Streamlit server is active and serving UI sessions.

### 5. Verify services and health status
```powershell
docker compose ps
```
All three services should report `healthy`:
- `postgres`: PostgreSQL 16 on port 5432 with volume `postgres_data`.
- `api`: FastAPI on port 8000 (applies migrations and serves predictions).
- `dashboard`: Streamlit dashboard on port 8501.

### 6. Run automated smoke test
```powershell
python scripts/smoke_test.py --url http://127.0.0.1:8000 --dashboard-url http://127.0.0.1:8501
```

### 7. Accessing interfaces
- API interactive docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health/ready`
- Monitoring dashboard: `http://localhost:8501`

### 8. Teardown
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

---

## Cloud Production Deployment (Neon + Render + Vercel)

### Architecture Overview
- **Database (Neon PostgreSQL):** Serverless PostgreSQL storing prediction telemetry and registered model versions.
- **Backend (Render):** Dockerized FastAPI inference engine executing reproducible models, checking schemas, and recording telemetry.
- **Frontend (Vercel):** React + Vite dashboard delivering real-time predictions, telemetry analytics, and model evaluation metrics over global CDN.

```
+--------------------+        REST JSON (CORS)       +-----------------------+
|  Vercel Frontend   |  -------------------------->  |   Render API Service  |
|   (React + Vite)   |  <--------------------------  |   (FastAPI + Model)   |
+--------------------+                               +-----------------------+
                                                                 |
                                                          SQLAlchemy (TLS)
                                                                 v
                                                     +-----------------------+
                                                     |    Neon PostgreSQL    |
                                                     |  (Serverless Storage) |
                                                     +-----------------------+
```

### Step 1: Provision Neon PostgreSQL
1. Create a project at [Neon.tech](https://neon.tech).
2. Copy the connection string from the Neon dashboard. It will look like:
   `postgresql://neondb_owner:***@ep-***.us-east-2.aws.neon.tech/neondb?sslmode=require`
3. The backend normalizes `postgresql://` to `postgresql+psycopg2://` automatically.

### Step 2: Deploy Backend to Render
1. Push this repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** -> **Web Service**.
3. Connect your GitHub repository `ModelServe-AI`.
4. Configure service settings:
   - **Environment:** `Docker` (or select `render.yaml` Blueprint)
   - **Dockerfile Path:** `Dockerfile.api` (or `Dockerfile`)
   - **Health Check Path:** `/health/live`
5. Add Environment Variables:
   - `DATABASE_URL`: Your Neon PostgreSQL connection string.
   - `CORS_ORIGINS`: `*` (or your Vercel URL e.g. `https://your-app.vercel.app,http://localhost:5173`)
   - `MODELSERVE_MAX_PAYLOAD_BYTES`: `65536`
6. Click **Deploy Web Service**.
   - During build, `Dockerfile.api` trains and packages the reproducible model artifact.
   - On startup, `scripts/docker-entrypoint.sh` executes Alembic migrations (`alembic upgrade head`), verifies model integrity, binds to Render's dynamic `$PORT`, and starts serving.
7. Verify deployment:
   - Check Liveness: `GET https://your-render-service.onrender.com/health/live`
   - Check Readiness: `GET https://your-render-service.onrender.com/health/ready` (confirms model loaded & database connected)
   - Check Docs: `GET https://your-render-service.onrender.com/docs`

### Step 3: Deploy Frontend to Vercel
1. In the [Vercel Dashboard](https://vercel.com), click **Add New...** -> **Project**.
2. Select your `ModelServe-AI` GitHub repository.
3. In Project Configuration:
   - **Framework Preset:** `Vite`
   - **Root Directory:** Edit to select `frontend` (or leave root since `vercel.json` is configured).
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Add Environment Variable:
   - `VITE_API_BASE_URL`: `https://your-render-service.onrender.com`
5. Click **Deploy**.
6. Open your Vercel URL:
   - System Status will show `API Process: Alive` and `Inference Engine: Ready to Serve`.
   - Test predictions via the **Prediction Playground**.
   - Inspect aggregated metrics and latency profiles in **Live Telemetry**.

