"""Rota de despesas por empreendimento. Não altera orçado/realizado/forecast — só lê."""
from __future__ import annotations

import copy
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.resposta_rapida import RespostaJSON
from app.api.deps import get_active_department, get_current_user, get_db
from app.api.routes.acompanhamento import get_acompanhamento_despesas
from app.api.routes.dashboard import _ids_forecast_dfc, _versoes_forecast_dfc, _visao_padrao_spec
from app.models.departamento import Departamento
from app.models.forecast import Forecast
from app.services.budget_shared import (
    expand_empresa_filter_ids,
    filter_itens_por_empresa_ids,
    list_forecast_versoes_disponiveis,
    merge_opcoes_produtos,
)
from app.services.holding_consolidation import maybe_apply_holding_mldu
from app.services.orcamento_despesas_empreendimento import CORTE_PADRAO, montar_despesas_empreendimento

router = APIRouter()


def _itens_mldu(db: Session, payload: dict, itens: list) -> tuple[list, list]:
    scaled = maybe_apply_holding_mldu(
        db,
        True,
        {**payload, "itens": copy.deepcopy(itens)},
        item_kind="acom_despesas",
    )
    return scaled.get("itens", []), list(scaled.get("holding_avisos") or [])


def _forecast_desp_id(db: Session, forecast_id: Optional[int], ano: int, dept_id: int) -> Optional[int]:
    desp_id, _rec_id = _ids_forecast_dfc(db, forecast_id, ano, dept_id)
    return desp_id


def _descricao_forecast(db: Session, forecast_id: Optional[int]) -> Optional[str]:
    if not forecast_id:
        return None
    row = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    return (row.descricao if row else None) or None


def _forecast_desp_id_ano(
    db: Session,
    ano: int,
    dept_id: int,
    descricao: Optional[str],
) -> tuple[Optional[int], list]:
    versoes = list(list_forecast_versoes_disponiveis(db, ano, "DESPESAS", dept_id) or [])
    if descricao:
        for v in versoes:
            if (v.get("descricao") or "") == descricao:
                return v.get("id"), versoes
    return (versoes[0].get("id") if versoes else None), versoes


@router.get("/despesas-empreendimento/{ano}")
def get_despesas_empreendimento(
    ano: int,
    corte: int = CORTE_PADRAO,
    consolidado: bool = False,
    empresa_ids: Optional[str] = None,
    forecast_id: Optional[int] = None,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    """Real do ano (YTD) + forecast (YTG) contra orçado/forecast do ano seguinte. Só despesas 05.xx."""
    vision, nodes_spec = _visao_padrao_spec(db)
    ano_ref = ano + 1
    desp_id_n = _forecast_desp_id(db, forecast_id, ano, dept.id)
    descricao = _descricao_forecast(db, desp_id_n or forecast_id)
    desp_id_ref, versoes_ref = _forecast_desp_id_ano(db, ano_ref, dept.id, descricao)

    desp_n = get_acompanhamento_despesas(
        ano, consolidado, False, db, dept, current_user, forecast_id=desp_id_n, realizado_agrupado=True
    )
    desp_ref = get_acompanhamento_despesas(
        ano_ref, consolidado, False, db, dept, current_user, forecast_id=desp_id_ref, realizado_agrupado=True
    )

    desp_itens = desp_n.get("itens", [])
    desp_itens_ref = desp_ref.get("itens", [])
    opcoes_produtos = merge_opcoes_produtos(
        desp_n.get("opcoes_produtos"),
        desp_ref.get("opcoes_produtos"),
    )
    ids_empresa = [e.strip() for e in empresa_ids.split(",")] if empresa_ids else []
    ids_empresa = expand_empresa_filter_ids(db, ids_empresa)
    if ids_empresa:
        desp_itens = filter_itens_por_empresa_ids(desp_itens, opcoes_produtos, ids_empresa)
        desp_itens_ref = filter_itens_por_empresa_ids(desp_itens_ref, opcoes_produtos, ids_empresa)

    desp_mldu, avisos_n = _itens_mldu(db, desp_n, desp_itens)
    desp_ref_mldu, avisos_ref = _itens_mldu(db, desp_ref, desp_itens_ref)

    arvore = montar_despesas_empreendimento(
        nodes_spec,
        desp_itens,
        desp_mldu,
        desp_itens_ref,
        desp_ref_mldu,
        opcoes_produtos,
        corte=corte,
    )

    avisos = list(dict.fromkeys(avisos_n + avisos_ref))
    if descricao and not desp_id_ref:
        avisos.append(f"Não há forecast de despesas em {ano_ref} com a descrição «{descricao}».")

    return RespostaJSON({
        "ano": ano,
        "ano_ref": ano_ref,
        "visao": (
            {"id": vision.id, "nome": vision.nome, "is_padrao": bool(vision.is_padrao)}
            if vision
            else None
        ),
        "active_forecast_id": desp_id_n or desp_n.get("active_forecast_id"),
        "active_forecast_id_ref": desp_id_ref or desp_ref.get("active_forecast_id"),
        "versoes_disponiveis": _versoes_forecast_dfc(db, ano, dept.id),
        "versoes_disponiveis_ref": versoes_ref,
        **arvore,
        "opcoes_produtos": opcoes_produtos,
        "holding_avisos": avisos,
    })
