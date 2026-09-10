import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.db.database import Base, get_db
from app.api.deps import get_current_user, get_active_department
from app.models.user import User
from app.models.departamento import Departamento, DepartamentoPlano, ProdutoPlanoFinanceiro
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.models.payment_plan import PaymentPlan
from app.models.economic_indicator import EconomicIndicator
from app.models.orcamento import Orcamento, OrcamentoItem, OrcamentoVendaItem
from app.models.auditoria import Auditoria

# 1. Configurar DB em memória
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def engine_fixture():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(engine_fixture):
    """Cria uma sessão isolada para cada teste."""
    connection = engine_fixture.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Injetar dados básicos
    _populate_mock_data(session)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def _populate_mock_data(db):
    """Popula banco com dados essenciais para os testes passarem."""
    u1 = User(id=1, email="admin@teste.com", full_name="Admin", role="Administrador", hashed_password="xxx")
    u2 = User(id=2, email="user@teste.com", full_name="Comum", role="Usuário Comum", hashed_password="xxx")
    
    d1 = Departamento(id=1, nome="Marketing")
    
    c1 = CostCenter(id=1, nome="Produto A")
    c2 = CostCenter(id=2, nome="Produto B")
    
    f1 = FinancialPlan(id=1, name="Plano Fin 1")
    f2 = FinancialPlan(id=2, name="Plano Fin 2")
    
    p1 = PaymentPlan(id=1, nome="Plano Ven 1")
    
    dp1 = DepartamentoPlano(departamento_id=1, plano_financeiro_id=1, permitido=True)
    pp1 = ProdutoPlanoFinanceiro(produto_id=1, plano_financeiro_id=1, permitido=True)
    
    db.add_all([u1, u2, d1, c1, c2, f1, f2, p1, dp1, pp1])
    db.commit()


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente FastAPI com injeção de dependências substituída."""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        # Retorna o admin por padrão
        return db_session.query(User).filter(User.id == 1).first()

    def override_get_active_department():
        return db_session.query(Departamento).filter(Departamento.id == 1).first()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_active_department] = override_get_active_department

    with TestClient(app) as c:
        yield c

    # Limpar overrides
    app.dependency_overrides.clear()
