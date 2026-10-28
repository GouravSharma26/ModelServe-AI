# AGENTS.md — ModelServe AI

## Mission
Build ModelServe AI as a demonstrably working, maintainable ML inference platform. Deliver a small, deployable Fast Track release first; then continue toward the full platform. Do not claim a feature is complete unless code, tests, and evidence support that claim.

## Working rules
1. Inspect the existing repository, git status, runtime versions, and all project documentation before editing. Preserve existing user work. Do not overwrite or reset changes without explicit permission.
2. Treat `plan.md`, `DEVELOPMENT_CHECKLIST.md`, `ACCEPTANCE_CRITERIA.md`, and `DECISIONS.md` as the source of truth. If code conflicts with these docs, report the conflict and recommend a change before silently changing scope.
3. Work in small, reviewable phases. Complete the current phase's implementation, tests, documentation, and verification before moving to the next phase.
4. Prefer a simple, reliable modular monolith. Do not add Kubernetes, Kafka, Redis, a frontend framework, GPU support, or paid services without a documented requirement.
5. Use Python type hints, clear module boundaries, dependency injection where useful, and configuration via environment variables. Avoid giant modules, hidden global state, and duplicated business logic.
6. Use stable, mutually compatible dependency versions and a reproducible lock/constraints strategy. Do not blindly install the newest versions or upgrade dependencies without checking compatibility.
7. Never hardcode secrets. Update `.env.example` with placeholders only. Ensure `.env`, credentials, local datasets, generated model binaries, logs, and database volumes are appropriately ignored by Git.
8. Never use real customer data. Use a publicly available, license-checked dataset and synthetic demo traffic. Do not log complete feature payloads by default.
9. Model artifacts are trusted only when produced by the documented training workflow. Validate artifact metadata and expected feature schema. Do not load arbitrary user-supplied pickle/joblib files.
10. Do not fabricate evaluation metrics, latency, throughput, uptime, monitoring results, screenshots, test outcomes, deployment URLs, or feature completion.
11. Run relevant tests after each change. At phase completion, run the full applicable test suite, lint/type checks, build/container checks, and smoke tests.
12. If an external service requires credentials, account access, a domain, or a manual action, implement what can be done locally, document the exact blocker and steps, and never claim deployment is complete until verified.
13. Never run destructive commands such as `git reset --hard`, force-push, deleting user files, dropping databases, or overwriting production data without explicit approval.
14. Do not commit or push unless the user has requested it or the repository's active instructions explicitly authorize it. Before a commit, inspect `git diff` and `git status`.
15. Keep documentation aligned with the actual implementation. Mark planned items as `PLANNED`, partial items as `IN PROGRESS`, and verified items as `DONE` with evidence.

## Required workflow
### Start of work
- Inspect the repository tree and existing docs.
- Check `git status --short --branch`.
- Identify available Python, Git, Docker, and Compose versions.
- Determine whether the repository already contains code, tests, migrations, or deployment configuration.
- Summarize the current state and proposed next phase before broad changes.

### Implementation
- Read the phase-specific section of `plan.md` and `ACCEPTANCE_CRITERIA.md`.
- Implement the smallest complete vertical slice.
- Add or update tests alongside implementation.
- Update `DEVELOPMENT_CHECKLIST.md`, `PHASE_LOG.md`, `DECISIONS.md`, and relevant user-facing docs.
- Avoid placeholders in core paths. If an external integration is deferred, expose an explicit, documented boundary rather than pretending it works.

### Verification
- Run formatting/lint/type checks configured by the repository.
- Run unit and integration tests.
- Build the frontend/dashboard and container images if applicable.
- Start services with the documented commands where the environment allows.
- Exercise real endpoints and inspect persisted database records.
- Verify error paths, not just the happy path.
- Record exact commands, outcomes, environment limitations, and evidence.

### Phase report format
At the end of every phase, provide:
1. Status: DONE / PARTIAL / BLOCKED.
2. Files created/changed.
3. Behavior implemented.
4. Commands executed and exact test results.
5. API/browser/manual verification performed.
6. Known defects, limitations, and security concerns.
7. Required human actions.
8. Git status and commit SHA if applicable.
9. Next recommended phase.
10. Evidence-based statement on whether the current release is resume-ready.

## Resume-readiness rule
A release is resume-ready only when the Fast Track acceptance criteria pass, a clean setup is reproducible, a real deployment is accessible or an honest local-demo limitation is disclosed, documentation matches behavior, and no critical known issue invalidates the claims. A green unit-test suite alone is insufficient.
