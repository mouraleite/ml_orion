from app.services.erp_integration import DummyErpService, SiengeErpService


class _FakeSiengeClient:
    password = "x"
    api_v1_base_url = "https://api.sienge.com.br/mouraleite/public/api/v1"

    def paginate_v1_pages(self, url: str):
        if url.endswith("/cost-centers"):
            yield [
                {"id": 90023, "name": "CC 90023", "idCompany": 1, "cnpj": None},
                {"id": 90024, "name": "CC 90024", "idCompany": 1},
            ]
        elif url.endswith("/enterprises"):
            yield [
                {
                    "id": 17901,
                    "name": "Obra 17901",
                    "cnpj": "00.000.000/0001-00",
                    "companyId": 2,
                    "companyName": "MLDU",
                    "type": "1",
                }
            ]
        elif url.endswith("/companies"):
            yield [{"id": 2, "name": "Moura Leite", "tradeName": "MLDU", "cnpj": "00"}]
        elif url.endswith("/payment-categories"):
            yield [
                {
                    "id": 2030409,
                    "name": "Conceituação e Inteligência de Produto",
                    "tpConta": "R",
                    "flRedutora": "N",
                    "flAtiva": "S",
                    "flAdiantamento": "N",
                    "flImposto": "N",
                }
            ]
        else:
            yield []


def test_dummy_continua_vazio():
    dummy = DummyErpService()
    assert dummy.fetch_centros_custo() == []
    assert dummy.fetch_enterprises() == []
    assert dummy.fetch_planos_financeiros() == []


def test_sienge_mapeia_empresas_id_como_texto():
    svc = SiengeErpService(client=_FakeSiengeClient())
    empresas = svc.fetch_empresas()
    assert empresas[0]["id"] == "2"
    assert empresas[0]["nomeFantasia"] == "MLDU"


def test_sienge_mapeia_centros_e_obras():
    svc = SiengeErpService(client=_FakeSiengeClient())
    centros = svc.fetch_centros_custo()
    assert {c["id"] for c in centros} == {90023, 90024}
    assert centros[0]["nome"] == "CC 90023"
    assert centros[0]["id_empresa"] == 1

    obras = svc.fetch_enterprises()
    assert obras[0]["id"] == 17901
    assert obras[0]["nome"] == "Obra 17901"
    assert obras[0]["id_empresa"] == 2
    assert obras[0]["nome_empresa"] == "MLDU"
    assert obras[0]["tipo"] == "1"


def test_sienge_mapeia_planos_financeiros():
    svc = SiengeErpService(client=_FakeSiengeClient())
    planos = svc.fetch_planos_financeiros()
    assert planos == [
        {
            "id": "2030409",
            "name": "Conceituação e Inteligência de Produto",
            "tpConta": "R",
            "flRedutora": "N",
            "flAtiva": "S",
            "flAdiantamento": "N",
            "flImposto": "N",
        }
    ]


def test_sem_senha_nao_consulta():
    class _SemSenha(_FakeSiengeClient):
        password = ""

    svc = SiengeErpService(client=_SemSenha())
    assert svc.fetch_centros_custo() == []
    assert svc.fetch_enterprises() == []
    assert svc.fetch_planos_financeiros() == []
