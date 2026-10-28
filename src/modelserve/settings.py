"""Application settings and configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from environment variables."""

    env: str = field(
        default_factory=lambda: os.getenv("MODELSERVE_ENV", "development").strip().lower()
    )
    host: str = field(
        default_factory=lambda: os.getenv("MODELSERVE_HOST", "0.0.0.0").strip()
    )
    port: int = field(
        default_factory=lambda: int(os.getenv("MODELSERVE_PORT", "8000").strip())
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("MODELSERVE_LOG_LEVEL", "INFO").strip().upper()
    )
    artifacts_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("MODELSERVE_ARTIFACTS_DIR", "artifacts/models").strip()
        )
    )
    model_version: str | None = field(
        default_factory=lambda: (
            os.getenv("MODELSERVE_MODEL_VERSION", "").strip() or None
        )
    )
    max_payload_bytes: int = field(
        default_factory=lambda: int(
            os.getenv("MODELSERVE_MAX_PAYLOAD_BYTES", "65536").strip()
        )
    )
    database_url: str | None = field(
        default_factory=lambda: (
            os.getenv("DATABASE_URL", "").strip() or None
        )
    )
    model_name: str = "customer-churn-classifier"


def get_settings() -> Settings:
    """Return an instance of Settings reflecting current environment."""
    return Settings()
