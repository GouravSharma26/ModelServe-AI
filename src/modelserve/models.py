"""SQLAlchemy data models for model metadata, lifecycle audit, and inference prediction events."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models."""


class ModelVersionRecord(Base):
    """Persisted metadata, lifecycle stage, and evaluation manifest for a trained model version."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stage: Mapped[str] = mapped_column(String(32), default="candidate", nullable=False)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "artifact_sha256": self.artifact_sha256,
            "dataset_fingerprint": self.dataset_fingerprint,
            "created_at_utc": self.created_at_utc.isoformat(),
            "is_active": self.is_active,
            "stage": self.stage,
            "mlflow_run_id": self.mlflow_run_id,
        }


class ModelPromotionAudit(Base):
    """Immutable audit log for model promotion, rollback, and retirement events."""

    __tablename__ = "model_promotion_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "promotion", "rollback", "demotion"
    previous_model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    new_model_version: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    quality_gate_results_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "previous_model_version": self.previous_model_version,
            "new_model_version": self.new_model_version,
            "actor": self.actor,
            "reason": self.reason,
            "quality_gate_results_json": self.quality_gate_results_json,
            "created_at_utc": self.created_at_utc.isoformat(),
        }


class PredictionRecord(Base):
    """Persisted prediction outcome and latency telemetry (raw features excluded by ADR-008)."""

    __tablename__ = "prediction_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "model_version": self.model_version,
            "label": self.label,
            "score": self.score,
            "latency_ms": self.latency_ms,
            "created_at_utc": self.created_at_utc.isoformat(),
        }
