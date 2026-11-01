"""Add model lifecycle stage, mlflow_run_id, and model_promotion_audit table.

Revision ID: 20261101_0002
Revises: 20261028_0001
Create Date: 2026-11-01 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261101_0002"
down_revision: Union[str, None] = "20261028_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add stage and mlflow_run_id to model_versions
    op.add_column(
        "model_versions",
        sa.Column("stage", sa.String(length=32), nullable=False, server_default="candidate"),
    )
    op.add_column(
        "model_versions",
        sa.Column("mlflow_run_id", sa.String(length=128), nullable=True),
    )

    # 2. Create model_promotion_audit table
    op.create_table(
        "model_promotion_audit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("previous_model_version", sa.String(length=128), nullable=True),
        sa.Column("new_model_version", sa.String(length=128), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("quality_gate_results_json", sa.Text(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_promotion_audit_new_model_version",
        "model_promotion_audit",
        ["new_model_version"],
        unique=False,
    )
    op.create_index(
        "ix_model_promotion_audit_created_at_utc",
        "model_promotion_audit",
        ["created_at_utc"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_model_promotion_audit_created_at_utc", table_name="model_promotion_audit")
    op.drop_index("ix_model_promotion_audit_new_model_version", table_name="model_promotion_audit")
    op.drop_table("model_promotion_audit")

    op.drop_column("model_versions", "mlflow_run_id")
    op.drop_column("model_versions", "stage")

