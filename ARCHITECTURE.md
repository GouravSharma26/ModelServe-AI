# Architecture — ModelServe AI

## Goals
1. Reproducible training.
2. Safe and predictable inference.
3. Traceable model artifacts.
4. Persistent prediction telemetry.
5. Real, explainable monitoring.
6. Simple local and demonstrable deployment.

## Logical components
### Training package
Loads the selected dataset, validates columns/types, creates train/validation/test splits, fits preprocessing only on training data, compares models, writes metrics and plots, and saves a complete preprocessing-plus-estimator pipeline.

### Artifact manifest
Every artifact version has a unique version identifier, creation time, source dataset fingerprint, training configuration, dependency/version information, feature schema, evaluation metrics, and SHA-256 checksum. Never load an untrusted artifact from a request. The MVP may use a local `artifacts/` directory mounted read-only into the API container. Store metadata in PostgreSQL and make the artifact location configurable.

### FastAPI service
Owns request validation, inference, request correlation, error responses, health/readiness, model metadata, and prediction persistence. Load the active model once during application lifespan, not on every request. Fail readiness if the configured model cannot be loaded or its schema does not match.

### PostgreSQL
Stores model-version metadata, prediction events, request errors/operational summaries where appropriate, and later drift/evaluation reports. Use Alembic migrations. Use connection pooling and parameterized ORM queries. Avoid raw SQL string interpolation.

### Streamlit dashboard
Reads aggregated data from API endpoints or a restricted read-only repository. It must not load model artifacts or perform model promotion in Release A. Dashboard visualizations must derive from actual persisted records. Clearly show when no data exists rather than inventing demo metrics.

### Observability
MVP: JSON logs, request IDs, latency, status, prediction distributions, and database-backed summaries. Release B: Prometheus scraping, alerts, optional tracing, and richer drift analytics.

## Request lifecycle
1. Client sends a request to `POST /v1/predictions`.
2. Middleware assigns/validates a request ID.
3. Pydantic validates payload shape and field types.
4. Application-level validation checks domain constraints and expected feature schema.
5. The loaded pipeline performs preprocessing and prediction.
6. Response includes request ID, model name/version, prediction, and score/probability when supported.
7. A telemetry event is persisted according to the documented persistence policy.
8. Request latency and outcome are logged and measured.
9. The dashboard later queries aggregated records.

If persistence is required for a successful response, return a controlled service error when the database write fails. If the implementation later adopts best-effort or asynchronous telemetry, explicitly document possible telemetry loss and add a durable mechanism before claiming reliable delivery.

## Training lifecycle
1. Fetch/load data using documented steps.
2. Verify source, license, schema, and dataset fingerprint.
3. Validate columns and target.
4. Split data with a fixed random seed and stratification where appropriate.
5. Fit preprocessing inside a Scikit-learn Pipeline/ColumnTransformer.
6. Train a baseline and candidates.
7. Select using validation metrics and documented rules.
8. Evaluate the selected model once on the held-out test set.
9. Save the complete pipeline and manifest.
10. Register model metadata in the local registry/database.
11. The API loads a specifically configured approved version.

## Data model (minimum)
### model_versions
- id (primary key)
- model_name
- version
- artifact_uri/path
- artifact_sha256
- feature_schema_json
- metrics_json
- dataset_fingerprint
- training_config_json
- status (`candidate`, `approved`, `active`, `retired`, or equivalent constrained set)
- created_at
- activated_at (nullable)

Use database constraints to prevent duplicate `(model_name, version)` and invalid status values.

### prediction_events
- id (primary key)
- request_id (unique or appropriately indexed)
- created_at
- model_name
- model_version
- prediction_label
- prediction_score/probability (nullable)
- latency_ms
- outcome/status
- optional non-sensitive summary fields only

Do not store the complete raw input by default. If input feature summaries are needed for drift, define a strict allowlist and retention policy.

### request_errors (optional MVP table)
- id
- request_id
- created_at
- error_code
- HTTP status
- model_version (nullable)
- safe message/category

Never store secrets, stack traces intended for internal logs, or raw invalid payloads here.

### Future tables
- training_runs
- model_deployment_events
- monitoring_windows
- drift_reports
- prediction_feedback / labeled_outcomes

## API contract (MVP)
- `GET /health/live`: process is running; should not depend on database availability.
- `GET /health/ready`: API can serve requests; verify model loaded and required dependencies available.
- `GET /v1/model/info`: active model name/version, artifact checksum prefix if safe, feature schema version, training timestamp, and available evaluation metrics.
- `POST /v1/predictions`: one validated record; return request ID, model metadata, label, and score/probability if supported.
- `GET /v1/monitoring/summary`: aggregate counts, error rate, latency percentiles where correctly calculated, and prediction distribution over a bounded time window.
- `GET /metrics`: Release B when Prometheus instrumentation is implemented; do not expose an unimplemented endpoint.

Optional batch endpoint: `POST /v1/predictions/batch`, with a strict maximum batch size and per-record error semantics explicitly documented.

## Security and privacy
- Secrets via environment variables/secrets manager, never source control.
- Restrict CORS to required origins; do not use wildcard credentials.
- Add payload and batch-size limits.
- Avoid logging raw request bodies.
- Keep dashboard management actions read-only in MVP.
- Use least-privilege database credentials; separate migration/admin credentials if practical.
- Pin dependencies and scan them in CI.
- Do not expose database ports publicly in deployed environments unless explicitly needed.
- Apply authentication/rate limiting before exposing a public API beyond a controlled demo.
- Public demo uses synthetic records only.
- Joblib/pickle artifacts can execute code when loaded; only load trusted artifacts produced by the controlled training pipeline.

## Deployment topology
Local: Docker Compose with `api`, `dashboard`, and `db`; optional `training` as a one-shot profile/command. PostgreSQL uses a named volume. Model artifacts are generated locally or downloaded from a trusted location and mounted/configured explicitly.

Public demo: deploy API and dashboard only after checking provider support for persistent storage, outbound access, port routing, health checks, environment variables, and database persistence. Use a managed PostgreSQL instance or supported persistent database service for public deployments. Never assume a local container volume persists on a hosting provider.

## Failure behavior
- Missing/corrupt artifact: application should fail readiness and provide a safe diagnostic in logs.
- Invalid request: stable 4xx response; no stack trace to client.
- Database unavailable: health/readiness reflects dependency policy; prediction behavior follows the documented telemetry policy.
- Unknown model version: fail deployment/configuration validation; never silently fall back to an arbitrary file.
- Empty monitoring window: return zero/empty values and an explicit no-data state.
- Drift threshold exceeded: record a warning/report; do not automatically claim model accuracy degraded.
