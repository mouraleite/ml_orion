from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.roles import is_admin_user, is_diretor_user, is_gestor_user
from app.api.deps import get_db, get_current_user, get_active_department, RoleChecker
from app.models.orcamento import Orcamento, OrcamentoItem, OrcamentoVendaItem, OrcamentoHistorico
from app.models.departamento import Departamento, DepartamentoPlano, ProdutoPlanoFinanceiro
from app.models.cost_center import CostCenter
from app.models.company import Company
from app.models.financial_plan import FinancialPlan
from app.models.payment_plan import PaymentPlan
from app.models.auditoria import Auditoria
from app.models.forecast import Forecast, ForecastItem, ForecastVendaItem
from app.services.periodos import (
    MESES_STR, mes_fechado_alterado, meses_fechados_do_ano,
    soma_meses_obj,
)
from app.services.auth_matrix import validate_budget_allocation
from app.services.budget_shared import (
    DESCRICAO_DOCUMENTO_ORCAMENTO,
    STATUS_ORCAMENTO_BLOQUEADO,
    build_empresas_map,
    build_opcoes_planos,
    build_opcoes_produtos,
    check_pessimistic_lock,
    group_venda_items,
    merge_catalog_with_used_items,
    orcamentos_da_versao_visualizacao,
    pode_editar_orcamento_vendas,
    resolve_orcamento_monthly_catalog,
    serialize_base_monthly_item,
    serialize_monthly_item_row,
    serialize_venda_base_item,
    list_visualizacao_versoes_disponiveis,
    extract_visualizacao_itens,
    is_venda_distrato,
    ordenar_e_dedupar_labels_versao,
)
from app.services.departamento_leitura import criterio_departamento
from app.services.sharepoint_departamento import (
    fix_forecasts_sharepoint_sem_departamento,
)
from app.services.excel_validator import (
    validar_despesas_receitas, validar_vendas, ler_excel
)
from app.services.excel_builder import (
    gerar_modelo_despesas_receitas, gerar_modelo_vendas, exportar_orcamento
)
from app.services.holding_consolidation import maybe_apply_holding_mldu
from app.services.budget_status import (
    exigir_permissao_status,
    irmaos_mesmo_grupo,
    resolver_transicao,
)
from datetime import datetime
from collections import Counter
from types import SimpleNamespace
import io

router = APIRouter()


def _orcamentos_mensais_do_departamento(
    db: Session,
    ano: int,
    tipo: str,
    dept: Departamento,
    *,
    leitura: bool = True,
) -> tuple[Orcamento | None, list[Orcamento]]:
    """Orçamentos do dept. ativo (sem reatribuir dept. em cada GET)."""
    dept_filter = (
        criterio_departamento(Orcamento.departamento_id, db, dept)
        if leitura
        else (Orcamento.departamento_id == dept.id)
    )
    base_q = (
        db.query(Orcamento)
        .filter(
            Orcamento.ano == ano,
            Orcamento.tipo == tipo.upper(),
            Orcamento.status != "Substituído",
            dept_filter,
        )
    )
    orcamento_ref = base_q.order_by(
        Orcamento.versao_numero.desc(), Orcamento.id.desc()
    ).first()
    if not orcamento_ref:
        return None, []

    orcamentos_do_grupo = (
        db.query(Orcamento)
        .filter(
            Orcamento.ano == ano,
            Orcamento.tipo == tipo.upper(),
            Orcamento.status != "Substituído",
            dept_filter,
            Orcamento.descricao == orcamento_ref.descricao,
        )
        .all()
    )
    return orcamento_ref, orcamentos_do_grupo


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


def _docs_ativos_dept(db: Session, ano: int, tipo: str, dept_id: int) -> list[Orcamento]:
    return (
        db.query(Orcamento)
        .filter(
            Orcamento.ano == ano,
            Orcamento.tipo == tipo,
            Orcamento.departamento_id == dept_id,
            Orcamento.status != "Substituído",
        )
        .order_by(Orcamento.versao_numero.desc(), Orcamento.id.desc())
        .all()
    )


def _produtos_nos_docs(db: Session, docs: list[Orcamento], tipo: str) -> set[int]:
    ids: set[int] = set()
    for orc in docs:
        if orc.produto_id:
            ids.add(orc.produto_id)
        if tipo == "VENDAS":
            rows = (
                db.query(OrcamentoVendaItem.produto_id)
                .filter(OrcamentoVendaItem.orcamento_id == orc.id)
                .distinct()
                .all()
            )
        else:
            rows = (
                db.query(OrcamentoItem.produto_id)
                .filter(OrcamentoItem.orcamento_id == orc.id)
                .distinct()
                .all()
            )
        for (pid,) in rows:
            if pid is not None:
                ids.add(pid)
    return ids


def _assert_docs_editaveis(docs: list[Orcamento]) -> None:
    for orc in docs:
        if orc.status in STATUS_ORCAMENTO_BLOQUEADO:
            raise HTTPException(
                status_code=403,
                detail="O orçamento deste departamento está em aprovação ou fechado. Não é possível alterar.",
            )


def _linha_mensal_sem_valor(item_data) -> bool:
    if getattr(item_data, "observacao", None):
        return False
    return soma_meses_obj(item_data) == 0


# Schemas Comuns
class OrcamentoItemCreate(BaseModel):
    produto_id: int
    plano_financeiro_id: int
    jan: float = 0.0
    fev: float = 0.0
    mar: float = 0.0
    abr: float = 0.0
    mai: float = 0.0
    jun: float = 0.0
    jul: float = 0.0
    ago: float = 0.0
    set: float = 0.0
    out: float = 0.0
    nov: float = 0.0
    dez: float = 0.0
    total_anual: float = 0.0
    observacao: str = None

class OrcamentoSaveRequest(BaseModel):
    itens: List[OrcamentoItemCreate]

class MesVenda(BaseModel):
    mes: int
    ticket_medio: float = 0.0
    numero_vendas: int = 0
    vgv: float = 0.0
    origem_venda: str = None

