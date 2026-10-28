"""Repository for database persistence of model metadata and prediction telemetry."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from modelserve.models import ModelVersionRecord, PredictionRecord


def record_prediction(
    session: Session,
    *,
    request_id: str,
    model_version: str,
    label: str,
    score: float,
    latency_ms: float,
    created_at_utc: datetime | None = None,
) -> PredictionRecord:
    """Persist a single prediction event without raw customer input features."""
    record = PredictionRecord(
        request_id=request_id,
        model_version=model_version,
        label=label,
        score=score,
        latency_ms=latency_ms,
        created_at_utc=created_at_utc or datetime.now(UTC),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def upsert_model_version(
    session: Session,
    *,
    version: str,
    name: str,
    artifact_sha256: str,
    dataset_fingerprint: str,
    created_at_utc: datetime,
    manifest: dict[str, Any],
) -> ModelVersionRecord:
    """Insert or update a registered model version record."""
    stmt = select(ModelVersionRecord).where(ModelVersionRecord.version == version)
    existing = session.execute(stmt).scalar_one_or_none()

    manifest_str = json.dumps(manifest, sort_keys=True)
    if existing is not None:
        existing.name = name
        existing.artifact_sha256 = artifact_sha256
        existing.dataset_fingerprint = dataset_fingerprint
        existing.manifest_json = manifest_str
        existing.is_active = True
        record = existing
    else:
        record = ModelVersionRecord(
            version=version,
            name=name,
            artifact_sha256=artifact_sha256,
            dataset_fingerprint=dataset_fingerprint,
            created_at_utc=created_at_utc,
            manifest_json=manifest_str,
            is_active=True,
        )
        session.add(record)

    session.commit()
    session.refresh(record)
    return record


def get_monitoring_summary(
    session: Session,
    *,
    window_hours: int = 24,
    model_version: str | None = None,
) -> dict[str, Any]:
    """Compute bounded-window aggregated prediction distribution and latency percentiles.

    Provides safe empty-state behavior when no predictions have been recorded.
    """
    now = datetime.now(UTC)
    window_start = now - timedelta(hours=window_hours)

    query = select(PredictionRecord).where(PredictionRecord.created_at_utc >= window_start)
    if model_version:
        query = query.where(PredictionRecord.model_version == model_version)

    records = list(session.execute(query).scalars().all())
    total_count = len(records)

    if total_count == 0:
        return {
            "window_hours": window_hours,
            "window_start_utc": window_start.isoformat(),
            "window_end_utc": now.isoformat(),
            "model_version": model_version,
            "total_predictions": 0,
            "label_distribution": {"No": 0, "Yes": 0},
            "score_summary": {"mean": 0.0, "min": 0.0, "max": 0.0},
            "latency_summary_ms": {
                "mean": 0.0,
                "p50": 0.0,
                "p90": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            },
        }

    scores = [r.score for r in records]
    latencies = [r.latency_ms for r in records]

    label_counts: dict[str, int] = {"No": 0, "Yes": 0}
    for r in records:
        label_counts[r.label] = label_counts.get(r.label, 0) + 1

    return {
        "window_hours": window_hours,
        "window_start_utc": window_start.isoformat(),
        "window_end_utc": now.isoformat(),
        "model_version": model_version,
        "total_predictions": total_count,
        "label_distribution": label_counts,
        "score_summary": {
            "mean": round(float(np.mean(scores)), 4),
            "min": round(float(np.min(scores)), 4),
            "max": round(float(np.max(scores)), 4),
        },
        "latency_summary_ms": {
            "mean": round(float(np.mean(latencies)), 2),
            "p50": round(float(np.percentile(latencies, 50)), 2),
            "p90": round(float(np.percentile(latencies, 90)), 2),
            "p95": round(float(np.percentile(latencies, 95)), 2),
            "p99": round(float(np.percentile(latencies, 99)), 2),
        },
    }

