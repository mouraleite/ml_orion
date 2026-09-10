"""SSO Microsoft: oid + senha opcional."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260910_microsoft_oid"
down_revision: Union[str, None] = "20260909_diretorias"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "microsoft_oid" not in cols:
        op.add_column("users", sa.Column("microsoft_oid", sa.String(), nullable=True))
        op.create_index("ix_users_microsoft_oid", "users", ["microsoft_oid"], unique=True)
    # SQLite: ALTER COLUMN limited; nullable via batch when needed.
    dialect = bind.dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.alter_column("hashed_password", existing_type=sa.String(), nullable=True)
    else:
        op.alter_column("users", "hashed_password", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    dialect = bind.dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.alter_column("hashed_password", existing_type=sa.String(), nullable=False)
    else:
        op.alter_column("users", "hashed_password", existing_type=sa.String(), nullable=False)
    if "microsoft_oid" in cols:
        op.drop_index("ix_users_microsoft_oid", table_name="users")
        op.drop_column("users", "microsoft_oid")
