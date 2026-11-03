"""Vincula viabilidade aprovada ao centro de custo da obra no acompanhamento."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261103_viability_obra_cc"
down_revision: Union[str, None] = "20260929_sienge_api_calls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "viabilities" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("viabilities")}
    if "obra_cost_center_id" in cols:
        return
    op.add_column(
        "viabilities",
        sa.Column("obra_cost_center_id", sa.Integer(), nullable=True),
    )
    if "cost_centers" in insp.get_table_names() and bind.dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_viabilities_obra_cost_center_id",
            "viabilities",
            "cost_centers",
            ["obra_cost_center_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "viabilities" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("viabilities")}
    if "obra_cost_center_id" not in cols:
        return
    if bind.dialect.name != "sqlite":
        try:
            op.drop_constraint("fk_viabilities_obra_cost_center_id", "viabilities", type_="foreignkey")
        except Exception:
            pass
    op.drop_column("viabilities", "obra_cost_center_id")
