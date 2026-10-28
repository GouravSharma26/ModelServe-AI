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
- [ ] PostgreSQL configuration.
- [ ] SQLAlchemy models.
- [ ] Alembic initial migration.
- [ ] Model-version metadata.
- [ ] Prediction event persistence.
- [ ] Monitoring summary query.
- [ ] Database integration tests.
- [ ] Persistence and outage behavior verified.

## Phase 4 — Dashboard and Compose
- [ ] Streamlit overview.
- [ ] Actual evaluation metrics.
- [ ] Prediction distribution.
- [ ] Recent prediction/latency/error summaries.
- [ ] Empty-data states.
- [ ] API Dockerfile.
- [ ] Dashboard Dockerfile.
- [ ] Compose configuration and database volume.
- [ ] Health checks and startup validation.
- [ ] Fresh checkout startup test.

## Phase 5 — Fast Track release
- [ ] CI workflow.
- [ ] Full test suite.
- [ ] Lint/type checks.
- [ ] Container build.
- [ ] Smoke test.
- [ ] Failure-path verification.
- [ ] Security and Git hygiene check.
- [ ] README and all required docs.
- [ ] Screenshots/evidence.
- [ ] Public deployment verified if claimed.
- [ ] Release notes and actual limitations.

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
- [ ] Alert rules.
- [ ] Optional OpenTelemetry traces.
- [ ] Load test with documented workload.
- [ ] Latency percentiles and throughput report.
- [ ] Resource and failure observations.

## Phase 9 — Final audit
- [ ] Re-run all checks on final commit.
- [ ] Review security and data retention.
- [ ] Review dependency vulnerabilities.
- [ ] Verify all docs/URLs.
- [ ] Verify screenshots show real behavior.
- [ ] Verify resume claims against evidence.
- [ ] Report unresolved issues and next steps.
