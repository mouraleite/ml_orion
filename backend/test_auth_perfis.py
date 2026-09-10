import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.database import init_db, SessionLocal
from app.models.user import User
from app.models.departamento import Departamento
from app.api.deps import RoleChecker, get_active_department
from fastapi import Request, HTTPException
from unittest.mock import MagicMock
from sqlalchemy import text

def setup_db():
    init_db()
    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM user_departamentos"))
        db.query(Departamento).delete()
        db.query(User).delete()
        db.commit()

        # Cria Departamentos
        d1 = Departamento(nome="Engenharia")
        d2 = Departamento(nome="Financeiro")
        db.add(d1)
        db.add(d2)
        db.commit()
        db.refresh(d1)
        db.refresh(d2)

        # Cria Usuarios com diferentes papeis
        u_admin = User(full_name="Admin", email="admin@teste.com", hashed_password="123", role="Administrador")
        u_gestor = User(full_name="Gestor", email="gestor@teste.com", hashed_password="123", role="Gestor")
        u_user = User(full_name="User", email="user@teste.com", hashed_password="123", role="Usuario")
        u_consulta = User(full_name="Consulta", email="consulta@teste.com", hashed_password="123", role="Consulta")
        u_integra = User(full_name="Integracao", email="integracao@teste.com", hashed_password="123", role="Integracao")

        db.add_all([u_admin, u_gestor, u_user, u_consulta, u_integra])
        db.commit()
        
        db.refresh(u_user)
        # Associa Usuario 1 (u_user) apenas ao Departamento Engenharia (d1)
        u_user.departamentos.append(d1)
        db.commit()

        return db, {
            "d1_id": d1.id,
            "d2_id": d2.id,
            "admin": u_admin,
            "gestor": u_gestor,
            "user": u_user,
            "consulta": u_consulta,
            "integra": u_integra
        }
    except Exception as e:
        db.rollback()
        raise e
    # db.close() removido para permitir leitura posterior

def test_roles():
    print("Testando RoleChecker...")
    db, data = setup_db()
    
    checker_somente_gestor = RoleChecker(["Gestor"])
    
    # Gestor deve passar
    assert checker_somente_gestor(user=data["gestor"]) == data["gestor"]
    
    # Admin sempre passa
    assert checker_somente_gestor(user=data["admin"]) == data["admin"]
    
    # Usuario normal deve falhar
    try:
        checker_somente_gestor(user=data["user"])
        assert False, "Usuario normal não deveria acessar rota de Gestor"
    except HTTPException as e:
        assert e.status_code == 403

    print("RoleChecker OK!")

def test_active_department():
    print("Testando Contexto de Departamentos...")
    db, data = setup_db()
    
    # Simula Requests do FastAPI
    req_d1 = MagicMock(spec=Request)
    req_d1.headers = {"X-Department-Id": str(data["d1_id"])}
    
    req_d2 = MagicMock(spec=Request)
    req_d2.headers = {"X-Department-Id": str(data["d2_id"])}
    
    req_sem_header = MagicMock(spec=Request)
    req_sem_header.headers = {}
    
    # 1. Teste de erro se faltar header
    try:
        get_active_department(request=req_sem_header, user=data["user"], db=db)
        assert False
    except HTTPException as e:
        assert e.status_code == 400
        
    # 2. Usuário normal acessa D1 (que ele tem permissão)
    dept = get_active_department(request=req_d1, user=data["user"], db=db)
    assert dept.id == data["d1_id"]
    
    # 3. Usuário normal tenta acessar D2 (bloqueado)
    try:
        get_active_department(request=req_d2, user=data["user"], db=db)
        assert False, "Não deveria acessar D2"
    except HTTPException as e:
        assert e.status_code == 403
        
    # 4. Administrador tenta acessar D2 (passa livre mesmo sem vínculo)
    dept_admin = get_active_department(request=req_d2, user=data["admin"], db=db)
    assert dept_admin.id == data["d2_id"]

    print("Contexto de Departamentos OK!")

if __name__ == "__main__":
    test_roles()
    test_active_department()
    print("TODOS OS TESTES DE AUTENTICAÇÃO/AUTORIZAÇÃO PASSARAM!")
