"""Tests for database models, migrations, persistence repository, and monitoring queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from modelserve.app import create_app
from modelserve.database import check_database_connection, init_db
from modelserve.models import Base, ModelVersionRecord, PredictionRecord
from modelserve.repository import (
    get_monitoring_summary,
    record_prediction,
    upsert_model_version,
)
from modelserve.settings import Settings


@pytest.fixture
def db_session(tmp_path: Path) -> Session:
    """Isolated SQLite database session for testing persistence logic."""
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    init_db(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_database_connection_check(tmp_path: Path):
    """Probe returns True for valid database and False for invalid connection."""
    db_file = tmp_path / "probe.db"
    engine = create_engine(f"sqlite:///{db_file}")
    assert check_database_connection(engine) is True
    engine.dispose()


def test_record_prediction_persists_telemetry(db_session: Session):
    """Prediction event persists timestamp, model version, label, score, and latency."""
    record = record_prediction(
        db_session,
        request_id="req_test_001",
        model_version="telco-churn-v1",
        label="Yes",
        score=0.85,
        latency_ms=12.5,
    )
    assert record.id is not None
    assert record.request_id == "req_test_001"
    assert record.model_version == "telco-churn-v1"
    assert record.label == "Yes"
    assert record.score == 0.85
    assert record.latency_ms == 12.5
    assert record.created_at_utc is not None

    # ADR-008: Verify raw features are not an attribute of the model
    assert not hasattr(record, "features")
    assert not hasattr(record, "raw_payload")


def test_upsert_model_version(db_session: Session):
    """Model version records can be inserted and subsequently updated."""
    manifest = {
        "artifact_version": "telco-churn-v1",
        "selected_model": "logistic_regression",
        "test_metrics": {"f1": 0.62},
    }
    rec1 = upsert_model_version(
        db_session,
        version="telco-churn-v1",
        name="logistic_regression",
        artifact_sha256="a" * 64,
        dataset_fingerprint="b" * 64,
        created_at_utc=datetime.now(UTC),
        manifest=manifest,
    )
    assert rec1.version == "telco-churn-v1"

    # Upsert existing version updates record
    rec2 = upsert_model_version(
        db_session,
        version="telco-churn-v1",
        name="logistic_regression_updated",
        artifact_sha256="c" * 64,
        dataset_fingerprint="b" * 64,
        created_at_utc=datetime.now(UTC),
        manifest=manifest,
    )
    assert rec2.id == rec1.id
    assert rec2.name == "logistic_regression_updated"


def test_monitoring_summary_empty_state(db_session: Session):
    """Empty database returns safe zero-valued monitoring metrics without ZeroDivisionError."""
    summary = get_monitoring_summary(db_session, window_hours=24)
    assert summary["total_predictions"] == 0
    assert summary["label_distribution"] == {"No": 0, "Yes": 0}
    assert summary["score_summary"] == {"mean": 0.0, "min": 0.0, "max": 0.0}
    assert summary["latency_summary_ms"] == {
        "mean": 0.0,
        "p50": 0.0,
        "p90": 0.0,
        "p95": 0.0,
        "p99": 0.0,
    }


def test_monitoring_summary_aggregations(db_session: Session):
    """Monitoring summary accurately computes distributions and latency percentiles."""
    now = datetime.now(UTC)
    # Record 4 predictions: 3 'No', 1 'Yes'
    record_prediction(db_session, request_id="r1", model_version="v1", label="No", score=0.1, latency_ms=10.0, created_at_utc=now)
    record_prediction(db_session, request_id="r2", model_version="v1", label="No", score=0.2, latency_ms=20.0, created_at_utc=now)
    record_prediction(db_session, request_id="r3", model_version="v1", label="No", score=0.3, latency_ms=30.0, created_at_utc=now)
    record_prediction(db_session, request_id="r4", model_version="v1", label="Yes", score=0.9, latency_ms=40.0, created_at_utc=now)

    # An older prediction outside the 24-hour window should be excluded
    record_prediction(db_session, request_id="r_old", model_version="v1", label="Yes", score=0.99, latency_ms=100.0, created_at_utc=now - timedelta(hours=48))

    summary = get_monitoring_summary(db_session, window_hours=24)
    assert summary["total_predictions"] == 4
    assert summary["label_distribution"] == {"No": 3, "Yes": 1}
    assert summary["score_summary"]["min"] == 0.1
    assert summary["score_summary"]["max"] == 0.9
    assert summary["score_summary"]["mean"] == round((0.1 + 0.2 + 0.3 + 0.9) / 4, 4)
    assert summary["latency_summary_ms"]["p50"] == 25.0


def test_api_prediction_persists_to_database(
    isolated_artifacts_dir: Path, sample_features: dict[str, object], tmp_path: Path
):
    """End-to-end API test verifying inference inserts a durable record in the database."""
    db_file = tmp_path / "api_test.db"
    db_url = f"sqlite:///{db_file}"
    settings = Settings(artifacts_dir=isolated_artifacts_dir, database_url=db_url)
    app = create_app(settings)

    with TestClient(app) as test_client:
        response = test_client.post(
            "/v1/predictions",
            json={"features": sample_features},
            headers={"X-Request-ID": "req_persisted_12345"},
        )
        assert response.status_code == 200

        # Query database to confirm record was persisted
        engine = create_engine(db_url)
        with Session(engine) as session:
            stmt = select(PredictionRecord).where(PredictionRecord.request_id == "req_persisted_12345")
            saved = session.execute(stmt).scalar_one_or_none()
            assert saved is not None
            assert saved.request_id == "req_persisted_12345"
            assert saved.label in ("Yes", "No")
            assert 0.0 <= saved.score <= 1.0
            assert saved.latency_ms > 0.0
        engine.dispose()


def test_api_monitoring_summary_endpoint(
    isolated_artifacts_dir: Path, sample_features: dict[str, object], tmp_path: Path
):
    """GET /v1/monitoring/summary returns live aggregated inference statistics."""
    db_file = tmp_path / "summary_test.db"
    db_url = f"sqlite:///{db_file}"
    settings = Settings(artifacts_dir=isolated_artifacts_dir, database_url=db_url)
    app = create_app(settings)

    with TestClient(app) as test_client:
        # Before predictions: empty summary
        res_empty = test_client.get("/v1/monitoring/summary")
        assert res_empty.status_code == 200
        assert res_empty.json()["total_predictions"] == 0

        # Execute 2 predictions
        test_client.post("/v1/predictions", json={"features": sample_features})
        test_client.post("/v1/predictions", json={"features": sample_features})

        # After predictions: summary reflects count
        res_populated = test_client.get("/v1/monitoring/summary")
        assert res_populated.status_code == 200
        data = res_populated.json()
        assert data["total_predictions"] == 2
        assert "latency_summary_ms" in data
        assert "p50" in data["latency_summary_ms"]


def test_api_prediction_resilience_when_db_down(
    isolated_artifacts_dir: Path, sample_features: dict[str, object], tmp_path: Path
):
    """If database write fails, prediction endpoint continues returning 200 without crashing."""
    db_file = tmp_path / "resilient_test.db"
    db_url = f"sqlite:///{db_file}"
    settings = Settings(artifacts_dir=isolated_artifacts_dir, database_url=db_url)
    app = create_app(settings)

    with TestClient(app) as test_client:
        # Simulate broken session factory
        def broken_factory():
            raise RuntimeError("Database connection suddenly dropped")

        test_client.app.state.session_factory = broken_factory

        # Prediction must still succeed!
        response = test_client.post("/v1/predictions", json={"features": sample_features})
        assert response.status_code == 200
        assert response.json()["status"] == "success"

