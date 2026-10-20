from datetime import datetime, timezone

from app.models.viability import Viability


def test_lista_traz_as_tres_viabilidades_raiz_e_esconde_cenario_filho(client, db_session):
    agora = datetime.now(timezone.utc)
    raiz_a = Viability(project_name="VIABILIDADE STRESS TEST", status="Em Andamento", created_at=agora, updated_at=agora)
    raiz_b = Viability(project_name="IGAVETÁ", status="Em Aprovação", created_at=agora, updated_at=agora)
    raiz_c = Viability(project_name="Jardim dos Ipês III", status="Aprovado", created_at=agora, updated_at=agora)
    db_session.add_all([raiz_a, raiz_b, raiz_c])
    db_session.commit()
    filho = Viability(
        project_name="Jardim dos Ipês III - Cenário II",
        status="Aprovado",
        version_of_id=raiz_c.id,
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(filho)
    db_session.commit()

    res = client.get("/api/v1/viabilities/")
    assert res.status_code == 200, res.text
    nomes = {row["project_name"] for row in res.json()}
    assert nomes == {"VIABILIDADE STRESS TEST", "IGAVETÁ", "Jardim dos Ipês III"}
    assert all(row.get("version_of_id") in (None, 0) for row in res.json())
