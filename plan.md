# ModelServe AI — Master Implementation Plan

## 1. Product vision
ModelServe AI is a small production-oriented machine-learning inference platform. It demonstrates a complete path from reproducible model training to validated API inference, persistence, operational visibility, and controlled model updates.

**Product statement:** Train and evaluate a classification model, serve predictions through a versioned REST API, persist prediction telemetry, and inspect service/model signals through a dashboard.

## 2. Delivery strategy: two releases

### Release A — Fast Track / Resume-Ready MVP
Target a complete, small, deployable vertical slice before implementing every advanced capability.

Must include:
- Public dataset ingestion with source/license notes.
- Reproducible Scikit-learn training/evaluation command.
- Persisted model artifact plus metadata and feature schema.
- FastAPI single-record prediction endpoint and OpenAPI docs.
- Pydantic validation and consistent errors.
- Liveness/readiness endpoints and model-info endpoint.
- PostgreSQL-backed prediction history and model metadata (SQLite may be used only for isolated unit tests, not as a substitute for the documented MVP runtime).
- Structured JSON logging with request IDs.
- Basic monitoring summary and Streamlit dashboard backed by real database records.
- Docker Compose startup for API, dashboard, and PostgreSQL.
- Automated unit/API/integration tests and GitHub Actions CI.
- README, architecture, model card, API, deployment, and troubleshooting docs.
- A successful smoke test and an actual deploy/demo URL if a suitable deployment environment is available. Never fabricate a URL.

Explicitly deferred from Release A:
- MLflow registry as a mandatory dependency; use a clean local artifact manifest/versioning design initially.
- Prometheus server and OpenTelemetry tracing.
- Automated champion/challenger promotion and one-click rollback.
- Advanced statistical drift methods and alert routing.
- Async queue and high-availability architecture.
- Kubernetes, Kafka, Redis, GPU, and LLM integration.

MVP monitoring can include prediction-label/score distributions, request counts, error counts, and latency summaries. Label this as basic monitoring; do not describe it as a full production observability stack.

### Release B — Full Platform
Add the remaining capabilities incrementally:
- MLflow experiment tracking and model registry.
- Model comparison and explicit quality gates.
- Prometheus scraping and alerts; optional OpenTelemetry tracing.
- Feature/prediction drift scoring (e.g., PSI), reference windows, thresholds, and persisted reports.
- Ground-truth feedback ingestion and delayed-label model evaluation.
- Controlled model promotion, version history, rollback, and audit events.
- Load testing and documented performance envelope.
- Security hardening, retention policy, deployment automation, and optional cloud scaling.
- Optional async telemetry ingestion only if measurement justifies it.

## 3. Primary use case
Customer churn classification using a public Telco Customer Churn dataset. The dataset's source, redistribution terms, schema, and preprocessing decisions must be verified and documented before use. If its terms or download availability are unsuitable, choose a clearly licensed public binary-classification dataset and document the decision.

The model estimates churn risk for a demonstration dataset; it must not be presented as a validated decision system for real customers.

## 4. Recommended stack
- Python; Pandas; NumPy; Scikit-learn
- FastAPI; Pydantic; Uvicorn
- PostgreSQL; SQLAlchemy; Alembic
- Streamlit; Plotly
- Docker; Docker Compose
- Pytest; HTTPX
- Ruff; mypy (where practical)
- GitHub Actions
- Release B: MLflow; Prometheus client/server; optional OpenTelemetry; optional Locust

Use compatible versions, pin dependencies, and document the supported Python version. Prefer a supported Python version available in the user's environment and deployment provider. Do not assume Python 3.14 support across every ML dependency; verify compatibility first.

## 5. Architecture principles
- Training is an offline workflow; inference is an online service.
- The model and preprocessing pipeline are saved together.
- Model artifacts are immutable and identified by version plus checksum.
- API schemas are explicit and versioned under `/v1`.
- PostgreSQL is the source of truth for model metadata and inference history in the MVP.
- Dashboard reads actual stored data and metrics.
- Do not expose raw customer records by default.
- Health checks distinguish process liveness from service readiness.
- Fail clearly if required artifacts or schema metadata are missing.
- Configuration comes from environment variables; secrets never enter Git.
- Start as a modular monolith and split services only for demonstrated reasons.

## 6. Delivery phases
### Phase 0 — Repository reconnaissance and design lock
Inspect repo, environment, existing work, and Git state. Finalize dataset source, Python/dependency compatibility, API contract, schema, and deployment constraints. Do not replace existing work.

### Phase 1 — Reproducible ML pipeline
Implement data validation, split strategy, preprocessing, baseline and candidate models, evaluation report, artifact manifest, and training CLI.

### Phase 2 — FastAPI inference vertical slice
Implement health/readiness, model info, prediction endpoint, batch-size guard if batch endpoint is included, validation, error contract, request ID, and OpenAPI docs.

### Phase 3 — PostgreSQL persistence
Implement migrations, repositories, model metadata, prediction records, and a monitoring summary query. Test against PostgreSQL.

### Phase 4 — Dashboard and local container deployment
Build real-data dashboard, Dockerfiles, Compose services, persistent volume, health checks, and startup instructions.

### Phase 5 — Fast Track verification and release
Run full tests, smoke test, fresh-start test, failure-path tests, CI, container build, and deployment verification. Tag/document Release A only after criteria pass.

### Phase 6 — MLflow and model lifecycle
Track runs, register versions, compare candidates, apply quality gates, and record model promotion events.

### Phase 7 — Drift and ground-truth monitoring
Implement reference distributions, PSI or another documented method, alert thresholds, feedback ingestion, and labeled performance evaluation.

### Phase 8 — Advanced observability and performance
Add Prometheus scraping/alerts, optional traces, load testing, and measured performance report.

### Phase 9 — Hardening and final audit
Review security, dependencies, data handling, failure behavior, docs, screenshots, and end-to-end demonstration.

## 7. Definition of done for any phase
A phase is done only when:
- Implementation is present and wired into the application.
- Tests cover happy paths and relevant failure paths.
- All relevant checks run and results are recorded.
- Documentation matches current behavior.
- No feature is represented as complete merely because files exist.
- `git diff` and `git status` are inspected.
- Remaining limitations are explicit.

## 8. Scope guardrails
Do not add Kubernetes, Kafka, Redis, a React frontend, or cloud-specific managed services in the MVP. Do not use real personal/customer data. Do not claim production readiness in the sense of enterprise SLA or high availability; describe it as a production-oriented portfolio platform unless those guarantees are actually engineered and measured.
