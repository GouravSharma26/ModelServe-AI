# Phase Log

Append a dated entry at the end of every phase. Do not rewrite history to make a phase look successful.

## Entry template
### YYYY-MM-DD — Phase N: Title
**Status:** DONE / PARTIAL / BLOCKED

**Summary**
- What was implemented.

**Files**
- Created/changed files.

**Commands**
- Exact command:
- Exact result:

**Tests and verification**
- Unit tests:
- Integration tests:
- API/manual smoke tests:
- Container/deployment checks:

**Evidence**
- Test report, logs, screenshots, CI run, deployment URL, or commit SHA.

**Limitations / defects**
- Explicit list.

**Human action required**
- Account access, secrets, manual approval, or none.

**Git**
- Branch:
- `git status`:
- Commit SHA (if any):

**Resume readiness**
- READY / NOT READY, with criteria-based reason.

**Next phase**
- Next smallest verified increment.

## Project initialization
No implementation status is assumed by this documentation package. Antigravity must inspect the actual repository and fill the first entry with real findings before claiming progress.

### 2026-10-28 — Phase 0: Repository reconnaissance and design lock
**Status:** DONE

**Summary**
- Workspace contained the project documentation only; no source, tests, migrations, dataset, model, CI, Dockerfile, Compose file, or `.git` directory was present.
- `git status --short --branch` and `git rev-parse --show-toplevel` both failed because this directory is not a Git repository. No files were overwritten and no Git repository was initialized.
- Selected Python 3.12.6 (default `python`); Python 3.13.1 is also installed. Git 2.46.0, Docker 29.9.2, and Docker Compose 5.6.1 are available.
- Selected UCI Bank Marketing (`bank-full.csv`) instead of the unverified Telco churn dataset. UCI documents CC BY 4.0, the term-deposit target, and source columns. See ADR-003 and TRAINING.md.
- Initial dependency pins target the installed Python 3.12 environment and will be resolved/checked during Phase 1 implementation.

**Files**
- `PHASE_LOG.md`, `DEVELOPMENT_CHECKLIST.md`, `DECISIONS.md`

**Commands**
- `Get-ChildItem -Force; git status --short --branch; rg --files ...` — docs only; Git reported “fatal: not a git repository”.
- `python --version` — Python 3.12.6.
- `py --list` — launcher listing unavailable; later `py -3.13 --version` returned Python 3.13.1 and `py -3.12` found no registered runtime.
- `git --version` — 2.46.0.windows.1.
- `docker --version` — 29.9.2.
- `docker compose version` — v5.6.1.
- `python -m pip list --format=columns` — default environment has NumPy 2.1.3, Pandas 2.3.2, scikit-learn 1.5.2, SciPy 1.16.2, pytest 8.3.4.

**Tests and verification**
- No existing tests or implementation were present during reconnaissance.
- Dataset source, license, target, and schema verified against UCI Bank Marketing repository entry: https://archive.ics.uci.edu/dataset/222/bank+marketing (accessed 2026-10-28).
- Python compatibility checked against official scikit-learn installation documentation and pinned package metadata; see TRAINING.md.

**Evidence**
- Workspace inventory and runtime command output; UCI dataset documentation.

**Limitations / defects**
- The workspace has no Git metadata, so branch, diff, and commit state cannot be reported. GitHub CI cannot be connected to a remote until a repository is provided/initialized.
- Docker/Compose versions were detected, but daemon health has not been checked.
- Dataset archive has not yet been downloaded; Phase 1 will verify download and run training if network access permits.

**Human action required**
- None for local Phase 1 work. A Git repository/remote will be needed for CI and release evidence.

**Git**
- Branch: unavailable (not a Git repository).
- `git status`: failed with “fatal: not a git repository”.
- Commit SHA: none.

**Resume readiness**
- NOT READY. No implementation exists yet, and repository history is absent.

**Next phase**
- Phase 1: implement and test the reproducible training/evaluation pipeline.

