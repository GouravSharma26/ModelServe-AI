"""Trusted model loader with provenance, schema validation, and SHA-256 integrity verification."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

logger = logging.getLogger("modelserve.loader")


class ArtifactError(Exception):
    """Base exception for model artifact resolution or validation errors."""


class ArtifactNotFoundError(ArtifactError):
    """Raised when the specified model version or manifest directory cannot be found."""


class ArtifactIntegrityError(ArtifactError):
    """Raised when an artifact checksum does not match its manifest specification."""


class ArtifactValidationError(ArtifactError):
    """Raised when artifact contents or manifest structure fail schema validation."""


@dataclass(frozen=True)
class LoadedModel:
    """Immutable loaded model instance with validated manifest and metadata."""

    pipeline: Pipeline
    manifest: dict[str, Any]
    version: str
    name: str
    positive_label: str
    feature_columns: list[str]
    score_interpretation: str

    def predict(self, features_df: pd.DataFrame) -> tuple[str, float]:
        """Generate prediction label and confidence score for a single observation.

        Returns (label, score).
        """
        ordered_features = features_df[self.feature_columns]
        prediction_arr = self.pipeline.predict(ordered_features)
        label = str(prediction_arr[0])

        if hasattr(self.pipeline, "predict_proba"):
            classes = list(getattr(self.pipeline, "classes_", []))
            if self.positive_label in classes:
                pos_idx = classes.index(self.positive_label)
                proba_arr = self.pipeline.predict_proba(ordered_features)
                score = float(proba_arr[0][pos_idx])
            else:
                score = 1.0 if label == self.positive_label else 0.0
        else:
            score = 1.0 if label == self.positive_label else 0.0

        return label, score


def _compute_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_latest_version(artifacts_dir: Path) -> Path:
    """Locate the latest model version directory containing manifest.json."""
    if not artifacts_dir.exists():
        raise ArtifactNotFoundError(f"Artifacts directory does not exist: {artifacts_dir}")

    candidates = [
        p for p in artifacts_dir.iterdir()
        if p.is_dir() and (p / "manifest.json").exists()
    ]
    if not candidates:
        raise ArtifactNotFoundError(
            f"No valid model versions with manifest.json found in {artifacts_dir}"
        )

    candidates.sort(key=lambda p: p.name)
    return candidates[-1]


def _validate_manifest_strict(manifest: dict[str, Any], version_dir: Path) -> Path:
    """Strictly validate manifest contents, rejecting path traversal, absolute paths, and malformed schemas."""
    if not isinstance(manifest, dict):
        raise ArtifactValidationError("Manifest root must be a JSON object")

    required_keys = (
        "artifact_version",
        "artifact_file",
        "artifact_sha256",
        "feature_columns",
        "positive_label",
        "feature_schema",
    )
    for key in required_keys:
        if key not in manifest:
            raise ArtifactValidationError(
                f"Manifest is missing required field '{key}' in {version_dir}"
            )

    declared_version = manifest["artifact_version"]
    if not isinstance(declared_version, str) or not declared_version:
        raise ArtifactValidationError("Manifest 'artifact_version' must be a non-empty string")
    if declared_version != version_dir.name:
        raise ArtifactValidationError(
            f"Mismatched artifact version: manifest declares '{declared_version}' "
            f"but directory is '{version_dir.name}'"
        )
    if "/" in declared_version or "\\" in declared_version or ".." in declared_version:
        raise ArtifactValidationError("Manifest 'artifact_version' contains invalid path characters")

    artifact_filename = manifest["artifact_file"]
    if not isinstance(artifact_filename, str) or not artifact_filename.strip():
        raise ArtifactValidationError("Manifest 'artifact_file' must be a non-empty string")

    # Reject absolute paths, path traversal, or nested directory components
    if "/" in artifact_filename or "\\" in artifact_filename or ".." in artifact_filename:
        raise ArtifactValidationError(
            f"Manifest 'artifact_file' ('{artifact_filename}') contains illegal path traversal or separators"
        )

    path_obj = Path(artifact_filename)
    if path_obj.is_absolute() or path_obj.name != artifact_filename:
        raise ArtifactValidationError(
            f"Manifest 'artifact_file' ('{artifact_filename}') must be a bare relative filename"
        )

    # Validate sha256 format
    sha256 = manifest["artifact_sha256"]
    if not isinstance(sha256, str) or len(sha256) != 64 or not all(c in "0123456789abcdefABCDEF" for c in sha256):
        raise ArtifactValidationError(
            f"Manifest 'artifact_sha256' is not a valid 64-character hexadecimal SHA-256 digest"
        )

    # Validate feature_schema
    feature_schema = manifest["feature_schema"]
    if not isinstance(feature_schema, dict) or "numeric" not in feature_schema or "categorical" not in feature_schema:
        raise ArtifactValidationError(
            "Manifest 'feature_schema' must be a dictionary containing 'numeric' and 'categorical' lists"
        )
    if not isinstance(feature_schema["numeric"], list) or not isinstance(feature_schema["categorical"], list):
        raise ArtifactValidationError(
            "Manifest 'feature_schema' 'numeric' and 'categorical' fields must be lists"
        )

    # Ensure resolved path is directly inside version_dir
    artifact_path = (version_dir / artifact_filename).resolve()
    try:
        artifact_path.relative_to(version_dir.resolve())
    except ValueError:
        raise ArtifactValidationError(
            f"Manifest 'artifact_file' escapes version directory: {artifact_filename}"
        )

    if artifact_path.parent != version_dir.resolve():
        raise ArtifactValidationError(
            f"Manifest 'artifact_file' must reside directly in version directory: {artifact_filename}"
        )

    return artifact_path


def load_active_model(artifacts_dir: Path, version: str | None = None) -> LoadedModel:
    """Load and verify a model artifact from its version directory.

    Performs full integrity validation:
      1. Manifest existence and strict schema structure.
      2. Path traversal and absolute path rejection.
      3. Artifact file existence.
      4. SHA-256 verification against the manifest checksum.
      5. Safe deserialization of Scikit-Learn Pipeline.
      6. Pipeline type and interface verification.
    """
    if version:
        version_dir = artifacts_dir / version
        if not version_dir.exists() or not (version_dir / "manifest.json").exists():
            raise ArtifactNotFoundError(
                f"Model version '{version}' not found in {artifacts_dir}"
            )
    else:
        version_dir = find_latest_version(artifacts_dir)

    manifest_path = version_dir / "manifest.json"
    try:
        manifest_raw = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(manifest_raw)
    except Exception as exc:
        raise ArtifactValidationError(
            f"Failed to read or parse manifest.json in {version_dir}: {exc}"
        ) from exc

    # Strictly validate manifest and get safe artifact path
    artifact_path = _validate_manifest_strict(manifest, version_dir)

    if not artifact_path.exists():
        raise ArtifactNotFoundError(
            f"Artifact file '{artifact_path.name}' listed in manifest does not exist in {version_dir}"
        )

    # Cryptographic integrity verification
    expected_sha256 = manifest["artifact_sha256"].lower()
    actual_sha256 = _compute_sha256(artifact_path).lower()
    if actual_sha256 != expected_sha256:
        raise ArtifactIntegrityError(
            f"Artifact checksum verification failed for {artifact_path.name}. "
            f"Expected SHA-256: {expected_sha256}, got: {actual_sha256}"
        )

    # Deserialization of trusted artifact
    try:
        pipeline = joblib.load(artifact_path)
    except Exception as exc:
        raise ArtifactValidationError(
            f"Failed to load joblib pipeline from {artifact_path}: {exc}"
        ) from exc

    if not isinstance(pipeline, Pipeline):
        raise ArtifactValidationError(
            f"Loaded model is of type {type(pipeline).__name__}, expected sklearn.pipeline.Pipeline"
        )

    if not hasattr(pipeline, "predict"):
        raise ArtifactValidationError("Loaded model pipeline does not implement 'predict' method")

    logger.info(
        "Successfully verified and loaded model version %s (SHA-256: %s...)",
        manifest["artifact_version"],
        actual_sha256[:12],
    )

    return LoadedModel(
        pipeline=pipeline,
        manifest=manifest,
        version=manifest["artifact_version"],
        name=manifest.get("selected_model", "customer-churn-classifier"),
        positive_label=manifest["positive_label"],
        feature_columns=list(manifest["feature_columns"]),
        score_interpretation=manifest.get(
            "score_interpretation", "Model score; probabilities have not been calibrated."
        ),
    )
