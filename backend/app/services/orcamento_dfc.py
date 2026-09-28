"""Agrupa orçado/realizado já calculados na árvore da Visão DFC.

Não recalcula orçamento, forecast nem realizado — só soma, sinal e %.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.services.periodos import MESES_STR

SENTIDO_ENTRADA = "entrada"
SENTIDO_SAIDA = "saida"

_ZERO = 1e-12


def ratio_ah(atual: float, base: float) -> Optional[float]:
    """(atual − base) / |base|. Sem base → None (a tela mostra —)."""
    if abs(base) < _ZERO:
        return None
    return (atual - base) / abs(base)


def ratio_av(linha: float, ancora: float) -> Optional[float]:
    """linha ÷ total de entradas. Sem âncora → None."""
    if abs(ancora) < _ZERO:
        return None
    return linha / ancora


def _empty_meses() -> Dict[str, float]:
    return {m: 0.0 for m in MESES_STR}


def _add_meses(a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
    return {m: float(a.get(m, 0.0) or 0.0) + float(b.get(m, 0.0) or 0.0) for m in MESES_STR}


def _signed(series: Dict[str, float], sentido: str) -> Dict[str, float]:
    sign = 1.0 if sentido == SENTIDO_ENTRADA else -1.0
    return {m: float(series.get(m, 0.0) or 0.0) * sign for m in MESES_STR}


def _soma(series: Dict[str, float], meses: Optional[Iterable[str]]) -> float:
    keys = list(meses) if meses else list(MESES_STR)
    return sum(float(series.get(m, 0.0) or 0.0) for m in keys if m in MESES_STR)


def _by_plan(itens: List[dict]) -> Dict[int, Dict[str, Dict[str, float]]]:
    out: Dict[int, Dict[str, Dict[str, float]]] = {}
    for item in itens or []:
        pid = item.get("plano_financeiro_id")
        if pid is None:
            continue
        bucket = out.setdefault(
            pid,
            {"orcado": _empty_meses(), "realizado": _empty_meses(), "forecast": _empty_meses()},
        )
        for serie in ("orcado", "realizado", "forecast"):
            src = item.get(serie) or {}
            for m in MESES_STR:
                bucket[serie][m] += float(src.get(m, 0.0) or 0.0)
    return out


def _blank_amounts() -> Dict[str, Any]:
    return {
        "meses": _empty_meses(),
        "meses_n1": _empty_meses(),
        "meses_orcado": _empty_meses(),
        "meses_forecast": _empty_meses(),
        "total": 0.0,
        "total_n1": 0.0,
        "total_orcado": 0.0,
        "total_forecast": 0.0,
        "ah": None,
        "av": None,
    }


def _attach_ratios(row: Dict[str, Any], ancora: float) -> None:
    row["ah"] = ratio_ah(row["total"], row["total_n1"])
    row["av"] = ratio_av(row["total"], ancora)


def _attach_ratios_meses(row: Dict[str, Any], ancora_meses: Dict[str, float]) -> None:
    row["meses_ah"] = {m: ratio_ah(row["meses"][m], row["meses_n1"][m]) for m in MESES_STR}
    row["meses_av"] = {m: ratio_av(row["meses"][m], ancora_meses[m]) for m in MESES_STR}


def par_ids_forecast_dfc(
    forecast_id: Optional[int],
    escolhido: Optional[Dict[str, Any]],
    pares: List[Dict[str, Any]],
    dept_id: Optional[int] = None,
) -> Tuple[Optional[int], Optional[int]]:
    """Devolve (id_despesas, id_receitas) da mesma descrição da versão escolhida.

    O acompanhamento só carrega forecast se o id for do próprio tipo. No DFC a
    lista pode vir de Vendas (7+5) — o par Despesas/Receitas Importado Sienge
    compartilha a descrição e precisa ser resolvido aqui, sem alterar o acompanhamento.
    """
    if not forecast_id:
        return None, None
    descricao = (escolhido or {}).get("descricao")
    dept_escolhido = (escolhido or {}).get("departamento_id")
    if not descricao:
        return forecast_id, forecast_id

    def pick(tipo: str) -> Optional[int]:
        same = [
            p
            for p in pares
            if (p.get("tipo") or "") == tipo and p.get("descricao") == descricao
        ]
        if not same:
            if (escolhido or {}).get("tipo") == tipo:
                return forecast_id
            return None

        def rank(p: Dict[str, Any]) -> Tuple[int, int, int]:
            dept = p.get("departamento_id")
            prefer_escolhido = 0 if dept_escolhido is not None and dept == dept_escolhido else 1
            prefer_ativo = 0 if dept_id is not None and dept == dept_id else 1
            return (prefer_escolhido, prefer_ativo, -(int(p.get("id") or 0)))

        return sorted(same, key=rank)[0].get("id")

    return pick("DESPESAS"), pick("RECEITAS")


def montar_dfc(
    nodes: List[dict],
    rec_n: List[dict],
    desp_n: List[dict],
    rec_n1: List[dict],
    desp_n1: List[dict],
    meses: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Monta a árvore DFC. Planos fora da visão são ignorados."""
    rec_n_map = _by_plan(rec_n)
    desp_n_map = _by_plan(desp_n)
    rec_n1_map = _by_plan(rec_n1)
    desp_n1_map = _by_plan(desp_n1)

    mapped_ids = set()
    linhas: List[Dict[str, Any]] = []
    by_id: Dict[int, Dict[str, Any]] = {}

    for node in nodes or []:
        row = {
            "kind": "categoria",
            "id": node.get("id"),
            "codigo": node.get("codigo") or "",
            "descricao": node.get("descricao") or "",
            "sentido": None,
            "planos": [],
            **_blank_amounts(),
        }
        for plano in node.get("planos") or []:
            pid = plano.get("id")
            if pid is None:
                continue
            mapped_ids.add(pid)
            is_entrada = pid in rec_n_map or pid in rec_n1_map
            is_saida = pid in desp_n_map or pid in desp_n1_map
            if is_entrada and not is_saida:
                sentido = SENTIDO_ENTRADA
            elif is_saida and not is_entrada:
                sentido = SENTIDO_SAIDA
            elif is_entrada and is_saida:
                sentido = SENTIDO_SAIDA
            else:
                sentido = SENTIDO_ENTRADA

            meses_n = _empty_meses()
            meses_n1 = _empty_meses()
            meses_orc = _empty_meses()
            meses_fc = _empty_meses()
            if pid in rec_n_map:
                meses_n = _add_meses(meses_n, _signed(rec_n_map[pid]["realizado"], SENTIDO_ENTRADA))
                meses_orc = _add_meses(meses_orc, _signed(rec_n_map[pid]["orcado"], SENTIDO_ENTRADA))
                meses_fc = _add_meses(meses_fc, _signed(rec_n_map[pid]["forecast"], SENTIDO_ENTRADA))
            if pid in desp_n_map:
                meses_n = _add_meses(meses_n, _signed(desp_n_map[pid]["realizado"], SENTIDO_SAIDA))
                meses_orc = _add_meses(meses_orc, _signed(desp_n_map[pid]["orcado"], SENTIDO_SAIDA))
                meses_fc = _add_meses(meses_fc, _signed(desp_n_map[pid]["forecast"], SENTIDO_SAIDA))
            if pid in rec_n1_map:
                meses_n1 = _add_meses(meses_n1, _signed(rec_n1_map[pid]["realizado"], SENTIDO_ENTRADA))
            if pid in desp_n1_map:
                meses_n1 = _add_meses(meses_n1, _signed(desp_n1_map[pid]["realizado"], SENTIDO_SAIDA))

            plano_row = {
                "kind": "plano",
                "id": pid,
                "codigo": plano.get("db_id") or "",
                "descricao": plano.get("name") or "",
                "sentido": sentido,
                "meses": meses_n,
                "meses_n1": meses_n1,
                "meses_orcado": meses_orc,
                "meses_forecast": meses_fc,
                "total": _soma(meses_n, meses),
                "total_n1": _soma(meses_n1, meses),
                "total_orcado": _soma(meses_orc, meses),
                "total_forecast": _soma(meses_fc, meses),
                "ah": None,
                "av": None,
            }
            row["planos"].append(plano_row)
            row["meses"] = _add_meses(row["meses"], meses_n)
            row["meses_n1"] = _add_meses(row["meses_n1"], meses_n1)
            row["meses_orcado"] = _add_meses(row["meses_orcado"], meses_orc)
            row["meses_forecast"] = _add_meses(row["meses_forecast"], meses_fc)

        row["planos"].sort(key=lambda p: ((p.get("descricao") or ""), p.get("id") or 0))
        linhas.append(row)
        by_id[row["id"]] = row

    linhas.sort(key=lambda r: r["codigo"] or "")

    # Pais recebem filhos (código com prefixo "01" ← "01.01"), do mais fundo ao raso.
    ordered = sorted(linhas, key=lambda r: r["codigo"].count("."), reverse=True)
    for child in ordered:
        parent = None
        best = -1
        for cand in linhas:
            if cand["id"] == child["id"]:
                continue
            codigo = cand["codigo"]
            if codigo and child["codigo"].startswith(codigo + ".") and len(codigo) > best:
                parent = cand
                best = len(codigo)
        if not parent:
            continue
        parent["meses"] = _add_meses(parent["meses"], child["meses"])
        parent["meses_n1"] = _add_meses(parent["meses_n1"], child["meses_n1"])
        parent["meses_orcado"] = _add_meses(parent["meses_orcado"], child["meses_orcado"])
        parent["meses_forecast"] = _add_meses(parent["meses_forecast"], child["meses_forecast"])

    for row in linhas:
        row["total"] = _soma(row["meses"], meses)
        row["total_n1"] = _soma(row["meses_n1"], meses)
        row["total_orcado"] = _soma(row["meses_orcado"], meses)
        row["total_forecast"] = _soma(row["meses_forecast"], meses)

    total_entradas = 0.0
    total_entradas_meses = _empty_meses()
    for pid, data in rec_n_map.items():
        if pid not in mapped_ids:
            continue
        signed = _signed(data["realizado"], SENTIDO_ENTRADA)
        total_entradas += _soma(signed, meses)
        total_entradas_meses = _add_meses(total_entradas_meses, signed)

    for row in linhas:
        _attach_ratios(row, total_entradas)
        _attach_ratios_meses(row, total_entradas_meses)
        for plano in row["planos"]:
            _attach_ratios(plano, total_entradas)
            _attach_ratios_meses(plano, total_entradas_meses)

    liquido = sum(r["total"] for r in linhas if r["codigo"].count(".") == 0)
    liquido_n1 = sum(r["total_n1"] for r in linhas if r["codigo"].count(".") == 0)
    liquido_orcado = sum(r["total_orcado"] for r in linhas if r["codigo"].count(".") == 0)
    liquido_forecast = sum(r["total_forecast"] for r in linhas if r["codigo"].count(".") == 0)

    return {
        "linhas": linhas,
        "total_entradas": total_entradas,
        "total_entradas_meses": total_entradas_meses,
        "liquido": liquido,
        "liquido_n1": liquido_n1,
        "liquido_orcado": liquido_orcado,
        "liquido_forecast": liquido_forecast,
        "ah_liquido": ratio_ah(liquido, liquido_n1),
        "av_liquido": ratio_av(liquido, total_entradas),
    }


