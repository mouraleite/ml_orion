"""Mês fechado no forecast = realizado do Sienge (decisão de 11/11/2026).

"Forecast - 7+5" quer dizer 7 meses realizados + 5 previstos. Antes, num mês fechado,
o forecast mantinha o valor da versão base (orçado ou forecast anterior); agora mostra
e grava o realizado (o mesmo que o Acompanhamento mostra como realizado).

Fechado = tabela da tela Fechamento (regra oficial). Convenção do forecast: planos
redutores ficam positivos na grade (o Acompanhamento inverte o sinal na exibição).
"""
from collections import defaultdict
from typing import Dict, Iterable, Optional, Tuple

from sqlalchemy.orm import Session

from app.services.periodos import MESES_STR
from app.services.realizado_sienge import (
    agregar_realizado_despesas_sienge,
    agregar_realizado_receitas_sienge,
    build_planos_maps,
)

Chave = Tuple[int, int]


def realizado_por_linha(
    db: Session,
    ano: int,
    tipo: str,
    produtos_ids: Iterable[int],
    planos_ids: Iterable[int],
    dept=None,
) -> Dict[Chave, Dict[str, float]]:
    """{(produto_id, plano_id): {mes_str: valor}} do realizado do ano, na convenção do forecast."""
    produtos = [p for p in produtos_ids if p]
    planos = [p for p in planos_ids if p]
    if not produtos or not planos:
        return {}
    matriz: dict = {}

    def init_key(cc_id, plano_id):
        if (cc_id, plano_id) not in matriz:
            matriz[(cc_id, plano_id)] = {"realizado": defaultdict(float)}

    if tipo == "DESPESAS":
        agregar_realizado_despesas_sienge(matriz, init_key, db, ano, produtos, planos, dept=dept, agrupado=True)
    else:
        agregar_realizado_receitas_sienge(matriz, init_key, db, ano, produtos, planos, agrupado=True)
    _, redutora = build_planos_maps(db)
    out: Dict[Chave, Dict[str, float]] = {}
    for (cc_id, plano_id), v in matriz.items():
        red = str(redutora.get(plano_id)).strip().upper() == "S"
        out[(cc_id, plano_id)] = {
            m: round(abs(val) if red else float(val), 2) for m, val in v["realizado"].items()
        }
    return out


def aplicar_realizado_nos_fechados(
    itens: list,
    realizado: Dict[Chave, Dict[str, float]],
    meses_fechados: Iterable[int],
    incluir_linhas_novas: bool = True,
) -> list:
    """Sobrescreve os meses fechados das linhas (dicts serializados) com o realizado.

    Linhas com realizado num mês fechado que ainda não estão no forecast entram como
    linhas novas (sem id), para o total "N realizados + M previstos" fechar.
    """
    fechados = [MESES_STR[m - 1] for m in sorted(set(meses_fechados)) if 1 <= m <= 12]
    if not fechados:
        return itens
    vistos = set()
    for row in itens:
        chave = (row.get("produto_id"), row.get("plano_financeiro_id"))
        vistos.add(chave)
        real = realizado.get(chave, {})
        for m in fechados:
            row[m] = real.get(m, 0.0)
        row["total_anual"] = round(sum(float(row.get(m) or 0.0) for m in MESES_STR), 2)
    if incluir_linhas_novas:
        for chave, real in sorted(realizado.items()):
            if chave in vistos or not any(abs(real.get(m, 0.0)) > 0.004 for m in fechados):
                continue
            row = {"produto_id": chave[0], "plano_financeiro_id": chave[1], "observacao": "Realizado Sienge"}
            for m in MESES_STR:
                row[m] = real.get(m, 0.0) if m in fechados else 0.0
            row["total_anual"] = round(sum(row[m] for m in MESES_STR), 2)
            itens.append(row)
    return itens


def valor_mes_fechado(realizado: Dict[Chave, Dict[str, float]], produto_id: int, plano_id: int, mes_str: str) -> float:
    return float(realizado.get((produto_id, plano_id), {}).get(mes_str, 0.0))


def corte_por_fechamento(db: Session, ano: int, hoje=None) -> Optional[int]:
    """Último mês fechado em sequência desde janeiro pela tabela de Fechamento; None sem fechamento no ano."""
    from app.services.periodos import meses_fechados_do_ano

    fechados = set(meses_fechados_do_ano(db, ano))
    if not fechados:
        return None
    n = 0
    while n + 1 in fechados and n < 12:
        n += 1
    return n
