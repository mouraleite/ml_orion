"""Log de chamadas deste ERP às APIs Sienge (REST e BULK)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260929_sienge_api_calls"
down_revision: Union[str, None] = "20260910_microsoft_oid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "sienge_api_calls" in insp.get_table_names():
        return
    op.create_table(
        "sienge_api_calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("family", sa.String(length=8), nullable=False),
        sa.Column("method", sa.String(length=8), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.create_index("ix_sienge_api_calls_created_at", "sienge_api_calls", ["created_at"])
    op.create_index("ix_sienge_api_calls_family", "sienge_api_calls", ["family"])
    op.create_index(
        "ix_sienge_api_calls_created_family",
        "sienge_api_calls",
        ["created_at", "family"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "sienge_api_calls" not in insp.get_table_names():
        return
    op.drop_index("ix_sienge_api_calls_created_family", table_name="sienge_api_calls")
    op.drop_index("ix_sienge_api_calls_family", table_name="sienge_api_calls")
    op.drop_index("ix_sienge_api_calls_created_at", table_name="sienge_api_calls")
    op.drop_table("sienge_api_calls")
