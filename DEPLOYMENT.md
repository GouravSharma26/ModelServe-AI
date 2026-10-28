# Deployment Guide

## Supported delivery stages
1. Local development.
2. Reproducible Docker Compose demo.
3. Optional public demo after provider suitability and persistence are verified.

## Prerequisites
- Git.
- A Python version supported by the pinned ML dependencies.
- Docker Engine/Desktop and Docker Compose.
- Dataset download access or a documented local dataset placement step.

Record exact versions after inspecting the actual environment. Do not assume the newest Python version is compatible with all ML libraries.

## Environment setup
1. Clone/open the repository.
2. Copy `.env.example` to `.env`.
3. Fill only required local values.
4. Never commit `.env`.
5. Obtain the dataset through the documented source/loader.
6. Create the model artifact using the documented training command.
7. Start services with the actual Compose command documented in the README.
8. Wait for health checks.
9. Run the smoke test.

The exact commands, service names, ports, and environment variable names must be updated after implementation. Do not leave this document with guessed commands.

## Docker Compose requirements
- API, dashboard, PostgreSQL services.
- Named PostgreSQL volume.
- Health checks.
- Explicit environment configuration.
- No embedded credentials in Dockerfiles or Compose.
- Restrict database port exposure to local development unless required.
- Use compatible startup/readiness checks.
- Do not use a timing sleep as the only dependency check.

## Public deployment checklist
- [ ] Confirm provider supports the required Python/container runtime.
- [ ] Confirm persistent database storage or use a managed PostgreSQL service.
- [ ] Confirm model artifact storage survives redeploys or is fetched from trusted artifact storage.
- [ ] Configure secrets through provider environment settings.
- [ ] Restrict public API access as appropriate.
- [ ] Configure allowed origins.
- [ ] Verify health checks and port binding.
- [ ] Confirm logs do not expose secrets or raw payloads.
- [ ] Run a smoke test from outside the provider environment.
- [ ] Confirm dashboard can read the intended API/database.
- [ ] Test persistence across redeployment/restart.
- [ ] Record exact commit, deployment time, and URL.

## Recovery
Document actual behavior for:
- API restart.
- Dashboard restart.
- PostgreSQL restart.
- Missing/corrupt model artifact.
- Invalid environment variables.
- Failed migration.
- Failed deployment.

Do not promise zero downtime or automatic rollback unless implemented and verified.

## Rollback
Fast Track rollback may initially mean restoring the previous known-good image/configuration and artifact manually. Document the exact tested procedure. Automated model promotion/rollback is Release B unless completed earlier.

## Troubleshooting
For each issue, include symptoms, commands/logs to inspect, likely causes, and recovery:
- Service remains unhealthy.
- API cannot load model.
- Database connection fails.
- Migration fails.
- Dataset is missing.
- Dashboard shows no records.
- Prediction returns validation error.
- Container port is unavailable.
