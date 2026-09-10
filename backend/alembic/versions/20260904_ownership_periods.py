"""Faixas de vigência do % societário MLDU."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260904_ownership_periods"
down_revision: Union[str, None] = "20260831_ownership_mldu"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "company_ownership_periods" in insp.get_table_names():
        return
    op.create_table(
        "company_ownership_periods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("link_id", sa.Integer(), nullable=False),
        sa.Column("percentage", sa.Float(), nullable=False),
        sa.Column("valid_from", sa.String(), nullable=True),
        sa.Column("valid_until", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["link_id"], ["company_ownership_links.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_company_ownership_periods_link_id", "company_ownership_periods", ["link_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "company_ownership_periods" not in insp.get_table_names():
        return
    op.drop_index("ix_company_ownership_periods_link_id", table_name="company_ownership_periods")
    op.drop_table("company_ownership_periods")
