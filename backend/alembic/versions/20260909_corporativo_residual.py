"""Renomeia Consolidado - Sienge → Corporativo e marca residual."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_corporativo_residual"
down_revision: Union[str, None] = "20260909_authorization_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "departamentos" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("departamentos")}
    if "is_residual" not in cols:
        op.add_column(
            "departamentos",
            sa.Column("is_residual", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    op.execute(
        sa.text(
            """
            UPDATE departamentos
            SET nome = 'Corporativo', is_residual = TRUE
            WHERE nome = 'Consolidado - Sienge' OR is_residual = TRUE
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE departamentos
            SET is_residual = TRUE
            WHERE nome = 'Corporativo'
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "departamentos" not in insp.get_table_names():
        return
    op.execute(
        sa.text(
            """
            UPDATE departamentos
            SET nome = 'Consolidado - Sienge'
            WHERE nome = 'Corporativo' AND is_residual = TRUE
            """
        )
    )
    cols = {c["name"] for c in insp.get_columns("departamentos")}
    if "is_residual" in cols:
        op.drop_column("departamentos", "is_residual")
