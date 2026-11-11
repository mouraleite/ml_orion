"""Tipos de coluna compartilhados.

Dinheiro: continua FLOAT no banco (nenhuma migração), mas todo valor gravado — pelo
ORM, por bulk_save_objects ou por insert/update do Core — é arredondado a centavo.
Etapa 1 da correção de centavos (11/11/2026): antes ~30% dos lançamentos tinham
resíduo abaixo do centavo (ex.: 281,549999999726). A troca para NUMERIC(14,2) e a
correção do histórico ficam para depois da reindexação do Neon.
"""
from sqlalchemy.types import Float, TypeDecorator


class Dinheiro(TypeDecorator):
    impl = Float
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return value
