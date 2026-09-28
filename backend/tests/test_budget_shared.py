"""Testes unitários dos helpers compartilhados orçamento/forecast (Onda 4)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.budget_shared import (
    _parse_forecast_rolling_left,
    check_pessimistic_lock,
    canonical_versao_vendas_planilha,
    dedupe_versoes_por_descricao,
    format_visualizacao_versao_label,
    group_venda_items,
    is_venda_distrato,
    ordenar_e_dedupar_labels_versao,
    serialize_base_monthly_item,
    serialize_monthly_item_row,
)


def test_serialize_monthly_item_row_defaults_zero():
    item = SimpleNamespace(
        id=1,
        produto_id=10,
        plano_financeiro_id=20,
        jan=None,
        fev=5.0,
        mar=None,
        abr=None,
        mai=None,
        jun=None,
        jul=None,
        ago=None,
        set=None,
        out=None,
        nov=None,
        dez=None,
        total_anual=None,
        observacao="x",
    )
    row = serialize_monthly_item_row(item)
    assert row["id"] == 1
    assert row["jan"] == 0.0
    assert row["fev"] == 5.0
    assert row["total_anual"] == 0.0


def test_serialize_base_monthly_item_preserva_none_sem_zero_defaults():
    ib = SimpleNamespace(
        produto_id=1,
        plano_financeiro_id=2,
        jan=100.0,
        fev=None,
        mar=None,
        abr=None,
        mai=None,
        jun=None,
        jul=None,
        ago=None,
        set=None,
        out=None,
        nov=None,
        dez=None,
        total_anual=100.0,
    )
    row = serialize_base_monthly_item(ib, zero_defaults=False)
    assert row["jan"] == 100.0
    assert row["fev"] is None
    assert row["total_anual"] == 100.0


def test_group_venda_items_separa_distrato():
    itens = [
        SimpleNamespace(
            produto_id=1,
            plano_venda_id=2,
            observacao="Normal",
            mes=1,
            ticket_medio=10.0,
            numero_vendas=1,
            vgv=10.0,
            origem_venda=None,
        ),
        SimpleNamespace(
            produto_id=1,
            plano_venda_id=2,
            observacao="Distrato cliente",
            mes=2,
            ticket_medio=5.0,
            numero_vendas=-1,
            vgv=-5.0,
            origem_venda=None,
        ),
    ]
    linhas = group_venda_items(itens)
    assert len(linhas) == 2
    assert is_venda_distrato(itens[1]) is True


def test_check_pessimistic_lock_outro_usuario():
    entity = SimpleNamespace(
        usuario_edicao_id=99,
        data_inicio_edicao=datetime.utcnow(),
        usuario_edicao=SimpleNamespace(nome="Maria"),
    )
    locked, nome = check_pessimistic_lock(entity, current_user_id=1)
    assert locked is True
    assert nome == "Maria"


def test_check_pessimistic_lock_expirada():
    entity = SimpleNamespace(
        usuario_edicao_id=99,
        data_inicio_edicao=datetime.utcnow() - timedelta(seconds=2000),
        usuario_edicao=SimpleNamespace(nome="Maria"),
    )
    locked, nome = check_pessimistic_lock(entity, current_user_id=1)
    assert locked is False
    assert nome is None


def test_dedupe_versoes_por_descricao():
    versoes = [
        SimpleNamespace(id=3, descricao="Forecast - 0+12", versao_numero=2, status="Rascunho"),
        SimpleNamespace(id=2, descricao="Forecast - 0+12", versao_numero=1, status="Fechado"),
        SimpleNamespace(id=5, descricao="Forecast - 3+9", versao_numero=1, status="Rascunho"),
    ]
    out = dedupe_versoes_por_descricao(versoes)
    assert len(out) == 2
    assert out[0]["id"] == 3
    assert out[1]["descricao"] == "Forecast - 3+9"


def test_parse_forecast_rolling_left():
    assert _parse_forecast_rolling_left("Forecast - 6+6") == 6
    assert _parse_forecast_rolling_left("Forecast - 1+11") == 1
    assert _parse_forecast_rolling_left("9+3") == 9
    assert _parse_forecast_rolling_left(None) is None
    assert _parse_forecast_rolling_left("Orçamento") is None


def test_format_visualizacao_versao_label():
    assert format_visualizacao_versao_label("Orçamento", kind="orcamento") == "Orçamento"
    assert format_visualizacao_versao_label("Orçamento Base", kind="orcamento") == "Orçamento"
    assert format_visualizacao_versao_label("1ª versão", kind="orcamento") == "Orçamento"
    assert format_visualizacao_versao_label("1º versão", kind="orcamento") == "Orçamento"
    assert format_visualizacao_versao_label("Orçamento Vendas 2026", kind="orcamento") == "Orçamento"
    assert format_visualizacao_versao_label("Carga Inicial Sienge 2026", kind="orcamento") == "Orçamento"
    assert format_visualizacao_versao_label("Forecast - 2+10", kind="forecast") == "Forecast - 2+10"
    assert format_visualizacao_versao_label("Forecast 8+4", kind="forecast") == "Forecast - 8+4"
    assert format_visualizacao_versao_label("2+10", kind="forecast") == "Forecast - 2+10"


def test_canonical_versao_vendas_planilha():
    assert canonical_versao_vendas_planilha("1ª versão")[1] == "orcamento"
    assert canonical_versao_vendas_planilha("Forecast 8+4") == ("Forecast - 8+4", "forecast")
    assert canonical_versao_vendas_planilha("Forecast - 7+5") == ("Forecast - 7+5", "forecast")


def _mes(produto, plano, **meses):
    from app.services.periodos import MESES_STR

    data = {m: 0.0 for m in MESES_STR}
    data.update(meses)
    return SimpleNamespace(produto_id=produto, plano_financeiro_id=plano, **data)


def _soma_por_plano(linhas):
    from app.services.periodos import MESES_STR

    out = {}
    for row in linhas:
        bucket = out.setdefault(row["plano_financeiro_id"], {m: 0.0 for m in MESES_STR})
        for m in MESES_STR:
            bucket[m] += row[m]
    return out


def test_assinar_itens_dfc_bate_com_a_regra_linha_a_linha():
    """Leitura em lote do comparativo DFC: mesmos totais da regra antiga (filtro, redutora, primeira linha)."""
    from app.services.budget_shared import assinar_itens_mensais_dfc
    from app.services.periodos import MESES_STR

    planos = {
        10: SimpleNamespace(id=10, db_id="101", name="Vendas", fl_redutora="N"),
        20: SimpleNamespace(id=20, db_id="201", name="Retenção IR", fl_redutora="N"),
        30: SimpleNamespace(id=30, db_id="301", name="Fora", fl_redutora="N"),
    }
    linhas = [
        _mes(1, 10, jan=100.0, fev=-5.0),
        _mes(1, 10, jan=999.0),
        _mes(2, 10, jan=40.0),
        _mes(1, 20, jan=12.0, fev=-3.0),
        _mes(1, 30, jan=80.0),
    ]

    def referencia(itens, planos_por_id, tipo):
        prefix = "2" if tipo == "DESPESAS" else "1"
        seen = set()
        out = []
        for item in itens:
            plano = planos_por_id.get(item.plano_financeiro_id)
            if not plano or not str(plano.db_id or "").startswith(prefix):
                continue
            key = (item.produto_id, item.plano_financeiro_id)
            if key in seen:
                continue
            seen.add(key)
            redutora = str(plano.fl_redutora or "").upper() == "S" or "reten" in str(plano.name or "").lower()
            row = {"produto_id": item.produto_id, "plano_financeiro_id": item.plano_financeiro_id}
            for m in MESES_STR:
                val = float(getattr(item, m) or 0)
                row[m] = -abs(val) if redutora else val
            out.append(row)
        return out

    got = assinar_itens_mensais_dfc(linhas, planos, "DESPESAS")
    ref = referencia(linhas, planos, "DESPESAS")
    assert _soma_por_plano(got) == _soma_por_plano(ref)
    assert got[0]["produto_id"] == 1 and got[0]["jan"] == -12.0
    assert len(got) == 1

    got_rec = assinar_itens_mensais_dfc(linhas, planos, "RECEITAS")
    ref_rec = referencia(linhas, planos, "RECEITAS")
    assert _soma_por_plano(got_rec) == _soma_por_plano(ref_rec)
    por_produto = {r["produto_id"]: r["jan"] for r in got_rec}
    assert por_produto == {1: 100.0, 2: 40.0}


def test_ordenar_versoes_orçamento_depois_forecasts():
    versoes = [
        {"id": "FC_Forecast - 8+4", "descricao": "Forecast - 8+4"},
        {"id": "OC_Orçamento Vendas 2026", "descricao": "Orçamento"},
        {"id": "OC_1ª versão", "descricao": "Orçamento"},
        {"id": "FC_Forecast - 1+11", "descricao": "Forecast - 1+11"},
    ]
    out = ordenar_e_dedupar_labels_versao(versoes)
    assert [v["descricao"] for v in out] == ["Orçamento", "Forecast - 1+11", "Forecast - 8+4"]
    assert out[0]["id"] == "OC_1ª versão"


def test_dedupe_carga_inicial_sienge_vira_orcamento_unico():
    """Cópia 'Orçamento' e 'Carga Inicial Sienge' não devem aparecer juntas no dropdown."""
    from app.services.budget_shared import format_visualizacao_versao_label, ordenar_e_dedupar_labels_versao

    versoes = [
        {
            "id": "OC_Orçamento",
            "descricao": format_visualizacao_versao_label("Orçamento", kind="orcamento"),
        },
        {
            "id": "OC_Carga Inicial Sienge 2026",
            "descricao": format_visualizacao_versao_label("Carga Inicial Sienge 2026", kind="orcamento"),
        },
        {
            "id": "FC_Forecast - 8+4",
            "descricao": format_visualizacao_versao_label("Forecast - 8+4", kind="forecast"),
        },
    ]
    out = ordenar_e_dedupar_labels_versao(versoes)
    assert [v["descricao"] for v in out] == ["Orçamento", "Forecast - 8+4"]
    assert out[0]["id"] == "OC_Carga Inicial Sienge 2026"


def test_build_empresas_map_usa_id_sienge():
    from app.services.budget_shared import build_empresas_map, build_opcoes_produtos

    companies = [
        SimpleNamespace(id=100, id_sienge="12", nome_fantasia="Ellenco", razao_social="Ellenco SA"),
        SimpleNamespace(id=101, id_sienge="1", nome_fantasia="MLDU", razao_social="ML"),
    ]

    class _Q:
        def __init__(self, items):
            self._items = items

        def all(self):
            return self._items

    class _Db:
        def query(self, _model):
            return _Q(companies)

    empresas_map = build_empresas_map(_Db())  # type: ignore[arg-type]
    assert empresas_map["12"] == "Ellenco"
    assert empresas_map["1"] == "MLDU"

    produto = SimpleNamespace(
        id=1,
        nome="CC Teste",
        id_sienge="501",
        custom_data={"__id_empresa": "12", "__nome_empresa": "Nome cache Sienge desatualizado"},
    )
    opcoes = build_opcoes_produtos([produto], empresas_map)
    assert opcoes[0]["id_empresa"] == "12"
    assert opcoes[0]["nome_empresa"] == "Ellenco"


def test_filter_itens_por_empresa_ids_recorta_pelo_id_do_cadastro():
    from app.services.budget_shared import filter_itens_por_empresa_ids

    opcoes = [
        {"id": 10, "id_empresa": "12"},
        {"id": 20, "id_empresa": "1"},
    ]
    itens = [
        {"produto_id": 10, "orcado": {"total": 100}},
        {"produto_id": 20, "orcado": {"total": 50}},
    ]
    filtrado = filter_itens_por_empresa_ids(itens, opcoes, ["12"])
    assert [i["produto_id"] for i in filtrado] == [10]


def test_filter_itens_por_empresa_ids_sem_match_devolve_lista_vazia():
    from app.services.budget_shared import filter_itens_por_empresa_ids

    opcoes = [{"id": 10, "id_empresa": "12"}]
    itens = [{"produto_id": 10}]
    assert filter_itens_por_empresa_ids(itens, opcoes, ["1"]) == []


def test_filter_itens_por_empresa_ids_vazio_nao_recorta():
    from app.services.budget_shared import filter_itens_por_empresa_ids

    itens = [{"produto_id": 10}]
    assert filter_itens_por_empresa_ids(itens, [{"id": 10, "id_empresa": "12"}], []) is itens
    assert filter_itens_por_empresa_ids(itens, [{"id": 10, "id_empresa": "12"}], None) is itens


def test_merge_opcoes_produtos_ignora_lista_vazia_e_nao_dict():
    from app.services.budget_shared import merge_opcoes_produtos

    merged = merge_opcoes_produtos(
        None,
        [{"id": 1, "id_empresa": "12"}],
        [{"id": 1, "id_empresa": "99"}],
        ["nao-dict"],
    )
    assert len(merged) == 1
    assert merged[0]["id"] == 1
    assert merged[0]["id_empresa"] == "99"


def test_dashboard_executivo_expõe_helpers_de_agregacao():
    """Regressão: a rota quebrava com NameError ao montar o resumo."""
    from app.api.routes import dashboard

    assert callable(dashboard.sumarizar_serie_mensal)
    assert callable(dashboard.agregar_serie_vendas_liquido)
    assert callable(dashboard.calcular_ranking_desvios)
    assert callable(dashboard.calculo_variacao_rs)
    assert callable(dashboard.calculo_variacao_perc)
