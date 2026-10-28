"""Tests for the reproducible model preparation module."""

from __future__ import annotations

import pandas as pd
import pytest

from modelserve.dataset import EXPECTED_COLUMNS
from modelserve.model_loader import load_active_model
from modelserve.model_preparation import prepare_model


def _make_synthetic_dataframe(rows: int = 120) -> pd.DataFrame:
    """Generate a reproducible, valid synthetic dataset conforming to the Telco schema."""
    result: dict[str, list[object]] = {}
    numeric = {"SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"}
    for column in EXPECTED_COLUMNS:
        if column in numeric:
            result[column] = [float((index * 13) % 97 + 1) for index in range(rows)]
        elif column == "customerID":
            result[column] = [f"TEST-{index:05d}" for index in range(rows)]
        elif column == "Churn":
            result[column] = ["Yes" if index % 2 == 0 else "No" for index in range(rows)]
        elif column == "gender":
            result[column] = ["Female" if index % 2 == 0 else "Male" for index in range(rows)]
        elif column == "Contract":
            contracts = ["Month-to-month", "One year", "Two year"]
            result[column] = [contracts[index % 3] for index in range(rows)]
        elif column == "PaymentMethod":
            methods = [
                "Electronic check",
                "Mailed check",
                "Bank transfer (automatic)",
                "Credit card (automatic)",
            ]
            result[column] = [methods[index % 4] for index in range(rows)]
        elif column == "InternetService":
            services = ["DSL", "Fiber optic", "No"]
            result[column] = [services[index % 3] for index in range(rows)]
        else:
            result[column] = ["Yes" if index % 2 == 0 else "No" for index in range(rows)]
    return pd.DataFrame(result)


def test_prepare_model_reproducible_run(tmp_path) -> None:
    # Generate synthetic CSV file mimicking raw IBM CSV
    df = _make_synthetic_dataframe(rows=120)
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