class OrcamentoVendaLinha(BaseModel):
    produto_id: int
    plano_venda_id: int
    meses: List[MesVenda]
    observacao: str = None

class OrcamentoVendasSaveRequest(BaseModel):
    itens: List[OrcamentoVendaLinha]

class OrcamentoStatusRequest(BaseModel):
    novo_status: str
    motivo: str = None

from typing import Optional
class OrcamentoCreateRequest(BaseModel):
    ano: int
    tipo: str
    produto_id: Optional[int] = None
    plano_financeiro_id: Optional[int] = None
    plano_venda_id: Optional[int] = None

# ==================== GERENCIAMENTO ====================

@router.get("/anos-disponiveis")
def get_anos_disponiveis(
    tipo: str,
    consolidado: bool = False,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    query = db.query(Orcamento.ano).filter(Orcamento.tipo == tipo.upper(), Orcamento.status != 'Substituído')
    _ = consolidado  # Onda A: legado ignorado
    query = query.filter(criterio_departamento(Orcamento.departamento_id, db, dept))
        
    anos = query.distinct().all()
    return {"anos": sorted([a[0] for a in anos])}


@router.get("/catalogo")
def get_catalogo_orcamento(
    tipo: str,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    """Empreendimentos e planos do departamento, mesmo sem orçamento no ano."""
    tipo = tipo.upper()
    if tipo not in ("DESPESAS", "RECEITAS", "VENDAS"):
        raise HTTPException(400, "Tipo inválido.")
    if tipo == "VENDAS":
        _exigir_vendas(current_user, dept)
        produtos = db.query(CostCenter).filter(CostCenter.status == "Ativo").all()
        planos = db.query(PaymentPlan).all()
        empresas_map = build_empresas_map(db)
        return {
            "opcoes_produtos": build_opcoes_produtos(produtos, empresas_map),
            "opcoes_planos": build_opcoes_planos(planos, nome_attr="nome"),
        }
    prefix = "2" if tipo == "DESPESAS" else "1"
    planos_permitidos, produtos_permitidos, _ = resolve_orcamento_monthly_catalog(
        db, dept, False, current_user, prefix
    )
    empresas_map = build_empresas_map(db)
    return {
        "opcoes_produtos": build_opcoes_produtos(produtos_permitidos, empresas_map),
        "opcoes_planos": build_opcoes_planos(planos_permitidos),
    }


@router.post("/criar")
def criar_orcamento(
    data: OrcamentoCreateRequest,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    tipo = data.tipo.upper()
    if tipo not in ["DESPESAS", "RECEITAS", "VENDAS"]:
        raise HTTPException(400, "Tipo inválido.")

    if tipo == "VENDAS":
        _exigir_vendas(current_user, dept)

    if not data.produto_id:
        raise HTTPException(
            status_code=400,
            detail="Centro de Custo (Empreendimento) é obrigatório para criação.",
        )

    docs = _docs_ativos_dept(db, data.ano, tipo, dept.id)
    nome = _nome_empreendimento(db, data.produto_id)
    if data.produto_id in _produtos_nos_docs(db, docs, tipo):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Já existe orçamento criado para o empreendimento {nome} em {data.ano}. "
                "Não é possível criar outro."
            ),
        )

    if docs:
        _assert_docs_editaveis(docs)
        orcamento = docs[0]
    else:
        orcamento = Orcamento(
            descricao=DESCRICAO_DOCUMENTO_ORCAMENTO,
            ano=data.ano,
            tipo=tipo,
            versao_numero=1,
            usuario_criador_id=current_user.id,
            departamento_id=dept.id,
            produto_id=None,
        )
        db.add(orcamento)
        db.flush()

    if tipo == "VENDAS":
        if not data.plano_venda_id:
            if not docs:
                db.commit()
                return {"message": "Criado com sucesso!", "orcamento_id": orcamento.id}
            raise HTTPException(400, "Plano de venda é obrigatório para incluir o empreendimento.")
        db.add(
            OrcamentoVendaItem(
                orcamento_id=orcamento.id,
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
        if not data.plano_financeiro_id:
            if not docs:
                db.commit()
                return {"message": "Criado com sucesso!", "orcamento_id": orcamento.id}
            raise HTTPException(
                400, "Plano financeiro é obrigatório para incluir o empreendimento."
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
            OrcamentoItem(
                orcamento_id=orcamento.id,
                produto_id=data.produto_id,
                plano_financeiro_id=data.plano_financeiro_id,
                **{m: 0.0 for m in MESES_STR},
                total_anual=0.0,
            )
        )

    db.commit()
    return {"message": "Criado com sucesso!", "orcamento_id": orcamento.id}


# ==================== DESPESAS ====================

@router.get("/despesas/{ano}")
def get_orcamento_despesas(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    descricao_orcamento = f"Orçamento Despesas {ano}"

    orcamento_ref, orcamentos_do_grupo = _orcamentos_mensais_do_departamento(
        db, ano, "DESPESAS", dept
    )
    if not orcamento_ref:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

    itens_base = []
    itens_base_db = []
    mapa_ids = {}
    for orc in orcamentos_do_grupo:
        mapa_ids[orc.produto_id] = orc.id
        if orc.versao_base_id:
            itens_base_db.extend(db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == orc.versao_base_id).all())

    for ib in itens_base_db:
        itens_base.append(serialize_base_monthly_item(ib))

    planos_permitidos, produtos_permitidos, is_consolidado = resolve_orcamento_monthly_catalog(
        db, dept, consolidado, current_user, "2"
    )

    itens_db = []
    for orc in orcamentos_do_grupo:
        itens_db.extend(db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == orc.id).all())

    produtos_permitidos, planos_permitidos = merge_catalog_with_used_items(
        db, produtos_permitidos, planos_permitidos, itens_db
    )
    empresas_map = build_empresas_map(db)
    opcoes_produtos = build_opcoes_produtos(produtos_permitidos, empresas_map)
    opcoes_planos = build_opcoes_planos(planos_permitidos)

    itens = [serialize_monthly_item_row(item) for item in itens_db]

    is_locked_by_other, usuario_edicao_nome = check_pessimistic_lock(orcamento_ref, current_user.id)

    return maybe_apply_holding_mldu(
        db,
        holding_mldu,
        {
        "orcamento_id": orcamento_ref.id,
        "ano": orcamento_ref.ano,
        "tipo": orcamento_ref.tipo,
        "status": orcamento_ref.status,
        "versao_numero": orcamento_ref.versao_numero,
        "versao_base_id": orcamento_ref.versao_base_id,
        "motivo_reabertura": orcamento_ref.motivo_reabertura,
        "data_criacao": orcamento_ref.data_criacao.isoformat() if orcamento_ref.data_criacao else None,
        "is_locked_by_other": is_locked_by_other,
        "usuario_edicao_nome": usuario_edicao_nome,
        "data_inicio_edicao": orcamento_ref.data_inicio_edicao.isoformat() if orcamento_ref.data_inicio_edicao else None,
        "is_consolidado": is_consolidado,
        "meses_fechados": meses_fechados_do_ano(db, ano),
        "itens": itens,
        "itens_base": itens_base,
        "opcoes_produtos": opcoes_produtos,
        "opcoes_planos": opcoes_planos,
        "mapa_ids": mapa_ids
        },
        item_kind="monthly",
    )

@router.post("/despesas/{ano}/salvar")
def salvar_orcamento_despesas(
    ano: int,
    data: OrcamentoSaveRequest,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    orcamento_ref = db.query(Orcamento).filter(Orcamento.ano == ano, Orcamento.tipo == 'DESPESAS', Orcamento.departamento_id == dept.id, Orcamento.status != 'Substituído').order_by(Orcamento.versao_numero.desc(), Orcamento.id.desc()).first()
    if not orcamento_ref:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
        
    orcamentos_do_grupo = db.query(Orcamento).filter(
        Orcamento.ano == ano, 
        Orcamento.tipo == 'DESPESAS', 
        Orcamento.departamento_id == dept.id, 
        Orcamento.status != 'Substituído',
        Orcamento.descricao == orcamento_ref.descricao
    ).all()

    meses_fechados = meses_fechados_do_ano(db, ano)

    atuais = {}
    for orc in orcamentos_do_grupo:
        if orc.status in STATUS_ORCAMENTO_BLOQUEADO:
            raise HTTPException(status_code=403, detail="O orçamento deste departamento está bloqueado para edição.")

        for item in db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == orc.id).all():
            atuais[(item.produto_id, item.plano_financeiro_id)] = item

    seen_keys: set[tuple] = set()
    for item_data in data.itens:
        key = (item_data.produto_id, item_data.plano_financeiro_id)
        if key in seen_keys:
            raise HTTPException(
                400,
                "Esta combinação empreendimento + plano já está no orçamento.",
            )
        seen_keys.add(key)
        mes_travado = mes_fechado_alterado(
            item_data, atuais.get(key), meses_fechados
        )
        if mes_travado:
            raise HTTPException(403, f"O mês {mes_travado} está fechado e não pode ser alterado.")

    por_produto = Counter(item_data.produto_id for item_data in data.itens)

    for orc in orcamentos_do_grupo:
        db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == orc.id).delete()
    
    novos_itens = []
    for item_data in data.itens:
        if _linha_mensal_sem_valor(item_data) and por_produto[item_data.produto_id] > 1:
            continue
            
        tem_permissao = validate_budget_allocation(db=db, departamento_id=dept.id, produto_id=item_data.produto_id, plano_financeiro_id=item_data.plano_financeiro_id)
        if not tem_permissao:
            db.rollback()
            raise HTTPException(403, f"Permissão negada (Produto {item_data.produto_id} x Plano {item_data.plano_financeiro_id}).")

        novos_itens.append(OrcamentoItem(
            orcamento_id=orcamento_ref.id, produto_id=item_data.produto_id, plano_financeiro_id=item_data.plano_financeiro_id,
            jan=item_data.jan, fev=item_data.fev, mar=item_data.mar, abr=item_data.abr, 
            mai=item_data.mai, jun=item_data.jun, jul=item_data.jul, ago=item_data.ago, 
            set=item_data.set, out=item_data.out, nov=item_data.nov, dez=item_data.dez,
            total_anual=item_data.total_anual, observacao=item_data.observacao
        ))
        
    db.bulk_save_objects(novos_itens)
    db.commit()
    return {"message": "Salvo com sucesso!", "linhas": len(novos_itens)}

# ==================== RECEITAS ====================

@router.get("/receitas/{ano}")
def get_orcamento_receitas(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    descricao_orcamento = f"Orçamento Receitas {ano}"

    orcamento_ref, orcamentos_do_grupo = _orcamentos_mensais_do_departamento(
        db, ano, "RECEITAS", dept
    )
    if not orcamento_ref:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
        
    itens_base = []
    itens_base_db = []
    mapa_ids = {}
    for orc in orcamentos_do_grupo:
        mapa_ids[orc.produto_id] = orc.id
        if orc.versao_base_id:
            itens_base_db.extend(db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == orc.versao_base_id).all())
            
    for ib in itens_base_db:
        itens_base.append(serialize_base_monthly_item(ib))

    planos_permitidos, produtos_permitidos, is_consolidado = resolve_orcamento_monthly_catalog(
        db, dept, consolidado, current_user, "1"
    )

    itens_db = []
    for orc in orcamentos_do_grupo:
        itens_db.extend(db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == orc.id).all())

    produtos_permitidos, planos_permitidos = merge_catalog_with_used_items(
        db, produtos_permitidos, planos_permitidos, itens_db
    )

    empresas_map = build_empresas_map(db)
    opcoes_produtos = build_opcoes_produtos(produtos_permitidos, empresas_map)
    opcoes_planos = build_opcoes_planos(planos_permitidos)

    itens = [serialize_monthly_item_row(item) for item in itens_db]

    is_locked_by_other, usuario_edicao_nome = check_pessimistic_lock(orcamento_ref, current_user.id)

    return maybe_apply_holding_mldu(
        db,
        holding_mldu,
        {
        "orcamento_id": orcamento_ref.id,
        "ano": orcamento_ref.ano,
        "tipo": orcamento_ref.tipo,
        "status": orcamento_ref.status,
        "versao_numero": orcamento_ref.versao_numero,
        "versao_base_id": orcamento_ref.versao_base_id,
        "motivo_reabertura": orcamento_ref.motivo_reabertura,
        "data_criacao": orcamento_ref.data_criacao.isoformat() if orcamento_ref.data_criacao else None,
        "is_locked_by_other": is_locked_by_other,
        "usuario_edicao_nome": usuario_edicao_nome,
        "data_inicio_edicao": orcamento_ref.data_inicio_edicao.isoformat() if orcamento_ref.data_inicio_edicao else None,
        "is_consolidado": is_consolidado,
        "meses_fechados": meses_fechados_do_ano(db, ano),
        "itens": itens,
        "itens_base": itens_base,
        "opcoes_produtos": opcoes_produtos,
        "opcoes_planos": opcoes_planos,
        "mapa_ids": mapa_ids
        },
        item_kind="monthly",
    )

