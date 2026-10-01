from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from app.api.deps import get_db, get_current_user, get_active_department
from app.models.forecast import Forecast, ForecastItem, ForecastVendaItem
from app.models.orcamento import Orcamento, OrcamentoItem, OrcamentoVendaItem
from app.models.fechamento import ClosedMonth
from app.models.departamento import Departamento, DepartamentoPlano, ProdutoPlanoFinanceiro
from app.models.cost_center import CostCenter
from app.models.company import Company
from app.models.financial_plan import FinancialPlan
from app.models.payment_plan import PaymentPlan
from app.models.actual_transaction import ActualTransaction
from app.schemas.forecast import ForecastCreateRequest, ForecastDespesasSaveRequest, ForecastStatusRequest
from app.core.roles import is_admin_user
from app.services.auth_matrix import validate_budget_allocation
from app.services.periodos import MESES_STR, skip_linha_total_zero
from app.services.budget_shared import (
    STATUS_ORCAMENTO_BLOQUEADO,
    build_empresas_map,
    build_opcoes_planos,
    build_opcoes_produtos,
    check_pessimistic_lock,
    copy_monthly_items_to_forecast,
    copy_venda_items_to_forecast,
    dedupe_versoes_por_descricao,
    group_venda_items,
    list_forecast_versoes_disponiveis,
    merge_catalog_with_used_items,
    pode_editar_orcamento_vendas,
    resolve_forecast_despesas_catalog,
    resolve_forecast_receitas_catalog,
    serialize_base_monthly_item,
    serialize_monthly_item_row,
    serialize_venda_base_item,
)
from app.services.sharepoint_departamento import fix_forecasts_sharepoint_sem_departamento
from app.services.departamento_leitura import criterio_departamento
from app.services.holding_consolidation import maybe_apply_holding_mldu
from app.models.auditoria import Auditoria
from app.services.budget_status import (
    exigir_permissao_status,
    irmaos_mesmo_grupo,
    resolver_transicao,
)

router = APIRouter()


def _descricao_forecast_rolling(ano: int) -> str:
    hoje = datetime.now()
    if ano == hoje.year:
        meses_realizados = hoje.month - 1
        meses_projetados = 13 - hoje.month
    elif ano < hoje.year:
        meses_realizados, meses_projetados = 12, 0
    else:
        meses_realizados, meses_projetados = 0, 12
    return f"Forecast - {meses_realizados}+{meses_projetados}"


def _exigir_vendas(current_user, dept: Departamento) -> None:
    if not pode_editar_orcamento_vendas(current_user, dept):
        raise HTTPException(status_code=403, detail="Restrito ao departamento Vendas.")


def _nome_empreendimento(db: Session, produto_id: int) -> str:
    p = db.query(CostCenter).filter(CostCenter.id == produto_id).first()
    if not p:
        return str(produto_id)
    if p.id_sienge:
        return f"{p.id_sienge} - {p.nome}"
    return p.nome or str(produto_id)


def _docs_forecast_versao(db: Session, ano: int, tipo: str, dept_id: int, descricao: str) -> list[Forecast]:
    return (
        db.query(Forecast)
        .filter(
            Forecast.ano == ano,
            Forecast.tipo == tipo,
            Forecast.departamento_id == dept_id,
            Forecast.descricao == descricao,
            Forecast.status != "Substituído",
        )
        .order_by(Forecast.versao_numero.desc(), Forecast.id.desc())
        .all()
    )


def _produtos_nos_forecasts(db: Session, docs: list[Forecast], tipo: str) -> set[int]:
    ids: set[int] = set()
    for fc in docs:
        if fc.produto_id:
            ids.add(fc.produto_id)
        if tipo == "VENDAS":
            rows = (
                db.query(ForecastVendaItem.produto_id)
                .filter(ForecastVendaItem.forecast_id == fc.id)
                .distinct()
                .all()
            )
        else:
            rows = (
                db.query(ForecastItem.produto_id)
                .filter(ForecastItem.forecast_id == fc.id)
                .distinct()
                .all()
            )
        for (pid,) in rows:
            if pid is not None:
                ids.add(pid)
    return ids


def _assert_forecasts_editaveis(docs: list[Forecast]) -> None:
    for fc in docs:
        if fc.status in STATUS_ORCAMENTO_BLOQUEADO:
            raise HTTPException(
                status_code=403,
                detail="O forecast deste departamento está em aprovação ou fechado. Não é possível alterar.",
            )


def _umbrella_ou_novo(
    db: Session,
    docs: list[Forecast],
    *,
    descricao: str,
    ano: int,
    tipo: str,
    current_user,
    dept: Departamento,
    versao_base_orcamento_id: Optional[int],
    versao_base_forecast_id: Optional[int],
) -> Forecast:
    for fc in docs:
        if fc.produto_id is None:
            return fc
    fc = Forecast(
        descricao=descricao,
        ano=ano,
        tipo=tipo,
        versao_numero=(docs[0].versao_numero if docs else 1),
        status="Rascunho",
        usuario_criador_id=current_user.id,
        departamento_id=dept.id,
        produto_id=None,
        versao_base_orcamento_id=versao_base_orcamento_id,
        versao_base_forecast_id=versao_base_forecast_id,
    )
    db.add(fc)
    db.flush()
    return fc


def _forecast_destino(forecasts_do_grupo: list[Forecast], produto_id: int) -> Optional[Forecast]:
    por_produto = {fc.produto_id: fc for fc in forecasts_do_grupo if fc.produto_id is not None}
    if produto_id in por_produto:
        return por_produto[produto_id]
    for fc in forecasts_do_grupo:
        if fc.produto_id is None:
            return fc
    return None


def _opcoes_base_forecast(db: Session, ano: int, tipo: str, dept: Departamento) -> list[dict]:
    orcs = (
        db.query(Orcamento)
        .filter(
            Orcamento.ano == ano,
            Orcamento.tipo == tipo,
            criterio_departamento(Orcamento.departamento_id, db, dept),
            Orcamento.status != "Substituído",
        )
        .order_by(Orcamento.versao_numero.desc())
        .all()
    )
    fcs = (
        db.query(Forecast)
        .filter(
            Forecast.ano == ano,
            Forecast.tipo == tipo,
            criterio_departamento(Forecast.departamento_id, db, dept),
            Forecast.status != "Substituído",
        )
        .order_by(Forecast.versao_numero.desc())
        .all()
    )
    return (
        [{"id": o.id, "tipo": "Orcamento", "descricao": o.descricao} for o in orcs]
        + [{"id": o.id, "tipo": "Forecast", "descricao": o.descricao} for o in fcs]
    )


