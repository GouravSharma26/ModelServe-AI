"""Tests for ModelLifecycleService and end-to-end promotion, rollback, and serving workflows."""

import hashlib
import json
from pathlib import Path

import joblib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modelserve.database import init_db
from modelserve.dataset import CATEGORICAL_COLUMNS, NUMERIC_COLUMNS
from modelserve.lifecycle import ModelLifecycleService
from modelserve.lifecycle_cli import main as cli_main
from modelserve.models import Base, ModelPromotionAudit, ModelVersionRecord
from modelserve.training import make_candidates


def setup_test_artifacts(artifacts_dir: Path, version: str, seed: int = 42) -> dict:
    version_dir = artifacts_dir / version
    version_dir.mkdir(parents=True, exist_ok=True)

    candidates = make_candidates(seed)
    model = candidates["logistic_regression"]
    # Fit dummy on dummy data to allow real predictions if needed
    import pandas as pd
    cols = list(NUMERIC_COLUMNS) + list(CATEGORICAL_COLUMNS)
    sample_df = pd.DataFrame([
        {
            "gender": "Female", "SeniorCitizen": 0, "Partner": "Yes", "Dependents": "No",
            "tenure": 12, "PhoneService": "Yes", "MultipleLines": "No",
            "InternetService": "DSL", "OnlineSecurity": "Yes", "OnlineBackup": "No",
            "DeviceProtection": "Yes", "TechSupport": "No", "StreamingTV": "No",
            "StreamingMovies": "No", "Contract": "One year", "PaperlessBilling": "No",
            "PaymentMethod": "Bank transfer (automatic)", "MonthlyCharges": 45.2, "TotalCharges": 542.4
        },
        {
            "gender": "Male", "SeniorCitizen": 1, "Partner": "No", "Dependents": "No",
            "tenure": 2, "PhoneService": "Yes", "MultipleLines": "Yes",
            "InternetService": "Fiber optic", "OnlineSecurity": "No", "OnlineBackup": "No",
            "DeviceProtection": "No", "TechSupport": "No", "StreamingTV": "Yes",
            "StreamingMovies": "Yes", "Contract": "Month-to-month", "PaperlessBilling": "Yes",
            "PaymentMethod": "Electronic check", "MonthlyCharges": 89.5, "TotalCharges": 179.0
        },
    ])
    model.fit(sample_df, ["No", "Yes"])

    model_path = version_dir / "model.joblib"
    joblib.dump(model, model_path)
    sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest()

    manifest = {
        "artifact_version": version,
        "artifact_file": "model.joblib",
        "artifact_sha256": sha256,
        "dataset": {
            "name": "IBM Telco Customer Churn",
            "sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
            "rows": 7043,
        },
        "target": "Churn",
        "positive_label": "Yes",
        "feature_columns": cols,
        "feature_schema": {
            "numeric": list(NUMERIC_COLUMNS),
            "categorical": list(CATEGORICAL_COLUMNS),
        },
        "selected_model": "logistic_regression",
        "validation_metrics": {
            "logistic_regression": {
                "pr_auc_average_precision": 0.6232,
                "roc_auc": 0.8321,
                "f1": 0.6247,
                "precision": 0.508,
                "recall": 0.810,
            }
        },
        "test_metrics": {
            "pr_auc_average_precision": 0.6190,
            "roc_auc": 0.8290,
            "f1": 0.6210,
            "precision": 0.505,
            "recall": 0.805,
            "confusion_matrix": [[742, 293], [71, 303]],
            "confusion_matrix_labels": ["No", "Yes"],
            "decision_threshold": 0.5,
        },
    }
    (version_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (version_dir / "evaluation.json").write_text(json.dumps(manifest["test_metrics"]), encoding="utf-8")
    return manifest


@pytest.fixture
def lifecycle_env(tmp_path: Path):
    db_file = tmp_path / "test_lifecycle.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)
    init_db(engine)
    session_factory = sessionmaker(bind=engine)

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    service = ModelLifecycleService(session_factory, artifacts_dir)
    return service, session_factory, artifacts_dir, db_url


def test_register_candidate(lifecycle_env):
    service, session_factory, artifacts_dir, _ = lifecycle_env
    version_a = "telco-churn-20261101T100000Z"
    setup_test_artifacts(artifacts_dir, version_a)

    record = service.register_candidate(version_a, mlflow_run_id="run-12345")
    assert record.version == version_a
    assert record.stage == "candidate"
    assert record.is_active is False
    assert record.mlflow_run_id == "run-12345"

    active = service.get_active_model()
    assert active is None


def test_compare_candidate_with_active(lifecycle_env):
    service, _, artifacts_dir, _ = lifecycle_env
    version_a = "telco-churn-20261101T100000Z"
    version_b = "telco-churn-20261101T110000Z"
    setup_test_artifacts(artifacts_dir, version_a)
    setup_test_artifacts(artifacts_dir, version_b)

    service.register_candidate(version_a)
    service.promote_model(version_a, actor="test_runner", reason="Initial promotion")

    service.register_candidate(version_b)
    comp = service.compare_candidate_with_active(version_b)

    assert comp["candidate"]["version"] == version_b
    assert comp["active"]["version"] == version_a
    assert comp["schema_compatible"] is True
    assert "metric_deltas" in comp


def test_promote_and_rollback_workflow(lifecycle_env):
    service, session_factory, artifacts_dir, _ = lifecycle_env
    ver_a = "telco-churn-ver-a"
    ver_b = "telco-churn-ver-b"
    setup_test_artifacts(artifacts_dir, ver_a)
    setup_test_artifacts(artifacts_dir, ver_b)

    # 1. Promote Model A
    service.register_candidate(ver_a)
    success, gates, audit_a = service.promote_model(
        ver_a, actor="engineer@modelserve.ai", reason="Promote baseline candidate A"
    )
    assert success is True
    assert gates.eligible is True
    assert audit_a.event_type == "promotion"
    assert audit_a.new_model_version == ver_a
    assert audit_a.previous_model_version is None

    active = service.get_active_model()
    assert active.version == ver_a
    assert active.is_active is True
    assert active.stage == "active"

    # 2. Promote Model B
    service.register_candidate(ver_b)
    success_b, _, audit_b = service.promote_model(
        ver_b, actor="engineer@modelserve.ai", reason="Promote improved candidate B"
    )
    assert success_b is True
    assert audit_b.previous_model_version == ver_a
    assert audit_b.new_model_version == ver_b

    active_b = service.get_active_model()
    assert active_b.version == ver_b

    # Previous model A is retired
    rec_a = service.get_model(ver_a)
    assert rec_a.is_active is False
    assert rec_a.stage == "retired"

    # 3. Rollback to Model A
    audit_rb = service.rollback_model(
        ver_a, actor="oncall@modelserve.ai", reason="Emergency rollback to ver_a"
    )
    assert audit_rb.event_type == "rollback"
    assert audit_rb.previous_model_version == ver_b
    assert audit_rb.new_model_version == ver_a

    active_restored = service.get_active_model()
    assert active_restored.version == ver_a
    assert active_restored.is_active is True
    assert active_restored.stage == "active"

    rec_b = service.get_model(ver_b)
    assert rec_b.is_active is False
    assert rec_b.stage == "retired"

    # 4. Check Audit Trail
    history = service.get_audit_history()
    assert len(history) == 3
    assert history[0].event_type == "rollback"
    assert history[1].event_type == "promotion"
    assert history[2].event_type == "promotion"


def test_promotion_blocked_on_failed_gates(lifecycle_env):
    service, _, artifacts_dir, _ = lifecycle_env
    ver_bad = "telco-churn-bad"
    manifest = setup_test_artifacts(artifacts_dir, ver_bad)
    # Inject failure: low PR-AUC
    manifest["validation_metrics"]["logistic_regression"]["pr_auc_average_precision"] = 0.35
    (artifacts_dir / ver_bad / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    service.register_candidate(ver_bad)
    with pytest.raises(ValueError, match="failed promotion gates"):
        service.promote_model(ver_bad, actor="ci", reason="Automated deploy attempt")

    active = service.get_active_model()
    assert active is None


def test_cli_interface(lifecycle_env):
    _, _, artifacts_dir, db_url = lifecycle_env
    ver = "telco-churn-cli-test"
    setup_test_artifacts(artifacts_dir, ver)

    # 1. Register via CLI
    code = cli_main(["--db-url", db_url, "--artifacts-dir", str(artifacts_dir), "register", ver])
    assert code == 0

    # 2. Check gates via CLI
    code = cli_main(["--db-url", db_url, "--artifacts-dir", str(artifacts_dir), "check-gates", ver])
    assert code == 0

    # 3. Promote via CLI
    code = cli_main([
        "--db-url", db_url, "--artifacts-dir", str(artifacts_dir),
        "promote", ver, "--actor", "cli_user", "--reason", "CLI verification"
    ])
    assert code == 0

    # 4. List via CLI
    code = cli_main(["--db-url", db_url, "--artifacts-dir", str(artifacts_dir), "list"])
    assert code == 0

    # 5. History via CLI
    code = cli_main(["--db-url", db_url, "--artifacts-dir", str(artifacts_dir), "history"])
    assert code == 0


def test_e2e_serving_integration_with_promotions_and_rollback(lifecycle_env, monkeypatch):
    from fastapi.testclient import TestClient
    from modelserve.app import create_app
    from modelserve.settings import Settings

    service, _, artifacts_dir, db_url = lifecycle_env
    ver_a = "telco-churn-api-a"
    ver_b = "telco-churn-api-b"
    setup_test_artifacts(artifacts_dir, ver_a)
    setup_test_artifacts(artifacts_dir, ver_b)

    # 1. Promote Model A to Active
    service.register_candidate(ver_a)
    service.promote_model(ver_a, actor="admin", reason="Initial prod model")

    test_settings = Settings(
        env="test",
        database_url=db_url,
        artifacts_dir=artifacts_dir,
        model_version="active",  # Explicitly resolve active model from database
        cors_origins=["http://localhost:5173"],
    )

    app_a = create_app(settings=test_settings)
    with TestClient(app_a) as client_a:
        health_resp = client_a.get("/health/ready")
        assert health_resp.status_code == 200
        assert health_resp.json()["model_version"] == ver_a

        # Predict with model A
        pred_payload = {
            "gender": "Female", "SeniorCitizen": 0, "Partner": "Yes", "Dependents": "No",
            "tenure": 12, "PhoneService": "Yes", "MultipleLines": "No",
            "InternetService": "DSL", "OnlineSecurity": "Yes", "OnlineBackup": "No",
            "DeviceProtection": "Yes", "TechSupport": "No", "StreamingTV": "No",
            "StreamingMovies": "No", "Contract": "One year", "PaperlessBilling": "No",
            "PaymentMethod": "Bank transfer (automatic)", "MonthlyCharges": 45.2, "TotalCharges": 542.4
        }
        pred_resp = client_a.post("/v1/predictions", json={"features": pred_payload})
        assert pred_resp.status_code == 200
        assert pred_resp.json()["model"]["version"] == ver_a

    # 2. Promote Model B to Active
    service.register_candidate(ver_b)
    service.promote_model(ver_b, actor="admin", reason="Promote model B")

    app_b = create_app(settings=test_settings)
    with TestClient(app_b) as client_b:
        health_resp = client_b.get("/health/ready")
        assert health_resp.status_code == 200
        assert health_resp.json()["model_version"] == ver_b

        pred_resp = client_b.post("/v1/predictions", json={"features": pred_payload})
        assert pred_resp.status_code == 200
        assert pred_resp.json()["model"]["version"] == ver_b

    # 3. Rollback to Model A
    service.rollback_model(ver_a, actor="admin", reason="Rollback to model A")

    app_restored = create_app(settings=test_settings)
    with TestClient(app_restored) as client_restored:
        health_resp = client_restored.get("/health/ready")
        assert health_resp.status_code == 200
        assert health_resp.json()["model_version"] == ver_a

        pred_resp = client_restored.post("/v1/predictions", json={"features": pred_payload})
        assert pred_resp.status_code == 200
        assert pred_resp.json()["model"]["version"] == ver_a

