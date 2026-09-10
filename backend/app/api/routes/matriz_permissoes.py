from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel

from app.api.deps import get_db, get_current_user
from app.models.departamento import (
    DepartamentoPlano,
    ProdutoPlanoFinanceiro,
    Departamento,
    DepartamentoCostCenter,
    DeparaAutorizacaoDepartamento,
    Diretoria,
)
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.schemas.user import UserResponse
from app.services import sienge_api
from app.services.depara_autorizacao import (
    aplicar_depara_manual,
    depara_payload,
    sincronizar_depara,
)

router = APIRouter()

# =====================================================
# SCHEMAS
# =====================================================

class DepartamentoPlanoCreate(BaseModel):
    departamento_id: int
    plano_financeiro_id: int
    permitido: bool = True

class ProdutoPlanoCreate(BaseModel):
    produto_id: int
    plano_financeiro_id: int
    permitido: bool = True

class DepartamentoCostCenterCreate(BaseModel):
    departamento_id: int
    cost_center_id: int
    permitido: bool = True

class BulkPermissaoCreate(BaseModel):
    departamento_id: int
    ids: List[int]
    permitido: bool = True

class CopiarAutorizacoesRequest(BaseModel):
    origem_id: int
    copiar_obras: bool = True
    copiar_planos: bool = True

class DepartamentoCreate(BaseModel):
    nome: str
    ativo: bool = True
    diretoria_id: Optional[int] = None

class DepartamentoResponse(BaseModel):
    id: int
    nome: str
    ativo: bool
    is_residual: bool = False
    diretoria_id: Optional[int] = None
    model_config = {"from_attributes": True}


class DiretoriaCreate(BaseModel):
    nome: str
    ativo: bool = True
    departamento_ids: List[int] = []


class DiretoriaUpdate(BaseModel):
    nome: Optional[str] = None
    ativo: Optional[bool] = None
    departamento_ids: Optional[List[int]] = None


class DiretoriaResponse(BaseModel):
    id: int
    nome: str
    ativo: bool
    departamento_ids: List[int] = []
    model_config = {"from_attributes": True}


def _diretoria_payload(di: Diretoria) -> dict:
    ids = [d.id for d in (di.departamentos or [])]
    return {
        "id": di.id,
        "nome": di.nome,
        "ativo": bool(di.ativo),
        "departamento_ids": ids,
    }


def _vincular_departamentos(db: Session, di: Diretoria, departamento_ids: List[int]) -> None:
    """Um dept só pode estar em uma diretoria."""
    wanted = set(int(i) for i in departamento_ids)
    for dept in db.query(Departamento).filter(Departamento.diretoria_id == di.id).all():
        if dept.id not in wanted:
            dept.diretoria_id = None
    if not wanted:
        return
    depts = db.query(Departamento).filter(Departamento.id.in_(wanted)).all()
    if len(depts) != len(wanted):
        raise HTTPException(400, "Departamento inválido na diretoria.")
    for dept in depts:
        dept.diretoria_id = di.id


# =====================================================
# DEPARTAMENTOS (CRUD INTERNO)
# =====================================================

@router.get("/departamentos", response_model=List[DepartamentoResponse])
def list_departamentos(db: Session = Depends(get_db)):
    """Lista todos os departamentos internos do ERP"""
    return db.query(Departamento).filter(Departamento.ativo == True).all()

@router.get("/departamentos/todos", response_model=List[DepartamentoResponse])
def list_all_departamentos(db: Session = Depends(get_db)):
    """Lista todos os departamentos, incluindo inativos"""
    return db.query(Departamento).all()

@router.post("/departamentos", response_model=DepartamentoResponse)
def create_departamento(
    data: DepartamentoCreate,
    db: Session = Depends(get_db)
):
    """Cria um novo departamento interno"""
    if data.diretoria_id is not None:
        di = db.query(Diretoria).filter(Diretoria.id == data.diretoria_id).first()
        if not di:
            raise HTTPException(400, "Diretoria não encontrada.")
    dept = Departamento(nome=data.nome, ativo=data.ativo, diretoria_id=data.diretoria_id)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept

@router.put("/departamentos/{dept_id}", response_model=DepartamentoResponse)
def update_departamento(
    dept_id: int,
    data: DepartamentoCreate,
    db: Session = Depends(get_db)
):
    dept = db.query(Departamento).filter(Departamento.id == dept_id).first()
    if not dept:
        raise HTTPException(404, "Departamento não encontrado")
    if data.diretoria_id is not None:
        di = db.query(Diretoria).filter(Diretoria.id == data.diretoria_id).first()
        if not di:
            raise HTTPException(400, "Diretoria não encontrada.")
    dept.nome = data.nome
    dept.ativo = data.ativo
    dept.diretoria_id = data.diretoria_id
    db.commit()
    db.refresh(dept)
    return dept

