"""Loading and validating IBM's public Telco Customer Churn sample."""

from __future__ import annotations

import hashlib
import io
import urllib.request
from pathlib import Path

import pandas as pd

DATASET_URL = "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv"
EXPECTED_COLUMNS = (
    "customerID", "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
    "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
    "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod", "MonthlyCharges", "TotalCharges", "Churn",
)
TARGET_COLUMN = "Churn"
EXCLUDED_FEATURES = ("customerID",)
NUMERIC_COLUMNS = ("SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges")
CATEGORICAL_COLUMNS = tuple(
    column
    for column in EXPECTED_COLUMNS
    if column not in (*NUMERIC_COLUMNS, TARGET_COLUMN, *EXCLUDED_FEATURES)
)


class DatasetValidationError(ValueError):
    """Raised when input data does not match the documented source schema."""


def _validate_columns(frame: pd.DataFrame) -> None:
    expected = set(EXPECTED_COLUMNS)
    actual = set(frame.columns)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra or len(frame.columns) != len(EXPECTED_COLUMNS):
        details = []
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected columns: {', '.join(extra)}")
        raise DatasetValidationError("Invalid Telco Churn schema (" + "; ".join(details) + ")")


def _parse_csv(content: bytes) -> pd.DataFrame:
    try:
        frame = pd.read_csv(io.BytesIO(content))
    except pd.errors.EmptyDataError as exc:
        raise DatasetValidationError("Dataset contains no data or headers") from exc
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise DatasetValidationError("Dataset is not a readable comma-delimited CSV") from exc
    except Exception as exc:
        raise DatasetValidationError(f"Failed to read CSV content: {exc}") from exc

    frame.columns = [str(column).strip() for column in frame.columns]

    # Validate column presence before accessing individual columns
    _validate_columns(frame)

    for column in NUMERIC_COLUMNS:
        series = frame[column]
        if series.dtype == object or pd.api.types.is_string_dtype(series):
            cleaned = series.astype(str).str.strip().replace("", float("nan"))
        else:
            cleaned = series
        converted = pd.to_numeric(cleaned, errors="coerce")
        malformed = cleaned.notna() & converted.isna()
        if malformed.any():
            raise DatasetValidationError(f"Column '{column}' must contain numeric values")
        frame[column] = converted

    validate_dataset(frame)
    return frame


def validate_dataset(frame: pd.DataFrame) -> None:
    """Validate the exact source schema, required fields, and binary target."""
    _validate_columns(frame)
    if frame.empty:
        raise DatasetValidationError("Dataset contains no rows")
    allowed_missing = {"TotalCharges"}
    required_columns = [column for column in frame.columns if column not in allowed_missing]
    if frame[required_columns].isna().any().any():
        raise DatasetValidationError("Dataset contains missing values in required columns")
    labels = set(frame[TARGET_COLUMN].astype(str).str.strip().unique())
    if labels != {"Yes", "No"}:
        raise DatasetValidationError("Target 'Churn' must contain exactly the labels 'Yes' and 'No'")
    for column in NUMERIC_COLUMNS:
        original = frame[column]
        if original.dtype == object or pd.api.types.is_string_dtype(original):
            cleaned = original.astype(str).str.strip().replace("", float("nan"))
        else:
            cleaned = original
        converted = pd.to_numeric(cleaned, errors="coerce")
        if converted[cleaned.notna()].isna().any():
            raise DatasetValidationError(f"Column '{column}' must contain numeric values")
        if column != "TotalCharges" and converted.isna().any():
            raise DatasetValidationError(f"Column '{column}' cannot contain missing values")


def load_dataset(path: Path | None = None, *, download: bool = True) -> tuple[pd.DataFrame, str]:
    """Load a local source CSV or download the official IBM sample CSV.

    Returns the validated dataframe and SHA-256 of the exact CSV content.
    The dataset is not written to disk unless the caller provides a local file.
    """
    if path is not None:
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise DatasetValidationError(f"Cannot read dataset file: {path}") from exc
    elif download:
        request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "ModelServe-AI/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()
        except OSError as exc:
            raise DatasetValidationError(f"Could not download the IBM dataset from {DATASET_URL}") from exc
    else:
        raise DatasetValidationError("Provide a local dataset path or enable downloading")

    return _parse_csv(content), hashlib.sha256(content).hexdigest()
