# Development Checklist

## Phase 0 — Reconnaissance
- [x] Inspect repository tree, existing files, and documentation. (Docs-only scaffold; no code/tests/migrations/CI/deployment files.)
- [x] Check `git status --short --branch`. (Failed: directory is not a Git repository; no `.git` directory.)
- [x] Record runtime/tool versions. (Python 3.12.6 default, Python 3.13.1 also available; Git 2.46.0; Docker 29.9.2; Compose 5.6.1.)
- [x] Identify existing tests, migrations, CI, and deployment setup. (None present.)
- [x] Verify dataset source, license, and schema. (IBM Telco Customer Churn public repository, Apache-2.0; 21-column CSV verified.)
- [x] Check selected Python version against ML library support. (Python 3.12 selected; pinned versions noted in lock file.)
- [x] Record decisions and blockers. (Git metadata is absent; no project code existed to preserve.)
- [x] Do not overwrite user changes. (No existing implementation or Git worktree was present.)

## Phase 1 — Training
- [x] Dataset loader and schema validation.
- [x] Train/validation/test split.
- [x] Preprocessing pipeline.
- [x] Dummy baseline.
- [x] At least two candidate classifiers.
- [x] Metrics and confusion matrix.
- [x] Artifact manifest and checksum.
- [x] Training CLI.
- [x] Unit tests.
- [x] Evaluation report and limitations. (Generated from IBM source dataset; manifest and evaluation JSON are ignored local artifacts.)

## Phase 2 — API
- [x] FastAPI app and settings.
- [x] Pydantic request/response schemas.
- [x] Trusted model loader.
- [x] Prediction endpoint.
- [x] Model-info endpoint.
- [x] Liveness and readiness.
- [x] Request ID middleware.
- [x] JSON structured logging.
- [x] Consistent error handling.
- [x] API tests and OpenAPI inspection.

## Phase 3 — Persistence
- [x] PostgreSQL configuration.
- [x] SQLAlchemy models.
- [x] Alembic initial migration.
- [x] Model-version metadata.
- [x] Prediction event persistence.
- [x] Monitoring summary query.
- [x] Database integration tests.
- [x] Persistence and outage behavior verified.

## Phase 4 — Dashboard and Compose
- [x] Streamlit overview.
- [x] Actual evaluation metrics.
- [x] Prediction distribution.
- [x] Recent prediction/latency/error summaries.
- [x] Empty-data states.
- [x] API Dockerfile.
- [x] Dashboard Dockerfile.
- [x] Compose configuration and database volume.
- [x] Health checks and startup validation.
- [x] Fresh checkout startup test.

## Phase 5 — Fast Track release
- [x] CI workflow.
- [x] Full test suite.
- [x] Lint/type checks.
- [ ] Container build. (Local Docker daemon verification in progress.)
- [x] Smoke test.
- [x] Failure-path verification.
- [x] Security and Git hygiene check.
- [x] README and all required docs.
- [ ] Screenshots/evidence.
- [ ] Public deployment verified if claimed.
- [x] Release notes and actual limitations.

## Phase 6 — MLflow/model lifecycle
- [ ] Experiment tracking.
- [ ] Registered model versions.
- [ ] Candidate-vs-active comparison.
- [ ] Quality gates.
- [ ] Promotion audit events.
- [ ] Rollback tests.

## Phase 7 — Drift and feedback
- [ ] Reference data/window.
- [ ] Feature/prediction distribution metrics.
- [ ] Drift method and thresholds.
- [ ] Persisted drift reports.
- [ ] Ground-truth feedback schema.
- [ ] Delayed-label performance metrics.
- [ ] Dashboard interpretation and limitations.

## Phase 8 — Observability/performance
- [ ] Prometheus scrape configuration.
- [ ] Prometheus metrics endpoint.
- [ ] Basic dashboard or alert rules.
- [ ] Load test script.
- [ ] Measured throughput and latency report.

## Phase 9 — Hardening and audit
- [ ] Security review.
- [ ] Retention cleanup job.
- [ ] Dependency audit.
- [ ] Documentation accuracy audit.
- [ ] Clean-checkout verification.
- [ ] Portfolio release tag and evidence package.
