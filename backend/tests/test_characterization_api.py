"""
Trava o comportamento atual das APIs de orçamento, forecast, acompanhamento,
Excel (validador) e matriz de permissão — sem alterar o produto.

Se um assert falhar após mudança de código, o número ou a regra visível
ao usuário pode ter mudado e precisa de revalidação.
"""
from app.models.forecast import Forecast, ForecastItem
from app.models.fechamento import ClosedMonth
from app.models.orcamento import Orcamento, OrcamentoItem
from app.services.auth_matrix import validate_budget_allocation
from app.services.excel_validator import validar_despesas_receitas


def _criar_orcamento_despesas(client, ano, produto_id=1):
    r = client.post("/api/v1/orcamentos/criar", json={
        "ano": ano,
        "tipo": "DESPESAS",
        "produto_id": produto_id,
    })
    assert r.status_code == 200, r.text
    return r.json()["orcamento_id"]


class TestMatrizPermissao:
    def test_whitelist_produto_plano_departamento(self, db_session):
        assert validate_budget_allocation(db_session, 1, 1, 1) is True
        assert validate_budget_allocation(db_session, 1, 1, 2) is False
        assert validate_budget_allocation(db_session, 1, 2, 1) is False


class TestExcelDespesasReceitas:
    def test_total_anual_e_soma_dos_meses(self, db_session):
        erros, ok = validar_despesas_receitas(
            rows=[{
                "produto": "Produto A",
                "plano_financeiro": "Plano Fin 1",
                "jan": "10,5",
                "fev": 20,
            }],
            tipo="DESPESAS",
            ano=2041,
            departamento_id=1,
            db=db_session,
        )
        assert erros == []
        assert len(ok) == 1
        assert ok[0]["jan"] == 10.5
        assert ok[0]["fev"] == 20.0
        assert ok[0]["total_anual"] == 30.5

    def test_plano_nao_autorizado_nao_entra_em_validas(self, db_session):
        erros, ok = validar_despesas_receitas(
            rows=[{
                "produto": "Produto A",
                "plano_financeiro": "Plano Fin 2",
                "jan": 100,
            }],
            tipo="DESPESAS",
            ano=2041,
            departamento_id=1,
            db=db_session,
        )
        assert any(e["codigo"] == "V04" for e in erros)
        assert ok == []


class TestOrcamentoDespesasTotais:
    def test_despesas_grava_total_anual_do_payload(self, client, db_session):
        """Comportamento atual: despesas NÃO recalculam total_anual no servidor."""
        ano = 2042
        _criar_orcamento_despesas(client, ano)
        r = client.post(f"/api/v1/orcamentos/despesas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 100.0,
                "fev": 200.0,
                "total_anual": 999.0,
            }]
        })
        assert r.status_code == 200, r.text
        db_session.expire_all()
        item = db_session.query(OrcamentoItem).join(Orcamento).filter(
            Orcamento.ano == ano, Orcamento.tipo == "DESPESAS"
        ).first()
        assert item is not None
        assert item.jan == 100.0
        assert item.fev == 200.0
        assert item.total_anual == 999.0

    def test_despesas_ignora_linha_com_total_zero_sem_obs(self, client, db_session):
        ano = 2043
        _criar_orcamento_despesas(client, ano)
        r = client.post(f"/api/v1/orcamentos/despesas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 50.0,
                "total_anual": 0.0,
            }]
        })
        assert r.status_code == 200, r.text
        assert db_session.query(OrcamentoItem).join(Orcamento).filter(
            Orcamento.ano == ano
        ).count() == 0


