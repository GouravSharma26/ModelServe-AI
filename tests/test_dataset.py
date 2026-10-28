from __future__ import annotations

import hashlib
import io

import pandas as pd
import pytest

from modelserve.dataset import (
    EXPECTED_COLUMNS,
    DatasetValidationError,
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


def test_loads_local_csv_and_returns_fingerprint(tmp_path) -> None:
    csv_path = tmp_path / "Telco-Customer-Churn.csv"
    csv_path.write_text(small_dataset().to_csv(index=False), encoding="utf-8")

    frame, fingerprint = load_dataset(csv_path)

    assert len(frame) == 20
    assert fingerprint == hashlib.sha256(csv_path.read_bytes()).hexdigest()


def test_downloads_source_csv_and_returns_fingerprint(monkeypatch) -> None:
    csv_bytes = small_dataset().to_csv(index=False).encode()

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr("modelserve.dataset.urllib.request.urlopen", lambda *args, **kwargs: Response(csv_bytes))
    frame, fingerprint = load_dataset()

    assert len(frame) == 20
    assert fingerprint == hashlib.sha256(csv_bytes).hexdigest()
