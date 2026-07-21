"""single KYC vendor (Persona)

The console integrates a single KYC vendor. This shrinks the ``kyc_vendor`` enum
from PERSONA / STRIPE_IDENTITY / MOCK_VENDOR down to just PERSONA, mapping any
legacy rows onto PERSONA first.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE kyc_vendor RENAME TO kyc_vendor_old")
    op.execute("CREATE TYPE kyc_vendor AS ENUM ('PERSONA')")
    op.execute("UPDATE kyc_cases SET vendor = 'PERSONA' WHERE vendor <> 'PERSONA'")
    op.execute(
        "ALTER TABLE kyc_cases ALTER COLUMN vendor TYPE kyc_vendor "
        "USING vendor::text::kyc_vendor"
    )
    op.execute("DROP TYPE kyc_vendor_old")


def downgrade() -> None:
    op.execute("ALTER TYPE kyc_vendor RENAME TO kyc_vendor_old")
    op.execute(
        "CREATE TYPE kyc_vendor AS ENUM ('PERSONA', 'STRIPE_IDENTITY', 'MOCK_VENDOR')"
    )
    op.execute(
        "ALTER TABLE kyc_cases ALTER COLUMN vendor TYPE kyc_vendor "
        "USING vendor::text::kyc_vendor"
    )
    op.execute("DROP TYPE kyc_vendor_old")
