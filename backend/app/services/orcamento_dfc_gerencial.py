"""DFC gerencial: mesmos números do DFC, fatiados por empresa e centro de custo.

Não recalcula orçado/realizado/forecast. Cheio e MLDU vêm prontos; N-1 é só realizado.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.services.orcamento_dfc import (
    MESES_STR,
    SENTIDO_ENTRADA,
    SENTIDO_SAIDA,
    _add_meses,
    _empty_meses,
    _signed,
    _soma,
    ratio_ah,
    ratio_av,
)

AGRUPAMENTO_VISAO = "visao"
AGRUPAMENTO_CENTRO = "centro"

_SERIES = (
    "real",
    "real_mldu",
    "n1",
    "n1_mldu",
    "orcado",
    "orcado_mldu",
    "forecast",
    "forecast_mldu",
)


def _empty_amounts() -> Dict[str, Dict[str, float]]:
    return {k: _empty_meses() for k in _SERIES}


def _add_amounts(a: Dict[str, Dict[str, float]], b: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    return {k: _add_meses(a.get(k) or _empty_meses(), b.get(k) or _empty_meses()) for k in _SERIES}


def _by_prod_plan(itens: List[dict]) -> Dict[Tuple[Any, Any], Dict[str, Dict[str, float]]]:
    out: Dict[Tuple[Any, Any], Dict[str, Dict[str, float]]] = {}
    for item in itens or []:
        pid = item.get("plano_financeiro_id")
        prod = item.get("produto_id")
        if pid is None or prod is None:
            continue
        key = (prod, pid)
        bucket = out.setdefault(
            key,
            {"orcado": _empty_meses(), "realizado": _empty_meses(), "forecast": _empty_meses()},
        )
        for serie in ("orcado", "realizado", "forecast"):
            src = item.get(serie) or {}
            for m in MESES_STR:
                bucket[serie][m] += float(src.get(m, 0.0) or 0.0)
    return out


_MAPA_PRODUTOS: Tuple[Any, Dict[Any, dict]] = (None, {})


def _mapa_produtos(opcoes_produtos: List[dict]) -> Dict[Any, dict]:
    """id → produto, montado uma vez por lista (antes era refeito a cada linha)."""
    global _MAPA_PRODUTOS
    ref, mapa = _MAPA_PRODUTOS
    if ref is opcoes_produtos:
        return mapa
    mapa = {}
    for p in opcoes_produtos or []:
        if isinstance(p, dict) and p.get("id") is not None:
            mapa[p["id"]] = p
    _MAPA_PRODUTOS = (opcoes_produtos, mapa)
    return mapa


def _produto_meta(opcoes_produtos: List[dict], produto_id: Any) -> Dict[str, Any]:
    p = _mapa_produtos(opcoes_produtos).get(produto_id) or {}
    emp_id = str(p.get("id_empresa") or "").strip() or "_sem"
    emp_nome = str(p.get("nome_empresa") or "").strip() or "Sem empresa"
    cc_nome = str(p.get("nome") or "").strip() or f"CC {produto_id}"
    return {
        "produto_id": produto_id,
        "empresa_id": emp_id,
        "empresa_nome": emp_nome,
        "cc_nome": cc_nome,
    }


def _mix(key, rec_map, desp_map, serie: str) -> Dict[str, float]:
    """Entradas − saídas por mês, numa passada só (mesmo resultado de antes)."""
    rec = rec_map[key][serie] if key in rec_map else None
    desp = desp_map[key][serie] if key in desp_map else None
    if rec is None and desp is None:
        return _empty_meses()
    if desp is None:
        return {m: 0.0 + float(rec.get(m, 0.0) or 0.0) for m in MESES_STR}
    if rec is None:
        return {m: 0.0 - float(desp.get(m, 0.0) or 0.0) for m in MESES_STR}
    # "0.0 +" mantém o zero sem sinal, como na soma original.
    return {m: (0.0 + float(rec.get(m, 0.0) or 0.0)) - float(desp.get(m, 0.0) or 0.0) for m in MESES_STR}


def _leaf_amounts(
    key: Tuple[Any, Any],
    rec_n,
    desp_n,
    rec_n_mldu,
    desp_n_mldu,
    rec_n1,
    desp_n1,
    rec_n1_mldu,
    desp_n1_mldu,
) -> Dict[str, Dict[str, float]]:
    return {
        "real": _mix(key, rec_n, desp_n, "realizado"),
        "real_mldu": _mix(key, rec_n_mldu, desp_n_mldu, "realizado"),
        "n1": _mix(key, rec_n1, desp_n1, "realizado"),
        "n1_mldu": _mix(key, rec_n1_mldu, desp_n1_mldu, "realizado"),
        "orcado": _mix(key, rec_n, desp_n, "orcado"),
        "orcado_mldu": _mix(key, rec_n_mldu, desp_n_mldu, "orcado"),
        "forecast": _mix(key, rec_n, desp_n, "forecast"),
        "forecast_mldu": _mix(key, rec_n_mldu, desp_n_mldu, "forecast"),
    }


def _row(
    *,
    kind: str,
    id: str,
    codigo: str,
    descricao: str,
    amounts: Dict[str, Dict[str, float]],
    meses: Optional[Iterable[str]],
    filhos: Optional[List[dict]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "kind": kind,
        "id": id,
        "codigo": codigo or "",
        "descricao": descricao or "",
        "filhos": filhos or [],
        "meses_real": amounts["real"],
        "meses_real_mldu": amounts["real_mldu"],
        "meses_n1": amounts["n1"],
        "meses_n1_mldu": amounts["n1_mldu"],
        "meses_orcado": amounts["orcado"],
        "meses_orcado_mldu": amounts["orcado_mldu"],
        "meses_forecast": amounts["forecast"],
        "meses_forecast_mldu": amounts["forecast_mldu"],
        "meses": amounts["real"],
        "total_real": _soma(amounts["real"], meses),
        "total_real_mldu": _soma(amounts["real_mldu"], meses),
        "total_n1": _soma(amounts["n1"], meses),
        "total_n1_mldu": _soma(amounts["n1_mldu"], meses),
        "total_orcado": _soma(amounts["orcado"], meses),
        "total_orcado_mldu": _soma(amounts["orcado_mldu"], meses),
        "total_forecast": _soma(amounts["forecast"], meses),
        "total_forecast_mldu": _soma(amounts["forecast_mldu"], meses),
        "ah": None,
        "av": None,
    }
    row["total"] = row["total_real"]
    if extra:
        row.update(extra)
    return row


def _amounts_of(row: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    return {
        "real": row["meses_real"],
        "real_mldu": row["meses_real_mldu"],
        "n1": row["meses_n1"],
        "n1_mldu": row["meses_n1_mldu"],
        "orcado": row["meses_orcado"],
        "orcado_mldu": row["meses_orcado_mldu"],
        "forecast": row["meses_forecast"],
        "forecast_mldu": row["meses_forecast_mldu"],
    }


def _apply_amounts(row: Dict[str, Any], amounts: Dict[str, Dict[str, float]], meses: Optional[Iterable[str]]) -> None:
    row["meses_real"] = amounts["real"]
    row["meses_real_mldu"] = amounts["real_mldu"]
    row["meses_n1"] = amounts["n1"]
    row["meses_n1_mldu"] = amounts["n1_mldu"]
    row["meses_orcado"] = amounts["orcado"]
    row["meses_orcado_mldu"] = amounts["orcado_mldu"]
    row["meses_forecast"] = amounts["forecast"]
    row["meses_forecast_mldu"] = amounts["forecast_mldu"]
    row["meses"] = amounts["real"]
    row["total_real"] = _soma(amounts["real"], meses)
    row["total_real_mldu"] = _soma(amounts["real_mldu"], meses)
    row["total_n1"] = _soma(amounts["n1"], meses)
    row["total_n1_mldu"] = _soma(amounts["n1_mldu"], meses)
    row["total_orcado"] = _soma(amounts["orcado"], meses)
    row["total_orcado_mldu"] = _soma(amounts["orcado_mldu"], meses)
    row["total_forecast"] = _soma(amounts["forecast"], meses)
    row["total_forecast_mldu"] = _soma(amounts["forecast_mldu"], meses)
    row["total"] = row["total_real"]


def _rollup_categorias(linhas: List[Dict[str, Any]], meses: Optional[Iterable[str]]) -> None:
    ordered = sorted(linhas, key=lambda r: (r.get("codigo") or "").count("."), reverse=True)
    for child in ordered:
        parent = None
        best = -1
        child_codigo = child.get("codigo") or ""
        for cand in linhas:
            if cand["id"] == child["id"]:
                continue
            codigo = cand.get("codigo") or ""
            if codigo and child_codigo.startswith(codigo + ".") and len(codigo) > best:
                parent = cand
                best = len(codigo)
        if not parent:
            continue
        _apply_amounts(parent, _add_amounts(_amounts_of(parent), _amounts_of(child)), meses)


def _attach_ratios_tree(rows: List[Dict[str, Any]], ancora: float, ancora_meses: Dict[str, float]) -> None:
    for row in rows:
        row["ah"] = ratio_ah(row["total_real"], row["total_n1"])
        row["av"] = ratio_av(row["total_real"], ancora)
        row["meses_ah"] = {m: ratio_ah(row["meses_real"][m], row["meses_n1"][m]) for m in MESES_STR}
        row["meses_av"] = {m: ratio_av(row["meses_real"][m], ancora_meses[m]) for m in MESES_STR}
        _attach_ratios_tree(row.get("filhos") or [], ancora, ancora_meses)


def _walk_ids(rows: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for row in rows:
        out.append(row["id"])
        out.extend(_walk_ids(row.get("filhos") or []))
    return out


def _montar_visao(
    prefix: str,
    nodes: List[dict],
    plano_centros: Dict[Any, Dict[Any, Dict[str, Any]]],
    meses: Optional[Iterable[str]],
) -> List[Dict[str, Any]]:
    linhas: List[Dict[str, Any]] = []
    for node in nodes or []:
        node_id = node.get("id")
        cat_amounts = _empty_amounts()
        planos_rows: List[Dict[str, Any]] = []
        for plano in node.get("planos") or []:
            pid = plano.get("id")
            if pid is None:
                continue
            centros_src = plano_centros.get(pid) or {}
            if not centros_src:
                continue
            plano_amounts = _empty_amounts()
            centros_rows: List[Dict[str, Any]] = []
            for prod_id, info in sorted(
                centros_src.items(),
                key=lambda kv: ((kv[1].get("cc_nome") or ""), kv[0] or 0),
            ):
                amt = info["amounts"]
                centros_rows.append(
                    _row(
                        kind="centro",
                        id=f"{prefix}|n|{node_id}|p|{pid}|c|{prod_id}",
                        codigo="",
                        descricao=info["cc_nome"],
                        amounts=amt,
                        meses=meses,
                        extra={"produto_id": prod_id},
                    )
                )
                plano_amounts = _add_amounts(plano_amounts, amt)
            planos_rows.append(
                _row(
                    kind="plano",
                    id=f"{prefix}|n|{node_id}|p|{pid}",
                    codigo=plano.get("db_id") or "",
                    descricao=plano.get("name") or "",
                    amounts=plano_amounts,
                    meses=meses,
                    filhos=centros_rows,
                    extra={"plano_financeiro_id": pid},
                )
            )
            cat_amounts = _add_amounts(cat_amounts, plano_amounts)
        planos_rows.sort(key=lambda p: ((p.get("descricao") or ""), p.get("id") or ""))
        linhas.append(
            _row(
                kind="categoria",
                id=f"{prefix}|n|{node_id}",
                codigo=node.get("codigo") or "",
                descricao=node.get("descricao") or "",
                amounts=cat_amounts,
                meses=meses,
                filhos=planos_rows,
            )
        )
    linhas.sort(key=lambda r: r["codigo"] or "")
    _rollup_categorias(linhas, meses)
    return linhas


def _empresa_row(
    emp_id: str,
    emp_nome: str,
    filhos: List[Dict[str, Any]],
    meses: Optional[Iterable[str]],
) -> Dict[str, Any]:
    totals = _empty_amounts()
    for child in filhos:
        if child.get("kind") == "centro":
            totals = _add_amounts(totals, _amounts_of(child))
        elif child.get("kind") == "categoria" and (child.get("codigo") or "").count(".") == 0:
            totals = _add_amounts(totals, _amounts_of(child))
    return _row(
        kind="empresa",
        id=f"e|{emp_id}",
        codigo="" if emp_id == "_sem" else emp_id,
        descricao=emp_nome,
        amounts=totals,
        meses=meses,
        filhos=filhos,
        extra={"empresa_id": emp_id},
    )


def montar_dfc_gerencial(
    nodes: List[dict],
    rec_n: List[dict],
    desp_n: List[dict],
    rec_n_mldu: List[dict],
    desp_n_mldu: List[dict],
    rec_n1: List[dict],
    desp_n1: List[dict],
    rec_n1_mldu: List[dict],
    desp_n1_mldu: List[dict],
    opcoes_produtos: List[dict],
    meses: Optional[Iterable[str]] = None,
    agrupamento: str = AGRUPAMENTO_VISAO,
) -> Dict[str, Any]:
    """Árvore gerencial. Planos fora da visão são ignorados — igual ao DFC."""
    rec_n_map = _by_prod_plan(rec_n)
    desp_n_map = _by_prod_plan(desp_n)
    rec_m_map = _by_prod_plan(rec_n_mldu)
    desp_m_map = _by_prod_plan(desp_n_mldu)
    rec_n1_map = _by_prod_plan(rec_n1)
    desp_n1_map = _by_prod_plan(desp_n1)
    rec_n1m_map = _by_prod_plan(rec_n1_mldu)
    desp_n1m_map = _by_prod_plan(desp_n1_mldu)

    mapped_ids = set()
    for node in nodes or []:
        for plano in node.get("planos") or []:
            pid = plano.get("id")
            if pid is not None:
                mapped_ids.add(pid)

    keys = set()
    for mp in (
        rec_n_map,
        desp_n_map,
        rec_m_map,
        desp_m_map,
        rec_n1_map,
        desp_n1_map,
        rec_n1m_map,
        desp_n1m_map,
    ):
        keys.update(mp.keys())

    # emp -> plano -> produto -> {cc_nome, amounts}
    visao_leaves: Dict[str, Dict[Any, Dict[Any, Dict[str, Any]]]] = {}
    # emp -> produto -> plano -> {cc_nome, empresa_nome, amounts}
    centro_leaves: Dict[str, Dict[Any, Dict[Any, Dict[str, Any]]]] = {}
    empresas_nome: Dict[str, str] = {}
    cc_nome_por_prod: Dict[Any, str] = {}

    for key in keys:
        prod_id, pid = key
        if pid not in mapped_ids:
            continue
        meta = _produto_meta(opcoes_produtos, prod_id)
        emp_id = meta["empresa_id"]
        empresas_nome[emp_id] = meta["empresa_nome"]
        cc_nome_por_prod[prod_id] = meta["cc_nome"]
        amounts = _leaf_amounts(
            key,
            rec_n_map,
            desp_n_map,
            rec_m_map,
            desp_m_map,
            rec_n1_map,
            desp_n1_map,
            rec_n1m_map,
            desp_n1m_map,
        )
        visao_leaves.setdefault(emp_id, {}).setdefault(pid, {})[prod_id] = {
            "cc_nome": meta["cc_nome"],
            "amounts": amounts,
        }
        centro_leaves.setdefault(emp_id, {}).setdefault(prod_id, {})[pid] = {
            "cc_nome": meta["cc_nome"],
            "amounts": amounts,
        }

    modo = AGRUPAMENTO_CENTRO if agrupamento == AGRUPAMENTO_CENTRO else AGRUPAMENTO_VISAO
    empresas: List[Dict[str, Any]] = []

    for emp_id, emp_nome in sorted(empresas_nome.items(), key=lambda kv: (kv[1].lower(), kv[0])):
        prefix = f"e|{emp_id}"
        if modo == AGRUPAMENTO_VISAO:
            filhos = _montar_visao(prefix, nodes, visao_leaves.get(emp_id) or {}, meses)
        else:
            centros_rows: List[Dict[str, Any]] = []
            for prod_id, planos_map in sorted(
                (centro_leaves.get(emp_id) or {}).items(),
                key=lambda kv: ((cc_nome_por_prod.get(kv[0]) or ""), kv[0] or 0),
            ):
                plano_centros: Dict[Any, Dict[Any, Dict[str, Any]]] = {}
                for pid, info in planos_map.items():
                    plano_centros[pid] = {prod_id: info}
                visao = _montar_visao(f"{prefix}|c|{prod_id}", nodes, plano_centros, meses)
                cc_amounts = _empty_amounts()
                for cat in visao:
                    if (cat.get("codigo") or "").count(".") == 0:
                        cc_amounts = _add_amounts(cc_amounts, _amounts_of(cat))
                # No agrupamento por CC o plano já é a folha — tira o centro duplicado.
                for cat in visao:
                    for plano in cat.get("filhos") or []:
                        plano["filhos"] = []
                centros_rows.append(
                    _row(
                        kind="centro",
                        id=f"{prefix}|c|{prod_id}",
                        codigo="",
                        descricao=cc_nome_por_prod.get(prod_id) or f"CC {prod_id}",
                        amounts=cc_amounts,
                        meses=meses,
                        filhos=visao,
                        extra={"produto_id": prod_id},
                    )
                )
            filhos = centros_rows
        empresas.append(_empresa_row(emp_id, emp_nome, filhos, meses))

    total_entradas = 0.0
    total_entradas_meses = _empty_meses()
    for (prod_id, pid), data in rec_n_map.items():
        if pid not in mapped_ids:
            continue
        signed = _signed(data["realizado"], SENTIDO_ENTRADA)
        total_entradas += _soma(signed, meses)
        total_entradas_meses = _add_meses(total_entradas_meses, signed)

    _attach_ratios_tree(empresas, total_entradas, total_entradas_meses)

    liquido = sum(e["total_real"] for e in empresas)
    liquido_n1 = sum(e["total_n1"] for e in empresas)
    liquido_orcado = sum(e["total_orcado"] for e in empresas)
    liquido_forecast = sum(e["total_forecast"] for e in empresas)
    liquido_real_mldu = sum(e["total_real_mldu"] for e in empresas)
    liquido_n1_mldu = sum(e["total_n1_mldu"] for e in empresas)
    liquido_orcado_mldu = sum(e["total_orcado_mldu"] for e in empresas)
    liquido_forecast_mldu = sum(e["total_forecast_mldu"] for e in empresas)

    return {
        "empresas": empresas,
        "agrupamento": modo,
        "total_entradas": total_entradas,
        "total_entradas_meses": total_entradas_meses,
        "liquido": liquido,
        "liquido_n1": liquido_n1,
        "liquido_orcado": liquido_orcado,
        "liquido_forecast": liquido_forecast,
        "liquido_real_mldu": liquido_real_mldu,
        "liquido_n1_mldu": liquido_n1_mldu,
        "liquido_orcado_mldu": liquido_orcado_mldu,
        "liquido_forecast_mldu": liquido_forecast_mldu,
        "ah_liquido": ratio_ah(liquido, liquido_n1),
        "av_liquido": ratio_av(liquido, total_entradas),
        "ids_expansao": _walk_ids(empresas),
    }
