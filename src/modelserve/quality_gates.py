"""Deterministic quality gates for ModelServe AI promotion eligibility.

Evaluates artifact existence, manifest schema validity, cryptographic SHA-256 integrity,
feature schema stability, finite metric bounds, PR-AUC baseline thresholds, and regression tolerances.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from modelserve.dataset import CATEGORICAL_COLUMNS, NUMERIC_COLUMNS

DEFAULT_MIN_VAL_PR_AUC = 0.55
DEFAULT_MAX_ALLOWED_PR_AUC_REGRESSION = 0.03


@dataclass(frozen=True)
class GateCheck:
    """Individual quality gate check result."""

    name: str
    passed: bool
    message: str
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class QualityGateResult:
    """Aggregated quality gate evaluation for a model promotion candidate."""

    eligible: bool
    candidate_version: str
    active_version: str | None
    checks: list[GateCheck]

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "candidate_version": self.candidate_version,
            "active_version": self.active_version,
            "passed_count": sum(1 for c in self.checks if c.passed),
            "failed_count": sum(1 for c in self.checks if not c.passed),
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "details": c.details or {},
                }
                for c in self.checks
            ],
        }


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_candidate_gates(
    manifest: dict[str, Any],
    version_dir: Path,
    active_manifest: dict[str, Any] | None = None,
    *,
    min_val_pr_auc: float = DEFAULT_MIN_VAL_PR_AUC,
    max_allowed_regression: float = DEFAULT_MAX_ALLOWED_PR_AUC_REGRESSION,
    is_retired: bool = False,
) -> QualityGateResult:
    """Evaluate deterministic promotion quality gates for a model candidate against the active model."""
    checks: list[GateCheck] = []
    candidate_version = manifest.get("artifact_version", version_dir.name)
    active_version = active_manifest.get("artifact_version") if active_manifest else None

    # Gate 1: Candidate is not marked as retired
    if is_retired:
        checks.append(GateCheck(
            name="lifecycle_stage_check",
            passed=False,
            message=f"Model version '{candidate_version}' is marked as retired and cannot be promoted.",
        ))
    else:
        checks.append(GateCheck(
            name="lifecycle_stage_check",
            passed=True,
            message="Candidate is not retired.",
        ))

    # Gate 2: Deployable candidate check (exclude dummy prior)
    selected_model = manifest.get("selected_model", "")
    if selected_model == "dummy_prior" or not selected_model:
        checks.append(GateCheck(
            name="deployable_model_check",
            passed=False,
            message=f"Model '{selected_model}' is a non-deployable baseline.",
        ))
    else:
        checks.append(GateCheck(
            name="deployable_model_check",
            passed=True,
            message=f"Candidate algorithm '{selected_model}' is deployable.",
        ))

    # Gate 3: Artifact directory and file existence
    artifact_file = manifest.get("artifact_file", "model.joblib")
    artifact_path = version_dir / artifact_file
    if not version_dir.is_dir() or not artifact_path.is_file():
        checks.append(GateCheck(
            name="artifact_existence_check",
            passed=False,
            message=f"Artifact file '{artifact_path}' does not exist.",
        ))
    else:
        checks.append(GateCheck(
            name="artifact_existence_check",
            passed=True,
            message="Artifact file exists and is accessible.",
        ))

    # Gate 4: Cryptographic SHA-256 integrity verification
    manifest_sha256 = str(manifest.get("artifact_sha256", "")).lower()
    if artifact_path.is_file():
        actual_sha256 = _compute_sha256(artifact_path).lower()
        if manifest_sha256 and manifest_sha256 == actual_sha256:
            checks.append(GateCheck(
                name="cryptographic_integrity_check",
                passed=True,
                message="SHA-256 integrity matches manifest specification.",
                details={"expected": manifest_sha256, "actual": actual_sha256},
            ))
        else:
            checks.append(GateCheck(
                name="cryptographic_integrity_check",
                passed=False,
                message=f"SHA-256 checksum mismatch (expected {manifest_sha256}, got {actual_sha256}).",
                details={"expected": manifest_sha256, "actual": actual_sha256},
            ))
    else:
        checks.append(GateCheck(
            name="cryptographic_integrity_check",
            passed=False,
            message="Cannot verify checksum: artifact file missing.",
        ))

    # Gate 5: Feature schema compatibility
    feature_schema = manifest.get("feature_schema", {})
    cand_numeric = set(feature_schema.get("numeric", []))
    cand_categorical = set(feature_schema.get("categorical", []))
    expected_numeric = set(NUMERIC_COLUMNS)
    expected_categorical = set(CATEGORICAL_COLUMNS)

    schema_match = (cand_numeric == expected_numeric) and (cand_categorical == expected_categorical)
    if schema_match:
        checks.append(GateCheck(
            name="schema_compatibility_check",
            passed=True,
            message="Feature schema conforms to expected 19 model inputs without drift.",
        ))
    else:
        diff_num = list(cand_numeric.symmetric_difference(expected_numeric))
        diff_cat = list(cand_categorical.symmetric_difference(expected_categorical))
        checks.append(GateCheck(
            name="schema_compatibility_check",
            passed=False,
            message=f"Feature schema mismatch. Differences: numeric={diff_num}, categorical={diff_cat}",
            details={"diff_numeric": diff_num, "diff_categorical": diff_cat},
        ))

    # Gate 6: Dataset fingerprint check
    fingerprint = manifest.get("dataset", {}).get("sha256", "")
    if fingerprint and len(fingerprint) == 64 and all(c in "0123456789abcdefABCDEF" for c in fingerprint):
        checks.append(GateCheck(
            name="dataset_fingerprint_check",
            passed=True,
            message="Dataset cryptographic fingerprint recorded.",
            details={"dataset_fingerprint": fingerprint},
        ))
    else:
        checks.append(GateCheck(
            name="dataset_fingerprint_check",
            passed=False,
            message="Missing or invalid dataset fingerprint.",
        ))

    # Gate 7: Finite metric bounds validation
    val_metrics = manifest.get("validation_metrics", {}).get(selected_model, {})
    test_metrics = manifest.get("test_metrics", {})

    cand_val_pr_auc = val_metrics.get("pr_auc_average_precision")
    cand_val_f1 = val_metrics.get("f1")
    cand_test_pr_auc = test_metrics.get("pr_auc_average_precision")

    metrics_valid = True
    metric_errors = []
    for metric_name, metric_val in [
        ("val_pr_auc", cand_val_pr_auc),
        ("val_f1", cand_val_f1),
        ("test_pr_auc", cand_test_pr_auc),
    ]:
        if metric_val is None or not isinstance(metric_val, (int, float)) or math.isnan(metric_val) or math.isinf(metric_val):
            metrics_valid = False
            metric_errors.append(f"{metric_name} is non-finite or missing")
        elif not (0.0 <= metric_val <= 1.0):
            metrics_valid = False
            metric_errors.append(f"{metric_name} ({metric_val}) is outside [0.0, 1.0]")

    if metrics_valid:
        checks.append(GateCheck(
            name="metric_bounds_check",
            passed=True,
            message="All validation and test evaluation metrics are finite and within [0, 1].",
        ))
    else:
        checks.append(GateCheck(
            name="metric_bounds_check",
            passed=False,
            message=f"Metric validation failed: {', '.join(metric_errors)}",
        ))

    # Gate 8: Validation PR-AUC threshold
    if cand_val_pr_auc is not None and cand_val_pr_auc >= min_val_pr_auc:
        checks.append(GateCheck(
            name="minimum_performance_gate",
            passed=True,
            message=f"Validation PR-AUC ({cand_val_pr_auc:.4f}) meets minimum threshold ({min_val_pr_auc:.4f}).",
            details={"val_pr_auc": cand_val_pr_auc, "threshold": min_val_pr_auc},
        ))
    else:
        score_repr = f"{cand_val_pr_auc:.4f}" if isinstance(cand_val_pr_auc, (int, float)) else str(cand_val_pr_auc)
        checks.append(GateCheck(
            name="minimum_performance_gate",
            passed=False,
            message=f"Validation PR-AUC ({score_repr}) falls below required threshold ({min_val_pr_auc:.4f}).",
            details={"val_pr_auc": cand_val_pr_auc, "threshold": min_val_pr_auc},
        ))

    # Gate 9: Regression tolerance against active model
    if active_manifest:
        active_model = active_manifest.get("selected_model", "")
        active_val_pr_auc = active_manifest.get("validation_metrics", {}).get(active_model, {}).get("pr_auc_average_precision")
        if active_val_pr_auc is not None and cand_val_pr_auc is not None:
            regression = active_val_pr_auc - cand_val_pr_auc
            if regression <= max_allowed_regression:
                checks.append(GateCheck(
                    name="regression_tolerance_check",
                    passed=True,
                    message=f"Regression ({regression:.4f}) within allowed tolerance ({max_allowed_regression:.4f}).",
                    details={
                        "candidate_val_pr_auc": cand_val_pr_auc,
                        "active_val_pr_auc": active_val_pr_auc,
                        "regression": regression,
                        "max_allowed": max_allowed_regression,
                    },
                ))
            else:
                checks.append(GateCheck(
                    name="regression_tolerance_check",
                    passed=False,
                    message=f"Candidate suffers regression of {regression:.4f} vs active model (limit: {max_allowed_regression:.4f}).",
                    details={
                        "candidate_val_pr_auc": cand_val_pr_auc,
                        "active_val_pr_auc": active_val_pr_auc,
                        "regression": regression,
                        "max_allowed": max_allowed_regression,
                    },
                ))
        else:
            checks.append(GateCheck(
                name="regression_tolerance_check",
                passed=True,
                message="Active model metrics unavailable; regression check skipped.",
            ))
    else:
        checks.append(GateCheck(
            name="regression_tolerance_check",
            passed=True,
            message="No active model currently designated; candidate establishes baseline.",
        ))

    eligible = all(c.passed for c in checks)
    return QualityGateResult(
        eligible=eligible,
        candidate_version=candidate_version,
        active_version=active_version,
        checks=checks,
    )

