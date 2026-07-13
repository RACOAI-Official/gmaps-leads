"""runtime_config table

Revision ID: a1b2c3d4e5f6
Revises: 119ee21c7064
Create Date: 2026-07-09 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "119ee21c7064"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "runtime_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scrape_delay_min_s", sa.Float(), nullable=False),
        sa.Column("scrape_delay_max_s", sa.Float(), nullable=False),
        sa.Column("scrape_daily_cap", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Seed the single config row from the current .env defaults so the live
    # values start out matching what's configured.
    op.execute(
        "INSERT INTO runtime_config (id, scrape_delay_min_s, scrape_delay_max_s, scrape_daily_cap) "
        "VALUES (1, 3.0, 8.0, 400)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("runtime_config")
