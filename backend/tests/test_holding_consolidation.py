"""Motor Consolidação MLDU — ponderação por centro/empresa (Onda C)."""

from app.models.company import Company, CompanyOwnershipLink
from app.models.cost_center import CostCenter
from app.services.holding_consolidation import (
    HoldingContext,
    apply_holding_mldu_read_layer,
    scale_monthly_row,
)
from app.services.mldu_ownership_periods import PeriodoInvalido, record_percentage_change


def _seed(db_session):
    ml = Company(id_sienge="1", cnpj="1", razao_social="MLDU", nome_fantasia="MLDU", participacao_mldu_efetiva=100.0)
    ellenco = Company(id_sienge="12", cnpj="12", razao_social="Ellenco", nome_fantasia="Ellenco")
    cc_ml = CostCenter(id_sienge="101", nome="CC MLDU", custom_data={"__id_empresa": "1"})
    cc_ell = CostCenter(id_sienge="102", nome="CC Ellenco", custom_data={"__id_empresa": "12"})
    db_session.add_all([ml, ellenco, cc_ml, cc_ell])
    db_session.flush()
    db_session.add(
        CompanyOwnershipLink(parent_company_id=ml.id, child_company_id=ellenco.id, percentage=50.0)
    )
    ellenco.participacao_mldu_efetiva = 50.0
    db_session.commit()
    return cc_ml.id, cc_ell.id


def test_factor_por_empresa(db_session):
    cc_ml, cc_ell = _seed(db_session)
    ctx = HoldingContext(db_session)
    assert abs(ctx.factor_for_produto(cc_ml) - 1.0) < 0.0001
    assert abs(ctx.factor_for_produto(cc_ell) - 0.5) < 0.0001


def test_pondera_itens_mensais(db_session):
    cc_ml, cc_ell = _seed(db_session)
    payload = {
        "itens": [
            {"produto_id": cc_ml, "plano_financeiro_id": 1, "jan": 100.0, "total_anual": 100.0},
            {"produto_id": cc_ell, "plano_financeiro_id": 1, "jan": 200.0, "total_anual": 200.0},
        ]
    }
    out = apply_holding_mldu_read_layer(db_session, payload, item_kind="monthly")
    assert out["holding_mldu"] is True
    assert out["itens"][0]["jan"] == 100.0
    assert out["itens"][1]["jan"] == 100.0  # 200 × 50%


def test_centro_sem_empresa_zera(db_session):
    cc = CostCenter(id_sienge="999", nome="Sem empresa", custom_data={})
    db_session.add(cc)
    db_session.commit()
    row = scale_monthly_row({"produto_id": cc.id, "jan": 500.0}, HoldingContext(db_session).factor_for_produto(cc.id))
    assert row["jan"] == 0.0


def test_override_manual_empresa(db_session):
    spe = Company(
        id_sienge="99",
        cnpj="99",
        razao_social="SPE",
        usa_participacao_manual=True,
        participacao_mldu_manual=33.0,
    )
    cc = CostCenter(id_sienge="991", nome="CC SPE", custom_data={"__id_empresa": "99"})
    db_session.add_all([spe, cc])
    db_session.commit()
    ctx = HoldingContext(db_session)
    assert abs(ctx.factor_for_produto(cc.id) - 0.33) < 0.0001


def _set_participacao(db_session, cc_id, valor):
    cc = db_session.get(CostCenter, cc_id)
    data = dict(cc.custom_data or {})
    data["Participação"] = valor
    cc.custom_data = data
    db_session.commit()


def test_participacao_cc_vazia_nao_muda_fator(db_session):
    _, cc_ell = _seed(db_session)
    ctx = HoldingContext(db_session)
    assert abs(ctx.factor_for_produto(cc_ell) - 0.5) < 0.0001


def test_participacao_cc_100_nao_muda_fator(db_session):
    _, cc_ell = _seed(db_session)
    _set_participacao(db_session, cc_ell, 100)
    ctx = HoldingContext(db_session)
    assert abs(ctx.factor_for_produto(cc_ell) - 0.5) < 0.0001


def test_participacao_cc_multiplica_empresa(db_session):
    _, cc_ell = _seed(db_session)
    _set_participacao(db_session, cc_ell, 50)
    ctx = HoldingContext(db_session)
    assert abs(ctx.factor_for_produto(cc_ell) - 0.25) < 0.0001


def test_participacao_cc_string_percentual(db_session):
    _, cc_ell = _seed(db_session)
    _set_participacao(db_session, cc_ell, "50,0%")
    ctx = HoldingContext(db_session)
    assert abs(ctx.factor_for_produto(cc_ell) - 0.25) < 0.0001


def test_participacao_cc_invalida_trata_como_100(db_session):
    _, cc_ell = _seed(db_session)
    _set_participacao(db_session, cc_ell, "abc")
    ctx = HoldingContext(db_session)
    assert abs(ctx.factor_for_produto(cc_ell) - 0.5) < 0.0001


def test_pondera_itens_com_participacao_cc(db_session):
    _, cc_ell = _seed(db_session)
    _set_participacao(db_session, cc_ell, 50)
    payload = {
        "itens": [
            {"produto_id": cc_ell, "plano_financeiro_id": 1, "jan": 200.0, "total_anual": 200.0},
        ]
    }
    out = apply_holding_mldu_read_layer(db_session, payload, item_kind="monthly")
    assert out["itens"][0]["jan"] == 50.0  # 200 × 50% empresa × 50% CC


