"""Comprehensive API tests for ModelServe AI inference service."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from modelserve.app import create_app
from modelserve.settings import Settings


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


def test_health_ready_unready_returns_generic_message(tmp_path: Path):
    """GET /health/ready returns generic 503 message and does not leak internal diagnostic paths."""
    settings = Settings(artifacts_dir=tmp_path / "empty_dir")
    app = create_app(settings)
    with TestClient(app) as test_client:
        response = test_client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        # Generic message required by review finding 3
        assert data["error"]["message"] == "Service unavailable: model is not ready to serve predictions."
        assert "request_id" in data["error"]
        # Ensure internal paths are not leaked to client
        assert str(tmp_path) not in response.text


def test_model_info_success(client: TestClient):
    """GET /v1/model/info returns active model metadata and evaluation."""
    response = client.get("/v1/model/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] in ("logistic_regression", "random_forest")
    assert data["version"].startswith("telco-churn-")
    assert data["positive_label"] == "Yes"
    assert "feature_columns" in data
    assert "dataset" in data
    assert "test_metrics" in data
    assert data["test_metrics"]["decision_threshold"] == 0.5


def test_prediction_success(client: TestClient, sample_features: dict[str, object]):
    """POST /v1/predictions produces valid classification label and score."""
    response = client.post("/v1/predictions", json={"features": sample_features})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "request_id" in data
    assert response.headers["X-Request-ID"] == data["request_id"]
    assert data["model"]["name"] in ("logistic_regression", "random_forest")
    assert data["model"]["version"].startswith("telco-churn-")
    assert data["prediction"]["label"] in ("Yes", "No")
    assert 0.0 <= data["prediction"]["score"] <= 1.0


def test_prediction_with_null_total_charges(client: TestClient, sample_features: dict[str, object]):
    """POST /v1/predictions allows null TotalCharges (handled by imputation)."""
    payload = {
        "features": {**sample_features, "TotalCharges": None}
    }
    response = client.post("/v1/predictions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["prediction"]["label"] in ("Yes", "No")


def test_prediction_custom_request_id_preserved(client: TestClient, sample_features: dict[str, object]):
    """Custom X-Request-ID header is propagated to response body and headers."""
    custom_id = "req_custom_trace_98765"
    response = client.post(
        "/v1/predictions",
        json={"features": sample_features},
        headers={"X-Request-ID": custom_id},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id
    assert response.json()["request_id"] == custom_id


def test_prediction_missing_required_field(client: TestClient, sample_features: dict[str, object]):
    """Missing a required feature field returns a stable 422 error."""
    incomplete_features = {
        k: v for k, v in sample_features.items() if k != "Contract"
    }
    response = client.post("/v1/predictions", json={"features": incomplete_features})
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in data["error"]
    assert any("Contract" in str(detail["loc"]) for detail in data["error"]["details"])


def test_prediction_invalid_category(client: TestClient, sample_features: dict[str, object]):
    """Invalid category string returns 422 validation error."""
    invalid_features = {**sample_features, "InternetService": "SatelliteBeam"}
    response = client.post("/v1/predictions", json={"features": invalid_features})
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_prediction_negative_tenure(client: TestClient, sample_features: dict[str, object]):
    """Negative tenure returns 422 validation error."""
    invalid_features = {**sample_features, "tenure": -5}
    response = client.post("/v1/predictions", json={"features": invalid_features})
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_prediction_forbidden_extra_field(client: TestClient, sample_features: dict[str, object]):
    """Extra unexpected feature fields are forbidden and return 422."""
    extra_features = {**sample_features, "unknown_extra_feature": "malicious"}
    response = client.post("/v1/predictions", json={"features": extra_features})
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert any("unknown_extra_feature" in str(detail["loc"]) for detail in data["error"]["details"])


def test_validation_error_logging_does_not_leak_input_values(
    client: TestClient, sample_features: dict[str, object], caplog: pytest.LogCaptureFixture
):
    """Review Finding 2: Validate that rejected input values do not appear in captured log records."""
    canary_secret = "CONFIDENTIAL_CANARY_VALUE_SECRET_98765"
    malicious_features = {**sample_features, "gender": canary_secret}

    with caplog.at_level(logging.WARNING, logger="modelserve.app"):
        response = client.post("/v1/predictions", json={"features": malicious_features})
        assert response.status_code == 422

    # The canary secret must NOT appear anywhere in the captured logs
    assert canary_secret not in caplog.text
    # Log must still record the error type and location
    assert "literal_error" in caplog.text or "validation_error" in caplog.text
    assert "gender" in caplog.text


def test_prediction_oversized_payload_returns_413(isolated_artifacts_dir: Path, sample_features: dict[str, object]):
    """Payloads exceeding maximum size limit return HTTP 413."""
    settings = Settings(artifacts_dir=isolated_artifacts_dir, max_payload_bytes=50)
    app = create_app(settings)
    with TestClient(app) as test_client:
        response = test_client.post("/v1/predictions", json={"features": sample_features})
        assert response.status_code == 413
        data = response.json()
        assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"
        assert "request_id" in data["error"]


def test_streamed_oversized_payload_without_content_length_returns_413(isolated_artifacts_dir: Path):
    """Review Finding 1: Enforce payload limit when Content-Length is absent or streamed."""
    settings = Settings(artifacts_dir=isolated_artifacts_dir, max_payload_bytes=100)
    app = create_app(settings)

    def generate_large_stream():
        # Stream 10 chunks of 50 bytes = 500 bytes (exceeds 100 bytes limit)
        for _ in range(10):
            yield b"X" * 50

    with TestClient(app) as test_client:
        response = test_client.post(
            "/v1/predictions",
            content=generate_large_stream(),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413
        data = response.json()
        assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"


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


def test_safe_500_error_handling(isolated_artifacts_dir: Path, sample_features: dict[str, object], monkeypatch):
    """Unhandled exceptions return a safe HTTP 500 without leaking stack traces."""
    from modelserve.model_loader import LoadedModel

    def broken_predict(*args, **kwargs):
        raise RuntimeError("Sensitive internal database connection failed: secret_pw_123")

    monkeypatch.setattr(LoadedModel, "predict", broken_predict)

    settings = Settings(artifacts_dir=isolated_artifacts_dir)
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client_no_raise:
        response = client_no_raise.post("/v1/predictions", json={"features": sample_features})
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "request_id" in data["error"]
        assert "secret_pw_123" not in response.text
        assert "Traceback" not in response.text
