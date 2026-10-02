"""Árvore societária MLDU — cálculo de % efetivo (Onda B)."""

from app.models.company import Company, CompanyOwnershipLink
from app.services.mldu_ownership import (
    compute_effective_map,
    format_calculation_tooltip,
    sync_company_effective_percentages,
    would_create_cycle,
)


def _seed_companies(db_session):
    companies = [
        Company(id_sienge="1", cnpj="1", razao_social="MLDU", nome_fantasia="MLDU"),
        Company(id_sienge="12", cnpj="12", razao_social="Ellenco & ML", nome_fantasia="Ellenco"),
        Company(id_sienge="13", cnpj="13", razao_social="Vercellino", nome_fantasia="Vercellino"),
        Company(id_sienge="16", cnpj="16", razao_social="Loteadora Ypes IV", nome_fantasia="Ypes IV"),
        Company(id_sienge="21", cnpj="21", razao_social="Reserva Ypes IV", nome_fantasia="Reserva Ypes"),
        Company(id_sienge="28", cnpj="28", razao_social="Reserva Ramos", nome_fantasia="Reserva Ramos"),
        Company(id_sienge="5", cnpj="5", razao_social="MLES", nome_fantasia="MLES"),
    ]
    db_session.add_all(companies)
    db_session.commit()
    return {c.id_sienge: c for c in companies}


def test_vercellino_indireto_2775(db_session):
    by_sienge = _seed_companies(db_session)
    db_session.add(
        CompanyOwnershipLink(
            parent_company_id=by_sienge["1"].id,
            child_company_id=by_sienge["12"].id,
            percentage=50.0,
        )
    )
    db_session.add(
        CompanyOwnershipLink(
            parent_company_id=by_sienge["12"].id,
            child_company_id=by_sienge["13"].id,
            percentage=55.498,
        )
    )
    db_session.commit()

    effective, paths = compute_effective_map(db_session)
    vercellino_id = by_sienge["13"].id
    assert abs(effective[vercellino_id] - 27.749) < 0.01
    tooltip = format_calculation_tooltip(paths[vercellino_id])
    assert "50%" in tooltip and "55.498%" in tooltip


def test_ypes_reserva_238(db_session):
    by_sienge = _seed_companies(db_session)
    db_session.add(
        CompanyOwnershipLink(
            parent_company_id=by_sienge["1"].id,
            child_company_id=by_sienge["16"].id,
            percentage=35.0,
        )
    )
    db_session.add(
        CompanyOwnershipLink(
            parent_company_id=by_sienge["16"].id,
            child_company_id=by_sienge["21"].id,
            percentage=68.0,
        )
    )
    db_session.commit()

    effective, _ = compute_effective_map(db_session)
    assert abs(effective[by_sienge["21"].id] - 23.8) < 0.01


def test_ramos_2258(db_session):
    by_sienge = _seed_companies(db_session)
    mirante = Company(id_sienge="15", cnpj="15", razao_social="Mirante dos Ramos", nome_fantasia="Mirante")
    db_session.add(mirante)
    db_session.commit()
    db_session.add(
        CompanyOwnershipLink(
            parent_company_id=by_sienge["1"].id,
            child_company_id=mirante.id,
            percentage=35.0,
        )
    )
    db_session.add(
        CompanyOwnershipLink(
            parent_company_id=mirante.id,
            child_company_id=by_sienge["28"].id,
            percentage=64.5,
        )
    )
    db_session.commit()

    effective, _ = compute_effective_map(db_session)
    assert abs(effective[by_sienge["28"].id] - 22.575) < 0.01


def test_mles_33(db_session):
    by_sienge = _seed_companies(db_session)
    db_session.add(
        CompanyOwnershipLink(
            parent_company_id=by_sienge["1"].id,
            child_company_id=by_sienge["5"].id,
            percentage=33.0,
        )
    )
    db_session.commit()
    sync_company_effective_percentages(db_session)
    db_session.refresh(by_sienge["5"])
    assert by_sienge["5"].participacao_mldu_efetiva == 33.0