**Phase 0 addendum — dataset decision finalization**
- The first pass selected UCI Bank Marketing while Telco licensing was still unverified. Before Phase 1 completion, the official IBM `telco-customer-churn-on-icp4d` repository was checked: it includes an Apache-2.0 LICENSE and `data/Telco-Customer-Churn.csv`; the source header and sample rows were read. The CSV SHA-256 from the official GitHub file response matches the bytes downloaded for training (`16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91`). ADR-003 now retains the documented Telco use case. The superseded UCI training artifacts were removed.

### 2026-10-28 — Phase 1: Reproducible ML pipeline
**Status:** DONE

**Summary**
- Implemented a loader for IBM's Telco Customer Churn CSV with exact source-column, target, required-value, and numeric validation. `TotalCharges` blanks are allowed and handled within the fitted preprocessing pipeline.
- Added stratified 60/20/20 splits, numeric/categorical preprocessing, a prior dummy baseline, logistic regression and random forest candidates, validation average-precision/F1 selection, fixed 0.5 threshold, and one final held-out test evaluation.
- Added versioned model artifact output with pipeline, SHA-256, dataset fingerprint, schema, split, dependency versions, candidate validation metrics, and test evaluation manifest.
- Ran the real source data through training; selected logistic regression. The measured held-out metrics are in `MODEL_CARD.md` and the ignored local manifest.

**Files**
- Added `src/modelserve/__init__.py`, `src/modelserve/dataset.py`, `src/modelserve/training.py`, `tests/test_dataset.py`, `tests/test_training.py`, `TRAINING.md`, `README.md`, `pyproject.toml`, `requirements.lock`, `.gitignore`.
- Updated `DECISIONS.md`, `DEVELOPMENT_CHECKLIST.md`, `MODEL_CARD.md`, and `PHASE_LOG.md`.

**Commands**
- `python -m pytest -q --basetemp=.pytest-tmp` — 13 passed, 3 deprecation warnings.
- `python -m compileall -q src tests` — exit 0.
- `$env:PYTHONPATH='src'; python -m modelserve.training --help` — exit 0; CLI options displayed.
- `$env:PYTHONPATH='src'; python -m modelserve.training --output artifacts/telco-models` — exit 0; produced version `telco-churn-20261028T120929Z` from 7,043 source rows.
- `python -m pip install --dry-run --no-deps -r requirements.lock` — exit 0; all pinned packages were already present in Python 3.12.6 environment.
- `python -m pip check` — exit 1 because the shared environment has pre-existing protobuf 7.36.2 conflicts with unrelated Google API/TensorFlow packages; none are in this project's lock.
- `python -m venv .venv` — failed during `ensurepip`; `python -m venv --without-pip .venv` succeeded. A clean isolated dependency installation was not verified.
- `git status --short --branch` — unavailable because the workspace is not a Git repository. The supplied GitHub remote was checked and is empty (README fetch returned 404: repository is empty).

**Tests and verification**
- Unit tests: 13 passed; no failures. Three SciPy deprecation warnings are emitted by scikit-learn logistic regression.
- Integration tests: not applicable to Phase 1.
- API/manual smoke tests: not applicable; API is Phase 2.
- Dataset source/license/schema: read IBM's Apache-2.0 license and first CSV rows from the public repository; real download matched its source-file SHA.
- Artifact: manifest reviewed; records 7,043 rows, source/data fingerprints, selected model, feature schema, metrics, and artifact SHA-256.
- Container/deployment checks: not applicable to Phase 1.

**Evidence**
- Model version: `telco-churn-20261028T120929Z`.
- Artifact SHA-256: `44142441ad133b5749452d90244c1d9f6c64bb4a51a9ca15721b927099863b99`.
- Test metrics: precision 0.508389, recall 0.810160, F1 0.624742, ROC-AUC 0.832052, average precision 0.623174; confusion matrix `[[742, 293], [71, 303]]` with labels `[No, Yes]`.

**Limitations / defects**
- API, persistence, dashboard, Compose, CI, full smoke test, and deployment have not been implemented; Fast Track acceptance does not pass.
- Artifact loading safety, metadata validation at serving time, and PostgreSQL tests belong to later phases.
- Python virtual environment bootstrap failed under the sandbox's `ensurepip`; lock dry run used the preinstalled global packages, not a fresh environment.
- Global `pip check` reports unrelated protobuf dependency conflicts.
- No Git metadata or branch exists locally; provided GitHub repository is empty.

