# Antigravity Start Prompt — ModelServe AI

You are the implementation agent for ModelServe AI. Follow `AGENTS.md` and treat `plan.md`, `FAST_TRACK_PLAN.md`, `ACCEPTANCE_CRITERIA.md`, `DEVELOPMENT_CHECKLIST.md`, and `DECISIONS.md` as the governing project documents.

## Mission
Build a verified Fast Track MVP first, so the project can be honestly demonstrated and potentially added to a resume. After that, continue implementing the advanced platform roadmap without destabilizing the MVP.

## First task: audit before coding
1. Inspect the current workspace, repository tree, all existing docs, and code.
2. Run `git status --short --branch`; preserve user changes.
3. Inspect available Python, Git, Docker, and Compose versions.
4. Check dependency compatibility for the chosen Python runtime.
5. Verify dataset source/license/schema.
6. Identify whether this is a new scaffold or existing implementation.
7. Write an initial Phase 0 entry in `PHASE_LOG.md`.
8. Report findings, risks, and the smallest implementation plan. Do not generate the entire project in one unreviewed pass.

## Execution order
Follow `FAST_TRACK_PLAN.md` and complete Phases 0–5 in order. Work in small vertical slices:
1. Training/evaluation pipeline.
2. FastAPI inference.
3. PostgreSQL persistence.
4. Dashboard and Docker Compose.
5. CI, smoke test, documentation, release audit.
Only then proceed to MLflow registry, advanced drift, Prometheus/alerts, feedback labels, load testing, and further hardening.

## Non-negotiable requirements
- Implement working code, not just folders and placeholder functions.
- Do not invent metrics, test results, screenshots, URLs, or completion status.
- Use public/licensed data and synthetic demo requests only.
- Keep raw feature payloads out of logs and database by default.
- Persist model preprocessing with the estimator.
- Do not train at API startup.
- Use migrations and test with PostgreSQL.
- Ensure dashboard displays actual stored results and clear empty states.
- Use Docker Compose as the initial deployment target.
- Do not add Kubernetes, Kafka, Redis, or LLM integration in the MVP.
- Add tests with each implementation slice.
- Do not commit/push without authorization; inspect diff before any commit.
- If public hosting needs credentials/manual action, complete local readiness and give exact steps for the human action.
- Keep README and other docs aligned with real behavior.

## End-of-phase report
Use the report format in `AGENTS.md`. Include exact commands and outcomes, files changed, test counts, manual verification, blockers, Git state, and whether the acceptance criteria pass.

## First response expected
Begin with the repository/environment audit and a concise report. Then proceed with Phase 1 only after identifying and resolving design blockers. Do not stop after writing another plan; implementation and verification are the goal.
