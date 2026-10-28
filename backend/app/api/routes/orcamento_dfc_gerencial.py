"""Rota do DFC gerencial. Não altera o DFC atual — só lê as mesmas fontes."""
from __future__ import annotations

import copy
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_active_department, get_current_user, get_db
from app.api.routes.acompanhamento import (
    get_acompanhamento_despesas,
    get_acompanhamento_receitas,
)
from app.api.routes.dashboard import (
    _ids_forecast_dfc,
    _versoes_forecast_dfc,
    _visao_padrao_spec,
)
from app.services.periodos import MESES_STR
from app.models.departamento import Departamento
from app.services.budget_shared import (
    expand_empresa_filter_ids,
    filter_itens_por_empresa_ids,
    merge_opcoes_produtos,
)
from app.services.holding_consolidation import maybe_apply_holding_mldu
from app.services.orcamento_dfc_gerencial import AGRUPAMENTO_CENTRO, montar_dfc_gerencial

router = APIRouter()


def _itens_mldu(db: Session, payload: dict, itens: list, item_kind: str) -> tuple[list, list]:
    scaled = maybe_apply_holding_mldu(
        db,
        True,
        {**payload, "itens": copy.deepcopy(itens)},
        item_kind=item_kind,
    )
    return scaled.get("itens", []), list(scaled.get("holding_avisos") or [])


@router.get("/dfc/{ano}/gerencial")
def get_orcamento_dfc_gerencial(
    ano: int,
    consolidado: bool = False,
    meses: Optional[str] = None,
    empresa_ids: Optional[str] = None,
    forecast_id: Optional[int] = None,
    agrupamento: str = "visao",
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    """Mesmos números do DFC, com cheio e MLDU lado a lado, por empresa e CC."""
    vision, nodes_spec = _visao_padrao_spec(db)
    desp_id, rec_id = _ids_forecast_dfc(db, forecast_id, ano, dept.id)

    desp_n = get_acompanhamento_despesas(
        ano, consolidado, False, db, dept, current_user, forecast_id=desp_id, realizado_agrupado=True
    )
    rec_n = get_acompanhamento_receitas(
        ano, consolidado, False, db, dept, current_user, forecast_id=rec_id, realizado_agrupado=True
    )
    desp_n1 = get_acompanhamento_despesas(
        ano - 1, consolidado, False, db, dept, current_user, realizado_agrupado=True
    )
    rec_n1 = get_acompanhamento_receitas(
        ano - 1, consolidado, False, db, dept, current_user, realizado_agrupado=True
    )

    desp_itens = desp_n.get("itens", [])
    rec_itens = rec_n.get("itens", [])
    desp_itens_n1 = desp_n1.get("itens", [])
    rec_itens_n1 = rec_n1.get("itens", [])

    opcoes_produtos = merge_opcoes_produtos(
        desp_n.get("opcoes_produtos"),
        rec_n.get("opcoes_produtos"),
        desp_n1.get("opcoes_produtos"),
        rec_n1.get("opcoes_produtos"),
    )
    ids_empresa = [e.strip() for e in empresa_ids.split(",")] if empresa_ids else []
    ids_empresa = expand_empresa_filter_ids(db, ids_empresa)
    if ids_empresa:
        desp_itens = filter_itens_por_empresa_ids(desp_itens, opcoes_produtos, ids_empresa)
        rec_itens = filter_itens_por_empresa_ids(rec_itens, opcoes_produtos, ids_empresa)
        desp_itens_n1 = filter_itens_por_empresa_ids(desp_itens_n1, opcoes_produtos, ids_empresa)
        rec_itens_n1 = filter_itens_por_empresa_ids(rec_itens_n1, opcoes_produtos, ids_empresa)

    meses_validos = [m.strip() for m in meses.split(",")] if meses else list(MESES_STR)
    meses_validos = [m for m in meses_validos if m in MESES_STR]
    if not meses_validos:
        meses_validos = list(MESES_STR)

    desp_mldu, avisos_desp = _itens_mldu(db, desp_n, desp_itens, "acom_despesas")
    rec_mldu, avisos_rec = _itens_mldu(db, rec_n, rec_itens, "acom_receitas")
    desp_n1_mldu, avisos_desp_n1 = _itens_mldu(db, desp_n1, desp_itens_n1, "acom_despesas")
    rec_n1_mldu, avisos_rec_n1 = _itens_mldu(db, rec_n1, rec_itens_n1, "acom_receitas")

    arvore = montar_dfc_gerencial(
        nodes_spec,
        rec_itens,
        desp_itens,
        rec_mldu,
        desp_mldu,
        rec_itens_n1,
        desp_itens_n1,
        rec_n1_mldu,
        desp_n1_mldu,
        opcoes_produtos,
        meses_validos,
        agrupamento=AGRUPAMENTO_CENTRO if agrupamento == AGRUPAMENTO_CENTRO else "visao",
    )

    avisos = list(dict.fromkeys(avisos_desp + avisos_rec + avisos_desp_n1 + avisos_rec_n1))

    return {
        "ano": ano,
        "ano_anterior": ano - 1,
        "meses_selecionados": meses_validos,
        "visao": (
            {"id": vision.id, "nome": vision.nome, "is_padrao": bool(vision.is_padrao)}
            if vision
            else None
        ),
        "ah_base": "real_n1",
        "av_ancora": "total_entradas",
        "active_forecast_id": desp_id or rec_id or desp_n.get("active_forecast_id") or rec_n.get("active_forecast_id"),
        "versoes_disponiveis": _versoes_forecast_dfc(db, ano, dept.id),
        **arvore,
        "opcoes_produtos": opcoes_produtos,
        "holding_avisos": avisos,
    }
