"""Initial schema: model_versions and prediction_records tables.

Revision ID: 20261028_0001
Revises: 
Create Date: 2026-10-28 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261028_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("dataset_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_versions_version", "model_versions", ["version"], unique=True)

    op.create_table(
        "prediction_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prediction_records_request_id", "prediction_records", ["request_id"], unique=True)
    op.create_index("ix_prediction_records_model_version", "prediction_records", ["model_version"], unique=False)
    op.create_index("ix_prediction_records_created_at_utc", "prediction_records", ["created_at_utc"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_prediction_records_created_at_utc", table_name="prediction_records")
    op.drop_index("ix_prediction_records_model_version", table_name="prediction_records")
    op.drop_index("ix_prediction_records_request_id", table_name="prediction_records")
    op.drop_table("prediction_records")

    op.drop_index("ix_model_versions_version", table_name="model_versions")
    op.drop_table("model_versions")

