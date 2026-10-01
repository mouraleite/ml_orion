"""Transições de status do Orçamento e do Forecast.

Regra (3 set 2026): analista envia; gerente/diretor/admin aprova e fecha,
ou rejeita e devolve ao rascunho. Pedido 'Aprovado' a partir de
'Em aprovação' grava Fechado — o estado Aprovado deixa de ser destino novo.
"""

from fastapi import HTTPException

from app.core.roles import is_gestor_user

ACOES_GESTOR = frozenset({"aprovar", "rejeitar", "recusar_reabertura", "aprovar_reabertura"})


def resolver_transicao(status_atual: str, pedido: str) -> tuple[str, str]:
    """Devolve (status a gravar, ação). Ação: enviar | aprovar | rejeitar | solicitar_reabertura | recusar_reabertura."""
    atual = (status_atual or "").strip()
    novo = (pedido or "").strip()

    if atual in ("Rascunho", "Reaberto") and novo == "Em aprovação":
        return "Em aprovação", "enviar"
    if atual == "Em aprovação" and novo in ("Fechado", "Aprovado"):
        return "Fechado", "aprovar"
    if atual == "Em aprovação" and novo == "Rascunho":
        return "Rascunho", "rejeitar"
    if atual in ("Fechado", "Aprovado") and novo == "Solicitação Reabertura":
        return "Solicitação Reabertura", "solicitar_reabertura"
    if atual == "Solicitação Reabertura" and novo == "Fechado":
        return "Fechado", "recusar_reabertura"
    if atual == "Solicitação Reabertura" and novo == "Reaberto":
        return "Reaberto", "aprovar_reabertura"

    raise HTTPException(
        status_code=400,
        detail=f"Não é permitido ir de {atual or '—'} para {novo or '—'}.",
    )


def exigir_permissao_status(acao: str, user) -> None:
    if acao in ACOES_GESTOR and not is_gestor_user(user):
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para aprovar ou rejeitar.",
        )


def irmaos_mesmo_grupo(db, modelo, registro):
    """Registros do mesmo documento (ano + tipo + descrição), sem Substituído."""
    q = db.query(modelo).filter(
        modelo.ano == registro.ano,
        modelo.tipo == registro.tipo,
        modelo.status != "Substituído",
        modelo.descricao == registro.descricao,
    )
    dept_id = getattr(registro, "departamento_id", None)
    if dept_id is not None and hasattr(modelo, "departamento_id"):
        q = q.filter(modelo.departamento_id == dept_id)
    return q.all()