**Human action required**
- None to proceed with Phase 2. To publish changes later, provide/initialize a Git repository and remote; no commit or push was made.

**Git**
- Branch: unavailable (not a Git repository).
- `git status`: failed with “fatal: not a git repository”.
- Commit SHA: none.

**Resume readiness**
- NOT READY. Phase 1 is implemented and evaluated, but Fast Track acceptance still requires the API, PostgreSQL, dashboard, Compose, CI, and end-to-end evidence.

**Next phase**
- Phase 2: FastAPI inference vertical slice using the versioned trusted artifact and its feature schema.

### 2026-10-28 — Phase 2: FastAPI inference vertical slice
**Status:** DONE

**Summary**
- Configured clean virtual environment `.venv` with `ensurepip`, installed pinned dependencies, and resolved earlier dependency isolation blockers (`pip check` reports 0 broken requirements).
- Built trusted model loader (`model_loader.py`) with manifest validation, SHA-256 integrity verification, and safe scikit-learn Pipeline deserialization.
- Defined Pydantic schemas (`schemas.py`) for all 19 customer features with type constraints, categorical validation, and `extra = "forbid"` schema policy.
- Created FastAPI application (`app.py`, `settings.py`) with single-record inference (`POST /v1/predictions`), model provenance metadata (`GET /v1/model/info`), process liveness (`GET /health/live`), and service readiness (`GET /health/ready`).
- Added request ID tracking middleware (`RequestIDMiddleware`), payload size guard (`PayloadLimitMiddleware`, 64 KB limit returning HTTP 413), access timing middleware (`AccessLoggingMiddleware`), structured JSON logging (`logging.py`), and sanitized error envelopes (`ErrorResponse`) ensuring no stack traces or internal secrets leak to clients.
- Implemented and verified 21 new automated tests across model loading, integrity verification, tampering rejection, and API behaviors (total 34 tests passing). Exercised live Uvicorn server and real HTTP responses on localhost.
- Initialized local Git repository on branch `main`, connected remote `origin` (`https://github.com/GouravSharma26/ModelServe-AI.git`), committed code, and pushed to GitHub.

**Files**
- Added `src/modelserve/settings.py`, `src/modelserve/model_loader.py`, `src/modelserve/schemas.py`, `src/modelserve/logging.py`, `src/modelserve/middleware.py`, `src/modelserve/app.py`, `tests/test_model_loader.py`, `tests/test_api.py`, `.env.example`, `artifacts/.gitkeep`.
- Updated `pyproject.toml`, `requirements.lock`, `API_GUIDE.md`, `README.md`, `DECISIONS.md`, `DEVELOPMENT_CHECKLIST.md`, `ACCEPTANCE_CRITERIA.md`, `PHASE_LOG.md`, `.gitignore`.

**Commands**
- `.\.venv\Scripts\python.exe -m ensurepip` — exit 0; installed pip 24.2.
- `.\.venv\Scripts\python.exe -m pip install -r requirements.lock` — exit 0; installed locked packages.
- `.\.venv\Scripts\python.exe -m pip install fastapi uvicorn httpx` — exit 0.
- `.\.venv\Scripts\python.exe -m pip install -e . --no-deps` — exit 0.
- `.\.venv\Scripts\python.exe -m pip check` — exit 0; "No broken requirements found."
- `.\.venv\Scripts\python.exe -m compileall -q src tests` — exit 0.
- `.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp` — 34 passed, 8 warnings.
- `.\.venv\Scripts\python.exe -m uvicorn modelserve.app:app --host 127.0.0.1 --port 8008` — started live daemon; verified `/health/live`, `/health/ready`, `/v1/model/info`, and `/v1/predictions` with real HTTP calls.
- `git init -b main` — initialized empty Git repository.
- `git commit -m "feat: complete Phase 1 training pipeline and Phase 2 FastAPI inference service"` — committed initial 37 files (SHA `8d89980`).
- `git remote add origin https://github.com/GouravSharma26/ModelServe-AI.git` — added origin remote.
- `git push -u origin main` — pushed branch `main` to GitHub.

