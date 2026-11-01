"""Administrative CLI tool for model lifecycle management, comparison, quality gating, and rollbacks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from modelserve.database import get_engine, get_session_factory, init_db
from modelserve.lifecycle import ModelLifecycleService
from modelserve.settings import get_settings


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="modelserve-lifecycle",
        description="ModelServe AI administrative CLI for model lifecycle, promotion, and rollbacks",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL (defaults to DATABASE_URL setting or sqlite:///data/modelserve.db)",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Artifacts directory (defaults to MODELSERVE_MODEL_DIR or artifacts/models)",
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Subcommand: list
    subparsers.add_parser("list", help="List all registered model versions and their lifecycle stages")

    # Subcommand: register
    reg_parser = subparsers.add_parser("register", help="Register a trained model version as a candidate")
    reg_parser.add_argument("version", type=str, help="Version string (e.g. telco-churn-20261028T184000Z)")
    reg_parser.add_argument("--mlflow-run-id", type=str, default=None, help="Associated MLflow run ID")

    # Subcommand: compare
    comp_parser = subparsers.add_parser("compare", help="Compare candidate metrics against active model")
    comp_parser.add_argument("candidate_version", type=str, help="Candidate version string to compare")

    # Subcommand: check-gates
    gate_parser = subparsers.add_parser("check-gates", help="Evaluate deterministic promotion quality gates")
    gate_parser.add_argument("candidate_version", type=str, help="Candidate version string to evaluate")
    gate_parser.add_argument("--min-pr-auc", type=float, default=0.55, help="Minimum validation PR-AUC")
    gate_parser.add_argument("--max-regression", type=float, default=0.03, help="Max allowed PR-AUC regression")

    # Subcommand: promote
    prom_parser = subparsers.add_parser("promote", help="Promote candidate model to active status")
    prom_parser.add_argument("candidate_version", type=str, help="Candidate version to promote")
    prom_parser.add_argument("--actor", type=str, required=True, help="Person or automated service performing action")
    prom_parser.add_argument("--reason", type=str, required=True, help="Detailed justification for promotion")
    prom_parser.add_argument("--force", action="store_true", help="Bypass quality gate failures with documented override")
    prom_parser.add_argument("--min-pr-auc", type=float, default=0.55, help="Minimum validation PR-AUC")
    prom_parser.add_argument("--max-regression", type=float, default=0.03, help="Max allowed PR-AUC regression")

    # Subcommand: rollback
    roll_parser = subparsers.add_parser("rollback", help="Safely roll back active model to a previous version")
    roll_parser.add_argument("target_version", type=str, help="Previously approved model version to restore")
    roll_parser.add_argument("--actor", type=str, required=True, help="Person or automated service performing action")
    roll_parser.add_argument("--reason", type=str, required=True, help="Detailed justification for rollback")

    # Subcommand: history
    hist_parser = subparsers.add_parser("history", help="Show model promotion and rollback audit trail")
    hist_parser.add_argument("--limit", type=int, default=20, help="Max audit rows to retrieve")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    settings = get_settings()
    db_url = args.db_url or settings.database_url or "sqlite:///data/modelserve.db"
    artifacts_dir = args.artifacts_dir or settings.artifacts_dir

    engine = get_engine(db_url)
    session_factory = get_session_factory(engine)
    if db_url.startswith("sqlite"):
        init_db(engine)

    service = ModelLifecycleService(session_factory, artifacts_dir)

    try:
        if args.subcommand == "list":
            models = service.list_models()
            print(f"Found {len(models)} registered model version(s):")
            for m in models:
                active_str = " [ACTIVE]" if m.is_active else ""
                print(f"  • {m.version} | Algorithm: {m.name} | Stage: {m.stage}{active_str} | Created: {m.created_at_utc.isoformat()}")
            return 0

        elif args.subcommand == "register":
            record = service.register_candidate(args.version, mlflow_run_id=args.mlflow_run_id)
            print(json.dumps({
                "status": "registered",
                "version": record.version,
                "stage": record.stage,
                "is_active": record.is_active,
                "mlflow_run_id": record.mlflow_run_id,
            }, indent=2))
            return 0

        elif args.subcommand == "compare":
            result = service.compare_candidate_with_active(args.candidate_version)
            print(json.dumps(result, indent=2))
            return 0

        elif args.subcommand == "check-gates":
            gate_result = service.evaluate_gates(
                args.candidate_version,
                min_val_pr_auc=args.min_pr_auc,
                max_allowed_regression=args.max_regression,
            )
            print(json.dumps(gate_result.to_dict(), indent=2))
            return 0 if gate_result.eligible else 1

        elif args.subcommand == "promote":
            success, gates, audit = service.promote_model(
                args.candidate_version,
                actor=args.actor,
                reason=args.reason,
                force=args.force,
                min_val_pr_auc=args.min_pr_auc,
                max_allowed_regression=args.max_regression,
            )
            print(json.dumps({
                "status": "promoted",
                "active_version": audit.new_model_version,
                "previous_version": audit.previous_model_version,
                "actor": audit.actor,
                "audit_id": audit.id,
                "eligible": gates.eligible,
                "created_at_utc": audit.created_at_utc.isoformat(),
            }, indent=2))
            return 0

        elif args.subcommand == "rollback":
            audit = service.rollback_model(
                args.target_version,
                actor=args.actor,
                reason=args.reason,
            )
            print(json.dumps({
                "status": "rolled_back",
                "active_version": audit.new_model_version,
                "previous_version": audit.previous_model_version,
                "actor": audit.actor,
                "audit_id": audit.id,
                "created_at_utc": audit.created_at_utc.isoformat(),
            }, indent=2))
            return 0

        elif args.subcommand == "history":
            history = service.get_audit_history(limit=args.limit)
            print(f"Promotion and Rollback Audit Trail ({len(history)} events):")
            for h in history:
                prev = h.previous_model_version or "(none)"
                print(f"  [{h.created_at_utc.isoformat()}] {h.event_type.upper()}: {prev} -> {h.new_model_version} | Actor: {h.actor} | Reason: {h.reason}")
            return 0

        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

