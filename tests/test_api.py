"""Comprehensive API tests for ModelServe AI inference service."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from modelserve.app import create_app
from modelserve.settings import Settings

VALID_PAYLOAD = {
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
        "TotalCharges": 29.85,
    }
}


@pytest.fixture
def client():
    """Test client initialized with the application lifespan."""
    settings = Settings(artifacts_dir=Path("artifacts/models"))
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


def test_health_live(client: TestClient):
    """GET /health/live returns alive status 200."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert "X-Request-ID" in response.headers


def test_health_ready_success(client: TestClient):
    """GET /health/ready returns ready status and model version 200."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["model_version"].startswith("telco-churn-")


def test_health_ready_unready_returns_503(tmp_path: Path):
    """GET /health/ready returns 503 when model artifact is missing/invalid."""
    settings = Settings(artifacts_dir=tmp_path / "empty_dir")
    app = create_app(settings)
    with TestClient(app) as test_client:
        response = test_client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "request_id" in data["error"]


def test_model_info_success(client: TestClient):
    """GET /v1/model/info returns active model metadata and evaluation."""
    response = client.get("/v1/model/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "logistic_regression"
    assert data["version"].startswith("telco-churn-")
    assert data["positive_label"] == "Yes"
    assert "feature_columns" in data
    assert "dataset" in data
    assert "test_metrics" in data
    assert data["test_metrics"]["decision_threshold"] == 0.5


def test_prediction_success(client: TestClient):
    """POST /v1/predictions produces valid classification label and score."""
    response = client.post("/v1/predictions", json=VALID_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "request_id" in data
    assert response.headers["X-Request-ID"] == data["request_id"]
    assert data["model"]["name"] == "logistic_regression"
    assert data["model"]["version"].startswith("telco-churn-")
    assert data["prediction"]["label"] in ("Yes", "No")
    assert 0.0 <= data["prediction"]["score"] <= 1.0


def test_prediction_with_null_total_charges(client: TestClient):
    """POST /v1/predictions allows null TotalCharges (handled by imputation)."""
    payload = {
        "features": {**VALID_PAYLOAD["features"], "TotalCharges": None}
    }
    response = client.post("/v1/predictions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["prediction"]["label"] in ("Yes", "No")


def test_prediction_custom_request_id_preserved(client: TestClient):
    """Custom X-Request-ID header is propagated to response body and headers."""
    custom_id = "req_custom_trace_98765"
    response = client.post(
        "/v1/predictions",
        json=VALID_PAYLOAD,
        headers={"X-Request-ID": custom_id},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id
    assert response.json()["request_id"] == custom_id


def test_prediction_missing_required_field(client: TestClient):
    """Missing a required feature field returns a stable 422 error."""
    incomplete_features = {
        k: v for k, v in VALID_PAYLOAD["features"].items() if k != "Contract"
    }
    response = client.post("/v1/predictions", json={"features": incomplete_features})
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in data["error"]
    assert any("Contract" in str(detail["loc"]) for detail in data["error"]["details"])


def test_prediction_invalid_category(client: TestClient):
    """Invalid category string returns 422 validation error."""
    invalid_features = {**VALID_PAYLOAD["features"], "InternetService": "SatelliteBeam"}
    response = client.post("/v1/predictions", json={"features": invalid_features})
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_prediction_negative_tenure(client: TestClient):
    """Negative tenure returns 422 validation error."""
    invalid_features = {**VALID_PAYLOAD["features"], "tenure": -5}
    response = client.post("/v1/predictions", json={"features": invalid_features})
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_prediction_forbidden_extra_field(client: TestClient):
    """Extra unexpected feature fields are forbidden and return 422."""
    extra_features = {**VALID_PAYLOAD["features"], "unknown_extra_feature": "malicious"}
    response = client.post("/v1/predictions", json={"features": extra_features})
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert any("unknown_extra_feature" in str(detail["loc"]) for detail in data["error"]["details"])


def test_prediction_oversized_payload_returns_413():
    """Payloads exceeding maximum size limit return HTTP 413."""
    # Set a tiny payload limit of 50 bytes for testing
    settings = Settings(artifacts_dir=Path("artifacts/models"), max_payload_bytes=50)
    app = create_app(settings)
    with TestClient(app) as test_client:
        response = test_client.post("/v1/predictions", json=VALID_PAYLOAD)
        assert response.status_code == 413
        data = response.json()
        assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"
        assert "request_id" in data["error"]


def test_not_found_route_returns_structured_error(client: TestClient):
    """Unknown route returns 404 with structured error envelope."""
    response = client.get("/v1/nonexistent_route")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert "request_id" in data["error"]


def test_openapi_schema(client: TestClient):
    """Inspect OpenAPI schema to ensure documentation contract matches."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "ModelServe AI"
    assert "/health/live" in schema["paths"]
    assert "/health/ready" in schema["paths"]
    assert "/v1/model/info" in schema["paths"]
    assert "/v1/predictions" in schema["paths"]


def test_safe_500_error_handling(monkeypatch):
    """Unhandled exceptions return a safe HTTP 500 without leaking stack traces."""
    from modelserve.model_loader import LoadedModel

    def broken_predict(*args, **kwargs):
        raise RuntimeError("Sensitive internal database connection failed: secret_pw_123")

    monkeypatch.setattr(LoadedModel, "predict", broken_predict)

    settings = Settings(artifacts_dir=Path("artifacts/models"))
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client_no_raise:
        response = client_no_raise.post("/v1/predictions", json=VALID_PAYLOAD)
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "request_id" in data["error"]
        # Ensure sensitive error message / stack trace is not leaked
        assert "secret_pw_123" not in response.text
        assert "Traceback" not in response.text
