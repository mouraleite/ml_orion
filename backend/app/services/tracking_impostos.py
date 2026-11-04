"""Tributos do estoque no acompanhamento: Lucro Presumido do Apoio, no prazo da DARF.

Lê as alíquotas no cadastro a cada cálculo. Não congela percentual.
PIS/COFINS (e outros): mês seguinte ao recebimento.
IRPJ/CSLL: mês seguinte ao fechamento do trimestre civil (abr/jul/out/jan).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from sqlalchemy.orm import Session

NOME_REGIME_ACOMPANHAMENTO = "Lucro Presumido"


def aliquotas_lucro_presumido(db: Session | None) -> dict[str, float]:
    """Alíquotas vigentes no Apoio. Vazio se o regime não existir."""
    if db is None:
        return {}
    from sqlalchemy import inspect as sa_inspect
    from app.models.tax_regime import TaxRegime

    bind = db.get_bind()
    if bind is not None and not sa_inspect(bind).has_table("tax_regimes"):
        return {}

    regime = (
        db.query(TaxRegime)
        .filter(TaxRegime.nome == NOME_REGIME_ACOMPANHAMENTO)
        .order_by(TaxRegime.id)
        .first()
    )
    if regime is None:
        return {}
    if regime.ativo is False:
        return {}
    return {
        "pis": float(regime.pis or 0),
        "cofins": float(regime.cofins or 0),
        "irpj": float(regime.irpj or 0),
        "csll": float(regime.csll or 0),
        "outros": float(regime.outros or 0),
    }


def _avanca_mes(ano: int, mes: int, n: int = 1) -> tuple[int, int]:
    mes += n
    while mes > 12:
        mes -= 12
        ano += 1
    return ano, mes


def mes_darf_pis_cofins(ano: int, mes: int) -> tuple[int, int]:
    """DARF PIS/COFINS: mês seguinte ao recebimento."""
    return _avanca_mes(ano, mes, 1)


def mes_darf_irpj_csll(ano: int, mes: int) -> tuple[int, int]:
    """DARF IRPJ/CSLL trimestral: mês seguinte ao fechamento do trimestre."""
    if mes <= 3:
        return ano, 4
    if mes <= 6:
        return ano, 7
    if mes <= 9:
        return ano, 10
    return ano + 1, 1


def _chave(ano: int, mes: int) -> str:
    return f"{ano:04d}-{mes:02d}"


def projetar_tributos_presumido(
    recebimentos_por_mes: Mapping[str, float],
    aliquotas: Mapping[str, Any],
) -> dict[str, float]:
    """Caixa de tributo por mês, só sobre os recebimentos projetados do estoque."""
    if not recebimentos_por_mes or not aliquotas:
        return {}
    pis_cofins = (float(aliquotas.get("pis") or 0) + float(aliquotas.get("cofins") or 0) + float(aliquotas.get("outros") or 0)) / 100.0
    irpj_csll = (float(aliquotas.get("irpj") or 0) + float(aliquotas.get("csll") or 0)) / 100.0
    if pis_cofins <= 0 and irpj_csll <= 0:
        return {}
    saida: dict[str, float] = defaultdict(float)
    for mes_raw, valor in recebimentos_por_mes.items():
        rec = float(valor or 0)
        if rec <= 0 or not mes_raw or mes_raw == "N/A" or len(mes_raw) < 7:
            continue
        try:
            ano = int(mes_raw[:4])
            mes = int(mes_raw[5:7])
        except (TypeError, ValueError):
            continue
        if not (1 <= mes <= 12):
            continue
        if pis_cofins > 0:
            a, m = mes_darf_pis_cofins(ano, mes)
            saida[_chave(a, m)] += rec * pis_cofins
        if irpj_csll > 0:
            a, m = mes_darf_irpj_csll(ano, mes)
            saida[_chave(a, m)] += rec * irpj_csll
    return {k: v for k, v in saida.items() if abs(v) > 1e-9}


def lancar_tributos_no_fluxo(
    tributos_por_mes: Mapping[str, float],
    anual_cf_fcst: dict,
    monthly_net_cf_fcst: dict,
) -> float:
    """Lança a saída no fluxo previsto. Devolve o total para somar em impostos da DRE."""
    total = 0.0
    for mes, val in tributos_por_mes.items():
        v = float(val or 0)
        if v <= 0:
            continue
        total += v
        monthly_net_cf_fcst[mes] = float(monthly_net_cf_fcst.get(mes) or 0) - v
        ano = mes[:4]
        linha = anual_cf_fcst[ano]
        linha["Tributos"] = float(linha.get("Tributos") or 0) + v
        linha["Saidas"] = float(linha.get("Saidas") or 0) + v
    return total
