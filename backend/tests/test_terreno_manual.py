from datetime import date


def _db():
    import importlib
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.database import Base

    for name in os.listdir("app/models"):
        if name.endswith(".py"):
            importlib.import_module("app.models." + name[:-3])

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_yyyy_mm_aceita_date_e_texto():
    from app.services.terreno_manual import yyyy_mm

    assert yyyy_mm(date(2026, 8, 15)) == "2026-08"
    assert yyyy_mm("2026-12-01") == "2026-12"
    assert yyyy_mm(None) is None


def test_primeiro_mes_olha_o_produto_e_ignora_previsao():
    from app.models.actual_transaction import ActualTransaction
    from app.models.cost_center import CostCenter
    from app.services.terreno_manual import primeiro_meses_caixa_produto

    db = _db()
    db.add_all([
        CostCenter(id=1, id_sienge="17700", nome="TAGUAI - JARDIM DOS IPÊS III"),
        CostCenter(id=2, id_sienge="17701", nome="TAGUAI - JARDIM DOS IPÊS III"),
        CostCenter(id=3, id_sienge="17712", nome="TAGUAI - JARDIM DOS IPÊS III - OBRAS"),
        CostCenter(id=4, id_sienge="17799", nome="TAGUAI - OUTRO PRODUTO"),
    ])
    db.add_all([
        ActualTransaction(
            cost_center_id=2, source_id="INC-1", transaction_type="INCOME",
            category="Receita", transaction_date=date(2026, 8, 10), value=400.0, is_forecast=False,
        ),
        ActualTransaction(
            cost_center_id=3, source_id="OUT-1", transaction_type="OUTCOME",
            category="Obras", transaction_date=date(2026, 12, 5), value=100.0, is_forecast=False,
        ),
        ActualTransaction(
            cost_center_id=3, source_id="FCST-OUT", transaction_type="OUTCOME",
            category="Obras", transaction_date=date(2026, 7, 1), value=50.0, is_forecast=True,
        ),
        ActualTransaction(
            cost_center_id=4, source_id="INC-OUTRO", transaction_type="INCOME",
            category="Receita", transaction_date=date(2025, 1, 1), value=9.0, is_forecast=False,
        ),
        ActualTransaction(
            cost_center_id=2, source_id="SALE-1", transaction_type="SALE",
            category="VGV Vendido", transaction_date=date(2026, 6, 1), value=1000.0, is_forecast=False,
        ),
    ])
    db.commit()

    head = db.query(CostCenter).filter(CostCenter.id == 1).one()
    out = primeiro_meses_caixa_produto(db, head)
    assert out["primeiro_mes_caixa"] == "2026-08"
    assert out["primeiro_mes_desembolso"] == "2026-12"
    assert out["mes_sugerido"] == "2026-08"


def test_nao_mistura_reserva_com_morada():
    from app.models.actual_transaction import ActualTransaction
    from app.models.cost_center import CostCenter
    from app.services.terreno_manual import primeiro_meses_caixa_produto

    db = _db()
    db.add_all([
        CostCenter(id=10, id_sienge="14300", nome="BOITUVA - MORADA DOS IPÊS II"),
        CostCenter(id=11, id_sienge="14304", nome="BOITUVA - RESERVA DOS IPÊS"),
    ])
    db.add_all([
        ActualTransaction(
            cost_center_id=10, source_id="INC-M", transaction_type="INCOME",
            category="Receita", transaction_date=date(2025, 3, 10), value=1000.0, is_forecast=False,
        ),
        ActualTransaction(
            cost_center_id=11, source_id="INC-R", transaction_type="INCOME",
            category="Receita", transaction_date=date(2024, 1, 10), value=9000.0, is_forecast=False,
        ),
    ])
    db.commit()

    morada = db.query(CostCenter).filter(CostCenter.id == 10).one()
    out = primeiro_meses_caixa_produto(db, morada)
    assert out["primeiro_mes_caixa"] == "2025-03"
    assert out["mes_sugerido"] == "2025-03"


def test_endpoint_produto_sem_caixa(client):
    r = client.get("/api/v1/apoio/centros-custo/1/primeiro-mes-caixa")
    assert r.status_code == 200
    body = r.json()
    assert body["primeiro_mes_caixa"] is None
    assert body["primeiro_mes_desembolso"] is None
    assert body["mes_sugerido"] is None


def test_endpoint_centro_inexistente(client):
    r = client.get("/api/v1/apoio/centros-custo/99999/primeiro-mes-caixa")
    assert r.status_code == 404