@router.post("/criar_de_base")
def criar_forecast_de_base(
    data: ForecastCreateRequest,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    """Inclui um empreendimento no documento do departamento para a versão rolling (ex.: Forecast - 9+3)."""
    tipo = (data.tipo or "DESPESAS").upper()
    if tipo not in ("DESPESAS", "VENDAS", "RECEITAS"):
        raise HTTPException(status_code=400, detail="Tipo inválido.")
    if tipo == "VENDAS":
        _exigir_vendas(current_user, dept)
    if not data.produto_id:
        raise HTTPException(status_code=400, detail="Centro de Custo (Empreendimento) é obrigatório para criação de Forecast.")

    descricao = _descricao_forecast_rolling(data.ano)
    docs = _docs_forecast_versao(db, data.ano, tipo, dept.id, descricao)
    nome = _nome_empreendimento(db, data.produto_id)
    if data.produto_id in _produtos_nos_forecasts(db, docs, tipo):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Já existe forecast criado para o empreendimento {nome} em {data.ano}. "
                "Não é possível criar outro."
            ),
        )
    if docs:
        _assert_forecasts_editaveis(docs)

    itens_base = []
    if data.versao_base_orcamento_id:
        base = (
            db.query(Orcamento)
            .filter(
                Orcamento.id == data.versao_base_orcamento_id,
                Orcamento.departamento_id == dept.id,
                Orcamento.ano == data.ano,
                Orcamento.tipo == tipo,
            )
            .first()
        )
        if not base:
            raise HTTPException(status_code=400, detail="Base de orçamento inválida para este departamento.")
        if tipo == "VENDAS":
            itens_base = (
                db.query(OrcamentoVendaItem)
                .filter(
                    OrcamentoVendaItem.orcamento_id == base.id,
                    OrcamentoVendaItem.produto_id == data.produto_id,
                )
                .all()
            )
        else:
            itens_base = (
                db.query(OrcamentoItem)
                .filter(
                    OrcamentoItem.orcamento_id == base.id,
                    OrcamentoItem.produto_id == data.produto_id,
                )
                .all()
            )
    elif data.versao_base_forecast_id:
        base_fc = (
            db.query(Forecast)
            .filter(
                Forecast.id == data.versao_base_forecast_id,
                Forecast.departamento_id == dept.id,
                Forecast.ano == data.ano,
                Forecast.tipo == tipo,
            )
            .first()
        )
        if not base_fc:
            raise HTTPException(status_code=400, detail="Base de forecast inválida para este departamento.")
        if tipo == "VENDAS":
            itens_base = (
                db.query(ForecastVendaItem)
                .filter(
                    ForecastVendaItem.forecast_id == base_fc.id,
                    ForecastVendaItem.produto_id == data.produto_id,
                )
                .all()
            )
        else:
            itens_base = (
                db.query(ForecastItem)
                .filter(
                    ForecastItem.forecast_id == base_fc.id,
                    ForecastItem.produto_id == data.produto_id,
                )
                .all()
            )

    dest = _umbrella_ou_novo(
        db,
        docs,
        descricao=descricao,
        ano=data.ano,
        tipo=tipo,
        current_user=current_user,
        dept=dept,
        versao_base_orcamento_id=data.versao_base_orcamento_id,
        versao_base_forecast_id=data.versao_base_forecast_id,
    )

    if tipo == "VENDAS":
        if itens_base:
            novos = copy_venda_items_to_forecast(itens_base, dest.id, ForecastVendaItem)
            for item in novos:
                if not getattr(item, "ano", None):
                    item.ano = data.ano
                db.add(item)
        else:
            if not data.plano_venda_id:
                if not docs:
                    db.commit()
                    return {"message": "Forecast criado com sucesso", "forecast_id": dest.id}
                raise HTTPException(status_code=400, detail="Plano de venda é obrigatório para incluir o empreendimento.")
            db.add(
                ForecastVendaItem(
                    forecast_id=dest.id,
                    produto_id=data.produto_id,
                    plano_venda_id=data.plano_venda_id,
                    mes=1,
                    ano=data.ano,
                    ticket_medio=0.0,
                    numero_vendas=0,
                    vgv=0.0,
                )
            )
    else:
        if itens_base:
            db.bulk_save_objects(copy_monthly_items_to_forecast(itens_base, dest.id, ForecastItem))
        else:
            if not data.plano_financeiro_id:
                if not docs:
                    db.commit()
                    return {"message": "Forecast criado com sucesso", "forecast_id": dest.id}
                raise HTTPException(
                    status_code=400, detail="Plano financeiro é obrigatório para incluir o empreendimento."
                )
            if not validate_budget_allocation(
                db=db,
                departamento_id=dept.id,
                produto_id=data.produto_id,
                plano_financeiro_id=data.plano_financeiro_id,
            ):
                db.rollback()
                raise HTTPException(
                    403,
                    "Este empreendimento/plano não está liberado para o seu departamento.",
                )
            db.add(
                ForecastItem(
                    forecast_id=dest.id,
                    produto_id=data.produto_id,
                    plano_financeiro_id=data.plano_financeiro_id,
                    **{m: 0.0 for m in MESES_STR},
                    total_anual=0.0,
                )
            )

    db.commit()
    return {"message": "Forecast criado com sucesso", "forecast_id": dest.id}


@router.get("/despesas/{ano}")
def get_forecast_despesas(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    versao_id: Optional[int] = None,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    fix_forecasts_sharepoint_sem_departamento(db)
    is_consolidado = False
    planos_permitidos, produtos_permitidos, is_consolidado = resolve_forecast_despesas_catalog(
        db, dept, consolidado, current_user
    )

    forecast = None
    if is_consolidado:
        # TODO: Consolidado precisaria somar todos. Por enquanto retornaremos os ativos
        pass
    else:
        if versao_id:
            forecast = db.query(Forecast).filter(Forecast.id == versao_id, criterio_departamento(Forecast.departamento_id, db, dept)).first()
        else:
            forecast = db.query(Forecast).filter(
                Forecast.ano == ano, Forecast.tipo == 'DESPESAS', Forecast.status != "Substituído",
                criterio_departamento(Forecast.departamento_id, db, dept),
            ).order_by(Forecast.versao_numero.desc()).first()
        
    if not forecast:
        opcoes_base_orc = db.query(Orcamento).filter(
            Orcamento.ano == ano, Orcamento.tipo == 'DESPESAS',
            criterio_departamento(Orcamento.departamento_id, db, dept)
        ).order_by(Orcamento.versao_numero.desc()).all()
        
        opcoes_base_for = db.query(Forecast).filter(
            Forecast.ano == ano, Forecast.tipo == 'DESPESAS',
            criterio_departamento(Forecast.departamento_id, db, dept)
        ).order_by(Forecast.versao_numero.desc()).all()
        
        empresas_map = build_empresas_map(db)
        opcoes_produtos_lista = build_opcoes_produtos(produtos_permitidos, empresas_map)
            
        return {
            "is_empty": True,
            "opcoes_base": [
                {"id": o.id, "tipo": "Orcamento", "descricao": o.descricao} for o in opcoes_base_orc
            ] + [
                {"id": o.id, "tipo": "Forecast", "descricao": o.descricao} for o in opcoes_base_for
            ],
            "opcoes_produtos": opcoes_produtos_lista,
            "opcoes_planos": [{"id": p.id, "nome": p.name, "db_id": p.db_id} for p in planos_permitidos]
        }
        
    # AGRUPAMENTO POR DESCRICAO
    forecasts_do_grupo = db.query(Forecast).filter(
        Forecast.ano == ano, 
        Forecast.tipo == 'DESPESAS',
        Forecast.descricao == forecast.descricao,
        Forecast.status != "Substituído",
        criterio_departamento(Forecast.departamento_id, db, dept)
    ).all()

    # Busca itens base (para o diff)
    itens_base = []
    itens_base_db = []
    itens_db = []
    mapa_ids = {}
    for fc in forecasts_do_grupo:
        mapa_ids[fc.produto_id] = fc.id
        if fc.versao_base_orcamento_id:
            itens_base_db.extend(db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == fc.versao_base_orcamento_id).all())
        elif fc.versao_base_forecast_id:
            itens_base_db.extend(db.query(ForecastItem).filter(ForecastItem.forecast_id == fc.versao_base_forecast_id).all())
            
        fc_itens = db.query(ForecastItem).filter(ForecastItem.forecast_id == fc.id).all()
        itens_db.extend(fc_itens)
        
    for ib in itens_base_db:
        itens_base.append(serialize_base_monthly_item(ib, zero_defaults=True))

    produtos_finais, planos_finais = merge_catalog_with_used_items(
        db, produtos_permitidos, planos_permitidos, itens_db
    )
    empresas_map = build_empresas_map(db)
    opcoes_produtos = build_opcoes_produtos(produtos_finais, empresas_map)
    opcoes_planos = build_opcoes_planos(planos_finais)

    itens = [serialize_monthly_item_row(item) for item in itens_db]

    is_locked_by_other, usuario_edicao_nome = check_pessimistic_lock(
        forecast, current_user.id, lock_user_label="Usuário"
    )

    meses_fechados_db = db.query(ClosedMonth).filter(ClosedMonth.ano == ano).all()
    meses_fechados = [mf.mes for mf in meses_fechados_db]

    versoes_disponiveis = list_forecast_versoes_disponiveis(db, ano, "DESPESAS", dept.id)

    return maybe_apply_holding_mldu(
        db,
        holding_mldu,
        {
        "forecast_id": forecast.id,
        "ano": forecast.ano,
        "tipo": forecast.tipo,
        "status": forecast.status,
        "versao_numero": forecast.versao_numero,
        "motivo_reabertura": forecast.motivo_reabertura,
        "data_criacao": forecast.data_criacao.isoformat() if forecast.data_criacao else None,
        "is_locked_by_other": is_locked_by_other,
        "usuario_edicao_nome": usuario_edicao_nome,
        "is_consolidado": is_consolidado,
        "meses_fechados": meses_fechados, # [1, 2, 3...]
        "itens": itens,
        "itens_base": itens_base,
        "opcoes_produtos": opcoes_produtos,
        "opcoes_planos": opcoes_planos,
        "mapa_ids": mapa_ids,
        "versoes_disponiveis": versoes_disponiveis
        },
        item_kind="monthly",
    )