class TestForecastCopiaETotais:
    def test_criar_de_base_copia_valores_mensais(self, client, db_session):
        ano = 2044
        oid = _criar_orcamento_despesas(client, ano)
        client.post(f"/api/v1/orcamentos/despesas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 111.0,
                "mar": 222.0,
                "total_anual": 333.0,
            }]
        })
        r = client.post("/api/v1/forecasts/criar_de_base", json={
            "ano": ano,
            "tipo": "DESPESAS",
            "produto_id": 1,
            "versao_base_orcamento_id": oid,
        })
        assert r.status_code == 200, r.text
        fid = r.json()["forecast_id"]
        db_session.expire_all()
        fi = db_session.query(ForecastItem).filter_by(forecast_id=fid).first()
        assert fi is not None
        assert fi.jan == 111.0
        assert fi.mar == 222.0
        assert fi.total_anual == 333.0

        orc = db_session.query(Orcamento).filter_by(id=oid).first()
        assert orc is not None

    def test_salvar_forecast_recalcula_total_anual(self, client, db_session):
        ano = 2045
        oid = _criar_orcamento_despesas(client, ano)
        client.post(f"/api/v1/orcamentos/despesas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 10.0,
                "total_anual": 10.0,
            }]
        })
        r = client.post("/api/v1/forecasts/criar_de_base", json={
            "ano": ano,
            "tipo": "DESPESAS",
            "produto_id": 1,
            "versao_base_orcamento_id": oid,
        })
        assert r.status_code == 200, r.text
        r2 = client.post(f"/api/v1/forecasts/despesas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 10.0,
                "fev": 40.0,
                "total_anual": 1.0,
            }]
        })
        assert r2.status_code == 200, r2.text
        db_session.expire_all()
        fi = db_session.query(ForecastItem).join(Forecast).filter(
            Forecast.ano == ano, Forecast.tipo == "DESPESAS"
        ).first()
        assert fi.jan == 10.0
        assert fi.fev == 40.0
        assert fi.total_anual == 50.0

    def test_mes_fechado_nao_altera_valor(self, client, db_session):
        ano = 2046
        oid = _criar_orcamento_despesas(client, ano)
        client.post(f"/api/v1/orcamentos/despesas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 80.0,
                "fev": 20.0,
                "total_anual": 100.0,
            }]
        })
        r = client.post("/api/v1/forecasts/criar_de_base", json={
            "ano": ano,
            "tipo": "DESPESAS",
            "produto_id": 1,
            "versao_base_orcamento_id": oid,
        })
        assert r.status_code == 200, r.text
        db_session.add(ClosedMonth(ano=ano, mes=1, fechado_por_id=1))
        db_session.commit()

        r2 = client.post(f"/api/v1/forecasts/despesas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 1.0,
                "fev": 20.0,
                "total_anual": 21.0,
            }]
        })
        assert r2.status_code == 403, r2.text


class TestAcompanhamentoTresBandas:
    def test_orcado_forecast_realizado_e_saldos(self, client, db_session):
        ano = 2047
        oid = _criar_orcamento_despesas(client, ano)
        client.post(f"/api/v1/orcamentos/despesas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 100.0,
                "total_anual": 100.0,
            }]
        })
        r = client.post("/api/v1/forecasts/criar_de_base", json={
            "ano": ano,
            "tipo": "DESPESAS",
            "produto_id": 1,
            "versao_base_orcamento_id": oid,
        })
        assert r.status_code == 200, r.text
        client.post(f"/api/v1/forecasts/despesas/{ano}/salvar", json={
            "itens": [{
                "produto_id": 1,
                "plano_financeiro_id": 1,
                "jan": 90.0,
                "total_anual": 90.0,
            }]
        })

        resp = client.get(f"/api/v1/acompanhamento/despesas/{ano}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "itens" in data
        assert len(data["itens"]) >= 1
        item = next(
            i for i in data["itens"]
            if i["produto_id"] == 1 and i["plano_financeiro_id"] == 1
        )
        assert item["orcado"]["jan"] == 100.0
        assert item["forecast"]["jan"] == 90.0
        assert item["realizado"]["jan"] == 0.0
        assert item["orcado"]["total"] == 100.0
        assert item["forecast"]["total"] == 90.0
        assert item["saldo_orcado"]["jan"] == 100.0
        assert item["saldo_forecast"]["jan"] == 90.0


class TestSegurancaPerfis:
    def test_crud_perfil_preserva_json_de_permissoes(self, client):
        payload = {
            "name": "Perfil Trava",
            "description": "characterization",
            "is_active": True,
            "permissions": {"Apoio": {"Empresas": True}, "Orçamento": {"Despesas": False}},
        }
        r = client.post("/api/v1/perfis-acesso/", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["permissions"]["Apoio"]["Empresas"] is True
        assert body["permissions"]["Orçamento"]["Despesas"] is False

        r2 = client.get("/api/v1/perfis-acesso/")
        assert r2.status_code == 200
        nomes = [p["name"] for p in r2.json()]
        assert "Perfil Trava" in nomes
