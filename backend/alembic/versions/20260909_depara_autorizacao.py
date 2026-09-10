"""De-para name Sienge → departamento do Apoio."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_depara_autorizacao"
down_revision: Union[str, None] = "20260904_ownership_periods"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "depara_autorizacao_departamento" in insp.get_table_names():
        return
    op.create_table(
        "depara_autorizacao_departamento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome_sienge", sa.String(), nullable=False),
        sa.Column("sienge_department_id", sa.Integer(), nullable=True),
        sa.Column("departamento_id", sa.Integer(), nullable=True),
        sa.Column("definido_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["departamento_id"], ["departamentos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome_sienge"),
    )
    op.create_index(
        "ix_depara_autorizacao_departamento_nome_sienge",
        "depara_autorizacao_departamento",
        ["nome_sienge"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "depara_autorizacao_departamento" not in insp.get_table_names():
        return
    op.drop_index(
        "ix_depara_autorizacao_departamento_nome_sienge",
        table_name="depara_autorizacao_departamento",
    )
    op.drop_table("depara_autorizacao_departamento")