@router.post("/despesas/{ano}/salvar")
def salvar_forecast_despesas(
    ano: int,
    data: ForecastDespesasSaveRequest,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    # Achar a versao atual ativa pelo ano/dept
    forecast_ref = db.query(Forecast).filter(
        Forecast.ano == ano, Forecast.tipo == 'DESPESAS', Forecast.departamento_id == dept.id,
        Forecast.status != "Substituído",
    ).order_by(Forecast.versao_numero.desc()).first()
    if not forecast_ref:
        raise HTTPException(status_code=404, detail="Forecast não encontrado.")
        
    # Carrega todos os forecasts deste grupo de descricao
    forecasts_do_grupo = db.query(Forecast).filter(
        Forecast.ano == ano, 
        Forecast.tipo == 'DESPESAS', 
        Forecast.departamento_id == dept.id,
        Forecast.descricao == forecast_ref.descricao,
        Forecast.status != "Substituído",
    ).all()
    
    fc_por_produto = {fc.produto_id: fc for fc in forecasts_do_grupo if fc.produto_id is not None}

    # Verificar meses fechados (FC-DESP-002)
    meses_fechados_db = db.query(ClosedMonth).filter(ClosedMonth.ano == ano).all()
    meses_fechados_idx = [mf.mes for mf in meses_fechados_db]
    
    # Buscar itens da base para todos os forecasts do grupo
    itens_base_dict = {}
    for fc in forecasts_do_grupo:
        if fc.status in STATUS_ORCAMENTO_BLOQUEADO:
            raise HTTPException(status_code=403, detail=f"O Forecast {fc.descricao} para o Empreendimento {fc.produto_id} está bloqueado para edição.")
        
        if fc.versao_base_orcamento_id:
            itens_base_db = db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == fc.versao_base_orcamento_id).all()
            for i in itens_base_db: itens_base_dict[(i.produto_id, i.plano_financeiro_id)] = i
        elif fc.versao_base_forecast_id:
            itens_base_db = db.query(ForecastItem).filter(ForecastItem.forecast_id == fc.versao_base_forecast_id).all()
            for i in itens_base_db: itens_base_dict[(i.produto_id, i.plano_financeiro_id)] = i

        db.query(ForecastItem).filter(ForecastItem.forecast_id == fc.id).delete()
    
    novos_itens = []
    for item_data in data.itens:
        if skip_linha_total_zero(item_data):
            continue
            
        fc_destino = _forecast_destino(forecasts_do_grupo, item_data.produto_id)
        if not fc_destino:
            raise HTTPException(400, f"O Empreendimento {item_data.produto_id} não possui o Forecast {forecast_ref.descricao} criado. Crie-o primeiro na listagem.")

        tem_permissao = validate_budget_allocation(db=db, departamento_id=dept.id, produto_id=item_data.produto_id, plano_financeiro_id=item_data.plano_financeiro_id)
        if not tem_permissao:
            db.rollback()
            raise HTTPException(403, f"Permissão negada (Prod {item_data.produto_id} x Plano {item_data.plano_financeiro_id}).")
            
        linha_base = itens_base_dict.get((item_data.produto_id, item_data.plano_financeiro_id))
        
        item_final = {}
        for mes_idx, mes_str in enumerate(MESES_STR, start=1):
            valor_novo = getattr(item_data, mes_str)
            if mes_idx in meses_fechados_idx:
                valor_base = getattr(linha_base, mes_str) if linha_base else 0.0
                if valor_novo != valor_base:
                    raise HTTPException(403, f"Mês {mes_str} está fechado, não pode ser alterado.")
                item_final[mes_str] = valor_base
            else:
                item_final[mes_str] = valor_novo
                
        total_anual_real = sum(item_final.values())
            
        novos_itens.append(ForecastItem(
            forecast_id=fc_destino.id, produto_id=item_data.produto_id, plano_financeiro_id=item_data.plano_financeiro_id,
            jan=item_final["jan"], fev=item_final["fev"], mar=item_final["mar"], abr=item_final["abr"], 
            mai=item_final["mai"], jun=item_final["jun"], jul=item_final["jul"], ago=item_final["ago"], 
            set=item_final["set"], out=item_final["out"], nov=item_final["nov"], dez=item_final["dez"],
            total_anual=total_anual_real, observacao=item_data.observacao
        ))
        
    db.bulk_save_objects(novos_itens)
    db.commit()
    return {"message": "Salvo com sucesso!", "linhas": len(novos_itens)}


@router.get("/receitas/{ano}")
def get_forecast_receitas(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    versao_id: Optional[int] = None,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    fix_forecasts_sharepoint_sem_departamento(db)
    planos_permitidos, produtos_permitidos, is_consolidado = resolve_forecast_receitas_catalog(
        db, dept, consolidado, current_user
    )

    forecast = None
    if not is_consolidado:
        if versao_id:
            forecast = db.query(Forecast).filter(
                Forecast.id == versao_id,
                Forecast.tipo == "RECEITAS",
                criterio_departamento(Forecast.departamento_id, db, dept),
            ).first()
        else:
            forecast = db.query(Forecast).filter(
                Forecast.ano == ano, Forecast.tipo == "RECEITAS", Forecast.status != "Substituído",
                criterio_departamento(Forecast.departamento_id, db, dept),
            ).order_by(Forecast.versao_numero.desc()).first()

    if not forecast:
        opcoes_base_orc = db.query(Orcamento).filter(
            Orcamento.ano == ano, Orcamento.tipo == "RECEITAS",
            criterio_departamento(Orcamento.departamento_id, db, dept),
            Orcamento.status != "Substituído",
        ).order_by(Orcamento.versao_numero.desc()).all()
        opcoes_base_for = db.query(Forecast).filter(
            Forecast.ano == ano, Forecast.tipo == "RECEITAS",
            criterio_departamento(Forecast.departamento_id, db, dept),
            Forecast.status != "Substituído",
        ).order_by(Forecast.versao_numero.desc()).all()
        empresas_map = build_empresas_map(db)
        return {
            "is_empty": True,
            "opcoes_base": [
                {"id": o.id, "tipo": "Orcamento", "descricao": o.descricao} for o in opcoes_base_orc
            ] + [
                {"id": o.id, "tipo": "Forecast", "descricao": o.descricao} for o in opcoes_base_for
            ],
            "opcoes_produtos": build_opcoes_produtos(produtos_permitidos, empresas_map),
            "opcoes_planos": [{"id": p.id, "nome": p.name, "db_id": p.db_id} for p in planos_permitidos],
        }

    forecasts_do_grupo = db.query(Forecast).filter(
        Forecast.ano == ano,
        Forecast.tipo == "RECEITAS",
        Forecast.descricao == forecast.descricao,
        Forecast.status != "Substituído",
        criterio_departamento(Forecast.departamento_id, db, dept),
    ).all()

    itens_base = []
    itens_base_db = []
    itens_db = []
    mapa_ids = {}
    for fc in forecasts_do_grupo:
        mapa_ids[fc.produto_id] = fc.id
        if fc.versao_base_orcamento_id:
            itens_base_db.extend(db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == fc.versao_base_orcamento_id).all())
        elif fc.versao_base_forecast_id:
            itens_base_db.extend(db.query(ForecastItem).filter(ForecastItem.forecast_id == fc.versao_base_forecast_id).all())
        itens_db.extend(db.query(ForecastItem).filter(ForecastItem.forecast_id == fc.id).all())

    for ib in itens_base_db:
        itens_base.append(serialize_base_monthly_item(ib, zero_defaults=True))

    produtos_finais, planos_finais = merge_catalog_with_used_items(
        db, produtos_permitidos, planos_permitidos, itens_db
    )
    empresas_map = build_empresas_map(db)
    itens = []
    for item in itens_db:
        row = serialize_monthly_item_row(item)
        row["is_auto_generated"] = bool(getattr(item, "is_auto_generated", False))
        itens.append(row)

    is_locked_by_other, usuario_edicao_nome = check_pessimistic_lock(
        forecast, current_user.id, lock_user_label="Usuário"
    )
    meses_fechados = [mf.mes for mf in db.query(ClosedMonth).filter(ClosedMonth.ano == ano).all()]

    return maybe_apply_holding_mldu(
        db,
        holding_mldu,
        {
            "forecast_id": forecast.id,
            "ano": forecast.ano,
            "tipo": forecast.tipo,
            "status": forecast.status,
            "versao_numero": forecast.versao_numero,
            "motivo_reabertura": forecast.motivo_reabertura,
            "data_criacao": forecast.data_criacao.isoformat() if forecast.data_criacao else None,
            "is_locked_by_other": is_locked_by_other,
            "usuario_edicao_nome": usuario_edicao_nome,
            "is_consolidado": is_consolidado,
            "meses_fechados": meses_fechados,
            "itens": itens,
            "itens_base": itens_base,
            "opcoes_produtos": build_opcoes_produtos(produtos_finais, empresas_map),
            "opcoes_planos": build_opcoes_planos(planos_finais),
            "mapa_ids": mapa_ids,
            "versoes_disponiveis": list_forecast_versoes_disponiveis(db, ano, "RECEITAS", dept.id),
        },
        item_kind="monthly",
    )


