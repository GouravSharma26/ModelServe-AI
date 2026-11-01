"""Tests for deterministic promotion quality gates."""

import hashlib
from pathlib import Path

from modelserve.dataset import CATEGORICAL_COLUMNS, NUMERIC_COLUMNS
from modelserve.quality_gates import evaluate_candidate_gates


def create_valid_manifest_and_artifact(version_dir: Path, version: str = "telco-churn-candidate") -> dict:
    version_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = version_dir / "model.joblib"
    content = b"valid_serialized_scikit_learn_pipeline_content"
    artifact_path.write_bytes(content)
    sha256 = hashlib.sha256(content).hexdigest()

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
        "feature_columns": list(NUMERIC_COLUMNS) + list(CATEGORICAL_COLUMNS),
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
    return manifest


def test_quality_gates_pass_for_healthy_candidate(tmp_path: Path):
    version_dir = tmp_path / "telco-churn-cand-01"
    manifest = create_valid_manifest_and_artifact(version_dir)

    result = evaluate_candidate_gates(manifest, version_dir)
    assert result.eligible is True
    assert result.candidate_version == "telco-churn-candidate"
    assert all(check.passed for check in result.checks)


def test_quality_gates_fail_on_sha256_mismatch(tmp_path: Path):
    version_dir = tmp_path / "telco-churn-cand-tampered"
    manifest = create_valid_manifest_and_artifact(version_dir)
    manifest["artifact_sha256"] = "wrong_hash_00000000000000000000000000000000000000000000000000000000"

    result = evaluate_candidate_gates(manifest, version_dir)
    assert result.eligible is False
    failed = [c for c in result.checks if not c.passed]
    assert any(c.name == "cryptographic_integrity_check" for c in failed)


def test_quality_gates_fail_when_pr_auc_below_minimum(tmp_path: Path):
    version_dir = tmp_path / "telco-churn-cand-low-prauc"
    manifest = create_valid_manifest_and_artifact(version_dir)
    # Set PR-AUC to 0.40, below 0.55 threshold
    manifest["validation_metrics"]["logistic_regression"]["pr_auc_average_precision"] = 0.40

    result = evaluate_candidate_gates(manifest, version_dir, min_val_pr_auc=0.55)
    assert result.eligible is False
    failed = [c for c in result.checks if not c.passed]
    assert any(c.name == "minimum_performance_gate" for c in failed)


def test_quality_gates_fail_on_excessive_regression(tmp_path: Path):
    version_dir = tmp_path / "telco-churn-cand-regressed"
    manifest = create_valid_manifest_and_artifact(version_dir)
    manifest["validation_metrics"]["logistic_regression"]["pr_auc_average_precision"] = 0.56

    active_manifest = {
        "artifact_version": "telco-churn-active",
        "selected_model": "logistic_regression",
        "validation_metrics": {
            "logistic_regression": {
                "pr_auc_average_precision": 0.62,
            }
        },
    }

    # Regression is 0.62 - 0.56 = 0.06 > max_allowed_regression 0.03
    result = evaluate_candidate_gates(
        manifest, version_dir, active_manifest=active_manifest, max_allowed_regression=0.03
    )
    assert result.eligible is False
    failed = [c for c in result.checks if not c.passed]
    assert any(c.name == "regression_tolerance_check" for c in failed)


def test_quality_gates_fail_on_schema_drift(tmp_path: Path):
    version_dir = tmp_path / "telco-churn-cand-schema-drift"
    manifest = create_valid_manifest_and_artifact(version_dir)
    # Remove MonthlyCharges from schema
    manifest["feature_schema"]["numeric"] = ["tenure", "TotalCharges"]

    result = evaluate_candidate_gates(manifest, version_dir)
    assert result.eligible is False
    failed = [c for c in result.checks if not c.passed]
    assert any(c.name == "schema_compatibility_check" for c in failed)


def test_quality_gates_fail_for_retired_candidate(tmp_path: Path):
    version_dir = tmp_path / "telco-churn-cand-retired"
    manifest = create_valid_manifest_and_artifact(version_dir)

    result = evaluate_candidate_gates(manifest, version_dir, is_retired=True)
    assert result.eligible is False
    failed = [c for c in result.checks if not c.passed]
    assert any(c.name == "lifecycle_stage_check" for c in failed)


def test_quality_gates_fail_for_dummy_prior(tmp_path: Path):
    version_dir = tmp_path / "telco-churn-cand-dummy"
    manifest = create_valid_manifest_and_artifact(version_dir)
    manifest["selected_model"] = "dummy_prior"

    result = evaluate_candidate_gates(manifest, version_dir)
    assert result.eligible is False
    failed = [c for c in result.checks if not c.passed]
    assert any(c.name == "deployable_model_check" for c in failed)

