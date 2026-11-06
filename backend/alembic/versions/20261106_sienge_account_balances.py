"""Snapshot 31/12 de contas correntes B+I+C (Sienge accounts-balances)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261106_sienge_account_balances"
down_revision: Union[str, None] = "20261103_viability_obra_cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "sienge_account_balances" in insp.get_table_names():
        return
    op.create_table(
        "sienge_account_balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id_sienge", sa.String(), nullable=False),
        sa.Column("account_number", sa.String(), nullable=False),
        sa.Column("account_name", sa.String(), nullable=True),
        sa.Column("account_type", sa.String(length=8), nullable=False),
        sa.Column("balance_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "company_id_sienge",
            "account_number",
            "balance_date",
            name="uq_sienge_account_balances_key",
        ),
    )
    op.create_index(
        "ix_sienge_account_balances_company_id_sienge",
        "sienge_account_balances",
        ["company_id_sienge"],
    )
    op.create_index(
        "ix_sienge_account_balances_account_type",
        "sienge_account_balances",
        ["account_type"],
    )
    op.create_index(
        "ix_sienge_account_balances_balance_date",
        "sienge_account_balances",
        ["balance_date"],
    )
    op.create_index(
        "ix_sienge_account_balances_date_type",
        "sienge_account_balances",
        ["balance_date", "account_type"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "sienge_account_balances" not in insp.get_table_names():
        return
    op.drop_index("ix_sienge_account_balances_date_type", table_name="sienge_account_balances")
    op.drop_index("ix_sienge_account_balances_balance_date", table_name="sienge_account_balances")
    op.drop_index("ix_sienge_account_balances_account_type", table_name="sienge_account_balances")
    op.drop_index(
        "ix_sienge_account_balances_company_id_sienge",
        table_name="sienge_account_balances",
    )
    op.drop_table("sienge_account_balances")