@router.post("/receitas/{ano}/salvar")
def salvar_forecast_receitas(
    ano: int,
    data: ForecastDespesasSaveRequest,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    forecast_ref = db.query(Forecast).filter(
        Forecast.ano == ano, Forecast.tipo == "RECEITAS", Forecast.departamento_id == dept.id,
        Forecast.status != "Substituído",
    ).order_by(Forecast.versao_numero.desc()).first()
    if not forecast_ref:
        raise HTTPException(status_code=404, detail="Forecast não encontrado.")

    forecasts_do_grupo = db.query(Forecast).filter(
        Forecast.ano == ano,
        Forecast.tipo == "RECEITAS",
        Forecast.departamento_id == dept.id,
        Forecast.descricao == forecast_ref.descricao,
        Forecast.status != "Substituído",
    ).all()

    meses_fechados_idx = [mf.mes for mf in db.query(ClosedMonth).filter(ClosedMonth.ano == ano).all()]
    itens_base_dict = {}
    auto_keys = set()
    for fc in forecasts_do_grupo:
        if fc.status in STATUS_ORCAMENTO_BLOQUEADO:
            raise HTTPException(status_code=403, detail="O forecast deste departamento está em aprovação ou fechado. Não é possível alterar.")
        if fc.versao_base_orcamento_id:
            for i in db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == fc.versao_base_orcamento_id).all():
                itens_base_dict[(i.produto_id, i.plano_financeiro_id)] = i
        elif fc.versao_base_forecast_id:
            for i in db.query(ForecastItem).filter(ForecastItem.forecast_id == fc.versao_base_forecast_id).all():
                itens_base_dict[(i.produto_id, i.plano_financeiro_id)] = i
        for i in db.query(ForecastItem).filter(
            ForecastItem.forecast_id == fc.id,
            ForecastItem.is_auto_generated == True,  # noqa: E712
        ).all():
            auto_keys.add((i.produto_id, i.plano_financeiro_id))
        db.query(ForecastItem).filter(
            ForecastItem.forecast_id == fc.id,
            ForecastItem.is_auto_generated == False,  # noqa: E712
        ).delete(synchronize_session=False)

    novos_itens = []
    for item_data in data.itens:
        key = (item_data.produto_id, item_data.plano_financeiro_id)
        if key in auto_keys:
            continue
        if skip_linha_total_zero(item_data):
            continue
        fc_destino = _forecast_destino(forecasts_do_grupo, item_data.produto_id)
        if not fc_destino:
            raise HTTPException(400, f"O Empreendimento {item_data.produto_id} não possui o Forecast {forecast_ref.descricao} criado. Crie-o primeiro na listagem.")
        tem_permissao = validate_budget_allocation(
            db=db, departamento_id=dept.id, produto_id=item_data.produto_id,
            plano_financeiro_id=item_data.plano_financeiro_id,
        )
        if not tem_permissao:
            db.rollback()
            raise HTTPException(403, f"Permissão negada (Prod {item_data.produto_id} x Plano {item_data.plano_financeiro_id}).")
        linha_base = itens_base_dict.get(key)
        item_final = {}
        for mes_idx, mes_str in enumerate(MESES_STR, start=1):
            valor_novo = getattr(item_data, mes_str)
            if mes_idx in meses_fechados_idx:
                valor_base = getattr(linha_base, mes_str) if linha_base else 0.0
                if valor_novo != valor_base:
                    raise HTTPException(403, f"Mês {mes_str} está fechado, não pode ser alterado.")
                item_final[mes_str] = valor_base
            else:
                item_final[mes_str] = valor_novo
        novos_itens.append(ForecastItem(
            forecast_id=fc_destino.id, produto_id=item_data.produto_id, plano_financeiro_id=item_data.plano_financeiro_id,
            jan=item_final["jan"], fev=item_final["fev"], mar=item_final["mar"], abr=item_final["abr"],
            mai=item_final["mai"], jun=item_final["jun"], jul=item_final["jul"], ago=item_final["ago"],
            set=item_final["set"], out=item_final["out"], nov=item_final["nov"], dez=item_final["dez"],
            total_anual=sum(item_final.values()), observacao=item_data.observacao,
            is_auto_generated=False,
        ))

    db.bulk_save_objects(novos_itens)
    db.commit()
    return {"message": "Salvo com sucesso!", "linhas": len(novos_itens)}


# ==================== VENDAS ====================

@router.get("/vendas/{ano}")
def get_forecast_vendas(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    versao_id: Optional[int] = None,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    fix_forecasts_sharepoint_sem_departamento(db)

    _ = consolidado  # Onda A: legado ignorado
    is_consolidado = False
    if not pode_editar_orcamento_vendas(current_user, dept):
        raise HTTPException(status_code=403, detail="Restrito ao departamento Vendas.")

    forecast = None
    if versao_id:
        forecast = db.query(Forecast).filter(
            Forecast.id == versao_id,
            criterio_departamento(Forecast.departamento_id, db, dept)
        ).first()
    else:
        forecast = db.query(Forecast).filter(
            Forecast.ano == ano,
            Forecast.tipo == 'VENDAS',
            Forecast.status != "Substituído",
            criterio_departamento(Forecast.departamento_id, db, dept)
        ).order_by(Forecast.versao_numero.desc()).first()

    planos_venda = db.query(PaymentPlan).all()
    produtos = db.query(CostCenter).all()
    opcoes_produtos = [{"id": p.id, "nome": p.nome} for p in produtos]
    opcoes_planos = [{"id": p.id, "nome": p.nome} for p in planos_venda]

    if not forecast:
        opcoes_base_orc = db.query(Orcamento).filter(
            Orcamento.ano == ano, Orcamento.tipo == 'VENDAS',
            criterio_departamento(Orcamento.departamento_id, db, dept)
        ).order_by(Orcamento.versao_numero.desc()).all()
        opcoes_base_for = db.query(Forecast).filter(
            Forecast.ano == ano, Forecast.tipo == 'VENDAS',
            criterio_departamento(Forecast.departamento_id, db, dept)
        ).order_by(Forecast.versao_numero.desc()).all()
        
        return {
            "is_empty": True,
            "opcoes_base": [
                {"id": o.id, "tipo": "Orcamento", "descricao": o.descricao} for o in opcoes_base_orc
            ] + [
                {"id": o.id, "tipo": "Forecast", "descricao": o.descricao} for o in opcoes_base_for
            ],
            "opcoes_produtos": opcoes_produtos,
            "opcoes_planos": opcoes_planos,
            "mapa_ids": {},
        }

    # AGRUPAMENTO POR DESCRICAO
    forecasts_do_grupo = db.query(Forecast).filter(
        Forecast.ano == ano, 
        Forecast.tipo == 'VENDAS',
        Forecast.descricao == forecast.descricao,
        Forecast.status != "Substituído",
        criterio_departamento(Forecast.departamento_id, db, dept)
    ).all()

    # Itens Base para Diff
    itens_base = []
    itens_base_db = []
    itens_db = []
    mapa_ids = {}
    for fc in forecasts_do_grupo:
        mapa_ids[fc.produto_id] = fc.id
        if fc.versao_base_orcamento_id:
            itens_base_db.extend(db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == fc.versao_base_orcamento_id).all())
        elif fc.versao_base_forecast_id:
            itens_base_db.extend(db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id == fc.versao_base_forecast_id).all())

        itens_db.extend(db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id == fc.id).all())
        
    for ib in itens_base_db:
        itens_base.append(serialize_venda_base_item(ib, zero_defaults=True))

    linhas = group_venda_items(itens_db)

    is_locked_by_other, usuario_edicao_nome = check_pessimistic_lock(
        forecast, current_user.id, lock_user_label="Usuário ID"
    )

    meses_fechados_db = db.query(ClosedMonth).filter(ClosedMonth.ano == ano).all()
    meses_fechados = [mf.mes for mf in meses_fechados_db]

    versoes_disponiveis = list_forecast_versoes_disponiveis(db, ano, "VENDAS", dept.id)

    return maybe_apply_holding_mldu(
        db,
        holding_mldu,
        {
        "forecast_id": forecast.id,
        "ano": forecast.ano,
        "tipo": forecast.tipo,
        "status": forecast.status,
        "versao_numero": forecast.versao_numero,
        "motivo_reabertura": forecast.motivo_reabertura,
        "data_criacao": forecast.data_criacao.isoformat() if forecast.data_criacao else None,
        "is_locked_by_other": is_locked_by_other,
        "usuario_edicao_nome": usuario_edicao_nome,
        "is_consolidado": is_consolidado,
        "meses_fechados": meses_fechados,
        "itens": linhas,
        "itens_base": itens_base,
        "opcoes_produtos": opcoes_produtos,
        "opcoes_planos": opcoes_planos,
        "mapa_ids": mapa_ids,
        "versoes_disponiveis": versoes_disponiveis
        },
        item_kind="venda_grouped",
    )


