"""phase_fundings.taxa_juros_periodicidade: taxa do funding digitada ao ano ou ao mês."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261109_funding_periodicidade"
down_revision: Union[str, None] = "20261106_sienge_account_balances"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "phase_fundings" not in insp.get_table_names():
        return
    if "taxa_juros_periodicidade" in {c["name"] for c in insp.get_columns("phase_fundings")}:
        return
    op.add_column(
        "phase_fundings",
        sa.Column("taxa_juros_periodicidade", sa.String(), nullable=True, server_default="a.a."),
    )
    op.execute("UPDATE phase_fundings SET taxa_juros_periodicidade = 'a.a.' WHERE taxa_juros_periodicidade IS NULL")


def downgrade() -> None:
    op.drop_column("phase_fundings", "taxa_juros_periodicidade")