def _agregar_visualizacao_por_plano(itens: List[dict]) -> Dict[int, Dict[str, float]]:
    """Soma linhas produto×plano da visualização em série mensal por plano."""
    out: Dict[int, Dict[str, float]] = {}
    for item in itens or []:
        pid = item.get("plano_financeiro_id")
        if pid is None:
            continue
        bucket = out.setdefault(pid, _empty_meses())
        for m in MESES_STR:
            bucket[m] += float(item.get(m, 0.0) or 0.0)
    return out


def montar_dfc_comparativo(
    nodes: List[dict],
    rec_a: List[dict],
    desp_a: List[dict],
    rec_b: List[dict],
    desp_b: List[dict],
    meses: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Árvore DFC comparando duas versões (mesma Visão). Não recalcula orçado/forecast."""
    rec_a_map = _agregar_visualizacao_por_plano(rec_a)
    desp_a_map = _agregar_visualizacao_por_plano(desp_a)
    rec_b_map = _agregar_visualizacao_por_plano(rec_b)
    desp_b_map = _agregar_visualizacao_por_plano(desp_b)

    mapped_ids = set()
    linhas: List[Dict[str, Any]] = []

    for node in nodes or []:
        row = {
            "kind": "categoria",
            "id": node.get("id"),
            "codigo": node.get("codigo") or "",
            "descricao": node.get("descricao") or "",
            "sentido": None,
            "planos": [],
            "meses_a": _empty_meses(),
            "meses_b": _empty_meses(),
            "meses_var": _empty_meses(),
            "total_a": 0.0,
            "total_b": 0.0,
            "var_rs": 0.0,
            "var_perc": None,
        }
        for plano in node.get("planos") or []:
            pid = plano.get("id")
            if pid is None:
                continue
            mapped_ids.add(pid)
            is_entrada = pid in rec_a_map or pid in rec_b_map
            is_saida = pid in desp_a_map or pid in desp_b_map
            if is_entrada and not is_saida:
                sentido = SENTIDO_ENTRADA
            elif is_saida and not is_entrada:
                sentido = SENTIDO_SAIDA
            elif is_entrada and is_saida:
                sentido = SENTIDO_SAIDA
            else:
                sentido = SENTIDO_ENTRADA

            meses_a = _empty_meses()
            meses_b = _empty_meses()
            if pid in rec_a_map:
                meses_a = _add_meses(meses_a, _signed(rec_a_map[pid], SENTIDO_ENTRADA))
            if pid in desp_a_map:
                meses_a = _add_meses(meses_a, _signed(desp_a_map[pid], SENTIDO_SAIDA))
            if pid in rec_b_map:
                meses_b = _add_meses(meses_b, _signed(rec_b_map[pid], SENTIDO_ENTRADA))
            if pid in desp_b_map:
                meses_b = _add_meses(meses_b, _signed(desp_b_map[pid], SENTIDO_SAIDA))

            meses_var = {m: meses_b[m] - meses_a[m] for m in MESES_STR}
            total_a = _soma(meses_a, meses)
            total_b = _soma(meses_b, meses)
            var_rs = total_b - total_a
            plano_row = {
                "kind": "plano",
                "id": pid,
                "codigo": plano.get("db_id") or "",
                "descricao": plano.get("name") or "",
                "sentido": sentido,
                "meses_a": meses_a,
                "meses_b": meses_b,
                "meses_var": meses_var,
                "total_a": total_a,
                "total_b": total_b,
                "var_rs": var_rs,
                "var_perc": ratio_ah(total_b, total_a),
            }
            row["planos"].append(plano_row)
            row["meses_a"] = _add_meses(row["meses_a"], meses_a)
            row["meses_b"] = _add_meses(row["meses_b"], meses_b)

        row["planos"].sort(key=lambda p: ((p.get("descricao") or ""), p.get("id") or 0))
        linhas.append(row)

    linhas.sort(key=lambda r: r["codigo"] or "")

    ordered = sorted(linhas, key=lambda r: r["codigo"].count("."), reverse=True)
    for child in ordered:
        parent = None
        best = -1
        for cand in linhas:
            if cand["id"] == child["id"]:
                continue
            codigo = cand["codigo"]
            if codigo and child["codigo"].startswith(codigo + ".") and len(codigo) > best:
                parent = cand
                best = len(codigo)
        if not parent:
            continue
        parent["meses_a"] = _add_meses(parent["meses_a"], child["meses_a"])
        parent["meses_b"] = _add_meses(parent["meses_b"], child["meses_b"])

    for row in linhas:
        row["meses_var"] = {m: row["meses_b"][m] - row["meses_a"][m] for m in MESES_STR}
        row["total_a"] = _soma(row["meses_a"], meses)
        row["total_b"] = _soma(row["meses_b"], meses)
        row["var_rs"] = row["total_b"] - row["total_a"]
        row["var_perc"] = ratio_ah(row["total_b"], row["total_a"])
        for plano in row["planos"]:
            plano["var_perc"] = ratio_ah(plano["total_b"], plano["total_a"])

    total_entradas_a = 0.0
    for pid, data in rec_a_map.items():
        if pid not in mapped_ids:
            continue
        total_entradas_a += _soma(_signed(data, SENTIDO_ENTRADA), meses)

    liquido_a = sum(r["total_a"] for r in linhas if r["codigo"].count(".") == 0)
    liquido_b = sum(r["total_b"] for r in linhas if r["codigo"].count(".") == 0)

    return {
        "linhas": linhas,
        "total_entradas_a": total_entradas_a,
        "liquido_a": liquido_a,
        "liquido_b": liquido_b,
        "var_liquido": liquido_b - liquido_a,
        "var_liquido_perc": ratio_ah(liquido_b, liquido_a),
    }