def injetar_vendas_em_receitas(forecast_vendas: Forecast, db: Session):
    ano = forecast_vendas.ano
    dept_id = forecast_vendas.departamento_id
    
    plano_rec = db.query(FinancialPlan).filter(FinancialPlan.db_id == '1.01.01.01').first()
    if not plano_rec:
        plano_rec = db.query(FinancialPlan).filter(FinancialPlan.name.ilike('%Receita%Vendas%')).first()
    
    plano_rec_id = plano_rec.id if plano_rec else None
    if not plano_rec_id:
        return
        
    f_receitas = db.query(Forecast).filter(
        Forecast.ano == ano,
        Forecast.descricao == forecast_vendas.descricao,
        Forecast.departamento_id == dept_id,
        Forecast.tipo == "RECEITAS"
    ).first()
    
    if not f_receitas:
        f_receitas = Forecast(
            descricao=forecast_vendas.descricao,
            ano=ano,
            tipo="RECEITAS",
            versao_numero=forecast_vendas.versao_numero,
            status="Rascunho",
            usuario_criador_id=forecast_vendas.usuario_criador_id,
            departamento_id=dept_id,
            versao_base_orcamento_id=forecast_vendas.versao_base_orcamento_id,
            versao_base_forecast_id=forecast_vendas.versao_base_forecast_id
        )
        db.add(f_receitas)
        db.commit()
        db.refresh(f_receitas)
        
    acumulador = {}
    
    # Produtos vindos das novas vendas (Forecast)
    itens_venda = db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id == forecast_vendas.id).all()
    planos_venda_ids = list(set([i.plano_venda_id for i in itens_venda]))
    planos_venda_objs = db.query(PaymentPlan).filter(PaymentPlan.id.in_(planos_venda_ids)).all()
    planos_venda_map = {p.id: p for p in planos_venda_objs}
    
    produtos_envolvidos = set()
    
    for iv in itens_venda:
        if not iv.vgv or iv.vgv <= 0:
            continue
            
        p_id = iv.produto_id
        produtos_envolvidos.add(p_id)
        if p_id not in acumulador:
            acumulador[p_id] = {m: 0.0 for m in range(1, 13)}
            
        plano = planos_venda_map.get(iv.plano_venda_id)
        if not plano or not plano.condicoes_json:
            acumulador[p_id][iv.mes] += iv.vgv
            continue
            
        for cond in plano.condicoes_json:
            nome = str(cond.get("nome", "")).upper().strip()
            perc = float(cond.get("perc", 0.0))
            if perc <= 0: continue
            
            valor_cond = iv.vgv * (perc / 100.0)
            
            if nome == "A VISTA":
                acumulador[p_id][iv.mes] += valor_cond
            else:
                try:
                    num_parcelas = int(nome)
                except ValueError:
                    num_parcelas = 1
                
                if num_parcelas <= 0: num_parcelas = 1
                valor_parcela = valor_cond / num_parcelas
                
                for i in range(1, num_parcelas + 1):
                    mes_alvo = iv.mes + i
                    if mes_alvo <= 12:
                        acumulador[p_id][mes_alvo] += valor_parcela
                        
    from sqlalchemy import extract
    from datetime import datetime
    
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Produtos vindos do Sienge (Realizado + Parcelas em Aberto)
    realizados = db.query(ActualTransaction).filter(
        extract('year', ActualTransaction.transaction_date) == ano,
        ActualTransaction.transaction_type == "INCOME"
    ).all()
    
    for r in realizados:
        p_id = r.cost_center_id
        if not p_id: continue
        
        produtos_envolvidos.add(p_id)
        
        if not r.transaction_date: continue
        
        if getattr(r, 'is_forecast', False):
            if ano == ano_atual and r.transaction_date.month < mes_atual:
                continue
            elif ano < ano_atual:
                continue
                
        if p_id not in acumulador:
            acumulador[p_id] = {m: 0.0 for m in range(1, 13)}
        
        mes = r.transaction_date.month
        if 1 <= mes <= 12:
            acumulador[p_id][mes] += float(r.value or 0.0)
            
    if produtos_envolvidos:
        linhas_manuais = db.query(ForecastItem.produto_id).filter(
            ForecastItem.forecast_id == f_receitas.id,
            ForecastItem.plano_financeiro_id == plano_rec_id,
            ForecastItem.produto_id.in_(produtos_envolvidos),
            ForecastItem.is_auto_generated == False
        ).all()
        produtos_manuais = set([p[0] for p in linhas_manuais])
        
        db.query(ForecastItem).filter(
            ForecastItem.forecast_id == f_receitas.id,
            ForecastItem.plano_financeiro_id == plano_rec_id,
            ForecastItem.produto_id.in_(produtos_envolvidos),
            ForecastItem.is_auto_generated == True
        ).delete(synchronize_session=False)
        
        novos_itens = []
        for p_id, meses_dict in acumulador.items():
            if p_id in produtos_manuais:
                continue
                
            total = sum(meses_dict.values())
            if total > 0.01:
                item = ForecastItem(
                    forecast_id=f_receitas.id,
                    produto_id=p_id,
                    plano_financeiro_id=plano_rec_id,
                    jan=meses_dict.get(1, 0.0),
                    fev=meses_dict.get(2, 0.0),
                    mar=meses_dict.get(3, 0.0),
                    abr=meses_dict.get(4, 0.0),
                    mai=meses_dict.get(5, 0.0),
                    jun=meses_dict.get(6, 0.0),
                    jul=meses_dict.get(7, 0.0),
                    ago=meses_dict.get(8, 0.0),
                    set=meses_dict.get(9, 0.0),
                    out=meses_dict.get(10, 0.0),
                    nov=meses_dict.get(11, 0.0),
                    dez=meses_dict.get(12, 0.0),
                    total_anual=total,
                    observacao="Injetado automaticamente do Forecast de Vendas",
                    is_auto_generated=True
                )
                novos_itens.append(item)
                
        if novos_itens:
            db.bulk_save_objects(novos_itens)
            
    db.commit()

from app.schemas.forecast import ForecastVendasSaveRequest