@router.post("/receitas/{ano}/salvar")
def salvar_orcamento_receitas(
    ano: int,
    data: OrcamentoSaveRequest,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    orcamento = db.query(Orcamento).filter(
        Orcamento.ano == ano,
        Orcamento.tipo == 'RECEITAS',
        Orcamento.departamento_id == dept.id,
        Orcamento.status != 'Substituído',
    ).order_by(Orcamento.versao_numero.desc(), Orcamento.id.desc()).first()
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
        
    if orcamento.status in STATUS_ORCAMENTO_BLOQUEADO:
        raise HTTPException(status_code=403, detail="Orçamento bloqueado para edição. Solicite reabertura.")

    orcamentos_do_grupo = db.query(Orcamento).filter(
        Orcamento.ano == ano,
        Orcamento.tipo == 'RECEITAS',
        Orcamento.departamento_id == dept.id,
        Orcamento.status != 'Substituído',
        Orcamento.descricao == orcamento.descricao,
    ).all()

    meses_fechados = meses_fechados_do_ano(db, ano)
    atuais = {}
    for orc in orcamentos_do_grupo:
        if orc.status in STATUS_ORCAMENTO_BLOQUEADO:
            raise HTTPException(status_code=403, detail="Orçamento bloqueado para edição. Solicite reabertura.")
        for item in db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == orc.id).all():
            atuais[(item.produto_id, item.plano_financeiro_id)] = item

    seen_keys: set[tuple] = set()
    for item_data in data.itens:
        key = (item_data.produto_id, item_data.plano_financeiro_id)
        if key in seen_keys:
            raise HTTPException(400, "Esta combinação empreendimento + plano já está no orçamento.")
        seen_keys.add(key)
        mes_travado = mes_fechado_alterado(item_data, atuais.get(key), meses_fechados)
        if mes_travado:
            raise HTTPException(403, f"O mês {mes_travado} está fechado e não pode ser alterado.")

    por_produto = Counter(item_data.produto_id for item_data in data.itens)

    for orc in orcamentos_do_grupo:
        db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == orc.id).delete()
    
    novos_itens = []
    for item_data in data.itens:
        if _linha_mensal_sem_valor(item_data) and por_produto[item_data.produto_id] > 1:
            continue
        tem_permissao = validate_budget_allocation(db=db, departamento_id=dept.id, produto_id=item_data.produto_id, plano_financeiro_id=item_data.plano_financeiro_id)
        if not tem_permissao:
            db.rollback()
            raise HTTPException(403, f"Permissão negada (Prod {item_data.produto_id} x Plano {item_data.plano_financeiro_id}).")
            
        _total = soma_meses_obj(item_data)
        novos_itens.append(OrcamentoItem(
            orcamento_id=orcamento.id, produto_id=item_data.produto_id, plano_financeiro_id=item_data.plano_financeiro_id,
            jan=item_data.jan, fev=item_data.fev, mar=item_data.mar, abr=item_data.abr, mai=item_data.mai, jun=item_data.jun,
            jul=item_data.jul, ago=item_data.ago, set=item_data.set, out=item_data.out, nov=item_data.nov, dez=item_data.dez,
            total_anual=_total, observacao=item_data.observacao
        ))
    db.bulk_save_objects(novos_itens)
    db.commit()
    return {"message": "Salvo com sucesso!", "linhas": len(novos_itens)}

