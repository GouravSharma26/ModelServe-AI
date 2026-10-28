# ModelServe AI

**Production-oriented ML inference, telemetry, and monitoring platform.**

> Project status: [In development / Fast Track MVP verified / Public demo verified]. Update only with evidence.

## Overview
ModelServe AI demonstrates a reproducible classification workflow, versioned model artifacts, validated FastAPI inference, PostgreSQL-backed prediction telemetry, and a Streamlit monitoring dashboard.

## Features
Only mark features as complete when implemented and verified:
- [ ] Reproducible training and evaluation
- [ ] FastAPI prediction endpoint
- [ ] Pydantic input validation and safe errors
- [ ] Model metadata/version endpoint
- [ ] PostgreSQL prediction history
- [ ] JSON structured logging
- [ ] Streamlit monitoring dashboard
- [ ] Docker Compose
- [ ] Automated tests and CI
- [ ] Drift monitoring
- [ ] MLflow model registry
- [ ] Prometheus monitoring

## Architecture
Link to `ARCHITECTURE.md`. Include an accurate architecture diagram.

## Dataset and model
Document the source, license, target, features, split strategy, evaluation metrics, limitations, and model card. Do not include invented metrics.

## Quick start
Replace this section with exact, tested commands after implementation:
1. Install prerequisites.
2. Configure `.env`.
3. Download/prepare dataset.
4. Train model.
5. Start Docker Compose.
6. Run smoke test.
7. Open API docs and dashboard at the actual configured addresses.

## API example
Copy a real request and response from the running API, using synthetic data only. Link to `API_GUIDE.md`.

## Evaluation
Include measured metrics from the generated evaluation report and explain the evaluation protocol.

## Monitoring
Explain actual implemented metrics, drift method, limitations, and whether ground-truth labels are available.

## Testing
List exact test/lint/build commands and current verified results, including the commit SHA.

## Deployment
Link to `DEPLOYMENT.md`. Include a public URL only after a live external smoke test succeeds. Otherwise clearly label it as a local Docker demo.

## Limitations
- Demonstration dataset does not establish real-world validity.
- Distribution drift does not prove predictive performance decline.
- Live performance evaluation requires genuine labels.
- No high-availability/SLA claims unless engineered and measured.

## Roadmap
Separate completed capabilities from planned Release B work.

## Resume note
Resume descriptions must match the implemented and verified release, not the roadmap.
