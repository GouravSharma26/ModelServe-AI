"""Model lifecycle management, quality gate validation, promotion, and rollback service."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from modelserve.model_loader import _compute_sha256
from modelserve.models import ModelPromotionAudit, ModelVersionRecord
from modelserve.quality_gates import (
    DEFAULT_MAX_ALLOWED_PR_AUC_REGRESSION,
    DEFAULT_MIN_VAL_PR_AUC,
    QualityGateResult,
    evaluate_candidate_gates,
)

logger = logging.getLogger("modelserve.lifecycle")


class ModelLifecycleService:
    """Production service for model candidate registration, comparison, quality gating, promotion, and rollback."""

    def __init__(self, session_factory: sessionmaker[Session], artifacts_dir: Path):
        self.session_factory = session_factory
        self.artifacts_dir = artifacts_dir

    def _read_manifest(self, version: str) -> dict[str, Any]:
        version_dir = self.artifacts_dir / version
        manifest_path = version_dir / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Manifest not found for version '{version}' in {version_dir}")
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def register_candidate(
        self,
        version: str,
        *,
        manifest: dict[str, Any] | None = None,
        mlflow_run_id: str | None = None,
    ) -> ModelVersionRecord:
        """Register a trained model version as a candidate without activating it."""
        if manifest is None:
            manifest = self._read_manifest(version)

        version_dir = self.artifacts_dir / version
        artifact_file = manifest.get("artifact_file", "model.joblib")
        artifact_path = version_dir / artifact_file

        if not artifact_path.is_file():
            raise FileNotFoundError(f"Model artifact file '{artifact_file}' does not exist in {version_dir}")

        # Verify integrity before registering
        actual_sha256 = _compute_sha256(artifact_path).lower()
        expected_sha256 = manifest.get("artifact_sha256", "").lower()
        if actual_sha256 != expected_sha256:
            raise ValueError(f"Artifact SHA-256 mismatch for {version}: expected {expected_sha256}, got {actual_sha256}")

        dataset_fingerprint = manifest.get("dataset", {}).get("sha256", "unknown")
        selected_model = manifest.get("selected_model", "customer-churn-classifier")
        run_id = mlflow_run_id or manifest.get("mlflow_run_id")

        with self.session_factory() as session:
            stmt = select(ModelVersionRecord).where(ModelVersionRecord.version == version)
            existing = session.execute(stmt).scalar_one_or_none()

            manifest_str = json.dumps(manifest, sort_keys=True)
            if existing is not None:
                existing.name = selected_model
                existing.artifact_sha256 = actual_sha256
                existing.dataset_fingerprint = dataset_fingerprint
                existing.manifest_json = manifest_str
                existing.mlflow_run_id = run_id
                record = existing
            else:
                record = ModelVersionRecord(
                    version=version,
                    name=selected_model,
                    artifact_sha256=actual_sha256,
                    dataset_fingerprint=dataset_fingerprint,
                    created_at_utc=datetime.now(UTC),
                    manifest_json=manifest_str,
                    is_active=False,
                    stage="candidate",
                    mlflow_run_id=run_id,
                )
                session.add(record)

            session.commit()
            session.refresh(record)
            logger.info("Registered model version '%s' in stage '%s'", version, record.stage)
            return record

    def get_active_model(self) -> ModelVersionRecord | None:
        """Return the currently designated active model version, or None."""
        with self.session_factory() as session:
            stmt = select(ModelVersionRecord).where(ModelVersionRecord.is_active.is_(True))
            return session.execute(stmt).scalar_one_or_none()

    def get_model(self, version: str) -> ModelVersionRecord | None:
        """Return the model version record for the given version string."""
        with self.session_factory() as session:
            stmt = select(ModelVersionRecord).where(ModelVersionRecord.version == version)
            return session.execute(stmt).scalar_one_or_none()

    def list_models(self) -> list[ModelVersionRecord]:
        """List all model versions ordered by creation time descending."""
        with self.session_factory() as session:
            stmt = select(ModelVersionRecord).order_by(ModelVersionRecord.created_at_utc.desc())
            return list(session.execute(stmt).scalars().all())

    def compare_candidate_with_active(self, candidate_version: str) -> dict[str, Any]:
        """Produce a structured side-by-side comparison between candidate and current active model."""
        cand_manifest = self._read_manifest(candidate_version)
        cand_dir = self.artifacts_dir / candidate_version
        cand_artifact = cand_dir / cand_manifest.get("artifact_file", "model.joblib")

        active_record = self.get_active_model()
        active_manifest = None
        if active_record is not None:
            try:
                active_manifest = json.loads(active_record.manifest_json)
            except Exception:
                active_manifest = self._read_manifest(active_record.version)

        cand_model_name = cand_manifest.get("selected_model", "")
        cand_val_metrics = cand_manifest.get("validation_metrics", {}).get(cand_model_name, {})
        cand_test_metrics = cand_manifest.get("test_metrics", {})

        comparison: dict[str, Any] = {
            "candidate": {
                "version": candidate_version,
                "algorithm": cand_model_name,
                "mlflow_run_id": cand_manifest.get("mlflow_run_id"),
                "artifact_sha256": cand_manifest.get("artifact_sha256"),
                "artifact_exists": cand_artifact.is_file(),
                "dataset_fingerprint": cand_manifest.get("dataset", {}).get("sha256"),
                "validation": {
                    "pr_auc": cand_val_metrics.get("pr_auc_average_precision"),
                    "roc_auc": cand_val_metrics.get("roc_auc"),
                    "f1": cand_val_metrics.get("f1"),
                    "precision": cand_val_metrics.get("precision"),
                    "recall": cand_val_metrics.get("recall"),
                },
                "test": {
                    "pr_auc": cand_test_metrics.get("pr_auc_average_precision"),
                    "roc_auc": cand_test_metrics.get("roc_auc"),
                    "f1": cand_test_metrics.get("f1"),
                    "precision": cand_test_metrics.get("precision"),
                    "recall": cand_test_metrics.get("recall"),
                },
            },
            "active": None,
            "metric_deltas": None,
            "schema_compatible": True,
        }

        if active_manifest is not None:
            active_model_name = active_manifest.get("selected_model", "")
            active_val_metrics = active_manifest.get("validation_metrics", {}).get(active_model_name, {})
            active_test_metrics = active_manifest.get("test_metrics", {})

            comparison["active"] = {
                "version": active_manifest.get("artifact_version"),
                "algorithm": active_model_name,
                "mlflow_run_id": active_manifest.get("mlflow_run_id"),
                "artifact_sha256": active_manifest.get("artifact_sha256"),
                "dataset_fingerprint": active_manifest.get("dataset", {}).get("sha256"),
                "validation": {
                    "pr_auc": active_val_metrics.get("pr_auc_average_precision"),
                    "roc_auc": active_val_metrics.get("roc_auc"),
                    "f1": active_val_metrics.get("f1"),
                    "precision": active_val_metrics.get("precision"),
                    "recall": active_val_metrics.get("recall"),
                },
                "test": {
                    "pr_auc": active_test_metrics.get("pr_auc_average_precision"),
                    "roc_auc": active_test_metrics.get("roc_auc"),
                    "f1": active_test_metrics.get("f1"),
                    "precision": active_test_metrics.get("precision"),
                    "recall": active_test_metrics.get("recall"),
                },
            }

            # Calculate deltas (candidate - active)
            c_val_pr = cand_val_metrics.get("pr_auc_average_precision") or 0.0
            a_val_pr = active_val_metrics.get("pr_auc_average_precision") or 0.0
            c_val_f1 = cand_val_metrics.get("f1") or 0.0
            a_val_f1 = active_val_metrics.get("f1") or 0.0

            c_test_pr = cand_test_metrics.get("pr_auc_average_precision") or 0.0
            a_test_pr = active_test_metrics.get("pr_auc_average_precision") or 0.0

            comparison["metric_deltas"] = {
                "val_pr_auc_delta": round(c_val_pr - a_val_pr, 4),
                "val_f1_delta": round(c_val_f1 - a_val_f1, 4),
                "test_pr_auc_delta": round(c_test_pr - a_test_pr, 4),
            }

            # Check schema compatibility between candidate and active
            c_schema = cand_manifest.get("feature_schema", {})
            a_schema = active_manifest.get("feature_schema", {})
            schema_equal = (
                set(c_schema.get("numeric", [])) == set(a_schema.get("numeric", []))
                and set(c_schema.get("categorical", [])) == set(a_schema.get("categorical", []))
            )
            comparison["schema_compatible"] = schema_equal

        return comparison

    def evaluate_gates(
        self,
        candidate_version: str,
        *,
        min_val_pr_auc: float = DEFAULT_MIN_VAL_PR_AUC,
        max_allowed_regression: float = DEFAULT_MAX_ALLOWED_PR_AUC_REGRESSION,
    ) -> QualityGateResult:
        """Run deterministic quality gate checks on a registered candidate version."""
        cand_manifest = self._read_manifest(candidate_version)
        cand_dir = self.artifacts_dir / candidate_version

        record = self.get_model(candidate_version)
        is_retired = (record.stage == "retired") if record else False

        active_record = self.get_active_model()
        active_manifest = None
        if active_record is not None and active_record.version != candidate_version:
            try:
                active_manifest = json.loads(active_record.manifest_json)
            except Exception:
                active_manifest = self._read_manifest(active_record.version)

        return evaluate_candidate_gates(
            cand_manifest,
            cand_dir,
            active_manifest,
            min_val_pr_auc=min_val_pr_auc,
            max_allowed_regression=max_allowed_regression,
            is_retired=is_retired,
        )

    def promote_model(
        self,
        candidate_version: str,
        *,
        actor: str,
        reason: str,
        force: bool = False,
        min_val_pr_auc: float = DEFAULT_MIN_VAL_PR_AUC,
        max_allowed_regression: float = DEFAULT_MAX_ALLOWED_PR_AUC_REGRESSION,
    ) -> tuple[bool, QualityGateResult, ModelPromotionAudit]:
        """Promote a candidate model to active status in a single transaction after quality verification."""
        gates = self.evaluate_gates(
            candidate_version,
            min_val_pr_auc=min_val_pr_auc,
            max_allowed_regression=max_allowed_regression,
        )

        if not gates.eligible and not force:
            failed_reasons = [c.message for c in gates.checks if not c.passed]
            raise ValueError(
                f"Candidate '{candidate_version}' failed promotion gates: {'; '.join(failed_reasons)}"
            )

        with self.session_factory() as session:
            # 1. Locate current active model and demote to retired
            active_stmt = select(ModelVersionRecord).where(ModelVersionRecord.is_active.is_(True))
            current_active = session.execute(active_stmt).scalar_one_or_none()
            prev_version = current_active.version if current_active else None

            if current_active is not None:
                current_active.is_active = False
                current_active.stage = "retired"

            # 2. Locate candidate and promote to active
            cand_stmt = select(ModelVersionRecord).where(ModelVersionRecord.version == candidate_version)
            candidate_record = session.execute(cand_stmt).scalar_one_or_none()
            if candidate_record is None:
                # If not registered in DB yet, register it now
                cand_manifest = self._read_manifest(candidate_version)
                candidate_record = ModelVersionRecord(
                    version=candidate_version,
                    name=cand_manifest.get("selected_model", "customer-churn-classifier"),
                    artifact_sha256=cand_manifest.get("artifact_sha256", ""),
                    dataset_fingerprint=cand_manifest.get("dataset", {}).get("sha256", ""),
                    created_at_utc=datetime.now(UTC),
                    manifest_json=json.dumps(cand_manifest, sort_keys=True),
                    is_active=True,
                    stage="active",
                    mlflow_run_id=cand_manifest.get("mlflow_run_id"),
                )
                session.add(candidate_record)
            else:
                candidate_record.is_active = True
                candidate_record.stage = "active"

            # 3. Create audit row
            audit_entry = ModelPromotionAudit(
                event_type="promotion",
                previous_model_version=prev_version,
                new_model_version=candidate_version,
                actor=actor,
                reason=reason + (" [FORCED]" if (force and not gates.eligible) else ""),
                quality_gate_results_json=json.dumps(gates.to_dict()),
                created_at_utc=datetime.now(UTC),
            )
            session.add(audit_entry)

            session.commit()
            session.refresh(audit_entry)

            logger.info(
                "Promoted model '%s' to active (previous: '%s') by actor '%s'",
                candidate_version,
                prev_version,
                actor,
            )
            return True, gates, audit_entry

    def rollback_model(
        self,
        target_version: str,
        *,
        actor: str,
        reason: str,
    ) -> ModelPromotionAudit:
        """Safely roll back the active model to a previously approved model version."""
        # Verify artifact and manifest existence and integrity on disk
        target_manifest = self._read_manifest(target_version)
        target_dir = self.artifacts_dir / target_version
        target_artifact = target_dir / target_manifest.get("artifact_file", "model.joblib")

        if not target_artifact.is_file():
            raise FileNotFoundError(f"Cannot rollback to '{target_version}': artifact file does not exist")

        expected_sha = target_manifest.get("artifact_sha256", "").lower()
        actual_sha = _compute_sha256(target_artifact).lower()
        if expected_sha != actual_sha:
            raise ValueError(f"Rollback target SHA-256 mismatch for {target_version}")

        with self.session_factory() as session:
            # 1. Demote current active
            active_stmt = select(ModelVersionRecord).where(ModelVersionRecord.is_active.is_(True))
            current_active = session.execute(active_stmt).scalar_one_or_none()
            prev_version = current_active.version if current_active else None

            if prev_version == target_version:
                raise ValueError(f"Model version '{target_version}' is already the active model.")

            if current_active is not None:
                current_active.is_active = False
                current_active.stage = "retired"

            # 2. Activate target
            target_stmt = select(ModelVersionRecord).where(ModelVersionRecord.version == target_version)
            target_record = session.execute(target_stmt).scalar_one_or_none()

            if target_record is None:
                target_record = ModelVersionRecord(
                    version=target_version,
                    name=target_manifest.get("selected_model", "customer-churn-classifier"),
                    artifact_sha256=actual_sha,
                    dataset_fingerprint=target_manifest.get("dataset", {}).get("sha256", ""),
                    created_at_utc=datetime.now(UTC),
                    manifest_json=json.dumps(target_manifest, sort_keys=True),
                    is_active=True,
                    stage="active",
                    mlflow_run_id=target_manifest.get("mlflow_run_id"),
                )
                session.add(target_record)
            else:
                target_record.is_active = True
                target_record.stage = "active"

            # 3. Append audit record
            audit_entry = ModelPromotionAudit(
                event_type="rollback",
                previous_model_version=prev_version,
                new_model_version=target_version,
                actor=actor,
                reason=reason,
                quality_gate_results_json=json.dumps({
                    "action": "rollback",
                    "target_version": target_version,
                    "previous_version": prev_version,
                    "sha256_verified": True,
                }),
                created_at_utc=datetime.now(UTC),
            )
            session.add(audit_entry)

            session.commit()
            session.refresh(audit_entry)

            logger.info(
                "Rolled back active model to '%s' (previous: '%s') by actor '%s'",
                target_version,
                prev_version,
                actor,
            )
            return audit_entry

    def get_audit_history(self, limit: int = 50) -> list[ModelPromotionAudit]:
        """Return the promotion and rollback audit trail ordered by time descending."""
        with self.session_factory() as session:
            stmt = (
                select(ModelPromotionAudit)
                .order_by(ModelPromotionAudit.created_at_utc.desc())
                .limit(limit)
            )
            return list(session.execute(stmt).scalars().all())

