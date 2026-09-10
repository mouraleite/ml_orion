"""Diretorias: agrupamento de departamentos."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_diretorias"
down_revision: Union[str, None] = "20260909_corporativo_residual"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "diretorias" not in tables:
        op.create_table(
            "diretorias",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nome", sa.String(), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.create_index("ix_diretorias_nome", "diretorias", ["nome"])
    if "departamentos" in tables:
        cols = {c["name"] for c in insp.get_columns("departamentos")}
        if "diretoria_id" not in cols:
            op.add_column(
                "departamentos",
                sa.Column("diretoria_id", sa.Integer(), sa.ForeignKey("diretorias.id"), nullable=True),
            )
            op.create_index("ix_departamentos_diretoria_id", "departamentos", ["diretoria_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "departamentos" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("departamentos")}
        if "diretoria_id" in cols:
            op.drop_index("ix_departamentos_diretoria_id", table_name="departamentos")
            op.drop_column("departamentos", "diretoria_id")
    if "diretorias" in insp.get_table_names():
        op.drop_index("ix_diretorias_nome", table_name="diretorias")
        op.drop_table("diretorias")
