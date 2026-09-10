from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi.responses import StreamingResponse
import io
import csv

from app.api.deps import get_db, get_current_active_admin
from app.models.auditoria import Auditoria
from app.models.user import User
from pydantic import BaseModel

router = APIRouter()

class AuditoriaResponse(BaseModel):
    id: int
    evento: str
    tabela_afetada: Optional[str]
    registro_id: Optional[int]
    campo: Optional[str]
    valor_anterior: Optional[str]
    novo_valor: Optional[str]
    usuario_id: Optional[int]
    data_hora: datetime
    usuario_nome: Optional[str]

    class Config:
        from_attributes = True

@router.get("/", response_model=dict)
def get_auditoria_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
    usuario_id: Optional[int] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    evento: Optional[str] = None,
    tabela_afetada: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    query = db.query(Auditoria, User.full_name.label("usuario_nome")).outerjoin(User, Auditoria.usuario_id == User.id)

    if usuario_id is not None:
        query = query.filter(Auditoria.usuario_id == usuario_id)
    if data_inicio:
        query = query.filter(Auditoria.data_hora >= data_inicio)
    if data_fim:
        query = query.filter(Auditoria.data_hora <= data_fim)
    if evento:
        query = query.filter(Auditoria.evento.ilike(f"%{evento}%"))
    if tabela_afetada:
        query = query.filter(Auditoria.tabela_afetada.ilike(f"%{tabela_afetada}%"))

    total = query.count()
    logs = query.order_by(desc(Auditoria.data_hora)).offset(skip).limit(limit).all()

    result = []
    for audit, user_name in logs:
        audit_dict = {
            "id": audit.id,
            "evento": audit.evento,
            "tabela_afetada": audit.tabela_afetada,
            "registro_id": audit.registro_id,
            "campo": audit.campo,
            "valor_anterior": audit.valor_anterior,
            "novo_valor": audit.novo_valor,
            "usuario_id": audit.usuario_id,
            "data_hora": audit.data_hora,
            "usuario_nome": user_name
        }
        result.append(audit_dict)

    return {
        "items": result,
        "total": total
    }

@router.get("/export")
def export_auditoria_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
    usuario_id: Optional[int] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    evento: Optional[str] = None,
    tabela_afetada: Optional[str] = None,
):
    query = db.query(Auditoria, User.full_name).outerjoin(User, Auditoria.usuario_id == User.id)

    if usuario_id is not None:
        query = query.filter(Auditoria.usuario_id == usuario_id)
    if data_inicio:
        query = query.filter(Auditoria.data_hora >= data_inicio)
    if data_fim:
        query = query.filter(Auditoria.data_hora <= data_fim)
    if evento:
        query = query.filter(Auditoria.evento.ilike(f"%{evento}%"))
    if tabela_afetada:
        query = query.filter(Auditoria.tabela_afetada.ilike(f"%{tabela_afetada}%"))

    logs = query.order_by(desc(Auditoria.data_hora)).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["ID", "Data/Hora", "Usuario", "Evento", "Tabela Afetada", "ID Registro", "Campo", "Valor Anterior", "Novo Valor"])

    for audit, user_name in logs:
        writer.writerow([
            audit.id,
            audit.data_hora.strftime("%d/%m/%Y %H:%M:%S") if audit.data_hora else "",
            user_name or "",
            audit.evento or "",
            audit.tabela_afetada or "",
            audit.registro_id or "",
            audit.campo or "",
            audit.valor_anterior or "",
            audit.novo_valor or ""
        ])

    output.seek(0)
    filename = f"auditoria_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)
