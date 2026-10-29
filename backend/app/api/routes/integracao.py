from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, not_, and_, or_
from pydantic import BaseModel

from app.api.deps import get_db, get_current_active_admin
from app.db.database import SessionLocal
from app.models.integracao import RealizadoSienge, IntegracaoLog
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.services.integracao_sienge import run_integracao_sienge

router = APIRouter()

class ReprocessRequest(BaseModel):
    start_date: str
    end_date: str

class IntegracaoLogResponse(BaseModel):
    id: int
    processo: str
    inicio: datetime
    fim: Optional[datetime]
    status: str
    volume_processado: int
    erros: Optional[str]

    class Config:
        from_attributes = True

class PendenciaResponse(BaseModel):
    id: int
    id_sienge: str
    produto_id_sienge: Optional[str]
    plano_financeiro_id_sienge: Optional[str]
    tipo: Optional[str]
    mes: int
    ano: int
    valor: float
    vgv: float
    data_integracao: datetime

    class Config:
        from_attributes = True

@router.post("/reprocessar")
def reprocessar_integracao(
    req: ReprocessRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_active_admin)
):
    try:
        # Validação simples
        datetime.strptime(req.start_date, "%Y-%m-%d")
        datetime.strptime(req.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")

    def _run():
        session = SessionLocal()
        try:
            run_integracao_sienge(session, req.start_date, req.end_date)
        finally:
            session.close()

    background_tasks.add_task(_run)
    return {"message": "Reprocessamento iniciado em background."}

@router.get("/logs", response_model=dict)
def get_integracao_logs(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    query = db.query(IntegracaoLog).order_by(desc(IntegracaoLog.inicio))
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return {
        "items": items,
        "total": total
    }

@router.get("/pendencias", response_model=dict)
def get_pendencias(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    # Subqueries para pegar IDs locais conhecidos
    cc_ids = db.query(CostCenter.id_sienge).filter(CostCenter.id_sienge.isnot(None)).scalar_subquery()
    fp_ids = db.query(FinancialPlan.db_id).filter(FinancialPlan.db_id.isnot(None)).scalar_subquery()

    # Pendência: produto não está na base (se houver produto_id_sienge na despesa/receita) 
    # OU plano financeiro não está na base (se houver plano)
    
    # Obs: Vendas geralmente não têm plano financeiro no Bulk Data (ver integracao_sienge.py)
    # Então se tipo == "Venda", não exige plano financeiro.
    
    query = db.query(RealizadoSienge).filter(
        or_(
            and_(
                RealizadoSienge.produto_id_sienge.isnot(None),
                not_(RealizadoSienge.produto_id_sienge.in_(cc_ids))
            ),
            and_(
                RealizadoSienge.tipo != "Venda", # Exceção para vendas
                RealizadoSienge.plano_financeiro_id_sienge.isnot(None),
                not_(RealizadoSienge.plano_financeiro_id_sienge.in_(fp_ids))
            )
        )
    )

    total = query.count()
    items = query.order_by(desc(RealizadoSienge.data_integracao)).offset(skip).limit(limit).all()

    return {
        "items": items,
        "total": total
    }
