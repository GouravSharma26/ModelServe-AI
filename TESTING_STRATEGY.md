# Testing Strategy

## Layers
### Unit tests
Test feature schema validation, preprocessing, prediction response mapping, metric calculations, artifact manifest validation, request ID generation, and monitoring aggregation.

### API tests
Use FastAPI's test client/HTTPX to test health endpoints, model metadata, valid prediction, missing fields, wrong types, unsupported categories, oversized input, model-unavailable behavior, and stable error formats.

### Database integration tests
Use a real PostgreSQL service/container for migrations, inserts, uniqueness constraints, query aggregation, persistence across API restart, and database failure behavior. Do not claim PostgreSQL integration is covered solely by SQLite tests.

### ML tests
Check target/schema validation, split stratification, pipeline composition, metric validity, deterministic configuration, artifact reload, and equivalence of predictions before and after save/load within reasonable numerical tolerances.

### End-to-end smoke test
1. Confirm services are healthy.
2. Confirm model info endpoint.
3. Submit a schema-valid synthetic record.
4. Validate response structure and model version.
5. Verify the prediction event exists in PostgreSQL.
6. Confirm the dashboard reflects the event.
7. Submit invalid input and verify a stable error.
8. Restart API and verify stored history remains.

### Performance tests
Release A: lightweight repeatable smoke benchmark, with no unsupported performance claims.
Release B: use Locust or an equivalent tool; document hardware, concurrency, request mix, duration, warmup, sample count, p50/p95/p99, throughput, errors, and database behavior.

## Test data
Use synthetic data and public dataset records where licensing permits. Avoid committing private data. Keep deterministic fixtures small. Never make tests depend on a public website being available during every CI run; cache/fixture a licensed, minimal test sample or mock the download boundary.

## Reporting
Record exact command, exit code, test count, failures, environment, commit SHA, and known skips. A skipped test must not be reported as passing.
