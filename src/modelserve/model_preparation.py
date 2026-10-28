"""Reproducible model preparation workflow for ModelServe AI.

Loads dataset, trains candidate models, serializes immutable artifacts with
manifests, and strictly verifies checksum integrity before deployment.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from modelserve.dataset import DatasetValidationError, load_dataset
from modelserve.model_loader import (
    ArtifactError,
    load_active_model,
)
from modelserve.training import RANDOM_SEED, train

logger = logging.getLogger("modelserve.preparation")


def prepare_model(
    output_dir: Path,
    data_path: Path | None = None,
    seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    """Train candidates, write versioned artifact and manifest, and verify integrity."""
    print("=== Step 1/3: Loading and validating dataset ===")
    try:
        frame, fingerprint = load_dataset(data_path)
    except DatasetValidationError as exc:
        print(f"[ERROR] Dataset validation failed: {exc}", file=sys.stderr)
        raise

    print(f"Dataset loaded: {len(frame):,} rows (SHA-256: {fingerprint[:16]}...)")

    print("\n=== Step 2/3: Training candidates and evaluating on held-out test split ===")
    manifest = train(frame, fingerprint, output_dir, seed=seed)
    version = manifest["artifact_version"]
    selected = manifest["selected_model"]
    test_metrics = manifest["test_metrics"]
    print(f"Model selected: {selected}")
    print(f"Artifact version: {version}")
    print(f"Held-out PR-AUC: {test_metrics['pr_auc_average_precision']:.4f} | F1: {test_metrics['f1']:.4f}")

    print("\n=== Step 3/3: Verifying artifact manifest and SHA-256 integrity ===")
    try:
        loaded = load_active_model(artifacts_dir=output_dir, version=version)
    except ArtifactError as exc:
        print(f"[ERROR] Integrity verification failed: {exc}", file=sys.stderr)
        raise

    print(f"[SUCCESS] Verified artifact '{loaded.name}' version '{loaded.version}'.")
    return manifest


def main() -> None:
    """CLI entrypoint for reproducible model preparation."""
    parser = argparse.ArgumentParser(description="Prepare and verify ModelServe AI model artifact")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/models"),
        help="Artifacts directory (defaults to artifacts/models)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Path to local Telco-Customer-Churn.csv (downloads IBM sample when omitted)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=RANDOM_SEED,
        help="Random seed for reproducible training split",
    )
    args = parser.parse_args()

    try:
        manifest = prepare_model(output_dir=args.output, data_path=args.data, seed=args.seed)
        version_dir = args.output / manifest["artifact_directory"]
        summary = {
            "status": "ready",
            "artifact_version": manifest["artifact_version"],
            "selected_model": manifest["selected_model"],
            "artifact_file": str(version_dir / manifest["artifact_file"]),
            "manifest_file": str(version_dir / "manifest.json"),
            "test_metrics": manifest["test_metrics"],
        }
        print("\n" + json.dumps(summary, indent=2))
    except Exception as exc:
        print(f"\n[FAIL] Model preparation failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