@router.post("/vendas/{ano}/salvar")
def salvar_forecast_vendas(
    ano: int,
    data: ForecastVendasSaveRequest,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    if not pode_editar_orcamento_vendas(current_user, dept):
        raise HTTPException(status_code=403, detail="Restrito ao departamento Vendas.")

    forecast_ref = db.query(Forecast).filter(
        Forecast.ano == ano,
        Forecast.tipo == 'VENDAS',
        Forecast.departamento_id == dept.id,
        Forecast.status != "Substituído",
    ).order_by(Forecast.versao_numero.desc()).first()
    
    if not forecast_ref:
        raise HTTPException(status_code=404, detail="Forecast não encontrado.")
        
    forecasts_do_grupo = db.query(Forecast).filter(
        Forecast.ano == ano, 
        Forecast.tipo == 'VENDAS', 
        Forecast.descricao == forecast_ref.descricao,
        Forecast.departamento_id == dept.id,
        Forecast.status != "Substituído",
    ).all()
    
    fc_por_produto = {fc.produto_id: fc for fc in forecasts_do_grupo}

    meses_fechados_db = db.query(ClosedMonth).filter(ClosedMonth.ano == ano).all()
    meses_fechados_idx = [mf.mes for mf in meses_fechados_db]

    itens_base_dict = {}
    for fc in forecasts_do_grupo:
        if fc.status in STATUS_ORCAMENTO_BLOQUEADO:
            raise HTTPException(status_code=403, detail=f"Forecast {fc.descricao} bloqueado para edição.")

        if fc.versao_base_orcamento_id:
            itens_base_db = db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == fc.versao_base_orcamento_id).all()
            for i in itens_base_db: itens_base_dict[(i.produto_id, i.plano_venda_id, i.mes)] = i
        elif fc.versao_base_forecast_id:
            itens_base_db = db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id == fc.versao_base_forecast_id).all()
            for i in itens_base_db: itens_base_dict[(i.produto_id, i.plano_venda_id, i.mes)] = i

        db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id == fc.id).delete()
    
    novos_itens = []
    for linha in data.itens:
        for mes_data in linha.meses:
            if mes_data.numero_vendas == 0 and mes_data.ticket_medio == 0 and not linha.observacao:
                continue

            fc_destino = _forecast_destino(forecasts_do_grupo, linha.produto_id)
            if not fc_destino:
                raise HTTPException(400, f"Empreendimento {linha.produto_id} não possui Forecast.")

            linha_base = itens_base_dict.get((linha.produto_id, linha.plano_venda_id, mes_data.mes))
            
            # FC-VEN-004 e FC-VEN-002: Meses fechados não podem ser alterados, pega da base
            if mes_data.mes in meses_fechados_idx:
                ticket_val = linha_base.ticket_medio if linha_base else 0.0
                vendas_val = linha_base.numero_vendas if linha_base else 0
                vgv_val = linha_base.vgv if linha_base else 0.0
                
                if (mes_data.ticket_medio != ticket_val) or (mes_data.numero_vendas != vendas_val):
                    raise HTTPException(403, f"Mês {mes_data.mes} está fechado, não pode ser alterado.")
            else:
                ticket_val = mes_data.ticket_medio
                vendas_val = mes_data.numero_vendas
                vgv_val = mes_data.vgv

            novos_itens.append(ForecastVendaItem(
                forecast_id=fc_destino.id, produto_id=linha.produto_id, plano_venda_id=linha.plano_venda_id,
                mes=mes_data.mes, numero_vendas=vendas_val, ticket_medio=ticket_val, vgv=vgv_val,
                observacao=linha.observacao
            ))

    db.bulk_save_objects(novos_itens)
    db.commit()
    
    # Injetar receitas automaticamente (Realizado + Projetado pelo Plano de Pagamento)
    injetar_vendas_em_receitas(forecast_ref, db)
    
    return {"message": "Salvo com sucesso!", "linhas": len(novos_itens)}


# ==================== WORKFLOW E VERSIONAMENTO ====================

