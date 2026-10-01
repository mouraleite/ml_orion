"""Importação Excel do Forecast (versão rolling, um documento)."""
import io

from openpyxl import Workbook

from app.models.departamento import ProdutoPlanoFinanceiro
from app.models.forecast import Forecast, ForecastItem
from app.services.periodos import MESES_STR


def _xlsx_despesas(*linhas):
    wb = Workbook()
    ws = wb.active
    ws.append(["produto", "plano_financeiro", *MESES_STR])
    for produto, plano, jan in linhas:
        meses = [0.0] * 12
        meses[0] = jan
        ws.append([produto, plano, *meses])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _files(content):
    return {
        "file": (
            "planilha.xlsx",
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def test_excel_invalido_nao_grava(client, db_session):
    resp = client.post(
        "/api/v1/forecasts/excel/importar/DESPESAS/2088",
        files=_files(b"not-xlsx"),
    )
    assert resp.status_code == 422
    assert db_session.query(Forecast).filter_by(ano=2088).count() == 0


def test_excel_receitas_grava_e_preserva_linha_auto(client, db_session):
    """Planilha grava receita manual. Linha injetada por Vendas não muda."""
    db_session.add(ProdutoPlanoFinanceiro(produto_id=2, plano_financeiro_id=1, permitido=True))
    db_session.commit()
    criado = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2092, "tipo": "RECEITAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert criado.status_code == 200, criado.text
    fid = criado.json()["forecast_id"]
    db_session.expire_all()
    auto = db_session.query(ForecastItem).filter_by(forecast_id=fid).one()
    auto.jan = 100.0
    auto.total_anual = 100.0
    auto.is_auto_generated = True
    db_session.commit()

    resp = client.post(
        "/api/v1/forecasts/excel/importar/RECEITAS/2092",
        files=_files(_xlsx_despesas(
            ("Produto A", "Plano Fin 1", 1),
            ("Produto B", "Plano Fin 1", 5),
        )),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["gravado"] is True
    db_session.expire_all()
    itens = db_session.query(ForecastItem).filter_by(forecast_id=fid).all()
    por_produto = {i.produto_id: i for i in itens}
    assert por_produto[1].is_auto_generated is True
    assert por_produto[1].jan == 100.0
    assert por_produto[2].is_auto_generated is False
    assert por_produto[2].jan == 5.0

    validado = client.post(
        "/api/v1/forecasts/excel/validar/RECEITAS/2092",
        files=_files(_xlsx_despesas(("Produto B", "Plano Fin 1", 5))),
    )
    assert validado.status_code == 200, validado.text
    assert validado.json()["pode_importar"] is True


def test_excel_recusa_forecast_fechado(client, db_session):
    r = client.post("/api/v1/forecasts/criar_de_base", json={
        "ano": 2087, "tipo": "DESPESAS", "produto_id": 1, "plano_financeiro_id": 1,
    })
    assert r.status_code == 200, r.text
    fid = r.json()["forecast_id"]
    assert client.post(f"/api/v1/forecasts/{fid}/status", json={"novo_status": "Em aprovação"}).status_code == 200
    assert client.post(f"/api/v1/forecasts/{fid}/status", json={"novo_status": "Fechado"}).status_code == 200
    resp = client.post(
        "/api/v1/forecasts/excel/importar/DESPESAS/2087",
        files=_files(_xlsx_despesas(("Produto A", "Plano Fin 1", 99))),
    )
    assert resp.status_code == 403
    item = db_session.query(ForecastItem).filter_by(forecast_id=fid).first()
    assert item is None or (item.jan or 0) != 99


def test_excel_nao_altera_versao_antiga(client, db_session):
    db_session.add(Forecast(
        descricao="Forecast - 7+5",
        ano=2091,
        tipo="DESPESAS",
        versao_numero=1,
        status="Rascunho",
        usuario_criador_id=1,
        departamento_id=1,
        produto_id=None,
    ))
    db_session.commit()
    resp = client.post(
        "/api/v1/forecasts/excel/importar/DESPESAS/2091",
        files=_files(_xlsx_despesas(("Produto A", "Plano Fin 1", 10))),
    )
    assert resp.status_code == 400
    assert db_session.query(Forecast).filter_by(ano=2091).count() == 1


def test_excel_grava_no_mesmo_documento(client, db_session):
    db_session.add(ProdutoPlanoFinanceiro(produto_id=2, plano_financeiro_id=1, permitido=True))
    db_session.commit()
    resp = client.post(
        "/api/v1/forecasts/excel/importar/DESPESAS/2088",
        files=_files(_xlsx_despesas(
            ("Produto A", "Plano Fin 1", 10),
            ("Produto B", "Plano Fin 1", 5),
        )),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["gravado"] is True
    assert db_session.query(Forecast).filter_by(ano=2088, tipo="DESPESAS").count() == 1
    fc = db_session.query(Forecast).filter_by(ano=2088, tipo="DESPESAS").one()
    assert fc.produto_id is None
    pids = {i.produto_id for i in db_session.query(ForecastItem).filter_by(forecast_id=fc.id).all()}
    assert pids == {1, 2}


def test_excel_exporta_depois_de_importar(client):
    imp = client.post(
        "/api/v1/forecasts/excel/importar/DESPESAS/2086",
        files=_files(_xlsx_despesas(("Produto A", "Plano Fin 1", 10))),
    )
    assert imp.status_code == 200, imp.text
    fid = imp.json()["forecast_id"]
    exp = client.get(f"/api/v1/forecasts/excel/exportar/{fid}")
    assert exp.status_code == 200
    assert exp.headers["content-type"].startswith("application/vnd.openxmlformats")