@router.delete("/departamentos/{dept_id}")
def delete_departamento(
    dept_id: int,
    db: Session = Depends(get_db)
):
    dept = db.query(Departamento).filter(Departamento.id == dept_id).first()
    if not dept:
        raise HTTPException(404, "Departamento não encontrado")
    db.delete(dept)
    db.commit()
    return {"ok": True}


# =====================================================
# DIRETORIAS
# =====================================================

@router.get("/diretorias", response_model=List[DiretoriaResponse])
def list_diretorias(db: Session = Depends(get_db)):
    rows = (
        db.query(Diretoria)
        .options(joinedload(Diretoria.departamentos))
        .order_by(Diretoria.nome)
        .all()
    )
    return [_diretoria_payload(d) for d in rows]


@router.post("/diretorias", response_model=DiretoriaResponse)
def create_diretoria(data: DiretoriaCreate, db: Session = Depends(get_db)):
    di = Diretoria(nome=data.nome.strip(), ativo=data.ativo)
    if not di.nome:
        raise HTTPException(400, "Nome da diretoria é obrigatório.")
    db.add(di)
    db.flush()
    _vincular_departamentos(db, di, data.departamento_ids)
    db.commit()
    di = (
        db.query(Diretoria)
        .options(joinedload(Diretoria.departamentos))
        .filter(Diretoria.id == di.id)
        .first()
    )
    return _diretoria_payload(di)


@router.put("/diretorias/{diretoria_id}", response_model=DiretoriaResponse)
def update_diretoria(diretoria_id: int, data: DiretoriaUpdate, db: Session = Depends(get_db)):
    di = (
        db.query(Diretoria)
        .options(joinedload(Diretoria.departamentos))
        .filter(Diretoria.id == diretoria_id)
        .first()
    )
    if not di:
        raise HTTPException(404, "Diretoria não encontrada.")
    if data.nome is not None:
        nome = data.nome.strip()
        if not nome:
            raise HTTPException(400, "Nome da diretoria é obrigatório.")
        di.nome = nome
    if data.ativo is not None:
        di.ativo = data.ativo
    if data.departamento_ids is not None:
        _vincular_departamentos(db, di, data.departamento_ids)
    db.commit()
    di = (
        db.query(Diretoria)
        .options(joinedload(Diretoria.departamentos))
        .filter(Diretoria.id == diretoria_id)
        .first()
    )
    return _diretoria_payload(di)


@router.delete("/diretorias/{diretoria_id}")
def delete_diretoria(diretoria_id: int, db: Session = Depends(get_db)):
    di = db.query(Diretoria).filter(Diretoria.id == diretoria_id).first()
    if not di:
        raise HTTPException(404, "Diretoria não encontrada.")
    for dept in db.query(Departamento).filter(Departamento.diretoria_id == diretoria_id).all():
        dept.diretoria_id = None
    db.delete(di)
    db.commit()
    return {"ok": True}


# =====================================================
# DE-PARA: name Sienge → departamento (Apoio)
# =====================================================

class DeparaUpdate(BaseModel):
    departamento_id: Optional[int] = None


def _depara_com_dept(db: Session, row_id: int | None = None):
    q = db.query(DeparaAutorizacaoDepartamento).options(
        joinedload(DeparaAutorizacaoDepartamento.departamento)
    )
    if row_id is not None:
        return q.filter(DeparaAutorizacaoDepartamento.id == row_id).first()
    return q.order_by(DeparaAutorizacaoDepartamento.nome_sienge).all()


@router.get("/depara-autorizacao")
def list_depara_autorizacao(db: Session = Depends(get_db)):
    return [depara_payload(r) for r in _depara_com_dept(db)]