# ==================== VENDAS ====================

@router.get("/vendas/{ano}")
def get_orcamento_vendas(
    ano: int,
    consolidado: bool = False,
    holding_mldu: bool = False,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    _ = consolidado  # Onda A: legado ignorado
    is_consolidado = False
    _exigir_vendas(current_user, dept)

    orcamento_ref, orcamentos_do_grupo = _orcamentos_mensais_do_departamento(
        db, ano, "VENDAS", dept
    )
    if not orcamento_ref:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
        
    itens_base = []
    itens_base_db = []
    mapa_ids = {}
    for orc in orcamentos_do_grupo:
        mapa_ids[orc.produto_id] = orc.id
        if orc.versao_base_id:
            itens_base_db.extend(db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == orc.versao_base_id).all())
            
    for ib in itens_base_db:
        itens_base.append(serialize_venda_base_item(ib))

    planos_venda = db.query(PaymentPlan).all()
    produtos = db.query(CostCenter).filter(CostCenter.status == "Ativo").all()
    empresas_map = build_empresas_map(db)
    opcoes_produtos = build_opcoes_produtos(produtos, empresas_map)
    opcoes_planos = build_opcoes_planos(planos_venda, nome_attr="nome")

    itens_db = []
    for orc in orcamentos_do_grupo:
        itens_db.extend(db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == orc.id).all())

    linhas = group_venda_items(itens_db)

    is_locked_by_other, usuario_edicao_nome = check_pessimistic_lock(orcamento_ref, current_user.id)

    return maybe_apply_holding_mldu(
        db,
        holding_mldu,
        {
        "orcamento_id": orcamento_ref.id,
        "ano": orcamento_ref.ano,
        "tipo": orcamento_ref.tipo,
        "status": orcamento_ref.status,
        "versao_numero": orcamento_ref.versao_numero,
        "versao_base_id": orcamento_ref.versao_base_id,
        "motivo_reabertura": orcamento_ref.motivo_reabertura,
        "data_criacao": orcamento_ref.data_criacao.isoformat() if orcamento_ref.data_criacao else None,
        "is_locked_by_other": is_locked_by_other,
        "usuario_edicao_nome": usuario_edicao_nome,
        "data_inicio_edicao": orcamento_ref.data_inicio_edicao.isoformat() if orcamento_ref.data_inicio_edicao else None,
        "is_consolidado": is_consolidado,
        "meses_fechados": meses_fechados_do_ano(db, ano),
        "itens": linhas,
        "itens_base": itens_base,
        "opcoes_produtos": opcoes_produtos,
        "opcoes_planos": opcoes_planos,
        "mapa_ids": mapa_ids
        },
        item_kind="venda_grouped",
    )


