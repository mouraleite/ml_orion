def calculo_variacao_rs(atual: float, comparado: float) -> float:
    return atual - comparado

def calculo_variacao_perc(atual: float, comparado: float) -> float:
    if comparado == 0:
        return 1.0 if atual > 0 else (0.0 if atual == 0 else -1.0)
    return (atual - comparado) / comparado

def calculo_saldo_despesas(valor_referencia: float, realizado: float) -> float:
    return valor_referencia - realizado

def calcular_ranking_desvios(itens: list, modo: str = "orcado", top_n: int = 10) -> list:
    """
    Recebe a lista de itens de acompanhamento (despesas ou receitas)
    e retorna os top_n itens com maior desvio absoluto entre realizado e referência.
    modo: 'orcado' ou 'forecast'
    """
    ranking = []
    for item in itens:
        ref_total = item.get(modo, {}).get("total", 0.0) or 0.0
        real_total = item.get("realizado", {}).get("total", 0.0) or 0.0
        var_rs = calculo_variacao_rs(real_total, ref_total)
        var_perc = calculo_variacao_perc(real_total, ref_total)
        ranking.append({
            "produto_id": item.get("produto_id"),
            "plano_financeiro_id": item.get("plano_financeiro_id"),
            "plano_venda_id": item.get("plano_venda_id"),
            "referencia": ref_total,
            "realizado": real_total,
            "variacao_rs": var_rs,
            "variacao_perc": var_perc,
            "variacao_abs": abs(var_rs),
        })
    ranking.sort(key=lambda x: x["variacao_abs"], reverse=True)
    return ranking[:top_n]

def sumarizar_serie_mensal(itens: list, campo_ref: str) -> dict:
    """
    Agrega a lista de itens num totalizador mensal.
    Retorna dict com chaves jan..dez + total para orcado, forecast e realizado.
    """
    MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    serie = {
        "orcado":    {m: 0.0 for m in MESES + ["total"]},
        "forecast":  {m: 0.0 for m in MESES + ["total"]},
        "realizado": {m: 0.0 for m in MESES + ["total"]},
    }
    for item in itens:
        for tp in ["orcado", "forecast", "realizado"]:
            for m in MESES + ["total"]:
                val = item.get(tp, {})
                if isinstance(val, dict):
                    serie[tp][m] += val.get(m, 0.0) or 0.0
    return serie


MESES_VENDAS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def agregar_serie_vendas_liquido(vend_itens: list) -> dict:
    """
    Agrega itens de get_acompanhamento_vendas em VGV e unidades líquidos (vendas − distratos).
    Estrutura de cada item: { vendas: { orcado|forecast|realizado: { mes: {vgv, unidades} } }, distratos: {...} }
    """
    serie = {
        tp: {m: {"vgv": 0.0, "unidades": 0} for m in MESES_VENDAS}
        for tp in ("orcado", "forecast", "realizado")
    }
    for item in vend_itens or []:
        for tp in ("orcado", "forecast", "realizado"):
            vendas_tp = (item.get("vendas") or {}).get(tp) or {}
            dist_tp = (item.get("distratos") or {}).get(tp) or {}
            for m in MESES_VENDAS:
                vb = vendas_tp.get(m) if isinstance(vendas_tp, dict) else {}
                db = dist_tp.get(m) if isinstance(dist_tp, dict) else {}
                if not isinstance(vb, dict):
                    vb = {}
                if not isinstance(db, dict):
                    db = {}
                serie[tp][m]["vgv"] += float(vb.get("vgv") or 0) - float(db.get("vgv") or 0)
                serie[tp][m]["unidades"] += int(vb.get("unidades") or 0) - int(db.get("unidades") or 0)
    return serie

