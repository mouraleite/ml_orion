"""De-para: name da autorização / departamento Sienge → departamento do Apoio.

Não filtra orçado nem realizado. Corporativo = departamento_id nulo.
Corporativo (residual) não é alvo de casamento.
"""
from __future__ import annotations

import unicodedata
from typing import Any, Optional

from app.services.corporativo import eh_corporativo

CONSOLIDADO_SIENGE_NORM = "consolidado - sienge"


def normalizar_nome(nome: str | None) -> str:
    s = " ".join((nome or "").strip().split())
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.casefold()


def eh_consolidado_sienge(nome: str | None) -> bool:
    """Compat: residual Corporativo (inclui o nome legado)."""
    return eh_corporativo(nome)


def _dept_id_nome(dept: Any) -> tuple[int, str]:
    if isinstance(dept, dict):
        return int(dept["id"]), str(dept.get("nome") or "")
    return int(dept.id), str(getattr(dept, "nome", "") or "")


def sugerir_departamento_id(nome_sienge: str | None, departamentos: list[Any]) -> Optional[int]:
    alvo = normalizar_nome(nome_sienge)
    if not alvo:
        return None
    for dept in departamentos:
        did, nome = _dept_id_nome(dept)
        if eh_corporativo(nome):
            continue
        if normalizar_nome(nome) == alvo:
            return did
    return None


def sincronizar_depara(db: Any, sienge_depts: list[dict]) -> list:
    """Cria/atualiza linhas a partir de /departments. Não sobrescreve definido_manual."""
    from app.models.departamento import Departamento, DeparaAutorizacaoDepartamento

    internos = db.query(Departamento).all()
    existentes = {
        normalizar_nome(r.nome_sienge): r
        for r in db.query(DeparaAutorizacaoDepartamento).all()
    }
    for item in sienge_depts:
        nome = str(item.get("name") or "").strip()
        if not nome:
            continue
        sid = item.get("id")
        key = normalizar_nome(nome)
        sugestao = sugerir_departamento_id(nome, internos)
        row = existentes.get(key)
        if row is None:
            row = DeparaAutorizacaoDepartamento(
                nome_sienge=nome,
                sienge_department_id=int(sid) if sid is not None else None,
                departamento_id=sugestao,
                definido_manual=False,
            )
            db.add(row)
            existentes[key] = row
            continue
        if sid is not None:
            row.sienge_department_id = int(sid)
        row.nome_sienge = nome
        if not row.definido_manual:
            row.departamento_id = sugestao
    db.commit()
    return (
        db.query(DeparaAutorizacaoDepartamento)
        .order_by(DeparaAutorizacaoDepartamento.nome_sienge)
        .all()
    )


def depara_payload(row: Any) -> dict:
    dept = getattr(row, "departamento", None)
    return {
        "id": row.id,
        "nome_sienge": row.nome_sienge,
        "sienge_department_id": row.sienge_department_id,
        "departamento_id": row.departamento_id,
        "departamento_nome": dept.nome if dept else None,
        "definido_manual": bool(row.definido_manual),
        "corporativo": row.departamento_id is None,
    }


def aplicar_depara_manual(db: Any, row_id: int, departamento_id: Optional[int]) -> Any:
    from app.models.departamento import Departamento, DeparaAutorizacaoDepartamento

    row = db.query(DeparaAutorizacaoDepartamento).filter(DeparaAutorizacaoDepartamento.id == row_id).first()
    if row is None:
        raise LookupError("depara")
    if departamento_id is not None:
        dept = db.query(Departamento).filter(Departamento.id == departamento_id).first()
        if dept is None:
            raise ValueError("departamento")
        if eh_corporativo(dept.nome) or getattr(dept, "is_residual", False):
            raise ValueError("consolidado")
    row.departamento_id = departamento_id
    row.definido_manual = True
    db.commit()
    db.refresh(row)
    return row
