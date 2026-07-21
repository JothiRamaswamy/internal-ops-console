"""drop processed_webhook_events (switch to sync/ETL ingestion)

Revision ID: a1b2c3d4e5f6
Revises: 375bc59a882f
Create Date: 2026-07-21

The console ingests vendor data via the sync/ETL layer (integration_* source
tables -> normalized domain tables), not via inbound webhooks, so the webhook
idempotency ledger is removed.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "375bc59a882f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("processed_webhook_events")


def downgrade() -> None:
    op.create_table(
        "processed_webhook_events",
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
