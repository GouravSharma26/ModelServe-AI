from __future__ import annotations

import hashlib
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from modelserve.dataset import EXPECTED_COLUMNS, NUMERIC_COLUMNS
from modelserve.training import RANDOM_SEED, train


def synthetic_dataset(rows: int = 300) -> pd.DataFrame:
    result: dict[str, list[object]] = {}
    numeric = {"SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"}
    for column in EXPECTED_COLUMNS:
        if column in numeric:
            result[column] = [float((index * 7) % 83 + 1) for index in range(rows)]
        elif column == "customerID":
            result[column] = [f"ID-{index:05d}" for index in range(rows)]
        elif column == "Churn":
            result[column] = ["Yes" if index % 3 == 0 else "No" for index in range(rows)]
        else:
            result[column] = ["blue" if index % 3 else "gold" for index in range(rows)]
    return pd.DataFrame(result)


def test_training_writes_real_metrics_and_integrity_manifest(tmp_path) -> None:
    manifest = train(synthetic_dataset(), "a" * 64, tmp_path)

    assert manifest["split"]["random_seed"] == RANDOM_SEED
    assert manifest["split"]["train"] == 0.60
    assert manifest["selected_model"] in {"logistic_regression", "random_forest"}
    assert "customerID" not in manifest["feature_columns"]
    assert set(manifest["validation_metrics"]) == {
        "dummy_prior",
        "logistic_regression",
        "random_forest",
    }
    for metric in ("precision", "recall", "f1", "roc_auc", "pr_auc_average_precision"):
        assert 0.0 <= manifest["test_metrics"][metric] <= 1.0
    assert manifest["test_metrics"]["confusion_matrix_labels"] == ["No", "Yes"]
    assert len(manifest["test_metrics"]["confusion_matrix"]) == 2

    version_dir = tmp_path / manifest["artifact_directory"]
    artifact_path = version_dir / manifest["artifact_file"]
    assert hashlib.sha256(artifact_path.read_bytes()).hexdigest() == manifest["artifact_sha256"]
    assert json.loads((version_dir / "manifest.json").read_text()) == manifest
    assert json.loads((version_dir / "evaluation.json").read_text()) == manifest["test_metrics"]

    loaded = joblib.load(artifact_path)
    frame = synthetic_dataset()
    features = frame.drop(columns=["Churn", "customerID"])
    assert loaded.predict(features).shape == (300,)

    # The fitted scaler statistics must equal the training-partition statistics,
    # proving test/validation records were not used when preprocessing was fitted.
    x_train, _, _, _ = train_test_split(
        features, frame["Churn"], test_size=0.40, stratify=frame["Churn"], random_state=RANDOM_SEED
    )
    scaler = loaded.named_steps["preprocess"].named_transformers_["numeric"].named_steps["scale"]
    np.testing.assert_allclose(scaler.mean_, x_train[list(NUMERIC_COLUMNS)].mean().to_numpy())


def test_training_is_repeatable_for_same_seed(tmp_path) -> None:
    first = train(synthetic_dataset(), "b" * 64, tmp_path / "first", seed=17)
    second = train(synthetic_dataset(), "b" * 64, tmp_path / "second", seed=17)
    assert first["selected_model"] == second["selected_model"]
    assert first["validation_metrics"] == second["validation_metrics"]
    assert first["test_metrics"] == second["test_metrics"]
