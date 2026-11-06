"""Despesas por empreendimento: Real N (YTD + Fcst YTG) × Orçado/Forecast N+1.

Só lê orçado, realizado e forecast já calculados. Não recalcula. Despesa positiva.
Grupos da Visão DFC 05.01–05.11 (sem 05.08). Planos 09.01* ficam de fora.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.services.orcamento_dfc import MESES_STR, _add_meses, _empty_meses, _soma, ratio_ah

CORTE_PADRAO = 9
GRUPO_RAIZ = "05"
GRUPO_EXCLUIDO = "05.08"
PLANO_NAV_PREFIX = "09.01"

_SERIES = ("n", "n_mldu", "orcado", "orcado_mldu", "forecast", "forecast_mldu")
_ZERO = 1e-12


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


def _produto_meta(opcoes_produtos: List[dict], produto_id: Any) -> Dict[str, Any]:
    by_id = {}
    for p in opcoes_produtos or []:
        if isinstance(p, dict) and p.get("id") is not None:
            by_id[p["id"]] = p
    p = by_id.get(produto_id) or {}
    emp_id = str(p.get("id_empresa") or "").strip() or "_sem"
    emp_nome = str(p.get("nome_empresa") or "").strip() or "Sem empresa"
    cc_nome = str(p.get("nome") or "").strip() or f"CC {produto_id}"
    return {
        "produto_id": produto_id,
        "empresa_id": emp_id,
        "empresa_nome": emp_nome,
        "cc_nome": cc_nome,
    }


def _grupo_codigo(codigo: str) -> Optional[str]:
    parts = [p for p in (codigo or "").split(".") if p]
    if len(parts) < 2:
        return None
    nivel2 = f"{parts[0]}.{parts[1]}"
    if parts[0] != GRUPO_RAIZ or nivel2 == GRUPO_EXCLUIDO:
        return None
    return nivel2


def _plano_excluido(db_id: Any) -> bool:
    return str(db_id or "").replace(" ", "").startswith(PLANO_NAV_PREFIX)


def _empty_amounts() -> Dict[str, Dict[str, float]]:
    return {k: _empty_meses() for k in _SERIES}


def _add_amounts(a: Dict[str, Dict[str, float]], b: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    return {k: _add_meses(a.get(k) or _empty_meses(), b.get(k) or _empty_meses()) for k in _SERIES}


def _copy_meses(series: Dict[str, float]) -> Dict[str, float]:
    """Copia o valor como no orçamento (despesa positiva; redutora mantém o sinal da fonte)."""
    return {m: float(series.get(m, 0.0) or 0.0) for m in MESES_STR}


def mix_real_forecast(realizado: Dict[str, float], forecast: Dict[str, float], corte: int) -> Dict[str, float]:
    """Meses ≤ corte = realizado; meses seguintes = forecast. Sem inverter sinal."""
    out = _empty_meses()
    real = _copy_meses(realizado)
    fcst = _copy_meses(forecast)
    for i, m in enumerate(MESES_STR, start=1):
        out[m] = real[m] if i <= corte else fcst[m]
    return out


def meses_periodo(corte: int, periodo: str) -> List[str]:
    if periodo == "ytd":
        return [m for i, m in enumerate(MESES_STR, start=1) if i <= corte]
    if periodo == "ytg":
        return [m for i, m in enumerate(MESES_STR, start=1) if i > corte]
    return list(MESES_STR)


def _periodos(amounts: Dict[str, Dict[str, float]], corte: int) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for nome in ("ano", "ytd", "ytg", "fy"):
        chave = "ano" if nome in ("ano", "fy") else nome
        meses = meses_periodo(corte, chave)
        out[nome] = {k: _soma(amounts[k], meses) for k in _SERIES}
    return out


def _is_zero(amounts: Dict[str, Dict[str, float]]) -> bool:
    for serie in amounts.values():
        if any(abs(float(v or 0.0)) > _ZERO for v in serie.values()):
            return False
    return True


def _row(
    *,
    kind: str,
    id: str,
    codigo: str,
    descricao: str,
    amounts: Dict[str, Dict[str, float]],
    corte: int,
    filhos: Optional[List[dict]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    periodos = _periodos(amounts, corte)
    row: Dict[str, Any] = {
        "kind": kind,
        "id": id,
        "codigo": codigo or "",
        "descricao": descricao or "",
        "filhos": filhos or [],
        "meses_n": amounts["n"],
        "meses_n_mldu": amounts["n_mldu"],
        "meses_orcado": amounts["orcado"],
        "meses_orcado_mldu": amounts["orcado_mldu"],
        "meses_forecast": amounts["forecast"],
        "meses_forecast_mldu": amounts["forecast_mldu"],
        "total_n": periodos["ano"]["n"],
        "total_n_mldu": periodos["ano"]["n_mldu"],
        "total_orcado": periodos["ano"]["orcado"],
        "total_orcado_mldu": periodos["ano"]["orcado_mldu"],
        "total_forecast": periodos["ano"]["forecast"],
        "total_forecast_mldu": periodos["ano"]["forecast_mldu"],
        "periodos": periodos,
        "ah_orcado": ratio_ah(periodos["ano"]["n"], periodos["ano"]["orcado"]),
        "ah_forecast": ratio_ah(periodos["ano"]["n"], periodos["ano"]["forecast"]),
    }
    if extra:
        row.update(extra)
    return row


def _mapear_grupos(nodes: List[dict]) -> Tuple[Dict[str, str], Dict[Any, str], Dict[Any, dict]]:
    """grupo_codigo → descrição; plano_id → grupo; plano_id → spec do plano."""
    grupos: Dict[str, str] = {}
    plano_grupo: Dict[Any, str] = {}
    plano_spec: Dict[Any, dict] = {}
    for node in nodes or []:
        codigo = node.get("codigo") or ""
        grupo = _grupo_codigo(codigo)
        if not grupo:
            continue
        if codigo == grupo or grupo not in grupos:
            grupos[grupo] = node.get("descricao") or grupo
        if codigo == grupo:
            grupos[grupo] = node.get("descricao") or grupo
        for plano in node.get("planos") or []:
            pid = plano.get("id")
            if pid is None or _plano_excluido(plano.get("db_id")):
                continue
            plano_grupo[pid] = grupo
            plano_spec[pid] = plano
    return grupos, plano_grupo, plano_spec


def _leaf_amounts(
    key: Tuple[Any, Any],
    n_map: Dict[Tuple[Any, Any], Dict[str, Dict[str, float]]],
    n_mldu_map: Dict[Tuple[Any, Any], Dict[str, Dict[str, float]]],
    ref_map: Dict[Tuple[Any, Any], Dict[str, Dict[str, float]]],
    ref_mldu_map: Dict[Tuple[Any, Any], Dict[str, Dict[str, float]]],
    corte: int,
) -> Dict[str, Dict[str, float]]:
    n = n_map.get(key) or {"realizado": _empty_meses(), "forecast": _empty_meses()}
    n_m = n_mldu_map.get(key) or {"realizado": _empty_meses(), "forecast": _empty_meses()}
    ref = ref_map.get(key) or {"orcado": _empty_meses(), "forecast": _empty_meses()}
    ref_m = ref_mldu_map.get(key) or {"orcado": _empty_meses(), "forecast": _empty_meses()}
    return {
        "n": mix_real_forecast(n.get("realizado") or {}, n.get("forecast") or {}, corte),
        "n_mldu": mix_real_forecast(n_m.get("realizado") or {}, n_m.get("forecast") or {}, corte),
        "orcado": _copy_meses(ref.get("orcado") or {}),
        "orcado_mldu": _copy_meses(ref_m.get("orcado") or {}),
        "forecast": _copy_meses(ref.get("forecast") or {}),
        "forecast_mldu": _copy_meses(ref_m.get("forecast") or {}),
    }


def montar_despesas_empreendimento(
    nodes: List[dict],
    desp_n: List[dict],
    desp_n_mldu: List[dict],
    desp_ref: List[dict],
    desp_ref_mldu: List[dict],
    opcoes_produtos: List[dict],
    corte: int = CORTE_PADRAO,
) -> Dict[str, Any]:
    """Árvore empresa → grupo 05.xx → centro → plano. Números já calculados."""
    corte_ok = int(corte) if 1 <= int(corte or 0) <= 12 else CORTE_PADRAO
    grupos_nome, plano_grupo, plano_spec = _mapear_grupos(nodes)
    mapped_ids = set(plano_grupo.keys())

    n_map = _by_prod_plan(desp_n)
    n_mldu_map = _by_prod_plan(desp_n_mldu)
    ref_map = _by_prod_plan(desp_ref)
    ref_mldu_map = _by_prod_plan(desp_ref_mldu)

    keys = set()
    for mp in (n_map, n_mldu_map, ref_map, ref_mldu_map):
        keys.update(mp.keys())

    # emp -> grupo -> prod -> plano -> amounts
    tree: Dict[str, Dict[str, Dict[Any, Dict[Any, Dict[str, Any]]]]] = {}
    empresas_nome: Dict[str, str] = {}
    cc_nome: Dict[Any, str] = {}

    for key in keys:
        prod_id, pid = key
        if pid not in mapped_ids:
            continue
        grupo = plano_grupo[pid]
        meta = _produto_meta(opcoes_produtos, prod_id)
        emp_id = meta["empresa_id"]
        empresas_nome[emp_id] = meta["empresa_nome"]
        cc_nome[prod_id] = meta["cc_nome"]
        amounts = _leaf_amounts(key, n_map, n_mldu_map, ref_map, ref_mldu_map, corte_ok)
        if _is_zero(amounts):
            continue
        tree.setdefault(emp_id, {}).setdefault(grupo, {}).setdefault(prod_id, {})[pid] = {
            "amounts": amounts,
            "plano": plano_spec.get(pid) or {},
            "cc_nome": meta["cc_nome"],
        }

    empresas: List[Dict[str, Any]] = []
    for emp_id, emp_nome in sorted(empresas_nome.items(), key=lambda kv: (kv[1].lower(), kv[0])):
        grupos_rows: List[Dict[str, Any]] = []
        emp_tot = _empty_amounts()
        for grupo in sorted(grupos_nome.keys()):
            centros_src = (tree.get(emp_id) or {}).get(grupo) or {}
            if not centros_src:
                continue
            centros_rows: List[Dict[str, Any]] = []
            grupo_tot = _empty_amounts()
            for prod_id, planos_map in sorted(
                centros_src.items(),
                key=lambda kv: ((cc_nome.get(kv[0]) or ""), kv[0] or 0),
            ):
                planos_rows: List[Dict[str, Any]] = []
                centro_tot = _empty_amounts()
                for pid, info in sorted(
                    planos_map.items(),
                    key=lambda kv: (
                        (kv[1]["plano"].get("name") or ""),
                        kv[0] or 0,
                    ),
                ):
                    plano = info["plano"]
                    planos_rows.append(
                        _row(
                            kind="plano",
                            id=f"e|{emp_id}|g|{grupo}|c|{prod_id}|p|{pid}",
                            codigo=plano.get("db_id") or "",
                            descricao=plano.get("name") or "",
                            amounts=info["amounts"],
                            corte=corte_ok,
                            extra={"plano_financeiro_id": pid, "produto_id": prod_id},
                        )
                    )
                    centro_tot = _add_amounts(centro_tot, info["amounts"])
                centros_rows.append(
                    _row(
                        kind="centro",
                        id=f"e|{emp_id}|g|{grupo}|c|{prod_id}",
                        codigo="",
                        descricao=cc_nome.get(prod_id) or f"CC {prod_id}",
                        amounts=centro_tot,
                        corte=corte_ok,
                        filhos=planos_rows,
                        extra={"produto_id": prod_id, "empresa_id": emp_id},
                    )
                )
                grupo_tot = _add_amounts(grupo_tot, centro_tot)
            grupos_rows.append(
                _row(
                    kind="grupo",
                    id=f"e|{emp_id}|g|{grupo}",
                    codigo=grupo,
                    descricao=grupos_nome[grupo],
                    amounts=grupo_tot,
                    corte=corte_ok,
                    filhos=centros_rows,
                    extra={"grupo": grupo},
                )
            )
            emp_tot = _add_amounts(emp_tot, grupo_tot)
        if not grupos_rows:
            continue
        empresas.append(
            _row(
                kind="empresa",
                id=f"e|{emp_id}",
                codigo="" if emp_id == "_sem" else emp_id,
                descricao=emp_nome,
                amounts=emp_tot,
                corte=corte_ok,
                filhos=grupos_rows,
                extra={"empresa_id": emp_id},
            )
        )

    totais = _empty_amounts()
    for emp in empresas:
        totais = _add_amounts(
            totais,
            {
                "n": emp["meses_n"],
                "n_mldu": emp["meses_n_mldu"],
                "orcado": emp["meses_orcado"],
                "orcado_mldu": emp["meses_orcado_mldu"],
                "forecast": emp["meses_forecast"],
                "forecast_mldu": emp["meses_forecast_mldu"],
            },
        )

    grupos_filtro = [{"codigo": c, "descricao": grupos_nome[c]} for c in sorted(grupos_nome)]
    centros_filtro = [
        {"produto_id": pid, "nome": nome}
        for pid, nome in sorted(cc_nome.items(), key=lambda kv: ((kv[1] or ""), kv[0] or 0))
    ]

    return {
        "corte": corte_ok,
        "meses_ytd": meses_periodo(corte_ok, "ytd"),
        "meses_ytg": meses_periodo(corte_ok, "ytg"),
        "grupos": grupos_filtro,
        "centros": centros_filtro,
        "empresas": empresas,
        "periodos": _periodos(totais, corte_ok),
        "total_n": _soma(totais["n"], MESES_STR),
        "total_n_mldu": _soma(totais["n_mldu"], MESES_STR),
        "total_orcado": _soma(totais["orcado"], MESES_STR),
        "total_orcado_mldu": _soma(totais["orcado_mldu"], MESES_STR),
        "total_forecast": _soma(totais["forecast"], MESES_STR),
        "total_forecast_mldu": _soma(totais["forecast_mldu"], MESES_STR),
    }
