"""add status_note to refunds

A human-readable note describing the refund's current status (e.g. why it
succeeded/failed or what remaining balance it left).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "refunds",
        sa.Column("status_note", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("refunds", "status_note")