@router.post("/{forecast_id}/travar")
def travar_forecast(
    forecast_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    orc = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not orc:
        raise HTTPException(404, "Forecast não encontrado.")
        
    agora = datetime.utcnow()
    if getattr(orc, "usuario_edicao_id", None) and orc.usuario_edicao_id != current_user.id and getattr(orc, "data_inicio_edicao", None):
        if (agora - orc.data_inicio_edicao).total_seconds() < 1800:
            nome = orc.usuario_edicao.nome if getattr(orc, "usuario_edicao", None) else f"Usuário {orc.usuario_edicao_id}"
            raise HTTPException(409, f"Forecast já está em edição por {nome}.")
            
    orc.usuario_edicao_id = current_user.id
    orc.data_inicio_edicao = agora
    db.commit()
    return {"message": "Trava adquirida com sucesso."}

@router.post("/{forecast_id}/destravar")
def destravar_forecast(
    forecast_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    orc = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not orc:
        raise HTTPException(404, "Forecast não encontrado.")
        
    if getattr(orc, "usuario_edicao_id", None) != current_user.id and not is_admin_user(current_user):
        raise HTTPException(403, "Sem permissão para destravar forecast de outro usuário.")
        
    orc.usuario_edicao_id = None
    orc.data_inicio_edicao = None
    db.commit()
    return {"message": "Trava removida com sucesso."}

@router.post("/{forecast_id}/status")
def change_status(
    forecast_id: int,
    data: ForecastStatusRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    fc = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not fc:
        raise HTTPException(404, "Forecast não encontrado.")

    destino, acao = resolver_transicao(fc.status, data.novo_status)
    if acao == "solicitar_reabertura":
        raise HTTPException(
            status_code=400,
            detail="Use a solicitação de reabertura com motivo.",
        )
    if acao == "aprovar_reabertura":
        raise HTTPException(
            status_code=400,
            detail="A aprovação de reabertura precisa guardar a cópia fechada.",
        )
    exigir_permissao_status(acao, current_user)

    alvos = irmaos_mesmo_grupo(db, Forecast, fc) or [fc]
    for item in alvos:
        anterior = item.status
        item.status = destino
        if acao == "recusar_reabertura":
            item.motivo_reabertura = None
        db.add(Auditoria(
            evento="Aprovacao" if acao == "aprovar" else "Alteracao",
            tabela_afetada="forecasts",
            registro_id=item.id,
            campo="status",
            valor_anterior=anterior,
            novo_valor=destino,
            motivo=data.motivo,
            usuario_id=current_user.id,
        ))

    db.commit()
    return {"message": f"Status alterado para {destino}", "status": destino, "registros": len(alvos)}


@router.post("/{forecast_id}/solicitar-reabertura")
def solicitar_reabertura_forecast(
    forecast_id: int,
    data: ForecastStatusRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = (data.motivo or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="Informe o motivo da solicitação de reabertura.")

    fc = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not fc:
        raise HTTPException(status_code=404, detail="Forecast não encontrado.")

    destino, acao = resolver_transicao(fc.status, "Solicitação Reabertura")
    exigir_permissao_status(acao, current_user)

    alvos = irmaos_mesmo_grupo(db, Forecast, fc) or [fc]
    for item in alvos:
        anterior = item.status
        item.status = destino
        item.motivo_reabertura = motivo
        db.add(Auditoria(
            evento="Alteracao",
            tabela_afetada="forecasts",
            registro_id=item.id,
            campo="status",
            valor_anterior=anterior,
            novo_valor=destino,
            motivo=motivo,
            usuario_id=current_user.id,
        ))

    db.commit()
    return {"message": f"Status alterado para {destino}", "status": destino, "registros": len(alvos)}


def _arquivar_forecast_fechado(db: Session, live: Forecast) -> Forecast:
    snap = Forecast(
        descricao=live.descricao,
        ano=live.ano,
        tipo=live.tipo,
        mes_corte=live.mes_corte,
        status="Substituído",
        versao_numero=live.versao_numero,
        versao_base_forecast_id=live.id,
        versao_base_orcamento_id=live.versao_base_orcamento_id,
        usuario_criador_id=live.usuario_criador_id,
        departamento_id=live.departamento_id,
        produto_id=live.produto_id,
    )
    db.add(snap)
    db.flush()
    if live.tipo == "VENDAS":
        for i in db.query(ForecastVendaItem).filter_by(forecast_id=live.id).all():
            db.add(ForecastVendaItem(
                forecast_id=snap.id,
                produto_id=i.produto_id,
                plano_venda_id=i.plano_venda_id,
                mes=i.mes,
                ano=i.ano,
                juros_mensal=i.juros_mensal,
                ticket_medio=i.ticket_medio,
                numero_vendas=i.numero_vendas,
                vgv=i.vgv,
                origem_venda=i.origem_venda,
                observacao=i.observacao,
            ))
    else:
        for i in db.query(ForecastItem).filter_by(forecast_id=live.id).all():
            meses = {m: getattr(i, m) or 0.0 for m in MESES_STR}
            db.add(ForecastItem(
                forecast_id=snap.id,
                produto_id=i.produto_id,
                plano_financeiro_id=i.plano_financeiro_id,
                total_anual=i.total_anual,
                observacao=i.observacao,
                is_auto_generated=i.is_auto_generated,
                **meses,
            ))
    return snap


@router.post("/{forecast_id}/aprovar-reabertura")
def aprovar_reabertura_forecast(
    forecast_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    fc = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not fc:
        raise HTTPException(status_code=404, detail="Forecast não encontrado.")

    destino, acao = resolver_transicao(fc.status, "Reaberto")
    exigir_permissao_status(acao, current_user)

    alvos = irmaos_mesmo_grupo(db, Forecast, fc) or [fc]
    for item in alvos:
        _arquivar_forecast_fechado(db, item)
        anterior = item.status
        item.status = destino
        db.add(Auditoria(
            evento="Alteracao",
            tabela_afetada="forecasts",
            registro_id=item.id,
            campo="status",
            valor_anterior=anterior,
            novo_valor=destino,
            motivo=item.motivo_reabertura,
            usuario_id=current_user.id,
        ))

    db.commit()
    return {"message": f"Status alterado para {destino}", "status": destino, "registros": len(alvos)}


@router.get("/anos-disponiveis")
def get_anos_disponiveis(
    tipo: str,
    consolidado: bool = False,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    fix_forecasts_sharepoint_sem_departamento(db)
    query = db.query(Forecast.ano).filter(Forecast.tipo == tipo.upper(), Forecast.status != 'Substituído')
    _ = consolidado  # Onda A: legado ignorado
    query = query.filter(
        criterio_departamento(Forecast.departamento_id, db, dept)
    )

    anos = query.distinct().all()
    year_now = datetime.now().year
    anos_list = sorted([a[0] for a in anos])
    if year_now not in anos_list:
        anos_list.append(year_now)

    return {"anos": sorted(list(set(anos_list)))}


@router.get("/catalogo")
def get_catalogo_forecast(
    tipo: str,
    ano: int,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    tipo = tipo.upper()
    if tipo not in ("DESPESAS", "VENDAS", "RECEITAS"):
        raise HTTPException(400, "Tipo inválido.")
    if tipo == "VENDAS":
        _exigir_vendas(current_user, dept)
        produtos = db.query(CostCenter).filter(CostCenter.status == "Ativo").all()
        if not produtos:
            produtos = db.query(CostCenter).all()
        planos = db.query(PaymentPlan).all()
        empresas_map = build_empresas_map(db)
        return {
            "opcoes_produtos": build_opcoes_produtos(produtos, empresas_map),
            "opcoes_planos": build_opcoes_planos(planos, nome_attr="nome"),
            "opcoes_base": _opcoes_base_forecast(db, ano, tipo, dept),
        }
    if tipo == "RECEITAS":
        planos_permitidos, produtos_permitidos, _ = resolve_forecast_receitas_catalog(
            db, dept, False, current_user
        )
    else:
        planos_permitidos, produtos_permitidos, _ = resolve_forecast_despesas_catalog(
            db, dept, False, current_user
        )
    empresas_map = build_empresas_map(db)
    return {
        "opcoes_produtos": build_opcoes_produtos(produtos_permitidos, empresas_map),
        "opcoes_planos": build_opcoes_planos(planos_permitidos),
        "opcoes_base": _opcoes_base_forecast(db, ano, tipo, dept),
    }


from app.services.excel_builder import gerar_modelo_despesas_receitas, gerar_modelo_vendas, exportar_forecast
from app.services.excel_validator import validar_despesas_receitas, validar_vendas, ler_excel
from fastapi.responses import Response
from fastapi import File, UploadFile
import io

@router.get("/excel/modelo/{tipo}/{ano}")
def download_modelo_excel(
    tipo: str,
    ano: int,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    tipo = tipo.upper()
    if tipo not in ("DESPESAS", "RECEITAS", "VENDAS"):
        raise HTTPException(status_code=400, detail="Tipo inválido.")

    if tipo == "VENDAS":
        conteudo = gerar_modelo_vendas(db, ano)
    else:
        conteudo = gerar_modelo_despesas_receitas(db, tipo, ano, dept.id)

    return Response(
        content=conteudo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=modelo_{tipo.lower()}_{ano}.xlsx"}
    )

@router.get("/excel/exportar/{forecast_id}")
def exportar_excel(
    forecast_id: int,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    try:
        conteudo = exportar_forecast(forecast_id, db)
        return Response(
            content=conteudo,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=forecast_{forecast_id}_export.xlsx"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/excel/validar/{tipo}/{ano}")
async def validar_excel(
    tipo: str,
    ano: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    tipo = tipo.upper()
    if tipo not in ("DESPESAS", "RECEITAS", "VENDAS"):
        raise HTTPException(status_code=400, detail="Forecast importa Despesas, Receitas ou Vendas.")

    conteudo = await file.read()
    try:
        rows, _ = ler_excel(conteudo, tipo)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not rows:
        raise HTTPException(status_code=422, detail="Planilha sem dados.")

    if tipo == "VENDAS":
        erros, linhas_validas = validar_vendas(rows, ano, dept.id, db)
    else:
        erros, linhas_validas = validar_despesas_receitas(rows, tipo, ano, dept.id, db)

    return {
        "tipo": tipo,
        "ano": ano,
        "total_linhas": len(rows),
        "total_erros": len(erros),
        "total_validas": len(linhas_validas),
        "pode_importar": len(erros) == 0,
        "erros": erros,
    }


@router.post("/excel/importar/{tipo}/{ano}")
async def importar_excel(
    tipo: str,
    ano: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    """Tudo-ou-nada na versão rolling atual. Não cria nem altera outra descrição (ex.: 7+5)."""
    tipo = tipo.upper()
    if tipo not in ("DESPESAS", "RECEITAS", "VENDAS"):
        raise HTTPException(status_code=400, detail="Forecast importa Despesas, Receitas ou Vendas.")
    if tipo == "VENDAS":
        _exigir_vendas(current_user, dept)

    descricao = _descricao_forecast_rolling(ano)
    docs = _docs_forecast_versao(db, ano, tipo, dept.id, descricao)
    outros = (
        db.query(Forecast)
        .filter(
            Forecast.ano == ano,
            Forecast.tipo == tipo,
            Forecast.departamento_id == dept.id,
            Forecast.status != "Substituído",
        )
        .all()
    )
    if not docs and outros:
        raise HTTPException(
            status_code=400,
            detail="Já existe forecast deste ano neste departamento em outra versão. Use a matriz; o Excel não altera versões antigas.",
        )
    if docs:
        _assert_forecasts_editaveis(docs)

    conteudo = await file.read()
    try:
        rows, _ = ler_excel(conteudo, tipo)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not rows:
        raise HTTPException(status_code=422, detail="Planilha sem dados.")

    if tipo == "VENDAS":
        erros, linhas_validas = validar_vendas(rows, ano, dept.id, db)
    else:
        erros, linhas_validas = validar_despesas_receitas(rows, tipo, ano, dept.id, db)

    if erros:
        return {
            "gravado": False,
            "mensagem": "Importação recusada: a planilha contém erros. Nenhum dado foi alterado.",
            "total_linhas": len(rows),
            "total_erros": len(erros),
            "erros": erros,
        }

    dest = _umbrella_ou_novo(
        db,
        docs,
        descricao=descricao,
        ano=ano,
        tipo=tipo,
        current_user=current_user,
        dept=dept,
        versao_base_orcamento_id=None,
        versao_base_forecast_id=None,
    )
    if dest not in docs:
        docs = list(docs) + [dest]

    meses_fechados_idx = [mf.mes for mf in db.query(ClosedMonth).filter(ClosedMonth.ano == ano).all()]
    itens_base_dict: dict = {}

    if tipo == "VENDAS":
        for fc in docs:
            if fc.versao_base_orcamento_id:
                for i in db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == fc.versao_base_orcamento_id).all():
                    itens_base_dict[(i.produto_id, i.plano_venda_id, i.mes)] = i
            elif fc.versao_base_forecast_id:
                for i in db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id == fc.versao_base_forecast_id).all():
                    itens_base_dict[(i.produto_id, i.plano_venda_id, i.mes)] = i
            db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id == fc.id).delete()

        novos_itens = []
        for linha in linhas_validas:
            fc_destino = _forecast_destino(docs, linha["produto_id"]) or dest
            mes = linha["mes"]
            linha_base = itens_base_dict.get((linha["produto_id"], linha["plano_venda_id"], mes))
            if mes in meses_fechados_idx:
                ticket_val = linha_base.ticket_medio if linha_base else 0.0
                vendas_val = linha_base.numero_vendas if linha_base else 0
                vgv_val = linha_base.vgv if linha_base else 0.0
                if linha["ticket_medio"] != ticket_val or linha["numero_vendas"] != vendas_val:
                    db.rollback()
                    raise HTTPException(status_code=403, detail=f"Mês {mes} está fechado, não pode ser alterado.")
            else:
                ticket_val = linha["ticket_medio"]
                vendas_val = linha["numero_vendas"]
                vgv_val = linha["vgv"]
            novos_itens.append(ForecastVendaItem(
                forecast_id=fc_destino.id,
                produto_id=linha["produto_id"],
                plano_venda_id=linha["plano_venda_id"],
                mes=mes,
                ano=ano,
                numero_vendas=vendas_val,
                ticket_medio=ticket_val,
                vgv=vgv_val,
            ))
        db.bulk_save_objects(novos_itens)
    else:
        auto_keys = set()
        for fc in docs:
            if fc.versao_base_orcamento_id:
                for i in db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == fc.versao_base_orcamento_id).all():
                    itens_base_dict[(i.produto_id, i.plano_financeiro_id)] = i
            elif fc.versao_base_forecast_id:
                for i in db.query(ForecastItem).filter(ForecastItem.forecast_id == fc.versao_base_forecast_id).all():
                    itens_base_dict[(i.produto_id, i.plano_financeiro_id)] = i
            if tipo == "RECEITAS":
                for i in db.query(ForecastItem).filter(
                    ForecastItem.forecast_id == fc.id,
                    ForecastItem.is_auto_generated == True,  # noqa: E712
                ).all():
                    auto_keys.add((i.produto_id, i.plano_financeiro_id))
                db.query(ForecastItem).filter(
                    ForecastItem.forecast_id == fc.id,
                    ForecastItem.is_auto_generated == False,  # noqa: E712
                ).delete(synchronize_session=False)
            else:
                db.query(ForecastItem).filter(ForecastItem.forecast_id == fc.id).delete()

        novos_itens = []
        for linha in linhas_validas:
            key = (linha["produto_id"], linha["plano_financeiro_id"])
            if tipo == "RECEITAS" and key in auto_keys:
                continue
            fc_destino = _forecast_destino(docs, linha["produto_id"]) or dest
            linha_base = itens_base_dict.get(key)
            item_final = {}
            for mes_idx, mes_str in enumerate(MESES_STR, start=1):
                valor_novo = linha.get(mes_str, 0.0) or 0.0
                if mes_idx in meses_fechados_idx:
                    valor_base = getattr(linha_base, mes_str) if linha_base else 0.0
                    if valor_novo != valor_base:
                        db.rollback()
                        raise HTTPException(status_code=403, detail=f"Mês {mes_str} está fechado, não pode ser alterado.")
                    item_final[mes_str] = valor_base
                else:
                    item_final[mes_str] = valor_novo
            novos_itens.append(ForecastItem(
                forecast_id=fc_destino.id,
                produto_id=linha["produto_id"],
                plano_financeiro_id=linha["plano_financeiro_id"],
                **item_final,
                total_anual=sum(item_final.values()),
                is_auto_generated=False,
            ))
        db.bulk_save_objects(novos_itens)

    db.add(Auditoria(
        evento="Importacao",
        tabela_afetada="forecasts",
        registro_id=dest.id,
        campo=None,
        valor_anterior=None,
        novo_valor=f"{len(linhas_validas)} linhas importadas via Excel ({file.filename})",
        usuario_id=current_user.id,
    ))
    db.commit()
    if tipo == "VENDAS":
        injetar_vendas_em_receitas(dest, db)

    return {
        "gravado": True,
        "mensagem": f"{len(linhas_validas)} linha(s) importada(s) com sucesso.",
        "forecast_id": dest.id,
        "total_linhas": len(linhas_validas),
    }


# =====================================================================
# ENDPOINT: GERAR FORECASTS EM LOTE (Smart Automation)
# =====================================================================

class GerarLoteRequest(BaseModel):
    """Solicita a geração em lote de Forecasts para um ano/tipo."""
    ano: int
    tipo: str = "DESPESAS"

@router.post("/gerar-lote")
def gerar_forecasts_em_lote(
    data: GerarLoteRequest,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user),
):
    """Inclui no documento da versão rolling os empreendimentos do orçamento aprovado que ainda faltam."""
    tipo = data.tipo.upper()
    ano = data.ano
    if tipo == "VENDAS":
        _exigir_vendas(current_user, dept)

    descricao = _descricao_forecast_rolling(ano)

    orcamentos_base = db.query(Orcamento).filter(
        Orcamento.ano == ano,
        Orcamento.tipo == tipo,
        Orcamento.departamento_id == dept.id,
        Orcamento.status.in_(["Aprovado", "Fechado"]),
    ).all()

    if not orcamentos_base:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum Orçamento Base aprovado encontrado para {tipo} {ano} neste departamento."
        )

    produto_ids_base: set[int] = set()
    orc_por_produto: dict[int, int] = {}
    for orc in orcamentos_base:
        if orc.produto_id:
            produto_ids_base.add(orc.produto_id)
            orc_por_produto[orc.produto_id] = orc.id
        if tipo == "VENDAS":
            itens = db.query(OrcamentoVendaItem.produto_id).filter(
                OrcamentoVendaItem.orcamento_id == orc.id
            ).distinct().all()
        else:
            itens = db.query(OrcamentoItem.produto_id).filter(
                OrcamentoItem.orcamento_id == orc.id
            ).distinct().all()
        for (pid,) in itens:
            if pid is None:
                continue
            produto_ids_base.add(pid)
            orc_por_produto[pid] = orc.id

    if not produto_ids_base:
        raise HTTPException(status_code=404, detail="Os orçamentos base não possuem itens de produto.")

    docs = _docs_forecast_versao(db, ano, tipo, dept.id, descricao)
    produtos_com_forecast = _produtos_nos_forecasts(db, docs, tipo)

    criados = []
    ignorados = []
    remaining = sorted(pid for pid in produto_ids_base if pid not in produtos_com_forecast)
    for pid in sorted(produto_ids_base):
        if pid in produtos_com_forecast:
            ignorados.append(pid)

    if remaining:
        if docs:
            _assert_forecasts_editaveis(docs)
        dest = _umbrella_ou_novo(
            db,
            docs,
            descricao=descricao,
            ano=ano,
            tipo=tipo,
            current_user=current_user,
            dept=dept,
            versao_base_orcamento_id=orc_por_produto.get(remaining[0]),
            versao_base_forecast_id=None,
        )
        for produto_id in remaining:
            orc_base_id = orc_por_produto[produto_id]
            if tipo == "VENDAS":
                itens_base = db.query(OrcamentoVendaItem).filter(
                    OrcamentoVendaItem.orcamento_id == orc_base_id,
                    OrcamentoVendaItem.produto_id == produto_id,
                ).all()
                for item in copy_venda_items_to_forecast(itens_base, dest.id, ForecastVendaItem):
                    if not getattr(item, "ano", None):
                        item.ano = ano
                    db.add(item)
            else:
                itens_base = db.query(OrcamentoItem).filter(
                    OrcamentoItem.orcamento_id == orc_base_id,
                    OrcamentoItem.produto_id == produto_id,
                ).all()
                db.bulk_save_objects(copy_monthly_items_to_forecast(itens_base, dest.id, ForecastItem))

            produto = db.query(CostCenter).filter(CostCenter.id == produto_id).first()
            criados.append({
                "forecast_id": dest.id,
                "produto_id": produto_id,
                "produto_nome": produto.nome if produto else f"Produto {produto_id}",
                "descricao": descricao,
            })

    db.commit()

    return {
        "message": f"{len(criados)} Forecast(s) gerado(s) com sucesso.",
        "criados": criados,
        "ignorados_ja_existentes": ignorados,
    }



@router.delete("/{forecast_id}")
def delete_forecast(
    forecast_id: int,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    forecast = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast não encontrado.")
        
    if forecast.status not in ["Rascunho", "Reaberto"]:
        raise HTTPException(status_code=403, detail="Apenas Forecasts em Rascunho ou Reaberto podem ser excluídos.")

    if not is_admin_user(current_user) and forecast.usuario_criador_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o criador ou Administrador pode excluir este Forecast.")

    # Apagar Itens de Vendas
    db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id == forecast_id).delete()
    # Apagar Itens de Despesas
    db.query(ForecastItem).filter(ForecastItem.forecast_id == forecast_id).delete()
    
    # Excluir o próprio Forecast
    db.delete(forecast)
    db.commit()
    
    return {"message": "Forecast excluído com sucesso."}

