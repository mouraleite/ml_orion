from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_admin
from app.models.fechamento import ClosedMonth
from app.schemas.fechamento import ClosedMonthCreate, ClosedMonthResponse
from datetime import datetime

router = APIRouter()

@router.get("/meses", response_model=list[ClosedMonthResponse])
def get_meses_fechados(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Lista todos os meses fechados (visível a todos autenticados — desabilita mês no frontend)."""
    return db.query(ClosedMonth).all()

@router.post("/mes", response_model=ClosedMonthResponse)
def fechar_mes(
    data: ClosedMonthCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Fecha um mês específico (somente administrador)."""
    existente = db.query(ClosedMonth).filter(ClosedMonth.ano == data.ano, ClosedMonth.mes == data.mes).first()
    if existente:
        raise HTTPException(status_code=400, detail="Mês já está fechado.")

    novo_fechamento = ClosedMonth(
        ano=data.ano,
        mes=data.mes,
        fechado_por_id=current_user.id,
        data_fechamento=datetime.utcnow()
    )
    db.add(novo_fechamento)
    db.commit()
    db.refresh(novo_fechamento)
    return novo_fechamento

@router.delete("/mes/{ano}/{mes}")
def abrir_mes(
    ano: int,
    mes: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Reabre um mês específico (somente administrador)."""
    fechamento = db.query(ClosedMonth).filter(ClosedMonth.ano == ano, ClosedMonth.mes == mes).first()
    if not fechamento:
        raise HTTPException(status_code=404, detail="Mês não está fechado.")

    db.delete(fechamento)
    db.commit()
    return {"message": "Mês reaberto com sucesso."}
