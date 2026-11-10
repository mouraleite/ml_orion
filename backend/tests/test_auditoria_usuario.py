"""Auditoria automática grava o usuário (antes: ContextVar não chegava ao endpoint e nada era gravado)."""
import os
import sys
from contextvars import ContextVar

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.db.audit_listener import setup_audit_listener
from app.models.auditoria import Auditoria
from app.models.cost_center import CostCenter

setup_audit_listener()


def test_contextvar_nao_atravessa_dependencia_sincrona():
    """Documenta o motivo da correção: o valor setado na dependência some no endpoint."""
    cv = ContextVar("u", default=None)
    app = FastAPI()

    def dep():
        cv.set(42)

    @app.get("/x")
    def x(_=Depends(dep)):
        return {"u": cv.get()}

    assert TestClient(app).get("/x").json() == {"u": None}


def test_alteracao_com_usuario_na_sessao_e_auditada(db_session):
    cc = db_session.query(CostCenter).filter(CostCenter.id == 1).first()
    db_session.info["audit_user_id"] = 1
    cc.nome = "Produto A renomeado"
    db_session.flush()
    a = db_session.query(Auditoria).filter_by(tabela_afetada="cost_centers", evento="Alteracao", registro_id=1).all()
    assert a and a[-1].usuario_id == 1 and "renomeado" in a[-1].novo_valor
    db_session.info.pop("audit_user_id", None)


def test_criacoes_viram_uma_linha_por_tabela(db_session):
    db_session.info["audit_user_id"] = 1
    antes = db_session.query(Auditoria).filter_by(tabela_afetada="cost_centers", evento="Criacao").count()
    for i in range(30):
        db_session.add(CostCenter(nome=f"Novo {i}", id_sienge=f"99{i:03d}"))
    db_session.flush()
    novas = db_session.query(Auditoria).filter_by(tabela_afetada="cost_centers", evento="Criacao").all()
    assert len(novas) == antes + 1
    assert novas[-1].novo_valor == "30 registro(s)"
    db_session.info.pop("audit_user_id", None)


def test_sem_usuario_nao_audita(db_session):
    db_session.info.pop("audit_user_id", None)
    antes = db_session.query(Auditoria).count()
    db_session.add(CostCenter(nome="Do sync", id_sienge="98001"))
    db_session.flush()
    assert db_session.query(Auditoria).count() == antes


def test_senha_nunca_vai_para_a_auditoria(db_session):
    from app.models.user import User
    u = db_session.query(User).filter(User.id == 2).first()
    db_session.info["audit_user_id"] = 1
    u.hashed_password = "novo-hash-secreto"
    db_session.flush()
    a = db_session.query(Auditoria).filter_by(tabela_afetada="users", registro_id=2).all()
    assert a and "novo-hash-secreto" not in (a[-1].novo_valor or "") and "***" in a[-1].novo_valor
    db_session.info.pop("audit_user_id", None)


def test_muitas_alteracoes_viram_linha_resumida(db_session):
    novos = [CostCenter(nome=f"Lote {i}", id_sienge=f"97{i:03d}") for i in range(25)]
    db_session.add_all(novos)
    db_session.flush()
    db_session.info["audit_user_id"] = 1
    for c in novos:
        c.nome = c.nome + " x"
    db_session.flush()
    a = db_session.query(Auditoria).filter_by(tabela_afetada="cost_centers", campo="Varios registros").all()
    assert len(a) == 1 and a[0].novo_valor.startswith("25 registro(s)")
    db_session.info.pop("audit_user_id", None)
