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
        VisionNode(id=7, vision_id=1, codigo="01.04", descricao="CANCELAMENTOS DE VENDAS"),
        VisionNode(id=3, vision_id=1, codigo="04", descricao="CUSTOS"),
        VisionNode(id=4, vision_id=1, codigo="04.03", descricao="OBRAS"),
        VisionNode(id=5, vision_id=1, codigo="05", descricao="DESPESAS"),
        VisionNode(id=6, vision_id=1, codigo="05.03", descricao="ADMINISTRATIVAS"),
        VisionNode(id=8, vision_id=1, codigo="03", descricao="CUSTOS E DESPESAS"),
        VisionNode(id=9, vision_id=1, codigo="06", descricao="GCO - GERAÇÃO DE CAIXA OPERACIONAL"),
        VisionNode(id=10, vision_id=1, codigo="02", descricao="IMPOSTOS"),
        VisionNode(id=11, vision_id=1, codigo="02.01", descricao="IMPOSTOS SOBRE VENDAS"),
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
        (11, "OUT-1-PMT-1-DT-20260801", "OUTCOME", "Materiais Aplicados (Obra)", date(2026, 8, 1), 300.0, False),
        (10, "FCST-OUT-1", "OUTCOME", "Administrativas Diversas", date(2026, 6, 1), 100.0, True),
        (12, "INC-RESERVA", "INCOME", "Receita de Venda de Lotes", date(2025, 4, 10), 9000.0, False),
        (11, "OUT-DIST-1-OP1-PMT-1-DT-20260901-FC-1", "OUTCOME", "Distrato de Venda", date(2026, 9, 1), 50.0, False),
        (11, "OUT-IRPJ-OP1-PMT-1-DT-20260801-FC-1", "OUTCOME", "IRPJ", date(2026, 8, 1), 40.0, False),
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
    assert conf["lucro_lista"] == 960.0
    assert conf["lucro_dfc"] == 960.0
    assert conf["ok"] is True
    assert payload["anos"] == ["2025", "2026", "2027"]

    by_codigo = {row["codigo"]: row for row in payload["linhas"]}
    assert by_codigo["01.01"]["valores"]["2025"] == 1000.0
    assert by_codigo["01.01"]["valores"]["2027"] == 400.0
    assert by_codigo["01"]["total"] == 1350.0
    assert by_codigo["04.03"]["valores"]["2026"] == -300.0
    assert by_codigo["04"]["total"] == -300.0
    assert by_codigo["05.03"]["valores"]["2026"] == -100.0
    assert by_codigo["01.04"]["valores_mes"]["2026-09"] == -50.0
    assert by_codigo["02.02"]["valores_mes"]["2026-08"] == -40.0
    assert by_codigo["02"]["total"] == -40.0
    assert by_codigo["03"]["total"] == -400.0
    assert by_codigo["06"]["total"] == 910.0
    assert 9000.0 not in by_codigo["01.01"]["valores"].values()
    assert payload["meses"] == ["2025-03", "2026-06", "2026-08", "2026-09", "2027-01"]
    assert by_codigo["01.01"]["valores_mes"]["2025-03"] == 1000.0
    assert by_codigo["04.03"]["valores_mes"]["2026-08"] == -300.0

    planos_0101 = {p["descricao"]: p for p in by_codigo["01.01"]["planos"]}
    planos_0403 = {p["descricao"]: p for p in by_codigo["04.03"]["planos"]}
    planos_0503 = {p["descricao"]: p for p in by_codigo["05.03"]["planos"]}
    assert planos_0101["Receita de Venda de Lotes"]["total"] == 1400.0
    assert planos_0403["Materiais Aplicados (Obra)"]["valores_mes"]["2026-08"] == -300.0
    assert planos_0503["Administrativas Diversas"]["total"] == -100.0
    assert "Receita de Venda de Lotes" not in {p["descricao"] for p in by_codigo["01"]["planos"]}


def test_redutora_sienge_entra_positiva_no_dfc():
    from app.api.routes.tracking_dfc import _signed_caixa_dfc

    assert _signed_caixa_dfc("OUTCOME", "(-) Retenção de INSS - Terceiros", 10) == 10
    assert _signed_caixa_dfc("OUTCOME", "Recolhimento de INSS - Terceiros", 10) == -10
    assert _signed_caixa_dfc("INCOME", "Receita de Venda de Lotes", 10) == 10


def test_titulo_vencido_aberto_entra_no_dfc_como_previsto():
    from app.api.routes.tracking_dfc import listar_empreendimentos_dfc, montar_dfc_vida
    from app.models.actual_transaction import ActualTransaction

    db = _seed_visao_e_centros(_sqlite_dfc())
    db.add(ActualTransaction(
        cost_center_id=10,
        source_id="TRK-VENC-INC-99-1",
        transaction_type="INCOME",
        category="Receita de Venda de Lotes",
        transaction_date=date(2026, 9, 20),
        value=80.0,
        is_forecast=True,
    ))
    db.commit()
    morada = next(
        row for row in listar_empreendimentos_dfc(db)
        if row["project_name"] == "MORADA DOS IPÊS II"
    )
    payload = montar_dfc_vida(db, morada["id"])
    by_codigo = {row["codigo"]: row for row in payload["linhas"]}
    assert by_codigo["01.01"]["valores_mes"]["2026-09"] == 80.0


def test_rotas_dfc_ficam_no_acompanhamento():
    from app.api.routes.tracking_dfc import router

    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/dfc" in paths
    assert "/dfc/empreendimentos" in paths


def test_seletor_lista_id_e_nome_sem_kpi():
    from app.api.routes.tracking import listar_empreendimentos_seletor, router
    from app.models.viability import Viability

    db = _sqlite_dfc()
    _seed_visao_e_centros(db)
    db.add(Viability(id=5, project_name="Land Bank Teste", status="Aprovado"))
    db.add(Viability(id=6, project_name="Obra em andamento", status="Em Andamento"))
    db.commit()

    items = listar_empreendimentos_seletor(db)
    ids = {row["id"] for row in items}
    names = {row["project_name"] for row in items}
    assert "v-5" in ids
    assert "v-6" not in ids
    assert "Land Bank Teste" in names
    assert "MORADA DOS IPÊS II" in names
    assert "RESERVA DOS IPÊS" in names
    assert any(item_id.startswith("cg-143_") for item_id in ids)
    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/empreendimentos" in paths
