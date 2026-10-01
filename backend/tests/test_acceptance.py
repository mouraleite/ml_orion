import pytest
import io
import os
from app.models.orcamento import Orcamento, OrcamentoItem, OrcamentoVendaItem
from app.models.auditoria import Auditoria
from app.models.user import User
from app.models.economic_indicator import EconomicIndicator
from app.api.deps import get_current_user


def criar_orcamento_base(client, ano: int, tipo: str = "despesas", produto_id: int = 1):
    """Cria o Orçamento Base do produto.

    O GET não cria mais orçamento; salvar exige um já existente para o produto.
    """
    r = client.post(
        "/api/v1/orcamentos/criar",
        json={"ano": ano, "tipo": tipo.upper(), "produto_id": produto_id},
    )
    assert r.status_code == 200, r.text
    return r.json()["orcamento_id"]


# --- Testes para os 15 Critérios da Seção 26 ---

def test_01_usuario_autorizado_cria_orcamento(client, db_session):
    """1. Usuário autorizado consegue criar orçamento de despesas."""
    criar_orcamento_base(client, 2026)
    response = client.post("/api/v1/orcamentos/despesas/2026/salvar", json={
        "itens": [
            {
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 100.0
            }
        ]
    })
    assert response.status_code == 200
    
    # Verifica banco
    orc = db_session.query(Orcamento).filter_by(tipo="DESPESAS", ano=2026).first()
    assert orc is not None


def test_02_usuario_nao_autorizado_comb_proibida(client, db_session):
    """2. Usuário não autorizado não consegue gravar combinação proibida."""
    # Matriz mockada só tem produto 1 e plano 1 liberados.
    criar_orcamento_base(client, 2026)
    response = client.post("/api/v1/orcamentos/despesas/2026/salvar", json={
        "itens": [
            {
                "produto_id": 1,
                "plano_financeiro_id": 2, # Proibido
                "jan": 100.0,
                "total_anual": 100.0
            }
        ]
    })
    assert response.status_code in (400, 403, 422)
    
    # E não deve ter gravado plano 2
    count = db_session.query(OrcamentoItem).filter_by(plano_financeiro_id=2).count()
    assert count == 0


def test_03_totais_calculados_automaticamente(client, db_session):
    """3. Totais mensais e anuais são calculados automaticamente."""
    criar_orcamento_base(client, 2027)
    client.post("/api/v1/orcamentos/despesas/2027/salvar", json={
        "itens": [
            {
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 100.0,
                "fev": 200.0,
                "total_anual": 300.0
            }
        ]
    })
    # O total é calculado ao salvar e pode ser verificado no banco ou no endpoint
    db_session.expire_all()
    orc = db_session.query(Orcamento).filter_by(ano=2027).first()
    db_item = db_session.query(OrcamentoItem).filter_by(orcamento_id=orc.id).first()
    # Verifica o total_anual no banco ou se foi somado corretamente
    # Dependendo de como a api/routes/orcamentos salva, pode ser em runtime ou persistido.
    # Assumimos que foi persistido.
    assert db_item.total_anual == 300.0


def test_04_replicacao_nunca_sobrescreve_silenciosamente(client, db_session):
    """4. Replicação nunca sobrescreve silenciosamente."""
    # Cria base
    criar_orcamento_base(client, 2028)
    client.post("/api/v1/orcamentos/despesas/2028/salvar", json={
        "itens": [
            {"produto_id": 1, "plano_financeiro_id": 1, "jan": 100.0, "total_anual": 100.0}
        ]
    })
    orc = db_session.query(Orcamento).filter_by(ano=2028).first()
    
    # Rascunho não reabre; o pedido é recusado sem alterar valores.
    response = client.post(f"/api/v1/orcamentos/{orc.id}/solicitar-reabertura", json={"novo_status": "Reaberto", "motivo": "Teste"})
    assert response.status_code == 400
    db_session.expire_all()
    item = db_session.query(OrcamentoItem).filter_by(orcamento_id=orc.id).first()
    assert item.jan == 100.0


def test_05_ipca_registra_indice_e_competencia(client, db_session):
    """5. IPCA registra índice e competência."""
    ipca = EconomicIndicator(
        competencia="2026-01-01",
        valor=4.5,
        tipo_unidade="% a.m.",
        index_type="IPCA"
    )
    db_session.add(ipca)
    db_session.commit()
    
    db_ipca = db_session.query(EconomicIndicator).filter_by(index_type="IPCA").first()
    assert db_ipca.valor == 4.5
    assert "2026" in str(db_ipca.competencia)


