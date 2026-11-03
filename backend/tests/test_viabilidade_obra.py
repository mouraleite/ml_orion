from app.models.cost_center import CostCenter
from app.models.viability import Viability
from app.services.viabilidade_obra import ids_centros_produtos_acompanhados, land_bank_oculto_por_obra


def test_ids_incluem_satelite_do_produto_rastreado(db_session):
    db_session.add_all([
        CostCenter(id=10, id_sienge="14300", nome="BOITUVA - MORADA DOS IPÊS II", track_in_dashboard=True),
        CostCenter(id=11, id_sienge="14301", nome="BOITUVA - MORADA DOS IPÊS II - OBRAS", track_in_dashboard=False),
        CostCenter(id=12, id_sienge="14304", nome="BOITUVA - RESERVA DOS IPÊS", track_in_dashboard=False),
    ])
    db_session.commit()
    ids = ids_centros_produtos_acompanhados(db_session)
    assert 10 in ids
    assert 11 in ids
    assert 12 not in ids


def test_land_bank_so_some_com_vinculo_e_obra_rastreada(db_session):
    acompanhados = {10, 11}
    livre = Viability(project_name="Livre", status="Aprovado")
    ligado = Viability(project_name="Morada", status="Aprovado", obra_cost_center_id=10)
    outro = Viability(project_name="Reserva", status="Aprovado", obra_cost_center_id=12)
    assert land_bank_oculto_por_obra(livre, acompanhados) is False
    assert land_bank_oculto_por_obra(ligado, acompanhados) is True
    assert land_bank_oculto_por_obra(outro, acompanhados) is False
