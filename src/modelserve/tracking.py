"""MLflow tracking integration for ModelServe AI experiments.

Manages experiment creation, parameter logging, distinct validation/test metrics,
and verified artifact tracking without logging sensitive customer data or raw features.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient

logger = logging.getLogger("modelserve.tracking")

DEFAULT_EXPERIMENT_NAME = "modelserve-customer-churn"


def get_default_tracking_uri(base_dir: Path | None = None) -> str:
    """Return the configured MLFLOW_TRACKING_URI or fallback to local file store."""
    env_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if env_uri:
        return env_uri
    if base_dir is None:
        base_dir = Path("artifacts")
    mlruns_dir = base_dir / "mlruns"
    mlruns_dir.mkdir(parents=True, exist_ok=True)
    return mlruns_dir.as_uri()


def get_experiment_name() -> str:
    """Return the configured MLFLOW_EXPERIMENT_NAME or default."""
    return os.environ.get("MLFLOW_EXPERIMENT_NAME", DEFAULT_EXPERIMENT_NAME)


def ensure_experiment(
    experiment_name: str | None = None,
    tracking_uri: str | None = None,
) -> str:
    """Ensure that the named experiment exists in MLflow and return its experiment_id."""
    uri = tracking_uri or get_default_tracking_uri()
    mlflow.set_tracking_uri(uri)
    name = experiment_name or get_experiment_name()

    client = MlflowClient(tracking_uri=uri)
    experiment = client.get_experiment_by_name(name)
    if experiment is not None:
        if experiment.lifecycle_stage == "deleted":
            client.restore_experiment(experiment.experiment_id)
        return experiment.experiment_id

    experiment_id = client.create_experiment(name=name)
    logger.info("Created MLflow experiment '%s' (id: %s) at %s", name, experiment_id, uri)
    return experiment_id


def log_training_run(
    manifest: dict[str, Any],
    version_dir: Path,
    *,
    tracking_uri: str | None = None,
    experiment_name: str | None = None,
) -> str:
    """Log model training parameters, validation/test metrics, and artifacts to MLflow.

    Enforces data minimization: does not log raw input data or customer records.
    Returns the MLflow run_id.
    """
    uri = tracking_uri or get_default_tracking_uri(version_dir.parent.parent)
    exp_name = experiment_name or get_experiment_name()

    mlflow.set_tracking_uri(uri)
    ensure_experiment(exp_name, uri)
    mlflow.set_experiment(exp_name)

    artifact_version = manifest["artifact_version"]
    selected_model = manifest["selected_model"]
    test_metrics = manifest.get("test_metrics", {})
    val_metrics_all = manifest.get("validation_metrics", {})
    selected_val_metrics = val_metrics_all.get(selected_model, {})

    with mlflow.start_run(run_name=artifact_version) as run:
        run_id = run.info.run_id

        # 1. Log Training Parameters (seeds, split policy, feature dimensions)
        split_info = manifest.get("split", {})
        params = {
            "artifact_version": artifact_version,
            "selected_model": selected_model,
            "random_seed": str(split_info.get("random_seed", 42)),
            "train_split": str(split_info.get("train", 0.60)),
            "val_split": str(split_info.get("validation", 0.20)),
            "test_split": str(split_info.get("test", 0.20)),
            "num_features": str(len(manifest.get("feature_columns", []))),
            "dataset_rows": str(manifest.get("dataset", {}).get("rows", 0)),
            "target_column": str(manifest.get("target", "Churn")),
            "positive_label": str(manifest.get("positive_label", "Yes")),
            "decision_threshold": str(test_metrics.get("decision_threshold", 0.5)),
        }
        mlflow.log_params(params)

        # 2. Log Validation Metrics (prefixed with val_)
        if selected_val_metrics:
            mlflow.log_metrics({
                "val_pr_auc": float(selected_val_metrics.get("pr_auc_average_precision", 0.0)),
                "val_roc_auc": float(selected_val_metrics.get("roc_auc", 0.0)),
                "val_f1": float(selected_val_metrics.get("f1", 0.0)),
                "val_precision": float(selected_val_metrics.get("precision", 0.0)),
                "val_recall": float(selected_val_metrics.get("recall", 0.0)),
            })

        # Also log per-candidate validation PR-AUC for model comparison visibility
        for cand_name, cand_val in val_metrics_all.items():
            if "pr_auc_average_precision" in cand_val:
                mlflow.log_metric(
                    f"cand_{cand_name}_val_pr_auc",
                    float(cand_val["pr_auc_average_precision"]),
                )
            if "f1" in cand_val:
                mlflow.log_metric(f"cand_{cand_name}_val_f1", float(cand_val["f1"]))

        # 3. Log Held-Out Test Metrics (distinct prefix test_)
        if test_metrics:
            mlflow.log_metrics({
                "test_pr_auc": float(test_metrics.get("pr_auc_average_precision", 0.0)),
                "test_roc_auc": float(test_metrics.get("roc_auc", 0.0)),
                "test_f1": float(test_metrics.get("f1", 0.0)),
                "test_precision": float(test_metrics.get("precision", 0.0)),
                "test_recall": float(test_metrics.get("recall", 0.0)),
            })

        # 4. Log Tags for Lineage and Integrity
        mlflow.set_tags({
            "model_version": artifact_version,
            "artifact_sha256": manifest.get("artifact_sha256", ""),
            "dataset_fingerprint": manifest.get("dataset", {}).get("sha256", ""),
            "lifecycle_stage": "candidate",
            "framework": "scikit-learn",
        })

        # 5. Log Artifacts
        manifest_path = version_dir / "manifest.json"
        if manifest_path.exists():
            mlflow.log_artifact(str(manifest_path), artifact_path="metadata")

        evaluation_path = version_dir / "evaluation.json"
        if evaluation_path.exists():
            mlflow.log_artifact(str(evaluation_path), artifact_path="metadata")

        model_path = version_dir / manifest.get("artifact_file", "model.joblib")
        if model_path.exists():
            mlflow.log_artifact(str(model_path), artifact_path="model")

        # Create and log confusion matrix artifact
        if "confusion_matrix" in test_metrics:
            cm_path = version_dir / "confusion_matrix.json"
            cm_payload = {
                "matrix": test_metrics["confusion_matrix"],
                "labels": test_metrics.get("confusion_matrix_labels", ["No", "Yes"]),
                "threshold": test_metrics.get("decision_threshold", 0.5),
            }
            cm_path.write_text(json.dumps(cm_payload, indent=2) + "\n", encoding="utf-8")
            mlflow.log_artifact(str(cm_path), artifact_path="evaluation")

        logger.info(
            "Logged training run to MLflow experiment '%s' (run_id: %s, version: %s)",
            exp_name,
            run_id,
            artifact_version,
        )
        return run_id