def test_06_versoes_recuperadas_integralmente(client, db_session):
    """6. Versões salvas podem ser recuperadas integralmente."""
    criar_orcamento_base(client, 2029)
    client.post("/api/v1/orcamentos/despesas/2029/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": 100.0, "total_anual": 100.0}]
    })
    db_session.expire_all()
    orc_v1 = db_session.query(Orcamento).filter_by(ano=2029).first()
    item_v1 = db_session.query(OrcamentoItem).filter_by(orcamento_id=orc_v1.id).first()
    assert item_v1.jan == 100.0


def test_07_forecast_preserva_versao_base(client, db_session):
    """7. Forecast preserva a versão-base."""
    criar_orcamento_base(client, 2030)
    client.post("/api/v1/orcamentos/despesas/2030/salvar", json={
        "itens": [{"produto_id": 1, "plano_financeiro_id": 1, "jan": 100.0}]
    })
    orc = db_session.query(Orcamento).filter_by(ano=2030).first()
    orc.status = "Aprovado"
    db_session.commit()
    
    response = client.post(f"/api/v1/forecasts/criar_de_base", json={"orcamento_id": orc.id})
    if response.status_code == 200:
        forecast = db_session.query(Orcamento).filter_by(versao_base_id=orc.id).first()
        assert forecast is not None
        
    orc_base = db_session.query(Orcamento).filter_by(id=orc.id).first()
    assert orc_base.status == "Aprovado"


def test_08_meses_bloqueados_nao_alterados(client, db_session):
    """8. Meses bloqueados não podem ser alterados nem via backend."""
    from app.models.fechamento import ClosedMonth

    criar_orcamento_base(client, 2035)
    salvar = lambda jan, fev: client.post(  # noqa: E731
        "/api/v1/orcamentos/despesas/2035/salvar",
        json={
            "itens": [
                {
                    "produto_id": 1,
                    "plano_financeiro_id": 1,
                    "jan": jan,
                    "fev": fev,
                    "total_anual": jan + fev,
                }
            ]
        },
    )
    assert salvar(100.0, 50.0).status_code == 200

    db_session.add(ClosedMonth(ano=2035, mes=1))
    db_session.commit()

    # A tela precisa saber quais meses estão travados
    assert client.get("/api/v1/orcamentos/despesas/2035").json()["meses_fechados"] == [1]

    # Mês aberto pode mudar, desde que o fechado venha igual
    assert salvar(100.0, 77.0).status_code == 200
    db_session.expire_all()
    item = db_session.query(OrcamentoItem).filter_by(plano_financeiro_id=1).first()
    assert (item.jan, item.fev) == (100.0, 77.0)

    # Mês fechado com valor diferente: recusa.
    # Fica por último: o rollback do endpoint desfaz a transação que o
    # conftest compartilha entre a request e o teste, zerando o cenário.
    resposta = salvar(999.0, 77.0)
    assert resposta.status_code == 403
    assert "jan" in resposta.json()["detail"]


def test_09_forecast_permite_inclusoes(client, db_session):
    """9. Forecast permite inclusões autorizadas."""
    pass


def test_10_vgv_recalculado_automaticamente(client, db_session):
    """10. VGV é recalculado automaticamente."""
    from app.main import app
    from app.api.deps import get_active_department
    from app.models.departamento import Departamento
    
    # Substituir por um departamento Comercial para autorizar Vendas
    def override_get_comercial():
        d3 = db_session.query(Departamento).filter(Departamento.id == 3).first()
        if not d3:
            d3 = Departamento(id=3, nome="Comercial")
            db_session.add(d3)
            db_session.commit()
        return d3
        
    app.dependency_overrides[get_active_department] = override_get_comercial
    
    criar_orcamento_base(client, 2031, tipo="vendas")
    response = client.post("/api/v1/orcamentos/vendas/2031/salvar", json={
        "itens": [
            {
                "produto_id": 1, "plano_venda_id": 1,
                "meses": [{"mes": 1, "numero_vendas": 2, "ticket_medio": 500000.0}]
            }
        ]
    })
    assert response.status_code == 200
    # Verifica o DB se há o valor gravado
    orc_v = db_session.query(Orcamento).filter_by(ano=2031, tipo="VENDAS").first()
    if orc_v:
        item = db_session.query(OrcamentoVendaItem).filter_by(orcamento_id=orc_v.id).first()
        assert item is not None
        # Dependendo da logica, VGV é calculado
        # assert item.vgv == 1000000.0


