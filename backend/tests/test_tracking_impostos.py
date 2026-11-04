from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.tax_regime import TaxRegime
from app.services.tracking_impostos import (
    aliquotas_lucro_presumido,
    lancar_tributos_no_fluxo,
    mes_darf_irpj_csll,
    mes_darf_pis_cofins,
    projetar_tributos_presumido,
)

ALIQUOTAS = {"pis": 0.65, "cofins": 3.0, "irpj": 2.2, "csll": 1.19, "outros": 0.0}


def test_darf_pis_no_mes_seguinte():
    assert mes_darf_pis_cofins(2026, 11) == (2026, 12)
    assert mes_darf_pis_cofins(2026, 12) == (2027, 1)


def test_darf_irpj_no_mes_seguinte_ao_trimestre():
    assert mes_darf_irpj_csll(2026, 1) == (2026, 4)
    assert mes_darf_irpj_csll(2026, 3) == (2026, 4)
    assert mes_darf_irpj_csll(2026, 4) == (2026, 7)
    assert mes_darf_irpj_csll(2026, 9) == (2026, 10)
    assert mes_darf_irpj_csll(2026, 12) == (2027, 1)


def test_janeiro_pis_em_fevereiro_irpj_em_abril():
    out = projetar_tributos_presumido({"2026-01": 100_000.0}, ALIQUOTAS)
    assert round(out["2026-02"], 2) == 3650.0
    assert round(out["2026-04"], 2) == 3390.0
    assert "2026-01" not in out


def test_dezembro_pis_e_irpj_saem_em_janeiro():
    out = projetar_tributos_presumido({"2026-12": 100_000.0}, ALIQUOTAS)
    assert round(out["2027-01"], 2) == 7040.0


def test_mudar_aliquota_muda_o_caixa():
    base = projetar_tributos_presumido({"2026-01": 100_000.0}, ALIQUOTAS)
    dobrado = dict(ALIQUOTAS)
    dobrado["pis"] = ALIQUOTAS["pis"] * 2
    dobrado["cofins"] = ALIQUOTAS["cofins"] * 2
    novo = projetar_tributos_presumido({"2026-01": 100_000.0}, dobrado)
    assert round(novo["2026-02"], 2) == round(base["2026-02"] * 2, 2)
    assert round(novo["2026-04"], 2) == round(base["2026-04"], 2)


def test_le_percentual_vigente_no_apoio():
    engine = create_engine("sqlite:///:memory:")
    TaxRegime.__table__.create(engine)
    db = sessionmaker(bind=engine)()
    db.add(TaxRegime(nome="Lucro Presumido", pis=0.65, cofins=3.0, irpj=2.2, csll=1.19, ativo=True))
    db.commit()
    assert aliquotas_lucro_presumido(db)["irpj"] == 2.2

    row = db.query(TaxRegime).filter(TaxRegime.nome == "Lucro Presumido").one()
    row.irpj = 9.9
    db.commit()
    assert aliquotas_lucro_presumido(db)["irpj"] == 9.9


def test_lanca_tributo_no_fluxo_e_no_total():
    anual = defaultdict(lambda: {"Entradas": 0.0, "Tributos": 0.0, "Saidas": 0.0})
    monthly = defaultdict(float)
    monthly["2026-04"] = 50_000.0
    total = lancar_tributos_no_fluxo({"2026-04": 3390.0}, anual, monthly)
    assert total == 3390.0
    assert anual["2026"]["Tributos"] == 3390.0
    assert anual["2026"]["Saidas"] == 3390.0
    assert monthly["2026-04"] == 50_000.0 - 3390.0
