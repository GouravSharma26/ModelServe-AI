# API Guide — ModelServe AI

## Base URL
Local Docker Compose URL is expected to be configured/documented after implementation. Do not assume a port or public URL without checking the actual configuration.

## Authentication
Fast Track local demo may be unauthenticated on a private local network. Before exposing publicly, implement appropriate authentication and/or rate limiting, restrict management functions, and document the security model. Do not expose a database or privileged model-management operation publicly.

## Endpoints
### `GET /health/live`
Indicates that the application process is running. It should not fail solely because PostgreSQL is unavailable.

### `GET /health/ready`
Indicates whether the service is ready to serve predictions. Check that the model is loaded and required dependencies are available according to the documented policy.

### `GET /v1/model/info`
Returns the active model's name, version, schema identifier, training time, and selected evaluation metadata.

### `POST /v1/predictions`
Accepts one record using the exact feature schema documented by the generated OpenAPI schema and model metadata.

Example request:
```json
{
  "features": {
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "Yes",
    "Dependents": "No",
    "tenure": 1,
    "PhoneService": "No",
    "MultipleLines": "No phone service",
    "InternetService": "DSL",
    "OnlineSecurity": "No",
    "OnlineBackup": "Yes",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 29.85,
    "TotalCharges": 29.85
  }
}
```

Example success response:
```json
{
  "request_id": "req_49ab79f4ba484f75",
  "model": {
    "name": "logistic_regression",
    "version": "telco-churn-20261028T120929Z"
  },
  "prediction": {
    "label": "Yes",
    "score": 0.8084
  },
  "status": "success"
}
```

Note on scores: Output scores represent estimated class likelihood for positive label `"Yes"`; probabilities have not been calibrated. Extra/unexpected feature fields are strictly rejected with HTTP 422 to prevent contract drift. Missing `TotalCharges` (null) is permitted for new customers with tenure 0 and handled via median imputation.

### `GET /v1/monitoring/summary`
Returns bounded-window aggregated inference activity. Define the default time window, timezone, empty-state behavior, and percentile calculation method.

## Error contract
Use a consistent response shape, for example:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request does not match the required input schema.",
    "request_id": "req_example_001"
  }
}
```
Do not return tracebacks or sensitive internal details to clients. Error codes and actual status mappings must match the implementation.

Suggested mapping:
- 400/422: invalid request, according to FastAPI/Pydantic contract.
- 404: unknown route or requested resource.
- 413: payload too large if explicitly handled.
- 503: model or required dependency unavailable.
- 500: unexpected internal failure with safe client message.

## Operational guidance
- Inspect `/docs` locally for interactive API documentation.
- Use a synthetic sample payload copied from the model schema.
- Check response model version against `/v1/model/info`.
- Verify successful predictions appear in monitoring history.
- Use health/readiness endpoints during startup troubleshooting.
- Never send secrets or real customer records in public demo requests.
