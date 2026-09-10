import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.departamento import Departamento
from app.models.orcamento import Orcamento, OrcamentoItem
from app.services.sharepoint_departamento import fix_orcamentos_sharepoint_sem_departamento


def test_fix_move_2026_bulk_orcamento_to_sienge(db_session):
    sienge = Departamento(id=99, nome="Consolidado - Sienge", ativo=True)
    db_session.add(sienge)
    orc = Orcamento(
        descricao="Orçamento",
        ano=2026,
        tipo="DESPESAS",
        status="Fechado",
        departamento_id=1,
        versao_numero=1,
    )
    db_session.add(orc)
    db_session.flush()
    db_session.add(
        OrcamentoItem(
            orcamento_id=orc.id,
            produto_id=1,
            plano_financeiro_id=1,
            jan=100,
            total_anual=100,
        )
    )
    db_session.commit()

    n = fix_orcamentos_sharepoint_sem_departamento(db_session)
    db_session.refresh(orc)
    assert n >= 1
    assert orc.departamento_id == 99
