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

# Tabelas de volume alto ou técnicas: não auditar.
LIMITE_LINHAS_POR_TABELA = 20
_CAMPOS_SENSIVEIS = ("password", "senha", "token", "secret", "hash")
_IGNORADAS = {"actual_transactions", "auditoria", "sienge_api_calls", "integracao_logs"}


def audit_before_flush(session: Session, flush_context, instances):
    # Usuário da requisição: vem na sessão (deps.get_current_user). O ContextVar
    # fica como reserva, mas não atravessa as threads do FastAPI.
    user_id = session.info.get("audit_user_id") or current_user_id.get()
    
    # Se não há usuário no contexto, não logamos
    if not user_id:
        return

    # Evita importação circular
    from app.models.auditoria import Auditoria
    
    new_audits = []
    alteracoes_por_tabela: dict = {}

    # 1. Tratamento de Updates (Modificações)
    for obj in session.dirty:
        if isinstance(obj, Auditoria):
            continue
            
        tabela = obj.__tablename__ if hasattr(obj, '__tablename__') else obj.__class__.__name__
        registro_id = getattr(obj, "id", None)
        
        if tabela in _IGNORADAS:
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
                    if any(p in attr.key.lower() for p in _CAMPOS_SENSIVEIS):
                        str_antigo, str_novo = "***", "***"  # nunca grava senha/hash/token
                    changes[attr.key] = {"de": str_antigo, "para": str_novo}
                    
        if changes:
            alteracoes_por_tabela.setdefault(tabela, []).append((registro_id, changes))

    # Até 20 registros alterados de uma tabela na mesma gravação: uma linha por registro.
    # Acima disso (ex.: salvar a grade inteira do orçamento), uma linha resumida.
    for tabela, lista in alteracoes_por_tabela.items():
        if len(lista) > LIMITE_LINHAS_POR_TABELA:
            campos = sorted({c for _, ch in lista for c in ch})
            new_audits.append(Auditoria(
                evento="Alteracao",
                tabela_afetada=tabela,
                registro_id=None,
                campo="Varios registros",
                valor_anterior=", ".join(str(r) for r, _ in lista if r is not None)[:255],
                novo_valor=f"{len(lista)} registro(s); campos: {', '.join(campos)}"[:255],
                usuario_id=user_id,
                data_hora=datetime.utcnow(),
            ))
            continue
        for registro_id, changes in lista:
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

    # 2. Criações e exclusões: uma linha por tabela em cada gravação (salvar um
    # orçamento cria centenas de itens; uma linha por item encheria o banco).
    for evento, objs, campo in (("Criacao", session.new, "Registros criados"), ("Exclusao", session.deleted, "Registros apagados")):
        por_tabela: dict = {}
        for obj in objs:
            if isinstance(obj, Auditoria):
                continue
            tabela = obj.__tablename__ if hasattr(obj, '__tablename__') else obj.__class__.__name__
            if tabela in _IGNORADAS:
                continue
            por_tabela.setdefault(tabela, []).append(getattr(obj, "id", None))
        for tabela, ids in por_tabela.items():
            ids_conhecidos = [str(x) for x in ids if x is not None]
            new_audits.append(Auditoria(
                evento=evento,
                tabela_afetada=tabela,
                registro_id=int(ids_conhecidos[0]) if len(ids) == 1 and ids_conhecidos else None,
                campo=campo,
                valor_anterior=(", ".join(ids_conhecidos)[:255] if evento == "Exclusao" else ""),
                novo_valor=f"{len(ids)} registro(s)",
                usuario_id=user_id,
                data_hora=datetime.utcnow(),
            ))

    if new_audits:
        session.add_all(new_audits)

def setup_audit_listener():
    # Registra o evento globalmente em todas as sessões
    if not event.contains(Session, "before_flush", audit_before_flush):  # idempotente
        event.listen(Session, "before_flush", audit_before_flush)
