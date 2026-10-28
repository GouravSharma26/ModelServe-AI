"""Shared test fixtures for reproducible ModelServe AI testing."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from modelserve.app import create_app
from modelserve.dataset import EXPECTED_COLUMNS
from modelserve.settings import Settings
from modelserve.training import train


def make_test_dataframe(rows: int = 60) -> pd.DataFrame:
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


@pytest.fixture(scope="session")
def isolated_artifacts_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate an isolated, genuine model artifact without downloading external data."""
    output_dir = tmp_path_factory.mktemp("test_artifacts")
    frame = make_test_dataframe(60)
    train(frame, "mock_dataset_sha256_for_testing", output_dir, seed=42)
    return output_dir


@pytest.fixture
def client(isolated_artifacts_dir: Path) -> Generator[TestClient, None, None]:
    """TestClient using the isolated session artifact directory."""
    settings = Settings(artifacts_dir=isolated_artifacts_dir)
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_features() -> dict[str, object]:
    """Valid feature dictionary matching the 19 expected input columns."""
    return {
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

