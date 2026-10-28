"""Tests for model loader integrity verification, strict manifest validation, and error handling."""

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


def test_load_active_model_success(isolated_artifacts_dir: Path, sample_features: dict[str, object]):
    """Verify loading from valid isolated test artifacts directory."""
    model = load_active_model(isolated_artifacts_dir)
    assert model.name in ("logistic_regression", "random_forest")
    assert model.version.startswith("telco-churn-")
    assert model.positive_label == "Yes"
    assert "MonthlyCharges" in model.feature_columns

    # Test prediction
    df = pd.DataFrame([sample_features])
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


def test_manifest_rejects_version_mismatch(tmp_path: Path):
    """Manifest declaring version different from directory name is rejected."""
    version_dir = tmp_path / "models" / "dir-version-1"
    version_dir.mkdir(parents=True)
    manifest = {
        "artifact_version": "different-version-2",
        "artifact_file": "model.joblib",
        "artifact_sha256": "a" * 64,
        "feature_columns": ["col1"],
        "positive_label": "Yes",
        "feature_schema": {"numeric": ["col1"], "categorical": []},
    }
    (version_dir / "manifest.json").write_text(json.dumps(manifest))

    with pytest.raises(ArtifactValidationError, match="Mismatched artifact version"):
        load_active_model(tmp_path / "models")


def test_manifest_rejects_absolute_artifact_path(tmp_path: Path):
    """Manifest specifying an absolute artifact path is rejected."""
    version_dir = tmp_path / "models" / "v1"
    version_dir.mkdir(parents=True)
    manifest = {
        "artifact_version": "v1",
        "artifact_file": "C:/Windows/System32/calc.exe" if Path("C:/").exists() else "/etc/passwd",
        "artifact_sha256": "a" * 64,
        "feature_columns": ["col1"],
        "positive_label": "Yes",
        "feature_schema": {"numeric": ["col1"], "categorical": []},
    }
    (version_dir / "manifest.json").write_text(json.dumps(manifest))

    with pytest.raises(ArtifactValidationError, match="illegal path traversal or separators|bare relative"):
        load_active_model(tmp_path / "models")


def test_manifest_rejects_path_traversal(tmp_path: Path):
    """Manifest attempting path traversal (../outside.joblib) is rejected."""
    version_dir = tmp_path / "models" / "v1"
    version_dir.mkdir(parents=True)
    manifest = {
        "artifact_version": "v1",
        "artifact_file": "../outside.joblib",
        "artifact_sha256": "a" * 64,
        "feature_columns": ["col1"],
        "positive_label": "Yes",
        "feature_schema": {"numeric": ["col1"], "categorical": []},
    }
    (version_dir / "manifest.json").write_text(json.dumps(manifest))

    with pytest.raises(ArtifactValidationError, match="illegal path traversal"):
        load_active_model(tmp_path / "models")


def test_manifest_rejects_invalid_sha256_format(tmp_path: Path):
    """Manifest with malformed sha256 (not 64-char hex) is rejected."""
    version_dir = tmp_path / "models" / "v1"
    version_dir.mkdir(parents=True)
    manifest = {
        "artifact_version": "v1",
        "artifact_file": "model.joblib",
        "artifact_sha256": "not-a-valid-hex-digest",
        "feature_columns": ["col1"],
        "positive_label": "Yes",
        "feature_schema": {"numeric": ["col1"], "categorical": []},
    }
    (version_dir / "manifest.json").write_text(json.dumps(manifest))

    with pytest.raises(ArtifactValidationError, match="valid 64-character hexadecimal"):
        load_active_model(tmp_path / "models")


def test_manifest_rejects_invalid_feature_schema(tmp_path: Path):
    """Manifest with malformed feature_schema (missing numeric/categorical) is rejected."""
    version_dir = tmp_path / "models" / "v1"
    version_dir.mkdir(parents=True)
    manifest = {
        "artifact_version": "v1",
        "artifact_file": "model.joblib",
        "artifact_sha256": "a" * 64,
        "feature_columns": ["col1"],
        "positive_label": "Yes",
        "feature_schema": "not-a-dict",
    }
    (version_dir / "manifest.json").write_text(json.dumps(manifest))

    with pytest.raises(ArtifactValidationError, match="must be a dictionary"):
        load_active_model(tmp_path / "models")


def test_load_active_model_tampered_artifact_fails_integrity(isolated_artifacts_dir: Path, tmp_path: Path):
    """Tampered artifact file triggers ArtifactIntegrityError."""
    source_version_dir = next(p for p in isolated_artifacts_dir.iterdir() if p.is_dir())

    test_models = tmp_path / "models"
    test_version = test_models / source_version_dir.name
    test_version.mkdir(parents=True)

    manifest_content = (source_version_dir / "manifest.json").read_text(encoding="utf-8")
    (test_version / "manifest.json").write_text(manifest_content, encoding="utf-8")

    # Write corrupt data into model.joblib
    (test_version / "model.joblib").write_bytes(b"TAMPERED_MALICIOUS_BYTES")

    with pytest.raises(ArtifactIntegrityError, match="checksum verification failed"):
        load_active_model(test_models)


def test_load_active_model_non_pipeline_object(tmp_path: Path):
    """An artifact containing an arbitrary non-Pipeline object is rejected."""
    test_models = tmp_path / "models"
    test_version = test_models / "v1"
    test_version.mkdir(parents=True)

    artifact_file = test_version / "model.joblib"
    joblib.dump({"not": "a pipeline"}, artifact_file)

    import hashlib
    digest = hashlib.sha256(artifact_file.read_bytes()).hexdigest()

    manifest = {
        "artifact_version": "v1",
        "artifact_file": "model.joblib",
        "artifact_sha256": digest,
        "feature_columns": ["col1"],
        "positive_label": "Yes",
        "feature_schema": {"numeric": ["col1"], "categorical": []},
    }
    (test_version / "manifest.json").write_text(json.dumps(manifest))

    with pytest.raises(ArtifactValidationError, match="expected sklearn.pipeline.Pipeline"):
        load_active_model(test_models)