@router.post("/depara-autorizacao/sync")
def sync_depara_autorizacao(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sincronizar_depara(db, sienge_api.get_departamentos())
    return [depara_payload(r) for r in _depara_com_dept(db)]


@router.put("/depara-autorizacao/{row_id}")
def update_depara_autorizacao(
    row_id: int,
    data: DeparaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        aplicar_depara_manual(db, row_id, data.departamento_id)
    except LookupError:
        raise HTTPException(404, "De-para não encontrado")
    except ValueError as exc:
        if str(exc) == "consolidado":
            raise HTTPException(400, "Corporativo é residual: use Corporativo (residual) no de-para, não o cadastro.")
        raise HTTPException(404, "Departamento não encontrado")
    row = _depara_com_dept(db, row_id)
    return depara_payload(row)


@router.get("/corporativo-residual")
def get_corporativo_residual(db: Session = Depends(get_db)):
    """Resumo do residual. Não altera orçado/realizado."""
    from app.services.corporativo import ensure_corporativo_departamento, resumo_residual

    ensure_corporativo_departamento(db)
    return resumo_residual(db)


# =====================================================
# MATRIZ: Departamento x Centros de Custo (Obras)
# =====================================================

def _sienge_id_sort_key(cc: CostCenter):
    raw = cc.id_sienge or ""
    try:
        return (0, int(raw))
    except ValueError:
        return (1, raw)


@router.get("/departamentos/{dept_id}/cost-centers")
def get_dept_cost_centers(dept_id: int, db: Session = Depends(get_db)):
    """Retorna todos os CCs e quais estão liberados para o departamento"""
    all_ccs = sorted(db.query(CostCenter).all(), key=_sienge_id_sort_key)
    links = {
        lk.cost_center_id: lk.permitido 
        for lk in db.query(DepartamentoCostCenter)
            .filter(DepartamentoCostCenter.departamento_id == dept_id)
            .all()
    }
    return [
        {
            "id": cc.id,
            "id_sienge": cc.id_sienge,
            "nome": cc.nome,
            "status": cc.status,
            "id_empresa": (cc.custom_data or {}).get("__id_empresa"),
            "nome_empresa": (cc.custom_data or {}).get("__nome_empresa"),
            "permitido": links.get(cc.id, False)
        }
        for cc in all_ccs
    ]

@router.post("/departamento-cost-center")
def set_departamento_cost_center(
    data: DepartamentoCostCenterCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Associa/remove um Centro de Custo ao Departamento"""
    link = db.query(DepartamentoCostCenter).filter(
        DepartamentoCostCenter.departamento_id == data.departamento_id,
        DepartamentoCostCenter.cost_center_id == data.cost_center_id
    ).first()
    
    if link:
        link.permitido = data.permitido
    else:
        link = DepartamentoCostCenter(
            departamento_id=data.departamento_id,
            cost_center_id=data.cost_center_id,
            permitido=data.permitido
        )
        db.add(link)
    
    db.commit()
    return {"message": "Permissão Departamento x Centro de Custo atualizada"}


def _upsert_departamento_cost_center(db: Session, departamento_id: int, cost_center_id: int, permitido: bool):
    link = db.query(DepartamentoCostCenter).filter(
        DepartamentoCostCenter.departamento_id == departamento_id,
        DepartamentoCostCenter.cost_center_id == cost_center_id,
    ).first()
    if link:
        link.permitido = permitido
    else:
        db.add(DepartamentoCostCenter(
            departamento_id=departamento_id,
            cost_center_id=cost_center_id,
            permitido=permitido,
        ))


@router.post("/departamento-cost-center/bulk")
def bulk_set_departamento_cost_center(
    data: BulkPermissaoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Atualiza permissões de vários centros de custo de uma vez"""
    for cc_id in data.ids:
        _upsert_departamento_cost_center(db, data.departamento_id, cc_id, data.permitido)
    db.commit()
    return {"message": f"{len(data.ids)} permissões atualizadas", "count": len(data.ids)}

# =====================================================
# MATRIZ: Departamento x Planos Financeiros
# =====================================================

@router.get("/departamentos/{dept_id}/planos")
def get_dept_planos(dept_id: int, db: Session = Depends(get_db)):
    """Retorna todos os Planos Financeiros e quais estão liberados para o departamento"""
    all_planos = db.query(FinancialPlan).order_by(FinancialPlan.db_id).all()
    links = {
        lk.plano_financeiro_id: lk.permitido 
        for lk in db.query(DepartamentoPlano)
            .filter(DepartamentoPlano.departamento_id == dept_id)
            .all()
    }
    return [
        {
            "id": p.id,
            "nome": p.name,
            "tipo": p.tp_conta or "",
            "db_id": p.db_id or "",
            "permitido": links.get(p.id, False)
        }
        for p in all_planos
    ]

@router.post("/departamento-plano")
def set_departamento_plano(
    data: DepartamentoPlanoCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Atribui ou atualiza a permissão de um Departamento para um Plano Financeiro"""
    link = db.query(DepartamentoPlano).filter(
        DepartamentoPlano.departamento_id == data.departamento_id,
        DepartamentoPlano.plano_financeiro_id == data.plano_financeiro_id
    ).first()
    
    if link:
        link.permitido = data.permitido
    else:
        link = DepartamentoPlano(
            departamento_id=data.departamento_id,
            plano_financeiro_id=data.plano_financeiro_id,
            permitido=data.permitido
        )
        db.add(link)
    
    db.commit()
    return {"message": "Permissão Departamento x Plano atualizada"}


def _upsert_departamento_plano(db: Session, departamento_id: int, plano_financeiro_id: int, permitido: bool):
    link = db.query(DepartamentoPlano).filter(
        DepartamentoPlano.departamento_id == departamento_id,
        DepartamentoPlano.plano_financeiro_id == plano_financeiro_id,
    ).first()
    if link:
        link.permitido = permitido
    else:
        db.add(DepartamentoPlano(
            departamento_id=departamento_id,
            plano_financeiro_id=plano_financeiro_id,
            permitido=permitido,
        ))


@router.post("/departamento-plano/bulk")
def bulk_set_departamento_plano(
    data: BulkPermissaoCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Atualiza permissões de vários planos financeiros de uma vez"""
    for plano_id in data.ids:
        _upsert_departamento_plano(db, data.departamento_id, plano_id, data.permitido)
    db.commit()
    return {"message": f"{len(data.ids)} permissões atualizadas", "count": len(data.ids)}


@router.post("/departamentos/{dest_id}/copiar-autorizacoes")
def copiar_autorizacoes(
    dest_id: int,
    data: CopiarAutorizacoesRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Copia obras e/ou planos liberados da origem para o destino, substituindo o que estava lá."""
    if data.origem_id == dest_id:
        raise HTTPException(400, "Escolha um departamento diferente do atual.")
    if not data.copiar_obras and not data.copiar_planos:
        raise HTTPException(400, "Marque obras, planos ou os dois.")

    origem = db.query(Departamento).filter(Departamento.id == data.origem_id).first()
    dest = db.query(Departamento).filter(Departamento.id == dest_id).first()
    if not origem or not dest:
        raise HTTPException(404, "Departamento não encontrado")

    result = {"obras": 0, "planos": 0, "origem": origem.nome, "destino": dest.nome}

    if data.copiar_obras:
        origem_ids = {
            lk.cost_center_id
            for lk in db.query(DepartamentoCostCenter).filter(
                DepartamentoCostCenter.departamento_id == origem.id,
                DepartamentoCostCenter.permitido == True,
            ).all()
        }
        dest_links = db.query(DepartamentoCostCenter).filter(
            DepartamentoCostCenter.departamento_id == dest.id
        ).all()
        existing = {lk.cost_center_id for lk in dest_links}
        for lk in dest_links:
            lk.permitido = lk.cost_center_id in origem_ids
        for cc_id in origem_ids:
            if cc_id not in existing:
                db.add(DepartamentoCostCenter(
                    departamento_id=dest.id,
                    cost_center_id=cc_id,
                    permitido=True,
                ))
        result["obras"] = len(origem_ids)

    if data.copiar_planos:
        origem_ids = {
            lk.plano_financeiro_id
            for lk in db.query(DepartamentoPlano).filter(
                DepartamentoPlano.departamento_id == origem.id,
                DepartamentoPlano.permitido == True,
            ).all()
        }
        dest_links = db.query(DepartamentoPlano).filter(
            DepartamentoPlano.departamento_id == dest.id
        ).all()
        existing = {lk.plano_financeiro_id for lk in dest_links}
        for lk in dest_links:
            lk.permitido = lk.plano_financeiro_id in origem_ids
        for plano_id in origem_ids:
            if plano_id not in existing:
                db.add(DepartamentoPlano(
                    departamento_id=dest.id,
                    plano_financeiro_id=plano_id,
                    permitido=True,
                ))
        result["planos"] = len(origem_ids)

    db.commit()
    return result

# =====================================================
# MATRIZ: Produto x Planos Financeiros (legado)
# =====================================================

@router.post("/produto-plano")
def set_produto_plano(
    data: ProdutoPlanoCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Atribui ou atualiza a permissão de um Produto para um Plano Financeiro"""
    link = db.query(ProdutoPlanoFinanceiro).filter(
        ProdutoPlanoFinanceiro.produto_id == data.produto_id,
        ProdutoPlanoFinanceiro.plano_financeiro_id == data.plano_financeiro_id
    ).first()
    
    if link:
        link.permitido = data.permitido
    else:
        link = ProdutoPlanoFinanceiro(
            produto_id=data.produto_id,
            plano_financeiro_id=data.plano_financeiro_id,
            permitido=data.permitido
        )
        db.add(link)
    
    db.commit()
    return {"message": "Permissão Produto x Plano atualizada"}