@router.post("/vendas/{ano}/salvar")
def salvar_orcamento_vendas(
    ano: int,
    data: OrcamentoVendasSaveRequest,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    _exigir_vendas(current_user, dept)

    orcamento_ref, orcamentos_do_grupo = _orcamentos_mensais_do_departamento(
        db, ano, "VENDAS", dept, leitura=False
    )
    if not orcamento_ref:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

    meses_fechados_idx = meses_fechados_do_ano(db, ano)

    atuais = {}
    for orc in orcamentos_do_grupo:
        if orc.status in STATUS_ORCAMENTO_BLOQUEADO:
            raise HTTPException(
                status_code=403,
                detail="O orçamento deste departamento está bloqueado para edição.",
            )
        for item in db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == orc.id).all():
            atuais[(item.produto_id, item.plano_venda_id, item.mes)] = item

    seen_linhas: set[tuple] = set()
    for linha in data.itens:
        dist = "Distrato" in str(linha.observacao or "") or any(
            (m.numero_vendas or 0) < 0 for m in linha.meses
        )
        key = (linha.produto_id, linha.plano_venda_id, dist)
        if key in seen_linhas:
            raise HTTPException(400, "Esta combinação empreendimento + plano já está no orçamento.")
        seen_linhas.add(key)

    por_produto = Counter(linha.produto_id for linha in data.itens)

    for linha in data.itens:
        for mes_data in linha.meses:
            if mes_data.mes in meses_fechados_idx:
                atual = atuais.get((linha.produto_id, linha.plano_venda_id, mes_data.mes))
                ticket_val = atual.ticket_medio if atual else 0.0
                vendas_val = atual.numero_vendas if atual else 0
                if mes_data.ticket_medio != ticket_val or mes_data.numero_vendas != vendas_val:
                    raise HTTPException(403, f"O mês {mes_data.mes} está fechado e não pode ser alterado.")

    for orc in orcamentos_do_grupo:
        db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == orc.id).delete()

    novos_itens = []
    for linha in data.itens:
        meses_uteis = []
        for mes_data in linha.meses:
            vazio = mes_data.numero_vendas == 0 and mes_data.ticket_medio == 0 and not linha.observacao
            if vazio and por_produto[linha.produto_id] > 1:
                continue
            meses_uteis.append(mes_data)
        if not meses_uteis and por_produto[linha.produto_id] == 1:
            meses_uteis = [SimpleNamespace(mes=1, ticket_medio=0.0, numero_vendas=0, vgv=0.0)]

        for mes_data in meses_uteis:
            if mes_data.mes in meses_fechados_idx:
                atual = atuais.get((linha.produto_id, linha.plano_venda_id, mes_data.mes))
                ticket_val = atual.ticket_medio if atual else 0.0
                vendas_val = atual.numero_vendas if atual else 0
                vgv_val = atual.vgv if atual else 0.0
            else:
                ticket_val = mes_data.ticket_medio
                vendas_val = mes_data.numero_vendas
                vgv_val = mes_data.vgv

            novos_itens.append(OrcamentoVendaItem(
                orcamento_id=orcamento_ref.id, produto_id=linha.produto_id,
                plano_venda_id=linha.plano_venda_id, mes=mes_data.mes,
                numero_vendas=vendas_val, ticket_medio=ticket_val, vgv=vgv_val,
                observacao=linha.observacao,
            ))

    db.bulk_save_objects(novos_itens)
    db.commit()
    return {"message": "Salvo com sucesso!", "linhas": len(novos_itens)}


