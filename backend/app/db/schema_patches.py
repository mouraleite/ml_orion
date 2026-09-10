"""Patches idempotentes para SQLite/Postgres quando create_all e Alembic divergem."""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _has_column(engine: Engine, table: str, column: str) -> bool:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def _has_table(engine: Engine, table: str) -> bool:
    return table in inspect(engine).get_table_names()


def apply_schema_patches(engine: Engine) -> None:
    """Garante colunas/tabelas da Onda B (MLDU) sem falhar se já existirem."""
    dialect = engine.dialect.name

    with engine.begin() as conn:
        if not _has_table(engine, "company_ownership_links"):
            if dialect == "sqlite":
                conn.execute(
                    text(
                        """
                        CREATE TABLE company_ownership_links (
                            id INTEGER NOT NULL PRIMARY KEY,
                            parent_company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                            child_company_id INTEGER NOT NULL UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
                            percentage FLOAT NOT NULL,
                            consolidates BOOLEAN DEFAULT 1,
                            notes VARCHAR,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
            logger.info("schema_patches: criada tabela company_ownership_links")

        company_cols = (
            ("participacao_mldu_efetiva", "FLOAT"),
            ("participacao_mldu_manual", "FLOAT"),
            ("usa_participacao_manual", "BOOLEAN DEFAULT 0"),
        )
        for col, col_type in company_cols:
            if not _has_column(engine, "companies", col):
                conn.execute(text(f"ALTER TABLE companies ADD COLUMN {col} {col_type}"))
                logger.info("schema_patches: companies.%s adicionada", col)

        if not _has_table(engine, "company_ownership_periods"):
            if dialect == "sqlite":
                conn.execute(
                    text(
                        """
                        CREATE TABLE company_ownership_periods (
                            id INTEGER NOT NULL PRIMARY KEY,
                            link_id INTEGER NOT NULL REFERENCES company_ownership_links(id) ON DELETE CASCADE,
                            percentage FLOAT NOT NULL,
                            valid_from VARCHAR,
                            valid_until VARCHAR,
                            notes VARCHAR,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
            else:
                conn.execute(
                    text(
                        """
                        CREATE TABLE company_ownership_periods (
                            id SERIAL PRIMARY KEY,
                            link_id INTEGER NOT NULL REFERENCES company_ownership_links(id) ON DELETE CASCADE,
                            percentage FLOAT NOT NULL,
                            valid_from VARCHAR,
                            valid_until VARCHAR,
                            notes VARCHAR,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
            logger.info("schema_patches: criada tabela company_ownership_periods")

        if _has_table(engine, "company_partners") and not _has_column(engine, "company_partners", "partner_user_id"):
            if dialect == "sqlite":
                conn.execute(text("ALTER TABLE company_partners ADD COLUMN partner_user_id INTEGER REFERENCES users(id)"))
            else:
                conn.execute(text("ALTER TABLE company_partners ADD COLUMN partner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL"))
            logger.info("schema_patches: company_partners.partner_user_id adicionada")

        if not _has_table(engine, "user_perfis"):
            if dialect == "sqlite":
                conn.execute(
                    text(
                        """
                        CREATE TABLE user_perfis (
                            user_id INTEGER NOT NULL REFERENCES users(id),
                            perfil_id INTEGER NOT NULL REFERENCES access_profiles(id),
                            PRIMARY KEY (user_id, perfil_id)
                        )
                        """
                    )
                )
            else:
                conn.execute(
                    text(
                        """
                        CREATE TABLE user_perfis (
                            user_id INTEGER NOT NULL REFERENCES users(id),
                            perfil_id INTEGER NOT NULL REFERENCES access_profiles(id),
                            PRIMARY KEY (user_id, perfil_id)
                        )
                        """
                    )
                )
            logger.info("schema_patches: criada tabela user_perfis")

        if not _has_table(engine, "depara_autorizacao_departamento"):
            if dialect == "sqlite":
                conn.execute(
                    text(
                        """
                        CREATE TABLE depara_autorizacao_departamento (
                            id INTEGER NOT NULL PRIMARY KEY,
                            nome_sienge VARCHAR NOT NULL UNIQUE,
                            sienge_department_id INTEGER,
                            departamento_id INTEGER REFERENCES departamentos(id),
                            definido_manual BOOLEAN NOT NULL DEFAULT 0
                        )
                        """
                    )
                )
            else:
                conn.execute(
                    text(
                        """
                        CREATE TABLE depara_autorizacao_departamento (
                            id SERIAL PRIMARY KEY,
                            nome_sienge VARCHAR NOT NULL UNIQUE,
                            sienge_department_id INTEGER,
                            departamento_id INTEGER REFERENCES departamentos(id),
                            definido_manual BOOLEAN NOT NULL DEFAULT FALSE
                        )
                        """
                    )
                )
            logger.info("schema_patches: criada tabela depara_autorizacao_departamento")

        if _has_table(engine, "actual_transactions") and not _has_column(engine, "actual_transactions", "authorization_name"):
            conn.execute(text("ALTER TABLE actual_transactions ADD COLUMN authorization_name VARCHAR"))
            logger.info("schema_patches: actual_transactions.authorization_name adicionada")

        if _has_table(engine, "departamentos"):
            if not _has_column(engine, "departamentos", "is_residual"):
                if dialect == "sqlite":
                    conn.execute(text("ALTER TABLE departamentos ADD COLUMN is_residual BOOLEAN NOT NULL DEFAULT 0"))
                else:
                    conn.execute(text("ALTER TABLE departamentos ADD COLUMN is_residual BOOLEAN NOT NULL DEFAULT FALSE"))
                logger.info("schema_patches: departamentos.is_residual adicionada")
            conn.execute(
                text(
                    """
                    UPDATE departamentos
                    SET nome = 'Corporativo', is_residual = TRUE
                    WHERE nome = 'Consolidado - Sienge'
                    """
                )
            )
            conn.execute(
                text(
                    """
                    UPDATE departamentos
                    SET is_residual = TRUE
                    WHERE nome = 'Corporativo'
                    """
                )
            )

        if not _has_table(engine, "diretorias"):
            if dialect == "sqlite":
                conn.execute(
                    text(
                        """
                        CREATE TABLE diretorias (
                            id INTEGER NOT NULL PRIMARY KEY,
                            nome VARCHAR NOT NULL,
                            ativo BOOLEAN NOT NULL DEFAULT 1
                        )
                        """
                    )
                )
            else:
                conn.execute(
                    text(
                        """
                        CREATE TABLE diretorias (
                            id SERIAL PRIMARY KEY,
                            nome VARCHAR NOT NULL,
                            ativo BOOLEAN NOT NULL DEFAULT TRUE
                        )
                        """
                    )
                )
            logger.info("schema_patches: criada tabela diretorias")

        if _has_table(engine, "departamentos") and not _has_column(engine, "departamentos", "diretoria_id"):
            conn.execute(text("ALTER TABLE departamentos ADD COLUMN diretoria_id INTEGER REFERENCES diretorias(id)"))
            logger.info("schema_patches: departamentos.diretoria_id adicionada")

        if _has_table(engine, "users") and not _has_column(engine, "users", "microsoft_oid"):
            conn.execute(text("ALTER TABLE users ADD COLUMN microsoft_oid VARCHAR"))
            try:
                conn.execute(text("CREATE UNIQUE INDEX ix_users_microsoft_oid ON users (microsoft_oid)"))
            except Exception:
                logger.exception("schema_patches: índice microsoft_oid")
            logger.info("schema_patches: users.microsoft_oid adicionada")

        if _has_table(engine, "users"):
            conn.execute(
                text(
                    """
                    INSERT INTO user_perfis (user_id, perfil_id)
                    SELECT id, perfil_id FROM users
                    WHERE perfil_id IS NOT NULL
                      AND NOT EXISTS (
                        SELECT 1 FROM user_perfis up
                        WHERE up.user_id = users.id AND up.perfil_id = users.perfil_id
                      )
                    """
                )
            )