def test_sem_vigencia_motor_igual_ao_atual(db_session):
    _, cc_ell = _seed(db_session)
    ctx = HoldingContext(db_session)
    assert ctx.produto_is_temporal(cc_ell) is False
    payload = {
        "ano": 2026,
        "itens": [
            {"produto_id": cc_ell, "jan": 200.0, "abr": 200.0, "total_anual": 400.0},
        ],
    }
    out = apply_holding_mldu_read_layer(db_session, payload, item_kind="monthly")
    assert out["itens"][0]["jan"] == 100.0
    assert out["itens"][0]["abr"] == 100.0
    assert out["itens"][0]["total_anual"] == 200.0


def test_vigencia_trava_meses_anteriores(db_session):
    cc_ml, cc_ell = _seed(db_session)
    ellenco = db_session.query(Company).filter(Company.id_sienge == "12").first()
    link = (
        db_session.query(CompanyOwnershipLink)
        .filter(CompanyOwnershipLink.child_company_id == ellenco.id)
        .first()
    )
    record_percentage_change(db_session, link, 40.0, "2026-04")
    db_session.commit()

    ctx = HoldingContext(db_session)
    assert ctx.produto_is_temporal(cc_ell) is True
    assert ctx.produto_is_temporal(cc_ml) is False
    assert abs(ctx.factor_for_produto_mes(cc_ell, 2026, 1) - 0.5) < 0.0001
    assert abs(ctx.factor_for_produto_mes(cc_ell, 2026, 4) - 0.4) < 0.0001
    assert abs(ctx.factor_for_produto_mes(cc_ell, 2025, 12) - 0.5) < 0.0001
    assert abs(ctx.factor_for_produto(cc_ml) - 1.0) < 0.0001

    payload = {
        "ano": 2026,
        "itens": [
            {"produto_id": cc_ell, "jan": 200.0, "abr": 200.0, "total_anual": 400.0},
        ],
    }
    out = apply_holding_mldu_read_layer(db_session, payload, item_kind="monthly")
    assert out["itens"][0]["jan"] == 100.0  # 200 × 50%
    assert out["itens"][0]["abr"] == 80.0  # 200 × 40%
    assert out["itens"][0]["total_anual"] == 180.0


def test_cc_parceria_zera_mldu_mesmo_com_participacao(db_session):
    _, cc_ell = _seed(db_session)
    cc = db_session.get(CostCenter, cc_ell)
    cc.nome = "ARAÇARIGUAMA - RESERVA DO ARAÇARI - PARCERIA GAP"
    data = dict(cc.custom_data or {})
    data["Participação"] = 44
    cc.custom_data = data
    db_session.commit()

    ctx = HoldingContext(db_session)
    assert ctx.factor_for_produto(cc_ell) == 0.0

    payload = {
        "itens": [
            {"produto_id": cc_ell, "plano_financeiro_id": 1, "jan": 115492.34, "total_anual": 115492.34},
        ]
    }
    out = apply_holding_mldu_read_layer(db_session, payload, item_kind="monthly")
    assert out["itens"][0]["jan"] == 0.0


def test_cc_obra_nao_parceria_continua_empresa_vezes_participacao(db_session):
    _, cc_ell = _seed(db_session)
    cc = db_session.get(CostCenter, cc_ell)
    cc.nome = "ARAÇARIGUAMA - RESERVA DO ARAÇARI"
    data = dict(cc.custom_data or {})
    data["Participação"] = 56
    cc.custom_data = data
    db_session.commit()

    ctx = HoldingContext(db_session)
    assert abs(ctx.factor_for_produto(cc_ell) - 0.28) < 0.0001  # 50% empresa × 56% CC


def test_cc_parceria_zera_mldu_com_vigencia(db_session):
    _, cc_ell = _seed(db_session)
    cc = db_session.get(CostCenter, cc_ell)
    cc.nome = "ARAÇARIGUAMA - IGAVETÁ - PARCERIA"
    db_session.commit()

    ellenco = db_session.query(Company).filter(Company.id_sienge == "12").first()
    link = (
        db_session.query(CompanyOwnershipLink)
        .filter(CompanyOwnershipLink.child_company_id == ellenco.id)
        .first()
    )
    record_percentage_change(db_session, link, 40.0, "2026-04")
    db_session.commit()

    ctx = HoldingContext(db_session)
    assert ctx.factor_for_produto_mes(cc_ell, 2026, 1) == 0.0
    assert ctx.factor_for_produto_mes(cc_ell, 2026, 4) == 0.0


def test_mudanca_percentual_exige_mes(db_session):
    _seed(db_session)
    ellenco = db_session.query(Company).filter(Company.id_sienge == "12").first()
    link = (
        db_session.query(CompanyOwnershipLink)
        .filter(CompanyOwnershipLink.child_company_id == ellenco.id)
        .first()
    )
    try:
        record_percentage_change(db_session, link, 40.0, "2026-13")
        assert False, "deveria rejeitar mês inválido"
    except PeriodoInvalido:
        pass
