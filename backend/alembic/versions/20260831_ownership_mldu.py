"""Onda B: company_ownership_links + campos de participação MLDU em companies."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_ownership_mldu"
down_revision: Union[str, None] = "20260828_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "company_ownership_links" not in insp.get_table_names():
        op.create_table(
            "company_ownership_links",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("parent_company_id", sa.Integer(), nullable=False),
            sa.Column("child_company_id", sa.Integer(), nullable=False),
            sa.Column("percentage", sa.Float(), nullable=False),
            sa.Column("consolidates", sa.Boolean(), nullable=True, server_default=sa.text("1")),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.ForeignKeyConstraint(["parent_company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["child_company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("child_company_id"),
        )
        op.create_index("ix_company_ownership_links_parent_company_id", "company_ownership_links", ["parent_company_id"])
        op.create_index("ix_company_ownership_links_child_company_id", "company_ownership_links", ["child_company_id"])

    company_cols = {c["name"] for c in insp.get_columns("companies")}
    with op.batch_alter_table("companies") as batch_op:
        if "participacao_mldu_efetiva" not in company_cols:
            batch_op.add_column(sa.Column("participacao_mldu_efetiva", sa.Float(), nullable=True))
        if "participacao_mldu_manual" not in company_cols:
            batch_op.add_column(sa.Column("participacao_mldu_manual", sa.Float(), nullable=True))
        if "usa_participacao_manual" not in company_cols:
            batch_op.add_column(sa.Column("usa_participacao_manual", sa.Boolean(), nullable=True, server_default=sa.text("0")))


def downgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("usa_participacao_manual")
        batch_op.drop_column("participacao_mldu_manual")
        batch_op.drop_column("participacao_mldu_efetiva")

    op.drop_index("ix_company_ownership_links_child_company_id", table_name="company_ownership_links")
    op.drop_index("ix_company_ownership_links_parent_company_id", table_name="company_ownership_links")
    op.drop_table("company_ownership_links")