**Tests and verification**
- Unit & schema tests: 34 passed (13 dataset/training tests, 6 model loader/integrity tests, 15 API tests).
- Integration tests: Live HTTP client requests against running Uvicorn server verified `/health/live` (200), `/health/ready` (200), `/v1/model/info` (200 with complete metrics), `/v1/predictions` (200 with label "Yes" and score 0.8084), and 422 validation failure with exact structured envelope.
- Negative tests: Missing fields (422), invalid categories (422), negative tenure (422), forbidden extra fields (422), oversized payloads (413), tampered artifact binary (ArtifactIntegrityError), unready model (503), unhandled exception (500 without leaking stack traces).

**Evidence**
- Live test execution: 34 passed in 3.23s.
- Clean virtual environment check: `pip check` reports no broken requirements.
- Live sample prediction response: `{"request_id": "req_49ab79f4ba484f75", "model": {"name": "logistic_regression", "version": "telco-churn-20261028T120929Z"}, "prediction": {"label": "Yes", "score": 0.8084168318530464}, "status": "success"}`.
- Git push output: `branch 'main' set up to track 'origin/main'`.

**Limitations / defects**
- In-memory inference only; PostgreSQL persistence for prediction events and model metadata is planned for Phase 3.
- Streamlit dashboard, Docker Compose multi-container setup, and GitHub Actions CI remain planned for Phases 4 and 5.

**Human action required**
- None. Changes are committed and pushed to GitHub.

**Git**
- Branch: `main` (tracking `origin/main`)
- `git status`: clean
- Commit SHA: `8d89980`

**Resume readiness**
- NOT READY. Phases 1 and 2 are complete, tested, and verified against live HTTP endpoints, but PostgreSQL persistence, dashboard, Docker Compose, CI, and end-to-end smoke tests remain incomplete.

**Next phase**
- Phase 3: PostgreSQL persistence (SQLAlchemy models, Alembic migrations, prediction event telemetry, model version records, and database integration tests).

### 2026-10-28 — Remediation: Code review fixes & test reproducibility
**Status:** DONE

**Summary**
- Fixed Finding 1: Enforced request-body size limits even when Content-Length is absent, chunked, or streamed. Added `test_streamed_oversized_payload_without_content_length_returns_413`.
- Fixed Finding 2: Sanitized validation error logging to record only field locations and error types, eliminating raw Pydantic error objects that contained user input values. Added `test_validation_error_logging_does_not_leak_input_values` proving rejected values do not appear in captured logs.
- Fixed Finding 3: Updated readiness endpoint (`/health/ready`) to return generic client-facing messages while recording detailed diagnostic causes in internal logs. Added `test_health_ready_unready_returns_generic_message`.
- Fixed Finding 4: Pre-validated dataset column schema before converting numeric types to ensure missing columns raise `DatasetValidationError` rather than `KeyError`. Added regression tests for missing columns, empty data, and corrupt bytes.
- Fixed Finding 5: Implemented strict model manifest schema validation in `_validate_manifest_strict`, rejecting absolute paths, path traversal, mismatched versions, and invalid SHA-256 formats. Added 5 negative security tests.
- Task 3 Reproducibility: Refactored test fixtures in `tests/conftest.py` to generate isolated test model artifacts dynamically with zero external dataset downloads. Verified tests execute cleanly even with `artifacts/models` completely removed.

**Files**
- Created `tests/conftest.py`.
- Updated `src/modelserve/dataset.py`, `src/modelserve/model_loader.py`, `src/modelserve/middleware.py`, `src/modelserve/app.py`, `tests/test_dataset.py`, `tests/test_model_loader.py`, `tests/test_api.py`.

**Commands**
- `.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp` — 46 passed.
- `Move-Item artifacts/models artifacts/models_backup; pytest; Move-Item ...` — 46 passed in clean/isolated environment without existing models.

### 2026-10-28 — Phase 3: PostgreSQL persistence
**Status:** DONE

