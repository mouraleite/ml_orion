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
