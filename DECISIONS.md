# Architecture Decision Records

Update this file when a decision changes. Do not silently change decisions that affect scope or data contracts.

## ADR-001: Build a modular monolith first
**Decision:** One Python codebase with distinct training, API, persistence, and monitoring modules.
**Reason:** Reduces operational overhead while showing clear boundaries.
**Consequences:** Separate services may be introduced later only when scaling or isolation needs justify them.

## ADR-002: Fast Track before advanced platform
**Decision:** Ship a tested API + model + PostgreSQL + dashboard + Docker Compose slice before MLflow registry, Prometheus server, tracing, and advanced drift.
**Reason:** A functioning, demonstrable project is more valuable than a large unfinished scaffold.
**Consequences:** The MVP registry is lightweight and must be documented as such.

## ADR-003: Public binary-classification dataset
**Decision:** Use the Telco Customer Churn CSV in IBM's `telco-customer-churn-on-icp4d` public repository. Its repository includes an Apache License 2.0 file and the CSV schema is verified against the source. Exclude `customerID` from model inputs.
**Reason:** This preserves the documented churn use case. The official IBM repository provides the source data and license, so the fallback dataset is unnecessary.
**Consequences:** Attribute IBM and link to the source repository/license. Validate its 21 raw columns and `Churn` target. Use synthetic demo requests; do not present the fictional sample as real customer data or a validated retention decision system.

## ADR-004: Persist complete pipeline, not estimator alone
**Decision:** Serialize the preprocessing-plus-model pipeline as one trusted artifact.
**Reason:** Prevents serving-time preprocessing mismatch.
**Consequences:** Artifact provenance and trusted loading are required.

## ADR-005: PostgreSQL is MVP persistence
**Decision:** PostgreSQL stores model metadata and inference telemetry.
**Reason:** Demonstrates durable persistence and realistic integration.
**Consequences:** Local deployment includes a database service and migrations.

## ADR-006: Monitoring claims must be precise
**Decision:** Separate service metrics, distribution drift, and labeled model performance.
**Reason:** Input drift alone does not prove quality degradation.
**Consequences:** Dashboard labels each signal and shows when labels are unavailable.

## ADR-007: Docker Compose before Kubernetes
**Decision:** Docker Compose is the primary reproducible environment.
**Reason:** Appropriate complexity for a solo portfolio project.
**Consequences:** Kubernetes remains optional and out of scope until the core platform is reliable.

## ADR-008: Avoid raw input retention
**Decision:** Prediction history stores prediction metadata and approved non-sensitive summaries, not full input records by default.
**Reason:** Data minimization and safer logging.
**Consequences:** Drift monitoring may require aggregate summaries or explicitly approved feature histograms.

## ADR-009: No fabricated deployment or performance claims
**Decision:** Only report measurements actually produced by tests or a live environment.
**Reason:** Resume credibility and reproducibility.
**Consequences:** If deployment credentials or persistent storage are unavailable, document the blocker and ship a verified local demo first.

## ADR-010: Strict schema validation and cryptographic artifact verification for serving
**Decision:** Enforce Pydantic validation with `extra = "forbid"` for all inference features, require SHA-256 checksum verification against `manifest.json` prior to deserializing any joblib model artifact, and distinguish `/health/live` (process health) from `/health/ready` (model and dependency readiness).
**Reason:** Prevents schema drift and silent feature degradation, mitigates untrusted deserialization risks by verifying provenance and integrity, and enables proper orchestrator startup lifecycle handling.
**Consequences:** Payloads with missing, misspelled, or extra attributes fail with standard 422 envelopes. Tampered or missing artifacts return HTTP 503 on `/health/ready` and inference routes while leaving the service process alive for diagnosis.
