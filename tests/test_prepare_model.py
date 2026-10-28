"""Tests for the reproducible model preparation script."""

from __future__ import annotations

import pandas as pd
import pytest

from modelserve.model_loader import load_active_model
from modelserve.model_preparation import prepare_model
from tests.conftest import make_test_dataframe


def test_prepare_model_reproducible_run(tmp_path) -> None:
    # Generate synthetic CSV file mimicking raw IBM CSV
    df = make_test_dataframe(rows=120)
    csv_file = tmp_path / "sample_telco.csv"
    df.to_csv(csv_file, index=False)

    models_dir = tmp_path / "artifacts" / "models"
    manifest = prepare_model(output_dir=models_dir, data_path=csv_file, seed=42)

    version = manifest["artifact_version"]
    assert version.startswith("telco-churn-")
    assert manifest["selected_model"] in ("logistic_regression", "random_forest")

    # Verify that files are present on disk
    version_dir = models_dir / version
    assert (version_dir / "manifest.json").exists()
    assert (version_dir / "evaluation.json").exists()
    assert (version_dir / "model.joblib").exists()

    # Verify loading through model_loader
    loaded = load_active_model(artifacts_dir=models_dir, version=version)
    assert loaded.version == version
    assert loaded.name == manifest["selected_model"]

    # Test single-record inference
    sample_feat = df.drop(columns=["Churn", "customerID"]).iloc[[0]]
    label, score = loaded.predict(sample_feat)
    assert label in ("Yes", "No")
    assert 0.0 <= score <= 1.0