@router.get("/comparativo/versoes/{ano}")
def get_versoes_comparativo(
    ano: int,
    tipo: str,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    tipo = tipo.upper()
    if tipo == "CONSOLIDADO":
        seen: dict[str, dict] = {}
        for t in ("DESPESAS", "RECEITAS"):
            for v in list_visualizacao_versoes_disponiveis(db, ano, t, dept.id):
                seen.setdefault(v["id"], v)
        return ordenar_e_dedupar_labels_versao(list(seen.values()))
    return list_visualizacao_versoes_disponiveis(db, ano, tipo, dept.id)

@router.get("/comparativo")
def get_comparativo_versoes(
    versao_a: str,
    versao_b: str,
    ano: int,
    tipo: str = "DESPESAS",
    consolidado: bool = False,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    is_consolidado = consolidado or (tipo == "CONSOLIDADO")
    planos_db = db.query(FinancialPlan).all()
    planos_map = {p.id: p.name for p in planos_db}
    
    from app.models.payment_plan import PaymentPlan
    planos_venda_db = db.query(PaymentPlan).all()
    for pv in planos_venda_db:
        planos_map[f"V_{pv.id}"] = pv.nome
        
    planos_redutora = {p.id: p.fl_redutora for p in planos_db}
    produtos_db = db.query(CostCenter).all()
    produtos_map = {p.id: p.nome for p in produtos_db}

    is_vendas = tipo == "VENDAS"

    def extrair_linhas(versao_id_str):
        if not versao_id_str: return []
        prefix = versao_id_str.split("_")[0]
        identifier = "_".join(versao_id_str.split("_")[1:])
        is_orc = prefix in ("O", "OC")
        
        linhas = []
        if is_consolidado:
            if is_orc:
                for t in ("DESPESAS", "RECEITAS"):
                    for o in orcamentos_da_versao_visualizacao(db, ano, t, 0, identifier):
                        linhas.extend(getattr(o, "itens_despesa", []))
            else:
                q = db.query(Forecast).filter(Forecast.ano == ano, Forecast.descricao == identifier)
                fcs = q.all()
                for f in fcs:
                    if f.tipo == "DESPESAS" or f.tipo == "RECEITAS":
                        linhas.extend(getattr(f, "itens_despesa", []))
        else:
            if is_orc:
                orcs = orcamentos_da_versao_visualizacao(db, ano, tipo, dept.id, identifier)
                for o in orcs:
                    if tipo == "VENDAS": linhas.extend(getattr(o, "itens_venda", []))
                    else: linhas.extend(getattr(o, "itens_despesa", []))
            else:
                q = db.query(Forecast).filter(Forecast.ano == ano, Forecast.descricao == identifier, Forecast.tipo == tipo)
                if not is_consolidado:
                    fcs = q.filter(criterio_departamento(Forecast.departamento_id, db, dept)).all()
                else:
                    fcs = q.all()
                    
                for f in fcs:
                    if tipo == "VENDAS": linhas.extend(getattr(f, "itens_venda", []))
                    else: linhas.extend(getattr(f, "itens_despesa", []))
        return linhas

    linhas_a = extrair_linhas(versao_a)
    linhas_b = extrair_linhas(versao_b)

    def agrupar_linhas(linhas):
        dict_res = {}
        for item in linhas:
            if hasattr(item, "mes"):
                plano_key = f"V_{getattr(item, 'plano_venda_id', '')}"
            else:
                plano_key = getattr(item, "plano_financeiro_id", None)

            if is_vendas:
                key = (item.produto_id, plano_key, is_venda_distrato(item))
            else:
                key = (item.produto_id, plano_key)
            if key not in dict_res:
                dict_res[key] = {m: 0.0 for m in MESES_STR + ["total"]}
                if is_vendas:
                    dict_res[key]["numero_vendas"] = {m: 0 for m in MESES_STR + ["total"]}
            
            if hasattr(item, "mes"):  # Vendas
                mes_idx = getattr(item, "mes", 1) - 1
                if 0 <= mes_idx < 12:
                    m = MESES_STR[mes_idx]
                    val = float(getattr(item, "vgv", 0.0) or 0.0)
                    dict_res[key][m] += val
                    dict_res[key]["total"] += val
                    if is_vendas:
                        nq = int(getattr(item, "numero_vendas", 0) or 0)
                        dict_res[key]["numero_vendas"][m] += nq
                        dict_res[key]["numero_vendas"]["total"] += nq
            else:  # Despesas / Receitas
                for m in MESES_STR:
                    val = float(getattr(item, m, 0.0) or 0.0)
                    dict_res[key][m] += val
                    dict_res[key]["total"] += val
        return dict_res

    dict_a = agrupar_linhas(linhas_a)
    dict_b = agrupar_linhas(linhas_b)

    inclusoes = []
    exclusoes = []
    alteracoes = []

    todas_chaves = set(dict_a.keys()).union(set(dict_b.keys()))

    for key in todas_chaves:
        a = dict_a.get(key)
        b = dict_b.get(key)

        prod_id = key[0]
        plano_id = key[1]
        distrato_flag = key[2] if is_vendas else False

        zero_meses = {m: 0.0 for m in MESES_STR + ["total"]}
        if is_vendas:
            zero_meses["numero_vendas"] = {m: 0 for m in MESES_STR + ["total"]}

        item_base = {
            "produto_id": prod_id,
            "plano_financeiro_id": plano_id,
        }
        if is_vendas:
            item_base["is_distrato"] = distrato_flag

        if a and not b:
            exclusoes.append({
                **item_base,
                "versao_a": a,
                "versao_b": zero_meses
            })
        elif b and not a:
            inclusoes.append({
                **item_base,
                "versao_a": zero_meses,
                "versao_b": b
            })
        else:
            alteracoes.append({
                **item_base,
                "versao_a": a,
                "versao_b": b
            })

    return {
        "inclusoes": inclusoes,
        "exclusoes": exclusoes,
        "alteracoes": alteracoes,
        "produtos_map": produtos_map,
        "planos_map": planos_map,
        "planos_redutora": planos_redutora
    }

# ==================== VISUALIZAÇÃO (Tela 4 - Somente Leitura) ====================



@router.get("/visualizacao/{ano}")
def get_orcamento_visualizacao(
    ano: int,
    tipo: str = "DESPESAS",
    consolidado: bool = False,
    holding_mldu: bool = False,
    versao_id: Optional[str] = None,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    """Retorna a matriz do orçamento (somente leitura) - Tela 4."""
    _ = consolidado  # Onda A: legado ignorado
    is_consolidado = False

    tipo = tipo.upper()

    if tipo == "VENDAS":
        fix_forecasts_sharepoint_sem_departamento(db)

    versoes_list = list_visualizacao_versoes_disponiveis(db, ano, tipo, dept.id)

    if not versoes_list:
        return {"ano": ano, "tipo": tipo, "is_consolidado": is_consolidado, "versoes": [], "itens": []}

    # Se não passou versao, pega a primeira
    if not versao_id or not any(v["id"] == versao_id for v in versoes_list):
        versao_id = versoes_list[0]["id"]

    itens = extract_visualizacao_itens(db, ano, tipo, dept.id, versao_id)

    payload: dict = {
        "ano": ano,
        "tipo": tipo,
        "is_consolidado": is_consolidado,
        "versao_selecionada": versao_id,
        "versoes": versoes_list,
        "itens": itens,
    }

    if tipo == "VENDAS":
        planos_venda = db.query(PaymentPlan).all()
        produtos = db.query(CostCenter).filter(CostCenter.status == "Ativo").all()
        empresas_map = build_empresas_map(db)
        payload["opcoes_produtos"] = build_opcoes_produtos(produtos, empresas_map)
        payload["opcoes_planos"] = build_opcoes_planos(planos_venda, nome_attr="nome")

    kind = "visualizacao_venda" if tipo == "VENDAS" else "visualizacao_monthly"
    return maybe_apply_holding_mldu(
        db,
        holding_mldu,
        payload,
        item_kind=kind,
    )

# ==================== EXCEL — IMPORTAÇÃO / EXPORTAÇÃO (EXC-001) ====================

@router.get("/excel/modelo/{tipo}/{ano}")
def download_modelo_excel(
    tipo: str,
    ano: int,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    """
    Retorna o modelo Excel em branco para preenchimento offline.
    Tipos suportados: DESPESAS, RECEITAS, VENDAS.
    """
    tipo = tipo.upper()
    if tipo not in ("DESPESAS", "RECEITAS", "VENDAS"):
        raise HTTPException(status_code=400, detail="Tipo inválido. Use DESPESAS, RECEITAS ou VENDAS.")

    if tipo == "VENDAS":
        conteudo = gerar_modelo_vendas(db, ano)
    else:
        conteudo = gerar_modelo_despesas_receitas(db, tipo, ano, dept.id)

    filename = f"modelo_{tipo.lower()}_{ano}.xlsx"
    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/excel/exportar/{orcamento_id}")
def exportar_orcamento_excel(
    orcamento_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Exporta um orçamento existente para Excel (somente leitura)."""
    try:
        conteudo = exportar_orcamento(orcamento_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    orc = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
    filename = f"orcamento_{orcamento_id}_{orc.tipo.lower()}_{orc.ano}.xlsx"
    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/excel/validar/{tipo}/{ano}")
async def validar_excel(
    tipo: str,
    ano: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user=Depends(get_current_user),
):
    """
    Valida planilha Excel SEM gravar no banco (dry-run).
    Retorna lista de erros por linha/campo (Seção 19.1).
    COM-007: Nenhum dado é alterado nesta etapa.
    """
    tipo = tipo.upper()
    if tipo not in ("DESPESAS", "RECEITAS", "VENDAS"):
        raise HTTPException(status_code=400, detail="Tipo inválido.")

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
    """
    Importa planilha Excel com modo TUDO-OU-NADA (DEC-005, EXC-001):
    - Se QUALQUER linha tiver erro, NENHUMA é gravada.
    - Se todas válidas, substitui os itens do orçamento ativo e registra auditoria.
    """
    tipo = tipo.upper()
    if tipo not in ("DESPESAS", "RECEITAS", "VENDAS"):
        raise HTTPException(status_code=400, detail="Tipo inválido.")
    if tipo == "VENDAS":
        _exigir_vendas(current_user, dept)

    orc_existente = db.query(Orcamento).filter(
        Orcamento.ano == ano,
        Orcamento.tipo == tipo,
        Orcamento.departamento_id == dept.id,
        Orcamento.status != "Substituído",
    ).order_by(Orcamento.versao_numero.desc(), Orcamento.id.desc()).first()
    if orc_existente and orc_existente.status in STATUS_ORCAMENTO_BLOQUEADO:
        raise HTTPException(
            status_code=403,
            detail="O orçamento deste departamento está em aprovação ou fechado. A importação foi recusada.",
        )

    conteudo = await file.read()
    try:
        rows, _ = ler_excel(conteudo, tipo)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not rows:
        raise HTTPException(status_code=422, detail="Planilha sem dados.")

    # ── Validação (DEC-005: tudo-ou-nada) ─────────────────────────────────
    if tipo == "VENDAS":
        erros, linhas_validas = validar_vendas(rows, ano, dept.id, db)
    else:
        erros, linhas_validas = validar_despesas_receitas(rows, tipo, ano, dept.id, db)

    if erros:
        # CA-001: Planilha com erros → retorna 422 com relatório, sem gravar nada
        return {
            "gravado": False,
            "mensagem": "Importação recusada: a planilha contém erros. Nenhum dado foi alterado.",
            "total_linhas": len(rows),
            "total_erros": len(erros),
            "erros": erros,
        }

    orc = db.query(Orcamento).filter(
        Orcamento.ano == ano,
        Orcamento.tipo == tipo,
        Orcamento.departamento_id == dept.id,
        Orcamento.status != "Substituído",
    ).order_by(Orcamento.versao_numero.desc(), Orcamento.id.desc()).first()

    if orc and orc.status in STATUS_ORCAMENTO_BLOQUEADO:
        raise HTTPException(
            status_code=403,
            detail="O orçamento deste departamento está em aprovação ou fechado. A importação foi recusada.",
        )

    if not orc:
        orc = Orcamento(
            descricao=DESCRICAO_DOCUMENTO_ORCAMENTO,
            ano=ano,
            tipo=tipo,
            status="Rascunho",
            departamento_id=dept.id,
            usuario_criador_id=current_user.id,
            versao_numero=1,
        )
        db.add(orc)
        db.flush()

    grupo = db.query(Orcamento).filter(
        Orcamento.ano == ano,
        Orcamento.tipo == tipo,
        Orcamento.departamento_id == dept.id,
        Orcamento.status != "Substituído",
        Orcamento.descricao == orc.descricao,
    ).all()

    # ── Substitui todos os itens (tudo-ou-nada) ───────────────────────────
    if tipo == "VENDAS":
        for doc in grupo:
            db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == doc.id).delete()
        for linha in linhas_validas:
            db.add(OrcamentoVendaItem(
                orcamento_id=orc.id,
                produto_id=linha["produto_id"],
                plano_venda_id=linha["plano_venda_id"],
                mes=linha["mes"],
                ano=linha["ano"],
                numero_vendas=linha["numero_vendas"],
                ticket_medio=linha["ticket_medio"],
                vgv=linha["vgv"],
                origem_venda=linha.get("origem_venda"),
            ))
    else:
        for doc in grupo:
            db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == doc.id).delete()
        for linha in linhas_validas:
            db.add(OrcamentoItem(
                orcamento_id=orc.id,
                produto_id=linha["produto_id"],
                plano_financeiro_id=linha["plano_financeiro_id"],
                **{m: linha.get(m, 0.0) for m in MESES_STR},
                total_anual=linha.get("total_anual", 0.0),
            ))

    # ── Registro de Auditoria (Seção 19.2) ────────────────────────────────
    db.add(Auditoria(
        evento="Importacao",
        tabela_afetada="orcamentos",
        registro_id=orc.id,
        campo=None,
        valor_anterior=None,
        novo_valor=f"{len(linhas_validas)} linhas importadas via Excel ({file.filename})",
        usuario_id=current_user.id,
    ))

    db.commit()

    return {
        "gravado": True,
        "mensagem": f"{len(linhas_validas)} linha(s) importada(s) com sucesso.",
        "orcamento_id": orc.id,
        "total_linhas": len(linhas_validas),
    }



@router.post("/{orcamento_id}/status")
def change_status_orcamento(
    orcamento_id: int,
    data: OrcamentoStatusRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    orc = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

    destino, acao = resolver_transicao(orc.status, data.novo_status)
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

    alvos = irmaos_mesmo_grupo(db, Orcamento, orc) or [orc]
    for item in alvos:
        anterior = item.status
        item.status = destino
        if acao == "recusar_reabertura":
            item.motivo_reabertura = None
        db.add(OrcamentoHistorico(
            orcamento_id=item.id,
            usuario_id=current_user.id,
            status_anterior=anterior,
            status_novo=destino,
            motivo=data.motivo,
        ))
        db.add(Auditoria(
            evento="Aprovacao" if acao == "aprovar" else "Alteracao",
            tabela_afetada="orcamentos",
            registro_id=item.id,
            campo="status",
            valor_anterior=anterior,
            novo_valor=destino,
            motivo=data.motivo,
            usuario_id=current_user.id,
        ))

    db.commit()
    return {"message": f"Status alterado para {destino}", "status": destino, "registros": len(alvos)}


@router.post("/{orcamento_id}/solicitar-reabertura")
def solicitar_reabertura_orcamento(
    orcamento_id: int,
    data: OrcamentoStatusRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    motivo = (data.motivo or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="Informe o motivo da solicitação de reabertura.")

    orc = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

    destino, acao = resolver_transicao(orc.status, "Solicitação Reabertura")
    exigir_permissao_status(acao, current_user)

    alvos = irmaos_mesmo_grupo(db, Orcamento, orc) or [orc]
    for item in alvos:
        anterior = item.status
        item.status = destino
        item.motivo_reabertura = motivo
        db.add(OrcamentoHistorico(
            orcamento_id=item.id,
            usuario_id=current_user.id,
            status_anterior=anterior,
            status_novo=destino,
            motivo=motivo,
        ))
        db.add(Auditoria(
            evento="Alteracao",
            tabela_afetada="orcamentos",
            registro_id=item.id,
            campo="status",
            valor_anterior=anterior,
            novo_valor=destino,
            motivo=motivo,
            usuario_id=current_user.id,
        ))

    db.commit()
    return {"message": f"Status alterado para {destino}", "status": destino, "registros": len(alvos)}


def _arquivar_orcamento_fechado(db: Session, live: Orcamento) -> Orcamento:
    snap = Orcamento(
        descricao=live.descricao,
        ano=live.ano,
        tipo=live.tipo,
        status="Substituído",
        versao_numero=live.versao_numero,
        versao_base_id=live.id,
        usuario_criador_id=live.usuario_criador_id,
        departamento_id=live.departamento_id,
        produto_id=live.produto_id,
    )
    db.add(snap)
    db.flush()
    if live.tipo == "VENDAS":
        for i in db.query(OrcamentoVendaItem).filter_by(orcamento_id=live.id).all():
            db.add(OrcamentoVendaItem(
                orcamento_id=snap.id,
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
        for i in db.query(OrcamentoItem).filter_by(orcamento_id=live.id).all():
            meses = {m: getattr(i, m) or 0.0 for m in MESES_STR}
            db.add(OrcamentoItem(
                orcamento_id=snap.id,
                produto_id=i.produto_id,
                plano_financeiro_id=i.plano_financeiro_id,
                total_anual=i.total_anual,
                observacao=i.observacao,
                **meses,
            ))
    return snap


@router.post("/{orcamento_id}/aprovar-reabertura")
def aprovar_reabertura_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    orc = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

    destino, acao = resolver_transicao(orc.status, "Reaberto")
    exigir_permissao_status(acao, current_user)

    alvos = irmaos_mesmo_grupo(db, Orcamento, orc) or [orc]
    for item in alvos:
        _arquivar_orcamento_fechado(db, item)
        anterior = item.status
        item.status = destino
        db.add(OrcamentoHistorico(
            orcamento_id=item.id,
            usuario_id=current_user.id,
            status_anterior=anterior,
            status_novo=destino,
            motivo=item.motivo_reabertura,
        ))
        db.add(Auditoria(
            evento="Alteracao",
            tabela_afetada="orcamentos",
            registro_id=item.id,
            campo="status",
            valor_anterior=anterior,
            novo_valor=destino,
            motivo=item.motivo_reabertura,
            usuario_id=current_user.id,
        ))

    db.commit()
    return {"message": f"Status alterado para {destino}", "status": destino, "registros": len(alvos)}


@router.delete("/{orcamento_id}")
def delete_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_db),
    dept: Departamento = Depends(get_active_department),
    current_user = Depends(get_current_user)
):
    orcamento = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
        
    if orcamento.status not in ["Rascunho", "Reaberto"]:
        raise HTTPException(status_code=403, detail="Apenas Orçamentos em Rascunho ou Reaberto podem ser excluídos.")

    if not is_admin_user(current_user) and orcamento.usuario_criador_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o criador ou Administrador pode excluir este Orçamento.")

    # Apagar Itens de Vendas
    db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id == orcamento_id).delete()
    # Apagar Itens de Despesas
    db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id == orcamento_id).delete()
    
    # Excluir o próprio Orçamento
    db.delete(orcamento)
    db.commit()
    
    return {"message": "Orçamento excluído com sucesso."}

