"""Persiste authorizations.name nas parcelas de contas a pagar."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_authorization_name"
down_revision: Union[str, None] = "20260909_depara_autorizacao"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "actual_transactions" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("actual_transactions")}
    if "authorization_name" in cols:
        return
    op.add_column("actual_transactions", sa.Column("authorization_name", sa.String(), nullable=True))
    op.create_index(
        "ix_actual_transactions_authorization_name",
        "actual_transactions",
        ["authorization_name"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "actual_transactions" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("actual_transactions")}
    if "authorization_name" not in cols:
        return
    op.drop_index("ix_actual_transactions_authorization_name", table_name="actual_transactions")
    op.drop_column("actual_transactions", "authorization_name")
