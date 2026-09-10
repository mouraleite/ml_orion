"""Validação organograma MLDU vs referência (Onda E)."""

from app.models.company import Company, CompanyOwnershipLink
from app.services.mldu_ownership import seed_reference_links
from app.services.mldu_organograma_validacao import validate_organograma


def _seed_all_reference_companies(db_session):
    """Empresas mínimas para validar organograma completo."""
    specs = [
        ("1", "MLDU"),
        ("4", "Terras de Itu"),
        ("5", "MLES"),
        ("6", "Araçari SPE"),
        ("12", "Ellenco"),
        ("13", "Vercellino"),
        ("16", "Loteadora Ypês IV"),
        ("21", "Reserva Ypês IV"),
        ("28", "Reserva Ramos"),
        ("32", "Novo Horizonte"),
    ]
    for id_sienge, nome in specs:
        if not db_session.query(Company).filter(Company.id_sienge == id_sienge).first():
            db_session.add(
                Company(
                    id_sienge=id_sienge,
                    cnpj=id_sienge,
                    razao_social=nome,
                    nome_fantasia=nome,
                )
            )
    db_session.commit()


def test_organograma_referencia_completo(db_session):
    _seed_all_reference_companies(db_session)
    seed_reference_links(db_session)

    result = validate_organograma(db_session)
    assert result["divergencias"] == 0
    assert result["ok"] is True

    by_sienge = {e["id_sienge"]: e for e in result["empresas"]}
    assert by_sienge["13"]["status"] == "ok"
    assert abs(by_sienge["13"]["actual_pct"] - 27.749) < 0.02
    assert by_sienge["5"]["actual_pct"] == 33.0


def test_detecta_divergencia_mles(db_session):
    _seed_all_reference_companies(db_session)
    seed_reference_links(db_session)

    mles = db_session.query(Company).filter(Company.id_sienge == "5").first()
    link = (
        db_session.query(CompanyOwnershipLink)
        .filter(CompanyOwnershipLink.child_company_id == mles.id)
        .first()
    )
    link.percentage = 66.0
    db_session.commit()

    from app.services.mldu_ownership import sync_company_effective_percentages

    sync_company_effective_percentages(db_session)

    result = validate_organograma(db_session)
    assert result["ok"] is False
    assert result["divergencias"] >= 1
    mles_row = next(e for e in result["empresas"] if e["id_sienge"] == "5")
    assert mles_row["status"] == "divergente"
