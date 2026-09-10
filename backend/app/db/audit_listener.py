import json
from datetime import datetime
from contextvars import ContextVar
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_history

# Variável de contexto para armazenar o ID do usuário atual
current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)

def serialize_val(val):
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)

def audit_before_flush(session: Session, flush_context, instances):
    user_id = current_user_id.get()
    
    # Se não há usuário no contexto, não logamos
    if not user_id:
        return

    # Evita importação circular
    from app.models.auditoria import Auditoria
    
    new_audits = []

    # 1. Tratamento de Updates (Modificações)
    for obj in session.dirty:
        if isinstance(obj, Auditoria):
            continue
            
        tabela = obj.__tablename__ if hasattr(obj, '__tablename__') else obj.__class__.__name__
        registro_id = getattr(obj, "id", None)
        
        # Ignorar auditoria para actual_transactions (volume muito alto)
        if tabela == 'actual_transactions':
            continue
            
        changes = {}
        for attr in obj.__mapper__.attrs:
            if not hasattr(attr, 'columns'):
                continue
            
            history = get_history(obj, attr.key)
            if history.has_changes():
                novo = history.added[0] if history.added else None
                antigo = history.deleted[0] if history.deleted else None
                str_novo = serialize_val(novo)
                str_antigo = serialize_val(antigo)
                
                if str_novo != str_antigo:
                    changes[attr.key] = {"de": str_antigo, "para": str_novo}
                    
        if changes:
            audit = Auditoria(
                evento="Alteracao",
                tabela_afetada=tabela,
                registro_id=registro_id,
                campo="Multiplos" if len(changes) > 1 else list(changes.keys())[0],
                valor_anterior=json.dumps({k: v["de"] for k, v in changes.items()})[:255],
                novo_valor=json.dumps({k: v["para"] for k, v in changes.items()})[:255],
                usuario_id=user_id,
                data_hora=datetime.utcnow()
            )
            new_audits.append(audit)

    # 2. Tratamento de Inserts (Criações)
    for obj in session.new:
        if isinstance(obj, Auditoria):
            continue
            
        tabela = obj.__tablename__ if hasattr(obj, '__tablename__') else obj.__class__.__name__
        
        if tabela == 'actual_transactions':
            continue
            
        audit = Auditoria(
            evento="Criacao",
            tabela_afetada=tabela,
            registro_id=None, 
            campo="Registro Completo",
            valor_anterior="",
            novo_valor="Registro Criado",
            usuario_id=user_id,
            data_hora=datetime.utcnow()
        )
        new_audits.append(audit)

    # 3. Tratamento de Deletes (Exclusões)
    for obj in session.deleted:
        if isinstance(obj, Auditoria):
            continue
            
        tabela = obj.__tablename__ if hasattr(obj, '__tablename__') else obj.__class__.__name__
        registro_id = getattr(obj, "id", None)
        
        if tabela == 'actual_transactions':
            continue
            
        audit = Auditoria(
            evento="Exclusao",
            tabela_afetada=tabela,
            registro_id=registro_id,
            campo="Registro Apagado",
            valor_anterior="",
            novo_valor="",
            usuario_id=user_id,
            data_hora=datetime.utcnow()
        )
        new_audits.append(audit)
        
    if new_audits:
        session.add_all(new_audits)

def setup_audit_listener():
    # Registra o evento globalmente em todas as sessões
    event.listen(Session, "before_flush", audit_before_flush)
