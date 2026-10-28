from __future__ import annotations

import io
import pandas as pd
import pytest

from modelserve.dataset import (
    EXPECTED_COLUMNS,
    DatasetValidationError,
    _parse_csv,
    load_dataset,
    validate_dataset,
)


def small_dataset(rows: int = 20) -> pd.DataFrame:
    values: dict[str, list[object]] = {}
    numeric = {"SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"}
    for column in EXPECTED_COLUMNS:
        if column in numeric:
            values[column] = [float(index + 1) for index in range(rows)]
        elif column == "customerID":
            values[column] = [f"ID-{index:05d}" for index in range(rows)]
        elif column == "Churn":
            values[column] = ["Yes" if index % 2 else "No" for index in range(rows)]
        else:
            values[column] = ["category_a" if index % 2 else "category_b" for index in range(rows)]
    return pd.DataFrame(values)


def test_validates_source_schema_and_binary_target() -> None:
    validate_dataset(small_dataset())


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda frame: frame.drop(columns=["tenure"]), "missing columns: tenure"),
        (lambda frame: frame.drop(columns=["TotalCharges"]), "missing columns: TotalCharges"),
        (lambda frame: frame.drop(columns=["customerID"]), "missing columns: customerID"),
        (lambda frame: frame.assign(extra=1), "unexpected columns: extra"),
        (lambda frame: frame.assign(Churn="maybe"), "exactly the labels"),
        (lambda frame: frame.assign(tenure="not-a-number"), "must contain numeric"),
        (lambda frame: frame.assign(TotalCharges="not-a-number"), "must contain numeric"),
        (lambda frame: frame.assign(Contract=None), "missing values"),
    ],
)
def test_rejects_invalid_dataset(mutation, message: str) -> None:
    with pytest.raises(DatasetValidationError, match=message):
        validate_dataset(mutation(small_dataset()))


def test_rejects_empty_dataset() -> None:
    with pytest.raises(DatasetValidationError, match="no rows"):
        validate_dataset(small_dataset(0))


def test_allows_missing_total_charges_for_training_imputation() -> None:
    frame = small_dataset()
    frame.loc[0, "TotalCharges"] = float("nan")
    validate_dataset(frame)


def test_parse_csv_allows_blank_spaces_in_total_charges() -> None:
    """IBM Telco raw CSV contains spaces for TotalCharges when tenure is 0; must parse without error."""
    df = small_dataset()
    df["TotalCharges"] = df["TotalCharges"].astype(object)
    df.loc[0, "TotalCharges"] = " "
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    parsed = _parse_csv(csv_bytes)
    assert pd.isna(parsed.loc[0, "TotalCharges"])


def test_parse_csv_missing_numeric_column_raises_validation_error() -> None:
    """CSV missing a numeric column must raise DatasetValidationError, not KeyError."""
    df = small_dataset().drop(columns=["TotalCharges"])
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    with pytest.raises(DatasetValidationError, match="missing columns: TotalCharges"):
        _parse_csv(csv_bytes)


def test_parse_csv_empty_content_raises_validation_error() -> None:
    """Completely empty CSV input must raise DatasetValidationError."""
    with pytest.raises(DatasetValidationError, match="contains no data or headers"):
        _parse_csv(b"")


def test_parse_csv_corrupt_bytes_raises_validation_error() -> None:
    """Malformed non-CSV binary data must raise DatasetValidationError."""
    with pytest.raises(DatasetValidationError):
        _parse_csv(b"\x00\xff\xfe\x00BinaryGibberish")


def test_parse_csv_numeric_conversion_failure() -> None:
    """Non-numeric string in numeric column raises DatasetValidationError."""
    df = small_dataset()
    df.loc[0, "tenure"] = "five_years"
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    with pytest.raises(DatasetValidationError, match="Column 'tenure' must contain numeric"):
        _parse_csv(csv_bytes)


def test_loads_local_csv_and_returns_fingerprint(tmp_path) -> None:
    csv_path = tmp_path / "Telco-Customer-Churn.csv"
    df = small_dataset()
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    csv_path.write_bytes(csv_bytes)

    loaded, fingerprint = load_dataset(csv_path, download=False)
    assert len(loaded) == len(df)
    assert len(fingerprint) == 64