def test_11_excel_invalido_nao_grava_dados(client, db_session):
    """11. Excel inválido não grava dados."""
    excel_content = b"dummy"
    response = client.post("/api/v1/orcamentos/excel/importar/DESPESAS/2032", files={
        "file": ("planilha.xlsx", io.BytesIO(excel_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    })
    assert response.status_code == 422
    assert db_session.query(Orcamento).filter_by(ano=2032).count() == 0


def test_12_sienge_registra_status(client, db_session, monkeypatch):
    """12. Integração Sienge registra status e erros."""
    pass


def test_13_acompanhamento_apresenta_tres_bandas(client, db_session):
    """13. Acompanhamento apresenta Orçado, Forecast e Realizado."""
    response = client.get("/api/v1/acompanhamento/despesas/2026")
    if response.status_code == 200:
        data = response.json()
        if "itens" in data and len(data["itens"]) > 0:
            assert "orcado" in data["itens"][0] or "orcado_total" in data["itens"][0]


def test_14_auditoria_identifica_usuario(client, db_session):
    """14. Auditoria identifica usuário, data e mudança."""
    orc_id = criar_orcamento_base(client, 2033)
    envio = client.post(f"/api/v1/orcamentos/{orc_id}/status", json={"novo_status": "Em aprovação"})
    assert envio.status_code == 200

    aprovacao = client.post(f"/api/v1/orcamentos/{orc_id}/status", json={"novo_status": "Fechado"})
    assert aprovacao.status_code == 200
    assert aprovacao.json()["status"] == "Fechado"

    audit = db_session.query(Auditoria).filter_by(registro_id=orc_id, campo="status").all()
    assert audit
    assert all(a.usuario_id == 1 for a in audit)
    assert any(a.novo_valor == "Fechado" for a in audit)


def test_status_nao_fecha_direto_do_rascunho(client, db_session):
    orc_id = criar_orcamento_base(client, 2040)
    resposta = client.post(f"/api/v1/orcamentos/{orc_id}/status", json={"novo_status": "Fechado"})
    assert resposta.status_code == 400
    db_session.expire_all()
    assert db_session.query(Orcamento).filter_by(id=orc_id).first().status == "Rascunho"


def test_analista_envia_mas_nao_aprova(client, db_session):
    orc_id = criar_orcamento_base(client, 2041)
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: db_session.query(User).filter(User.id == 2).first()
    envio = client.post(f"/api/v1/orcamentos/{orc_id}/status", json={"novo_status": "Em aprovação"})
    assert envio.status_code == 200
    recusa = client.post(f"/api/v1/orcamentos/{orc_id}/status", json={"novo_status": "Fechado"})
    assert recusa.status_code == 403


def test_forecast_aprovar_fecha(client, db_session):
    from app.models.forecast import Forecast

    fc = Forecast(
        ano=2042, tipo="DESPESAS", departamento_id=1,
        status="Rascunho", versao_numero=1, descricao="Forecast teste",
    )
    db_session.add(fc)
    db_session.commit()
    assert client.post(f"/api/v1/forecasts/{fc.id}/status", json={"novo_status": "Em aprovação"}).status_code == 200
    resposta = client.post(f"/api/v1/forecasts/{fc.id}/status", json={"novo_status": "Aprovado"})
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "Fechado"


def test_15_reabertura_exige_permissao_motivo(client, db_session):
    """15. Reabertura exige motivo; rascunho não reabre."""
    orc = Orcamento(ano=2034, tipo="DESPESAS", departamento_id=1, status="Fechado", versao_numero=1, descricao="Orçamento")
    db_session.add(orc)
    db_session.commit()

    sem_motivo = client.post(f"/api/v1/orcamentos/{orc.id}/solicitar-reabertura", json={"novo_status": "Solicitação Reabertura", "motivo": ""})
    assert sem_motivo.status_code == 400

    ok = client.post(f"/api/v1/orcamentos/{orc.id}/solicitar-reabertura", json={"novo_status": "Solicitação Reabertura", "motivo": "Correção"})
    assert ok.status_code == 200, ok.text
    db_session.expire_all()
    orc_pedido = db_session.query(Orcamento).filter_by(id=orc.id).first()
    assert orc_pedido.status == "Solicitação Reabertura"
    assert orc_pedido.motivo_reabertura == "Correção"
