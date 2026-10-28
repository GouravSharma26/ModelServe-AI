# Fast Track Plan — Resume-Ready Release A

## Objective
Deliver the smallest complete, deployed, verifiable ModelServe AI release first. The purpose is to have a credible portfolio project early while keeping a clear roadmap for the remaining advanced platform features.

**Target duration:** approximately 5–8 focused working days, depending on environment, dataset access, and deployment account availability. This is a planning estimate, not a promise. Antigravity must report actual progress and blockers rather than rush or skip tests.

## Release A feature freeze
Include:
1. Public classification dataset with documented source/license.
2. Reproducible training/evaluation CLI.
3. Saved preprocessing-plus-model pipeline and metadata manifest.
4. FastAPI prediction endpoint.
5. Input validation, stable error responses, request IDs, JSON logging.
6. Liveness/readiness and active-model-info endpoints.
7. PostgreSQL model metadata and prediction history.
8. Streamlit dashboard showing actual evaluation results and stored inference activity.
9. Docker Compose for API, dashboard, and PostgreSQL.
10. Unit, API, and database integration tests.
11. GitHub Actions CI.
12. Setup, architecture, API, model card, deployment, and troubleshooting documentation.
13. Real smoke test; deployed public demo only when a safe, supported target is available.

Do not wait for the complete advanced platform before publishing the MVP. Do not publish a nonfunctional scaffold as a finished project.

## Day-by-day work plan
### Day 0 — Reconnaissance and lock
- Inspect repository and machine environment.
- Confirm Git state and preserve all changes.
- Verify dataset availability and license.
- Check dependency support for chosen Python version.
- Lock Release A scope and acceptance criteria.
Deliverable: repo audit, environment report, final decisions.

### Day 1 — Training pipeline
- Implement dataset loader/validator.
- Create stratified splits and preprocessing pipeline.
- Train dummy baseline and at least two candidate models.
- Generate metrics, confusion matrix, and model manifest.
- Add tests for schema, leakage-safe pipeline construction, and deterministic setup.
Deliverable: documented training command and real evaluation report.

### Day 2 — Inference API
- Build model-loading service and Pydantic schemas.
- Implement prediction, model-info, liveness, readiness.
- Add request IDs, structured logging, and safe errors.
- Add unit/API tests for valid, invalid, missing-model, and prediction behavior.
Deliverable: locally running API with useful OpenAPI docs.

### Day 3 — Database and telemetry
- Add PostgreSQL, SQLAlchemy, and Alembic.
- Create model metadata and prediction event tables.
- Persist predictions and query a real monitoring summary.
- Test migrations and database failure behavior.
Deliverable: prediction history persists across API/container restarts.

### Day 4 — Dashboard and containers
- Build Streamlit dashboard with model metrics, prediction distribution, recent requests, latency/error summaries, and no-data states.
- Add API/dashboard Dockerfiles and Compose.
- Add health checks, named database volume, environment configuration.
Deliverable: one documented command starts the local platform.

### Day 5 — Integration, CI, and demo
- Add GitHub Actions checks.
- Run full test suite and container build.
- Execute smoke test and manual demo scenario.
- Fix blockers rather than merely documenting failing behavior.
Deliverable: reproducible local demo and green CI for the exact pushed commit, if push is authorized.

### Days 6–8 — Deployment and release polish
- Select an available hosting target based on account access and persistent-storage support.
- Configure environment variables and database securely.
- Deploy API/dashboard, run public smoke tests, capture evidence.
- Add screenshots, limitations, architecture diagram, and release notes.
- Re-test clean startup and ensure no credentials are in Git.
Deliverable: public demo URL if successfully deployed; otherwise a polished local Docker demo with exact deployment blocker documented.

## Required demo script
1. Open dashboard and show the trained model's actual evaluation metrics.
2. Call `GET /health/live`, `GET /health/ready`, and `GET /v1/model/info`.
3. Submit a valid prediction using documented sample input.
4. Submit invalid/missing/out-of-range input and show stable validation errors.
5. Confirm prediction history appears in the dashboard/database.
6. Restart API and confirm history remains.
7. Stop database in a controlled local test and verify documented failure behavior.
8. Show CI results and actual test counts.
9. Show limitations and deferred roadmap.

## Release A acceptance gate
Release A is READY only when every applicable item below is checked with evidence:
- [ ] Clean setup works from documented commands.
- [ ] Dataset source/license and preprocessing are documented.
- [ ] Training command completes and writes a manifest.
- [ ] Evaluation report contains actual results.
- [ ] No test-set leakage identified in review.
- [ ] API contract and OpenAPI docs match implementation.
- [ ] Valid prediction returns expected schema and model version.
- [ ] Invalid input returns safe, consistent 4xx errors.
- [ ] Liveness/readiness differ meaningfully.
- [ ] Model metadata and prediction telemetry persist in PostgreSQL.
- [ ] Dashboard uses real stored values and handles empty state.
- [ ] Docker Compose starts services and health checks pass.
- [ ] Unit/API/integration tests pass.
- [ ] CI runs on the target branch and passes.
- [ ] Smoke test passes against the built application.
- [ ] Secrets, local data, and generated binaries are not accidentally committed.
- [ ] README, deployment guide, model card, and known limitations are accurate.
- [ ] If a public URL is claimed, the live endpoints and dashboard were actually tested.
- [ ] Git status is clean or all remaining changes are explicitly disclosed.

## Resume rule
If deployed publicly, state that it is deployed only after testing the live service. If only local, it may still be listed as a working Dockerized project but must not be called publicly deployed. Use measured metrics only. Resume bullets must describe implemented features, not Release B plans.

## Fast Track to Release B
After Release A is tagged/documented:
1. Add MLflow experiment tracking and model registry.
2. Add champion/challenger comparisons and quality-gated promotion.
3. Add drift reports and configurable thresholds.
4. Add prediction feedback and labeled outcome evaluation.
5. Add Prometheus server, alert rules, and optional tracing.
6. Add load testing and a performance report.
7. Harden public access, authentication/rate limits, retention, and deployment recovery.
8. Re-run the full acceptance suite and update resume claims only after verification.
