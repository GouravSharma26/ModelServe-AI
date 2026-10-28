"""Tests for model loader integrity verification and error handling."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import pytest

from modelserve.model_loader import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactValidationError,
    load_active_model,
)

SAMPLE_FEATURES = {
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


def test_load_active_model_success():
    """Verify loading from valid artifacts/models directory."""
    model = load_active_model(Path("artifacts/models"))
    assert model.name == "logistic_regression"
    assert model.version.startswith("telco-churn-")
    assert model.positive_label == "Yes"
    assert "MonthlyCharges" in model.feature_columns

    # Test prediction
    df = pd.DataFrame([SAMPLE_FEATURES])
    label, score = model.predict(df)
    assert label in ("Yes", "No")
    assert 0.0 <= score <= 1.0


def test_load_active_model_nonexistent_dir(tmp_path: Path):
    """Missing directory raises ArtifactNotFoundError."""
    with pytest.raises(ArtifactNotFoundError, match="does not exist"):
        load_active_model(tmp_path / "does_not_exist")


def test_load_active_model_empty_dir(tmp_path: Path):
    """Directory with no valid model version raises ArtifactNotFoundError."""
    empty_dir = tmp_path / "empty_models"
    empty_dir.mkdir()
    with pytest.raises(ArtifactNotFoundError, match="No valid model versions"):
        load_active_model(empty_dir)


def test_load_active_model_missing_manifest_fields(tmp_path: Path):
    """Manifest missing essential keys raises ArtifactValidationError."""
    version_dir = tmp_path / "models" / "v1"
    version_dir.mkdir(parents=True)
    (version_dir / "manifest.json").write_text(json.dumps({"invalid": True}))

    with pytest.raises(ArtifactValidationError, match="missing required field"):
        load_active_model(tmp_path / "models")


def test_load_active_model_tampered_artifact_fails_integrity(tmp_path: Path):
    """Tampered artifact file triggers ArtifactIntegrityError."""
    # Copy valid manifest and artifact into tmp_path
    source_dir = Path("artifacts/models").iterdir()
    valid_version_dir = next(p for p in source_dir if p.is_dir() and (p / "manifest.json").exists())

    test_models = tmp_path / "models"
    test_version = test_models / "tampered-version"
    test_version.mkdir(parents=True)

    manifest_content = (valid_version_dir / "manifest.json").read_text(encoding="utf-8")
    (test_version / "manifest.json").write_text(manifest_content, encoding="utf-8")

    # Write corrupt data into model.joblib
    (test_version / "model.joblib").write_bytes(b"TAMPERED_MALICIOUS_BYTES")

    with pytest.raises(ArtifactIntegrityError, match="checksum verification failed"):
        load_active_model(test_models)


def test_load_active_model_non_pipeline_object(tmp_path: Path):
    """An artifact containing an arbitrary non-Pipeline object is rejected."""
    test_models = tmp_path / "models"
    test_version = test_models / "non-pipeline-version"
    test_version.mkdir(parents=True)

    artifact_file = test_version / "model.joblib"
    joblib.dump({"not": "a pipeline"}, artifact_file)

    import hashlib
    digest = hashlib.sha256(artifact_file.read_bytes()).hexdigest()

    manifest = {
        "artifact_version": "non-pipeline-version",
        "artifact_file": "model.joblib",
        "artifact_sha256": digest,
        "feature_columns": ["col1"],
        "positive_label": "Yes",
    }
    (test_version / "manifest.json").write_text(json.dumps(manifest))

    with pytest.raises(ArtifactValidationError, match="expected sklearn.pipeline.Pipeline"):
        load_active_model(test_models)

