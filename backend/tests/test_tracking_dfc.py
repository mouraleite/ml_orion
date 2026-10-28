from datetime import date


def _sqlite_dfc():
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


def _seed_visao_e_centros(db):
    from app.models.actual_transaction import ActualTransaction
    from app.models.cost_center import CostCenter
    from app.models.financial_plan import FinancialPlan
    from app.models.vision import FinancialPlanVisionLink, Vision, VisionNode

    db.add(Vision(id=1, nome="Padrão", is_padrao=True))
    db.add_all([
        VisionNode(id=1, vision_id=1, codigo="01", descricao="RECEITAS"),
        VisionNode(id=2, vision_id=1, codigo="01.01", descricao="VENDAS DE UNIDADES"),
        VisionNode(id=3, vision_id=1, codigo="04", descricao="CUSTOS"),
        VisionNode(id=4, vision_id=1, codigo="04.03", descricao="OBRAS"),
        VisionNode(id=5, vision_id=1, codigo="05", descricao="DESPESAS"),
        VisionNode(id=6, vision_id=1, codigo="05.03", descricao="ADMINISTRATIVAS"),
    ])
    db.add_all([
        FinancialPlan(id=1, name="Receita de Venda de Lotes", db_id="1.01"),
        FinancialPlan(id=2, name="Materiais Aplicados (Obra)", db_id="4.03"),
    ])
    db.add_all([
        FinancialPlanVisionLink(financial_plan_id=1, vision_id=1, vision_node_id=2),
        FinancialPlanVisionLink(financial_plan_id=2, vision_id=1, vision_node_id=4),
    ])
    db.add_all([
        CostCenter(id=10, id_sienge="14300", nome="BOITUVA - MORADA DOS IPÊS II", track_in_dashboard=True),
        CostCenter(id=11, id_sienge="14301", nome="BOITUVA - MORADA DOS IPÊS II - OBRAS", track_in_dashboard=False),
        CostCenter(id=12, id_sienge="14304", nome="BOITUVA - RESERVA DOS IPÊS", track_in_dashboard=True),
    ])
    rows = [
        (10, "INC-1", "INCOME", "Receita de Venda de Lotes", date(2025, 3, 10), 1000.0, False),
        (10, "FCST-INC-1", "INCOME", "Receita de Venda de Lotes", date(2027, 1, 10), 400.0, True),
        (11, "OUT-1-OP1-PMT-1-DT-20260801-FC-1", "OUTCOME", "Materiais Aplicados (Obra)", date(2026, 8, 1), 300.0, False),
        (10, "FCST-OUT-1", "OUTCOME", "Administrativas Diversas", date(2026, 6, 1), 100.0, True),
        (12, "INC-RESERVA", "INCOME", "Receita de Venda de Lotes", date(2025, 4, 10), 9000.0, False),
        (11, "OUT-DIST-1-OP1-PMT-1-DT-20260901-FC-1", "OUTCOME", "Distrato de Venda", date(2026, 9, 1), 50.0, False),
    ]
    for cc_id, source_id, tipo, categoria, dia, valor, previsto in rows:
        db.add(ActualTransaction(
            cost_center_id=cc_id,
            source_id=source_id,
            transaction_type=tipo,
            category=categoria,
            transaction_date=dia,
            value=valor,
            is_forecast=previsto,
        ))
    db.commit()
    return db


def test_lucro_dfc_bate_com_a_lista_e_soma_obra():
    from app.api.routes.tracking_dfc import listar_empreendimentos_dfc, montar_dfc_vida

    db = _seed_visao_e_centros(_sqlite_dfc())
    itens = listar_empreendimentos_dfc(db)
    ids = {row["id"] for row in itens}
    assert any(i.endswith("MORADA DOS IPÊS II") for i in ids)
    morada = next(row for row in itens if row["project_name"] == "MORADA DOS IPÊS II")
    sienge = {c["id_sienge"] for c in morada["centros"]}
    assert "14300" in sienge
    assert "14301" in sienge
    assert "14304" not in sienge

    payload = montar_dfc_vida(db, morada["id"])
    conf = payload["conferencia"]
    assert conf["lucro_lista"] == 1000.0
    assert conf["lucro_dfc"] == 1000.0
    assert conf["ok"] is True
    assert payload["anos"] == ["2025", "2026", "2027"]

    by_codigo = {row["codigo"]: row for row in payload["linhas"]}
    assert by_codigo["01.01"]["valores"]["2025"] == 1000.0
    assert by_codigo["01.01"]["valores"]["2027"] == 400.0
    assert by_codigo["01"]["total"] == 1400.0
    assert by_codigo["04.03"]["valores"]["2026"] == -300.0
    assert by_codigo["04"]["total"] == -300.0
    assert by_codigo["05.03"]["valores"]["2026"] == -100.0
    assert 9000.0 not in by_codigo["01.01"]["valores"].values()
    assert payload["meses"] == ["2025-03", "2026-06", "2026-08", "2027-01"]
    assert by_codigo["01.01"]["valores_mes"]["2025-03"] == 1000.0
    assert by_codigo["04.03"]["valores_mes"]["2026-08"] == -300.0

    planos_0101 = {p["descricao"]: p for p in by_codigo["01.01"]["planos"]}
    planos_0403 = {p["descricao"]: p for p in by_codigo["04.03"]["planos"]}
    planos_0503 = {p["descricao"]: p for p in by_codigo["05.03"]["planos"]}
    assert planos_0101["Receita de Venda de Lotes"]["total"] == 1400.0
    assert planos_0403["Materiais Aplicados (Obra)"]["valores_mes"]["2026-08"] == -300.0
    assert planos_0503["Administrativas Diversas"]["total"] == -100.0
    assert "Receita de Venda de Lotes" not in {p["descricao"] for p in by_codigo["01"]["planos"]}


def test_rotas_dfc_ficam_no_acompanhamento():
    from app.api.routes.tracking_dfc import router

    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/dfc" in paths
    assert "/dfc/empreendimentos" in paths
