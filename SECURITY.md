# Security and Privacy Checklist

## Secrets and configuration
- Never commit `.env`, passwords, API tokens, database URLs containing credentials, or cloud keys.
- Keep `.env.example` placeholder-only.
- Use separate least-privilege database users where practical.
- Rotate any credential accidentally exposed and remove it from active use; a Git deletion alone does not invalidate it.

## API
- Validate all inputs.
- Bound request size and batch size.
- Restrict CORS.
- Avoid exposing internal stack traces.
- Add authentication/rate limiting before public exposure where appropriate.
- Do not provide public model-promotion or rollback endpoints without authorization and audit logging.
- Do not expose database ports publicly without a clear need.

## ML artifact safety
Joblib/pickle-based formats can execute code during loading. Only load artifacts from the trusted training pipeline or a verified artifact store. Validate checksum and metadata; checksum alone does not make an untrusted artifact safe.

## Logging and data retention
- Do not log complete feature payloads by default.
- Redact credentials and personal data.
- Retain only fields needed for monitoring.
- Document retention and deletion policy.
- Use synthetic examples in public demo and screenshots.

## Supply chain
- Pin dependencies and use a lock/constraints file.
- Run dependency vulnerability checks.
- Build containers from trusted base images.
- Avoid running as root where feasible.
- Review Docker build context and `.dockerignore`.
- Never copy developer secrets or the full local workspace into production images.

## Before public release
- Inspect Git history for secrets.
- Verify public endpoints do not reveal environment variables or stack traces.
- Verify dashboard and API expose only intended data.
- Test oversized and malformed requests.
- Document residual risks.