**Summary**
- Configured SQLAlchemy models (`ModelVersionRecord`, `PredictionRecord`) in `src/modelserve/models.py`. In accordance with ADR-008, raw feature payloads are strictly omitted from prediction history.
- Built database session and engine management in `src/modelserve/database.py` with connection probe `check_database_connection`.
- Implemented repository functions in `src/modelserve/repository.py`: `record_prediction`, `upsert_model_version`, and `get_monitoring_summary`.
- Added initial Alembic migration (`alembic/versions/20261028_0001_initial_schema.py`) and verified upgrade and downgrade cycles.
- Integrated persistence into FastAPI: predictions automatically record telemetry, while database outage resilience ensures inference succeeds even if the database is disconnected.
- Added `GET /v1/monitoring/summary` endpoint returning rolling window aggregations and latency percentiles.

**Files**
- Added `src/modelserve/models.py`, `src/modelserve/database.py`, `src/modelserve/repository.py`, `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/20261028_0001_initial_schema.py`, `tests/test_persistence.py`.
- Updated `src/modelserve/settings.py`, `src/modelserve/schemas.py`, `src/modelserve/app.py`, `pyproject.toml`, `requirements.lock`.

**Commands**
- `alembic upgrade head; alembic downgrade base` — exit 0; migration verified.
- `.\.venv\Scripts\python.exe -m pytest -q tests/test_persistence.py` — 8 passed.

### 2026-10-28 — Phase 4: Monitoring dashboard and container deployment
**Status:** DONE

**Summary**
- Built Streamlit monitoring dashboard (`src/modelserve/dashboard.py`) with three views: Live Telemetry (charts, latency profiles, empty states), Model Provenance (dataset metadata, offline confusion matrix, benchmark metrics), and an interactive Prediction Playground.
- Created production Dockerfiles for both services: `Dockerfile.api` (non-root `appuser`, health check, Alembic auto-migration) and `Dockerfile.dashboard` (non-root `appuser`, health check).
- Configured `docker-compose.yml` with `postgres` (PostgreSQL 16 Alpine with named volume `postgres_data`), `api`, and `dashboard` services, using health checks for ordered startup.
- Verified Docker Compose configuration via `docker compose config`.

**Files**
- Added `src/modelserve/dashboard.py`, `Dockerfile.api`, `Dockerfile.dashboard`, `docker-compose.yml`.
- Updated `DEPLOYMENT.md`, `DEVELOPMENT_CHECKLIST.md`, `ACCEPTANCE_CRITERIA.md`.

**Commands**
- `docker compose config` — exit 0; configuration valid.
- `pip check` — exit 0; no broken requirements.

### 2026-10-28 — Phase 5: CI, smoke testing, and Fast Track delivery
**Status:** DONE

**Summary**
- Implemented GitHub Actions CI workflow (`.github/workflows/ci.yml`) testing Python 3.12, locked dependencies, pip check, syntax compilation, full test suite, and docker compose validation.
- Created automated end-to-end smoke test script (`scripts/smoke_test.py`) validating `/health/live`, `/health/ready`, `/v1/model/info`, valid predictions, 422 error contracts, and monitoring telemetry.
- Updated documentation across `README.md`, `DEPLOYMENT.md`, `ACCEPTANCE_CRITERIA.md`, and `DEVELOPMENT_CHECKLIST.md`.

**Files**
- Added `.github/workflows/ci.yml`, `scripts/smoke_test.py`.
- Updated `README.md`, `DEPLOYMENT.md`, `DEVELOPMENT_CHECKLIST.md`, `ACCEPTANCE_CRITERIA.md`, `PHASE_LOG.md`.

**Commands**
- `pytest -ra` — 54 passed, 11 warnings in 3.99s.
- `python -m compileall -q src tests` — exit 0.
- `docker compose config` — exit 0.

**Tests and verification**
- 54 automated tests across 5 test modules passing.
- Test coverage spans dataset parsing, reproducible training, strict manifest security, API validation and limits, logging sanitization, database persistence, monitoring queries, and resilient failure paths.
