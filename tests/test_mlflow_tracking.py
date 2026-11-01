"""Tests for MLflow experiment tracking and artifact lineage logging."""

import json
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient

from modelserve.tracking import ensure_experiment, get_default_tracking_uri, log_training_run


def create_sample_manifest(version_dir: Path, version: str = "telco-churn-20261101T000000Z") -> dict:
    version_dir.mkdir(parents=True, exist_ok=True)
    model_file = version_dir / "model.joblib"
    model_file.write_bytes(b"mock_joblib_binary_content_for_testing")

    manifest = {
        "artifact_version": version,
        "artifact_directory": version,
        "artifact_file": "model.joblib",
        "artifact_sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "dataset": {
            "name": "IBM Telco Customer Churn",
            "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "rows": 7043,
        },
        "target": "Churn",
        "positive_label": "Yes",
        "feature_columns": ["gender", "tenure", "MonthlyCharges", "TotalCharges"],
        "feature_schema": {
            "numeric": ["tenure", "MonthlyCharges", "TotalCharges"],
            "categorical": ["gender"],
        },
        "split": {
            "train": 0.60,
            "validation": 0.20,
            "test": 0.20,
            "random_seed": 42,
        },
        "selected_model": "logistic_regression",
        "validation_metrics": {
            "logistic_regression": {
                "pr_auc_average_precision": 0.6232,
                "roc_auc": 0.8321,
                "f1": 0.6247,
                "precision": 0.508,
                "recall": 0.810,
            },
            "random_forest": {
                "pr_auc_average_precision": 0.6150,
                "roc_auc": 0.8250,
                "f1": 0.6120,
                "precision": 0.520,
                "recall": 0.744,
            },
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


def test_ensure_experiment_creates_experiment(tmp_path: Path):
    tracking_uri = (tmp_path / "mlruns").as_uri()
    exp_id = ensure_experiment("test-experiment", tracking_uri)
    assert exp_id is not None

    client = MlflowClient(tracking_uri=tracking_uri)
    exp = client.get_experiment(exp_id)
    assert exp.name == "test-experiment"

    # Calling again returns the existing ID
    assert ensure_experiment("test-experiment", tracking_uri) == exp_id


def test_log_training_run_tracks_metrics_and_artifacts(tmp_path: Path):
    tracking_uri = (tmp_path / "mlruns").as_uri()
    version_dir = tmp_path / "models" / "telco-churn-20261101T000000Z"
    manifest = create_sample_manifest(version_dir)

    run_id = log_training_run(
        manifest,
        version_dir,
        tracking_uri=tracking_uri,
        experiment_name="test-churn-experiment",
    )
    assert run_id is not None

    client = MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(run_id)

    # 1. Verify Parameters
    assert run.data.params["selected_model"] == "logistic_regression"
    assert run.data.params["random_seed"] == "42"
    assert run.data.params["num_features"] == "4"

    # 2. Verify Distinct Validation and Test Metrics
    assert run.data.metrics["val_pr_auc"] == 0.6232
    assert run.data.metrics["val_roc_auc"] == 0.8321
    assert run.data.metrics["val_f1"] == 0.6247
    assert run.data.metrics["test_pr_auc"] == 0.6190
    assert run.data.metrics["test_roc_auc"] == 0.8290
    assert run.data.metrics["test_f1"] == 0.6210

    # 3. Verify Tags
    assert run.data.tags["lifecycle_stage"] == "candidate"
    assert run.data.tags["model_version"] == "telco-churn-20261101T000000Z"
    assert run.data.tags["dataset_fingerprint"] == manifest["dataset"]["sha256"]

    # 4. Verify Logged Artifacts
    artifacts = [a.path for a in client.list_artifacts(run_id)]
    assert "metadata" in artifacts
    assert "model" in artifacts
    assert "evaluation" in artifacts

    metadata_files = [a.path for a in client.list_artifacts(run_id, path="metadata")]
    assert any("manifest.json" in f for f in metadata_files)
    assert any("evaluation.json" in f for f in metadata_files)


def test_no_customer_pii_logged_to_mlflow(tmp_path: Path):
    tracking_uri = (tmp_path / "mlruns").as_uri()
    version_dir = tmp_path / "models" / "telco-churn-pii-check"
    manifest = create_sample_manifest(version_dir, version="telco-churn-pii-check")

    run_id = log_training_run(
        manifest,
        version_dir,
        tracking_uri=tracking_uri,
        experiment_name="test-pii-experiment",
    )

    client = MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(run_id)

    # Inspect all logged parameter keys and values
    for k, v in run.data.params.items():
        assert "customer" not in k.lower() or k == "dataset_rows"
        assert "@" not in str(v)  # No emails
        assert "phone" not in k.lower()  # No phone numbers