def test_detecta_ciclo(db_session):
    by_sienge = _seed_companies(db_session)
    db_session.add(
        CompanyOwnershipLink(
            parent_company_id=by_sienge["1"].id,
            child_company_id=by_sienge["12"].id,
            percentage=50.0,
        )
    )
    db_session.add(
        CompanyOwnershipLink(
            parent_company_id=by_sienge["12"].id,
            child_company_id=by_sienge["13"].id,
            percentage=55.498,
        )
    )
    db_session.commit()
    assert would_create_cycle(db_session, by_sienge["13"].id, by_sienge["1"].id) is True


def test_arvore_copia_socio_sem_mudar_consolidacao(db_session):
    from app.models.company import CompanyPartner
    from app.services.mldu_ownership import build_tree

    by_sienge = _seed_companies(db_session)
    db_session.add(
        CompanyOwnershipLink(
            parent_company_id=by_sienge["1"].id,
            child_company_id=by_sienge["12"].id,
            percentage=50.0,
        )
    )
    db_session.commit()
    sync_company_effective_percentages(db_session)
    antes = by_sienge["12"].participacao_mldu_efetiva

    tree = build_tree(db_session)
    db_session.refresh(by_sienge["12"])
    assert by_sienge["12"].participacao_mldu_efetiva == antes == 50.0
    filho = tree["root"]["children"][0]
    assert filho["percentage"] == 50.0
    assert filho["participacao_efetiva"] == 50.0
    socio = (
        db_session.query(CompanyPartner)
        .filter_by(company_id=by_sienge["12"].id, partner_company_id=by_sienge["1"].id)
        .one()
    )
    assert socio.percentage == 50.0
    assert tree["divergencias"] == []


def test_socio_diferente_nao_sobrescreve_consolidacao(db_session):
    from app.models.company import CompanyPartner
    from app.services.mldu_ownership import build_tree

    by_sienge = _seed_companies(db_session)
    db_session.add(
        CompanyOwnershipLink(
            parent_company_id=by_sienge["1"].id,
            child_company_id=by_sienge["5"].id,
            percentage=33.0,
        )
    )
    db_session.add(
        CompanyPartner(
            company_id=by_sienge["5"].id,
            tipo="Sócio",
            partner_company_id=by_sienge["1"].id,
            percentage=40.0,
        )
    )
    db_session.commit()
    sync_company_effective_percentages(db_session)

    tree = build_tree(db_session)
    db_session.refresh(by_sienge["5"])
    assert by_sienge["5"].participacao_mldu_efetiva == 33.0
    assert tree["root"]["children"][0]["percentage"] == 40.0
    assert tree["divergencias"][0]["apoio_pct"] == 40.0
    assert tree["divergencias"][0]["consolidacao_pct"] == 33.0


def test_alterar_socio_atualiza_percentual_atual_e_preserva_passado(db_session):
    from app.models.company import CompanyPartner
    from app.services.mldu_ownership import apply_structural_partner
    from app.services.mldu_ownership_periods import percentage_as_of, record_percentage_change

    by_sienge = _seed_companies(db_session)
    link = CompanyOwnershipLink(
        parent_company_id=by_sienge["1"].id,
        child_company_id=by_sienge["5"].id,
        percentage=50.0,
    )
    db_session.add(link)
    db_session.commit()
    record_percentage_change(db_session, link, 33.0, "2026-06")
    db_session.commit()

    socio = CompanyPartner(
        company_id=by_sienge["5"].id,
        tipo="Sócio",
        partner_company_id=by_sienge["1"].id,
        percentage=20.0,
    )
    db_session.add(socio)
    db_session.commit()
    apply_structural_partner(db_session, socio)
    db_session.refresh(link)
    assert link.percentage == 20.0
    assert percentage_as_of(link, link.periods, 2026, 5) == 50.0
    assert percentage_as_of(link, link.periods, 2026, 6) == 20.0
    db_session.refresh(by_sienge["5"])
    assert by_sienge["5"].participacao_mldu_efetiva == 20.0
