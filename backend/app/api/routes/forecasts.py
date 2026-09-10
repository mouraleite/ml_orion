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
    resolve_forecast_despesas_catalog,
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

@router.post("/criar_de_base")
def criar_forecast_de_base(
    data: ForecastCreateRequest,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    """
    Cria um novo Forecast a partir de um Orçamento aprovado/fechado ou de um Forecast anterior.
    """
    if not data.produto_id:
        raise HTTPException(status_code=400, detail="Centro de Custo (Empreendimento) é obrigatório para criação de Forecast.")

    from datetime import datetime
    hoje = datetime.now()
    if data.ano == hoje.year:
        meses_realizados = hoje.month - 1
        meses_projetados = 13 - hoje.month
    elif data.ano < hoje.year:
        meses_realizados = 12
        meses_projetados = 0
    else:
        meses_realizados = 0
        meses_projetados = 12
        
    descricao = f"Forecast - {meses_realizados}+{meses_projetados}"

    # Trava 1: Se já existe um forecast com o MESMO nome para este produto (Regra estrita)
    existente_nome = db.query(Forecast).filter(
        Forecast.produto_id == data.produto_id, 
        Forecast.descricao == descricao
    ).first()
    
    if existente_nome:
        raise HTTPException(status_code=400, detail=f"Já existe um {descricao} para este Empreendimento. Acesse-o na lista de versões para realizar alterações.")

    # Trava 2: Se tem algum forecast em aberto (Rascunho/Reaberto)
    query_existente = db.query(Forecast).filter(
        Forecast.ano == data.ano, 
        Forecast.tipo == data.tipo,
        Forecast.status.in_(["Rascunho", "Reaberto"]),
        Forecast.produto_id == data.produto_id
    )
    existente = query_existente.first()
    if existente:
        raise HTTPException(status_code=400, detail="Já existe um Forecast aberto para este Empreendimento. Salve ou aprove-o primeiro.")
        
    # Calcula nova versão (só numérico interno)
    query_versao = db.query(Forecast).filter(
        Forecast.ano == data.ano,
        Forecast.tipo == data.tipo,
        Forecast.produto_id == data.produto_id
    )
    
    ultima_versao = query_versao.order_by(Forecast.versao_numero.desc()).first()
    nova_versao_num = (ultima_versao.versao_numero + 1) if ultima_versao else 1
    
    # Auto-close months
    if meses_realizados > 0:
        from app.models.fechamento import ClosedMonth
        meses_fechados_existentes = db.query(ClosedMonth.mes).filter(ClosedMonth.ano == data.ano).all()
        meses_fechados_existentes = [m[0] for m in meses_fechados_existentes]
        
        for m in range(1, meses_realizados + 1):
            if m not in meses_fechados_existentes:
                novo_fechamento = ClosedMonth(
                    ano=data.ano,
                    mes=m,
                    fechado_por_id=current_user.id
                )
                db.add(novo_fechamento)
    
    novo_forecast = Forecast(
        descricao=descricao,
        ano=data.ano,
        tipo=data.tipo,
        versao_numero=nova_versao_num,
        status="Rascunho",
        usuario_criador_id=current_user.id,
        departamento_id=dept.id,
        produto_id=data.produto_id,  # Fase 2
        versao_base_orcamento_id=data.versao_base_orcamento_id,
        versao_base_forecast_id=data.versao_base_forecast_id
    )
    db.add(novo_forecast)
    db.commit()
    db.refresh(novo_forecast)
    
    # Copia itens da base
    if data.tipo == "DESPESAS":
        if data.versao_base_orcamento_id:
            itens_base = db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == data.versao_base_orcamento_id).all()
        elif data.versao_base_forecast_id:
            itens_base = db.query(ForecastItem).filter(ForecastItem.forecast_id == data.versao_base_forecast_id).all()
        else:
            itens_base = []
            
        novos_itens = copy_monthly_items_to_forecast(itens_base, novo_forecast.id, ForecastItem)
        db.bulk_save_objects(novos_itens)

    elif data.tipo == "VENDAS":
        if data.versao_base_orcamento_id:
            itens_base = db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == data.versao_base_orcamento_id).all()
        elif data.versao_base_forecast_id:
            itens_base = db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id == data.versao_base_forecast_id).all()
        else:
            itens_base = []

        novos_itens = copy_venda_items_to_forecast(itens_base, novo_forecast.id, ForecastVendaItem)
        db.bulk_save_objects(novos_itens)
        
    db.commit()
    return {"message": "Forecast criado com sucesso", "forecast_id": novo_forecast.id}


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
            forecast = db.query(Forecast).filter(Forecast.ano == ano, Forecast.tipo == 'DESPESAS', criterio_departamento(Forecast.departamento_id, db, dept)).order_by(Forecast.versao_numero.desc()).first()
        
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
    forecast_ref = db.query(Forecast).filter(Forecast.ano == ano, Forecast.tipo == 'DESPESAS', Forecast.departamento_id == dept.id).order_by(Forecast.versao_numero.desc()).first()
    if not forecast_ref:
        raise HTTPException(status_code=404, detail="Forecast não encontrado.")
        
    # Carrega todos os forecasts deste grupo de descricao
    forecasts_do_grupo = db.query(Forecast).filter(
        Forecast.ano == ano, 
        Forecast.tipo == 'DESPESAS', 
        Forecast.departamento_id == dept.id,
        Forecast.descricao == forecast_ref.descricao
    ).all()
    
    fc_por_produto = {fc.produto_id: fc for fc in forecasts_do_grupo}
    
    # Verificar meses fechados (FC-DESP-002)
    meses_fechados_db = db.query(ClosedMonth).filter(ClosedMonth.ano == ano).all()
    meses_fechados_idx = [mf.mes for mf in meses_fechados_db]
    
    # Buscar itens da base para todos os forecasts do grupo
    itens_base_dict = {}
    for fc in forecasts_do_grupo:
        if fc.status in ["Aprovado", "Fechado", "Em aprovação"]:
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
            
        fc_destino = fc_por_produto.get(item_data.produto_id)
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
    if not is_admin_user(current_user) and dept.nome.upper() != "COMERCIAL":
        raise HTTPException(status_code=403, detail="Restrito ao Comercial.")

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
        "mapa_ids": mapa_ids
        }

    # AGRUPAMENTO POR DESCRICAO
    forecasts_do_grupo = db.query(Forecast).filter(
        Forecast.ano == ano, 
        Forecast.tipo == 'VENDAS',
        Forecast.descricao == forecast.descricao,
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
    if not is_admin_user(current_user) and dept.nome.upper() != "COMERCIAL":
        raise HTTPException(status_code=403, detail="Restrito ao Comercial.")

    forecast_ref = db.query(Forecast).filter(
        Forecast.ano == ano,
        Forecast.tipo == 'VENDAS',
        Forecast.departamento_id == dept.id,
    ).order_by(Forecast.versao_numero.desc()).first()
    
    if not forecast_ref:
        raise HTTPException(status_code=404, detail="Forecast não encontrado.")
        
    forecasts_do_grupo = db.query(Forecast).filter(
        Forecast.ano == ano, 
        Forecast.tipo == 'VENDAS', 
        Forecast.descricao == forecast_ref.descricao,
        Forecast.departamento_id == dept.id,
    ).all()
    
    fc_por_produto = {fc.produto_id: fc for fc in forecasts_do_grupo}

    meses_fechados_db = db.query(ClosedMonth).filter(ClosedMonth.ano == ano).all()
    meses_fechados_idx = [mf.mes for mf in meses_fechados_db]

    itens_base_dict = {}
    for fc in forecasts_do_grupo:
        if fc.status in ["Aprovado", "Fechado", "Em aprovação"]:
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

            fc_destino = fc_por_produto.get(linha.produto_id)
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
    injetar_vendas_em_receitas(forecast, db)
    
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
    exigir_permissao_status(acao, current_user)

    alvos = irmaos_mesmo_grupo(db, Forecast, fc) or [fc]
    for item in alvos:
        anterior = item.status
        item.status = destino
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
    # Adicionar o ano atual e próximo se não existirem (como fallback para o frontend)
    from datetime import datetime
    year_now = datetime.now().year
    anos_list = sorted([a[0] for a in anos])
    if year_now not in anos_list:
        anos_list.append(year_now)
    
        
    return {"anos": sorted(list(set(anos_list)))}

from app.services.excel_builder import gerar_modelo_despesas_receitas, gerar_modelo_vendas, exportar_forecast
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
    raise HTTPException(status_code=501, detail="Validação de importação de Forecast ainda não implementada no backend.")

@router.post("/excel/importar/{tipo}/{ano}")
async def importar_excel(
    tipo: str,
    ano: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="Importação de Forecast ainda não implementada no backend.")


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
    """
    Automacao Smart: Varre todos os Orcamentos 'Base' aprovados do departamento,
    verifica quais produtos (Centros de Custo) ainda nao tem Forecast ativo
    para o ano/tipo solicitado, e os cria automaticamente.
    """
    tipo = data.tipo.upper()
    ano = data.ano

    hoje = datetime.now()
    if ano == hoje.year:
        meses_realizados = hoje.month - 1
        meses_projetados = 13 - hoje.month
    elif ano < hoje.year:
        meses_realizados, meses_projetados = 12, 0
    else:
        meses_realizados, meses_projetados = 0, 12
    descricao_base = f"{meses_realizados}+{meses_projetados}"

    # 1. Busca todos os Orcamentos aprovados/fechados do departamento para o ano e tipo
    orcamentos_base = db.query(Orcamento).filter(
        Orcamento.ano == ano,
        Orcamento.tipo == tipo,
        Orcamento.departamento_id == dept.id,
        Orcamento.status.in_(["Aprovado", "Fechado"])
    ).all()

    if not orcamentos_base:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum Orçamento Base aprovado encontrado para {tipo} {ano} neste departamento."
        )

    ja_tem_forecast = ("Rascunho", "Reaberto", "Em aprovação", "Aprovado", "Fechado")

    # 2. Produtos do orçamento (cabeçalho e linhas)
    produto_ids_base: set[int] = set()
    orc_por_produto: dict[int, int] = {}  # produto_id -> orcamento_id
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

    # 3. Quem já tem forecast deste ano/tipo não entra de novo
    forecasts_existentes = db.query(Forecast.produto_id).filter(
        Forecast.ano == ano,
        Forecast.tipo == tipo,
        Forecast.departamento_id == dept.id,
        Forecast.status.in_(ja_tem_forecast),
        Forecast.produto_id.isnot(None),
    ).all()
    produtos_com_forecast = {pid for (pid,) in forecasts_existentes}

    # 4. Para cada produto SEM forecast, cria um novo
    criados = []
    ignorados = []

    for produto_id in sorted(produto_ids_base):
        if produto_id in produtos_com_forecast:
            ignorados.append(produto_id)
            continue

        orc_base_id = orc_por_produto[produto_id]
        orc_base = db.query(Orcamento).filter(Orcamento.id == orc_base_id).first()

        # Calcula numero de versao para esse produto
        ultima_versao = db.query(Forecast).filter(
            Forecast.ano == ano, Forecast.tipo == tipo, Forecast.produto_id == produto_id
        ).order_by(Forecast.versao_numero.desc()).first()
        nova_versao_num = (ultima_versao.versao_numero + 1) if ultima_versao else 1

        descricao = f"Forecast - {descricao_base}"
        if nova_versao_num > 1:
            descricao += f" (v{nova_versao_num})"

        novo_forecast = Forecast(
            descricao=descricao,
            ano=ano,
            tipo=tipo,
            mes_corte=meses_realizados + 1,
            versao_numero=nova_versao_num,
            status="Rascunho",
            usuario_criador_id=current_user.id,
            departamento_id=dept.id,
            produto_id=produto_id,
            versao_base_orcamento_id=orc_base_id
        )
        db.add(novo_forecast)
        db.flush()  # precisa do id para copiar itens

        if tipo == "VENDAS":
            itens_base = db.query(OrcamentoVendaItem).filter(
                OrcamentoVendaItem.orcamento_id == orc_base_id,
                OrcamentoVendaItem.produto_id == produto_id,
            ).all()
            for item in copy_venda_items_to_forecast(itens_base, novo_forecast.id, ForecastVendaItem):
                if not getattr(item, "ano", None):
                    item.ano = ano
                db.add(item)
        else:
            itens_base = db.query(OrcamentoItem).filter(
                OrcamentoItem.orcamento_id == orc_base_id,
                OrcamentoItem.produto_id == produto_id,
            ).all()
            for ib in itens_base:
                db.add(ForecastItem(
                    forecast_id=novo_forecast.id, produto_id=ib.produto_id,
                    plano_financeiro_id=ib.plano_financeiro_id,
                    jan=ib.jan, fev=ib.fev, mar=ib.mar, abr=ib.abr,
                    mai=ib.mai, jun=ib.jun, jul=ib.jul, ago=ib.ago,
                    set=ib.set, out=ib.out, nov=ib.nov, dez=ib.dez,
                    total_anual=ib.total_anual,
                ))

        produto = db.query(CostCenter).filter(CostCenter.id == produto_id).first()
        criados.append({
            "forecast_id": novo_forecast.id,
            "produto_id": produto_id,
            "produto_nome": produto.nome if produto else f"Produto {produto_id}",
            "descricao": descricao
        })

    db.commit()

    return {
        "message": f"{len(criados)} Forecast(s) gerado(s) com sucesso.",
        "criados": criados,
        "ignorados_ja_existentes": ignorados
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

