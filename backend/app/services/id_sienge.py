"""ID público = ID Sienge. Amarração nunca é por nome.

Empresas, centros de custo, obras e 'obra e centro de custo' usam o código
Sienge como chave (Terras de Itu = 4, Novo Horizonte = 32). Nome é rótulo.
O PK interno do cadastro não entra no mapa, no filtro nem na árvore.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional, Sequence, TypeVar

T = TypeVar("T")


def chave_sienge(ent) -> str:
    v = getattr(ent, "id_sienge", None)
    return str(v).strip() if v not in (None, "") else ""


def mapa_nome_sienge_primeiro(
    entidades: Iterable,
    nome_fn: Callable[[Any], str],
) -> dict[str, str]:
    """Mapa id Sienge → nome. O PK interno não vira chave."""
    by_sienge: dict[str, str] = {}
    for e in entidades:
        sienge = chave_sienge(e)
        if sienge:
            by_sienge[sienge] = nome_fn(e)
    return by_sienge


def indexar_sienge_e_pk(entidades: Iterable[T]) -> tuple[dict[str, T], dict[str, T]]:
    by_sienge: dict[str, T] = {}
    by_id: dict[str, T] = {}
    for e in entidades:
        by_id[str(getattr(e, "id"))] = e
        sienge = chave_sienge(e)
        if sienge:
            by_sienge[sienge] = e
    return by_sienge, by_id


def resolver_sienge_ou_pk(entidades: Iterable[T], raw_id: Any) -> Optional[T]:
    """Acha a entidade pelo Sienge; só cai no PK se ninguém tiver esse Sienge."""
    key = str(raw_id or "").strip()
    if not key:
        return None
    by_sienge, by_id = indexar_sienge_e_pk(entidades)
    return by_sienge.get(key) or by_id.get(key)


def expand_ids_sienge_primeiro(
    entidades: Iterable,
    ids: Sequence[str] | None,
) -> list[str]:
    """Normaliza o filtro para o ID Sienge da entidade. PK interno não sai no resultado."""
    wanted = {str(e).strip() for e in (ids or []) if str(e).strip()}
    if not wanted:
        return []
    by_sienge, by_id = indexar_sienge_e_pk(entidades)
    resolved: set[str] = set()
    for raw in wanted:
        ent = by_sienge.get(raw) or by_id.get(raw)
        if ent is None:
            resolved.add(raw)
            continue
        sienge = chave_sienge(ent)
        resolved.add(sienge if sienge else raw)
    return list(resolved)


def get_by_sienge_or_pk(db, model, raw_id: Any):
    """Consulta: Sienge primeiro (único); PK só se não houver Sienge com esse código."""
    key = str(raw_id or "").strip()
    if not key:
        return None
    row = db.query(model).filter(model.id_sienge == key).first()
    if row is not None:
        return row
    if key.lstrip("-").isdigit():
        return db.query(model).filter(model.id == int(key)).first()
    return None


def centros_nome_por_id(centros: Iterable) -> dict[str, str]:
    return mapa_nome_sienge_primeiro(
        centros,
        lambda c: getattr(c, "nome", None) or f"Centro {c.id}",
    )
