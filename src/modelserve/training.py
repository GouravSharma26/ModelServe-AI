"""Reproducible training, evaluation, and trusted artifact creation."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from modelserve.dataset import (
    CATEGORICAL_COLUMNS,
    EXCLUDED_FEATURES,
    NUMERIC_COLUMNS,
    TARGET_COLUMN,
    load_dataset,
)

RANDOM_SEED = 42
POSITIVE_LABEL = "Yes"
SPLIT_POLICY = {"train": 0.60, "validation": 0.20, "test": 0.20}


def make_preprocessor() -> ColumnTransformer:
    """Build fresh transformers; callers fit them only within training pipelines."""
    numeric = Pipeline(
        steps=[("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
    )
    categorical = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric, list(NUMERIC_COLUMNS)),
            ("categorical", categorical, list(CATEGORICAL_COLUMNS)),
        ],
        remainder="drop",
    )


def make_candidates(seed: int = RANDOM_SEED) -> dict[str, Pipeline]:
    """Return the baseline and two fixed candidates with documented seeds."""
    models = {
        "dummy_prior": DummyClassifier(strategy="prior"),
        "logistic_regression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=seed
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=160,
            min_samples_leaf=3,
            class_weight="balanced_subsample",
            random_state=seed,
            n_jobs=-1,
        ),
    }
    return {
        name: Pipeline([("preprocess", make_preprocessor()), ("classifier", model)])
        for name, model in models.items()
    }


def _metrics(model: Pipeline, features: pd.DataFrame, labels: pd.Series) -> dict[str, Any]:
    predictions = model.predict(features)
    positive_index = list(model.classes_).index(POSITIVE_LABEL)
    scores = model.predict_proba(features)[:, positive_index]
    matrix = confusion_matrix(labels, predictions, labels=["No", "Yes"])
    return {
        "precision": float(np.clip(precision_score(labels, predictions, pos_label=POSITIVE_LABEL, zero_division=0), 0, 1)),
        "recall": float(np.clip(recall_score(labels, predictions, pos_label=POSITIVE_LABEL, zero_division=0), 0, 1)),
        "f1": float(np.clip(f1_score(labels, predictions, pos_label=POSITIVE_LABEL, zero_division=0), 0, 1)),
        "roc_auc": float(np.clip(roc_auc_score(labels == POSITIVE_LABEL, scores), 0, 1)),
        "pr_auc_average_precision": float(np.clip(average_precision_score(labels == POSITIVE_LABEL, scores), 0, 1)),
        "confusion_matrix": matrix.tolist(),
        "confusion_matrix_labels": ["No", "Yes"],
        "decision_threshold": 0.5,
        "threshold_policy": "classifier default at 0.5; not tuned on test data",
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for block in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def train(
    frame: pd.DataFrame,
    dataset_sha256: str,
    output_dir: Path,
    *,
    seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    """Train candidates, choose by validation PR-AUC/F1, test once, save outputs."""
    x = frame.drop(columns=[TARGET_COLUMN, *EXCLUDED_FEATURES])
    y = frame[TARGET_COLUMN].astype(str).str.strip()
    x_train, x_temp, y_train, y_temp = train_test_split(
        x, y, test_size=0.40, stratify=y, random_state=seed
    )
    x_validation, x_test, y_validation, y_test = train_test_split(
        x_temp, y_temp, test_size=0.50, stratify=y_temp, random_state=seed
    )

    candidates = make_candidates(seed)
    validation_results: dict[str, dict[str, Any]] = {}
    for name, candidate in candidates.items():
        candidate.fit(x_train, y_train)
        validation_results[name] = _metrics(candidate, x_validation, y_validation)

    # Selection rule fixed before test evaluation: highest validation average precision,
    # then highest validation F1. The dummy model is reported but never deployable.
    deployable = [name for name in candidates if name != "dummy_prior"]
    selected_name = max(
        deployable,
        key=lambda name: (
            validation_results[name]["pr_auc_average_precision"],
            validation_results[name]["f1"],
        ),
    )
    selected = candidates[selected_name]
    test_metrics = _metrics(selected, x_test, y_test)

    version = "telco-churn-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    version_dir = output_dir / version
    version_dir.mkdir(parents=True, exist_ok=False)
    artifact_path = version_dir / "model.joblib"
    joblib.dump(selected, artifact_path, compress=3)
    manifest = {
        "artifact_version": version,
        "artifact_directory": version,
        "artifact_file": artifact_path.name,
        "artifact_sha256": _sha256(artifact_path),
        "dataset": {
            "name": "IBM Telco Customer Churn sample, Telco-Customer-Churn.csv",
            "source": "https://github.com/IBM/telco-customer-churn-on-icp4d",
            "license": "Apache-2.0",
            "sha256": dataset_sha256,
            "rows": int(len(frame)),
        },
        "target": TARGET_COLUMN,
        "positive_label": POSITIVE_LABEL,
        "feature_columns": list(x.columns),
        "excluded_features": list(EXCLUDED_FEATURES),
        "feature_schema": {
            "numeric": list(NUMERIC_COLUMNS),
            "categorical": list(CATEGORICAL_COLUMNS),
        },
        "split": {
            **SPLIT_POLICY,
            "strategy": "two-stage stratified random split",
            "random_seed": seed,
            "selection_rule": "validation average precision, then validation F1; test evaluated once",
        },
        "selected_model": selected_name,
        "validation_metrics": validation_results,
        "test_metrics": test_metrics,
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "created_at_utc": datetime.now(UTC).isoformat(),
        "score_interpretation": "Model score; probabilities have not been calibrated.",
    }
    (version_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (version_dir / "evaluation.json").write_text(
        json.dumps(manifest["test_metrics"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate ModelServe AI classifiers")
    parser.add_argument("--data", type=Path, help="Local Telco-Customer-Churn.csv; downloads IBM's source CSV when omitted")
    parser.add_argument("--output", type=Path, default=Path("artifacts/models"), help="Directory under which a new immutable version folder is created")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()
    try:
        frame, fingerprint = load_dataset(args.data)
    except ValueError as exc:
        parser.error(str(exc))
    manifest = train(frame, fingerprint, args.output, seed=args.seed)
    version_dir = args.output / manifest["artifact_directory"]
    print(json.dumps({
        "artifact_version": manifest["artifact_version"],
        "selected_model": manifest["selected_model"],
        "artifact": str(version_dir / manifest["artifact_file"]),
        "manifest": str(version_dir / "manifest.json"),
        "test_metrics": manifest["test_metrics"],
    }, indent=2))


if __name__ == "__main__":
    main()
