"""Roll-forward de geração de caixa no DFC.

Não altera montar_dfc: lê as mesmas séries assinadas da visão e o snapshot 31/12
já persistido. Não consulta o Sienge.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from app.core.sienge_sync_schedule import TZ_BRASILIA
from app.services.orcamento_dfc import (
    MESES_STR,
    SENTIDO_ENTRADA,
    SENTIDO_SAIDA,
    _add_meses,
    _by_plan,
    _empty_meses,
    _signed,
)

TIPOS_CAIXA = frozenset({"B", "I", "C"})
TIPOS_FORA = frozenset({"M", "Q", "E"})
PRIMEIRO_ANO_SNAPSHOT = 2024


def hoje_brasilia(hoje: date | datetime | None = None) -> date:
    if hoje is None:
        return datetime.now(TZ_BRASILIA).date()
    if isinstance(hoje, datetime):
        return hoje.date()
    return hoje


def corte_caixa(ano: int, hoje: date | datetime | None = None, cortes: Optional[Dict[int, Optional[int]]] = None) -> int:
    """Último mês fechado no ano. 0 = o ano inteiro ainda é YTG.

    Regra oficial (11/11/2026): a tabela da tela Fechamento (``cortes`` = {ano: último
    mês fechado em sequência}). Ano sem fechamento cadastrado usa o calendário.
    """
    if cortes and cortes.get(ano) is not None:
        return int(cortes[ano])
    d = hoje_brasilia(hoje)
    if ano < d.year:
        return 12
    if ano > d.year:
        return 0
    return max(0, d.month - 1)


def anos_fechados_snapshot(hoje: date | datetime | None = None) -> List[int]:
    d = hoje_brasilia(hoje)
    ultimo = d.year - 1
    if ultimo < PRIMEIRO_ANO_SNAPSHOT:
        return []
    return list(range(PRIMEIRO_ANO_SNAPSHOT, ultimo + 1))


def tipo_conta(raw: Any) -> str:
    if isinstance(raw, dict):
        return str(raw.get("id") or "").strip().upper()
    return str(raw or "").strip().upper()


def _texto_conta(valor: Any) -> str:
    t = str(valor or "").upper()
    return t.replace("Ú", "U").replace("Ù", "U").replace("Ü", "U")


def eh_mutuo(*, tipo: Any = "", nome: Any = "", numero: Any = "") -> bool:
    """Conta mútuo não entra na abertura — nem pelo tipo M, nem pelo nome."""
    if tipo_conta(tipo) == "M":
        return True
    blob = f"{_texto_conta(nome)} {_texto_conta(numero)}"
    return "MUTUO" in blob


def eh_conta_caixa(row: dict) -> bool:
    t = tipo_conta(row.get("account_type") or row.get("accountType"))
    nome = row.get("account_name") or row.get("accountName") or ""
    numero = row.get("account_number") or row.get("accountNumber") or ""
    if eh_mutuo(tipo=t, nome=nome, numero=numero):
        return False
    if t in TIPOS_FORA:
        return False
    return t in TIPOS_CAIXA


def saldo_caixa(rows: Iterable[dict], tipos: Iterable[str] = TIPOS_CAIXA) -> float:
    aceitos = {str(t).strip().upper() for t in tipos}
    total = 0.0
    for row in rows or []:
        if not eh_conta_caixa(row):
            continue
        t = tipo_conta(row.get("account_type") or row.get("accountType"))
        if t not in aceitos:
            continue
        total += float(row.get("amount") or 0.0)
    return total


def fluxo_ytd_ytg(
    meses_real: Dict[str, float],
    meses_orcado: Dict[str, float],
    corte: int,
) -> Dict[str, float]:
    c = max(0, min(12, int(corte)))
    ytd_meses = MESES_STR[:c]
    ytg_meses = MESES_STR[c:]
    ytd = sum(float((meses_real or {}).get(m) or 0.0) for m in ytd_meses)
    ytg = sum(float((meses_orcado or {}).get(m) or 0.0) for m in ytg_meses)
    return {"ytd": ytd, "ytg": ytg, "geracao": ytd + ytg, "corte": c}


def serie_liquido_visao(
    nodes: List[dict],
    rec_itens: List[dict],
    desp_itens: List[dict],
) -> tuple[Dict[str, float], Dict[str, float]]:
    """Realizado e orçado mensal do líquido, mesmo sinal da visão DFC."""
    rec_map = _by_plan(rec_itens)
    desp_map = _by_plan(desp_itens)
    mapped: set[Any] = set()
    for node in nodes or []:
        for plano in node.get("planos") or []:
            pid = plano.get("id")
            if pid is not None:
                mapped.add(pid)
    real = _empty_meses()
    orcado = _empty_meses()
    for pid in mapped:
        if pid in rec_map:
            real = _add_meses(real, _signed(rec_map[pid]["realizado"], SENTIDO_ENTRADA))
            orcado = _add_meses(orcado, _signed(rec_map[pid]["orcado"], SENTIDO_ENTRADA))
        if pid in desp_map:
            real = _add_meses(real, _signed(desp_map[pid]["realizado"], SENTIDO_SAIDA))
            orcado = _add_meses(orcado, _signed(desp_map[pid]["orcado"], SENTIDO_SAIDA))
    return real, orcado


def ids_recorte_caixa(
    opcoes_produtos: Optional[Sequence[dict]],
    ids_filtro: Optional[Sequence[str]],
) -> Optional[List[str]]:
    """Empresas do recorte (id Sienge). None = todas as do snapshot."""
    filtro = [str(x).strip() for x in (ids_filtro or []) if str(x).strip()]
    if filtro:
        return filtro
    from_opcoes = sorted(
        {
            str(p.get("id_empresa") or "").strip()
            for p in (opcoes_produtos or [])
            if str(p.get("id_empresa") or "").strip()
        }
    )
    return from_opcoes or None


def abertura_encadeada(
    ano: int,
    snapshots: Dict[int, float],
    fluxos: Dict[int, Dict[str, float]],
) -> Dict[str, Any]:
    """Abertura de `ano` = último 31/12 persistido + geração dos anos no meio."""
    candidatos = [y for y in snapshots if y < ano]
    if not candidatos:
        return {
            "abertura": None,
            "origem": "sem_snapshot",
            "ano_base": None,
            "anos_intermediarios": [],
        }
    base = max(candidatos)
    pos = float(snapshots[base])
    intermediarios: List[int] = []
    for y in range(base + 1, ano):
        fluxo = fluxos.get(y)
        if fluxo is None or "geracao" not in fluxo:
            return {
                "abertura": None,
                "origem": "sem_fluxo_intermediario",
                "ano_base": base,
                "anos_intermediarios": intermediarios + [y],
            }
        pos = pos + float(fluxo["geracao"])
        intermediarios.append(y)
    origem = "snapshot" if base == ano - 1 else "projetada"
    return {
        "abertura": pos,
        "origem": origem,
        "ano_base": base,
        "anos_intermediarios": intermediarios,
    }


def posicao_fim_ano(
    ano: int,
    abertura: Dict[str, Any],
    fluxo: Dict[str, float],
    snapshots: Dict[int, float],
) -> Dict[str, Any]:
    """Ano fechado com 31/12 gravado usa o Sienge; senão abertura + YTD + YTG."""
    if ano in snapshots:
        return {"posicao_fim": float(snapshots[ano]), "origem": "snapshot"}
    if abertura.get("abertura") is None:
        return {"posicao_fim": None, "origem": "sem_abertura"}
    return {
        "posicao_fim": float(abertura["abertura"]) + float(fluxo.get("geracao") or 0.0),
        "origem": "projetada",
    }


def _bloco_ano(
    *,
    ano: int,
    fluxo: Dict[str, float],
    snapshots: Dict[int, float],
    fluxos_cadeia: Dict[int, Dict[str, float]],
) -> Dict[str, Any]:
    ab = abertura_encadeada(ano, snapshots, fluxos_cadeia)
    fim = posicao_fim_ano(ano, ab, fluxo, snapshots)
    tem_abertura = ab.get("abertura") is not None
    return {
        "ano": ano,
        "corte": int(fluxo.get("corte") or 0),
        "ytd": float(fluxo.get("ytd") or 0.0),
        "ytg": float(fluxo.get("ytg") or 0.0),
        "geracao": float(fluxo.get("geracao") or 0.0),
        "abertura": ab.get("abertura"),
        "abertura_origem": ab.get("origem"),
        "abertura_ano_base": ab.get("ano_base"),
        "posicao_fim": fim.get("posicao_fim"),
        "posicao_origem": fim.get("origem"),
        "tem_abertura": tem_abertura,
    }


def _legenda(bloco: Dict[str, Any]) -> str:
    if not bloco.get("tem_abertura"):
        return "YTD + YTG (sem abertura)"
    ano = int(bloco.get("ano") or 0)
    if bloco.get("abertura_origem") == "projetada" and ano:
        return f"abertura projetada 31/12/{ano - 1} + YTD + YTG"
    base = bloco.get("abertura_ano_base")
    if base is not None:
        return f"abertura 31/12/{int(base)} + YTD + YTG"
    return "abertura + YTD + YTG"


def payload_geracao_caixa(
    db,
    *,
    ano: int,
    nodes: List[dict],
    rec_n: List[dict],
    desp_n: List[dict],
    rec_n1: List[dict],
    desp_n1: List[dict],
    opcoes_produtos: Optional[Sequence[dict]] = None,
    ids_empresa: Optional[Sequence[str]] = None,
    hoje: date | datetime | None = None,
    holding_mldu: bool = False,
    rec_n_mldu: Optional[List[dict]] = None,
    desp_n_mldu: Optional[List[dict]] = None,
    rec_n1_mldu: Optional[List[dict]] = None,
    desp_n1_mldu: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    """Monta o bloco JSON do card. Lê só o snapshot já gravado."""
    from app.services.sienge_account_balances import saldos_31_12

    ids = ids_recorte_caixa(opcoes_produtos, ids_empresa)
    snaps_cheio = saldos_31_12(db, ids_empresa=ids, mldu=False)
    precisa_mldu = holding_mldu or rec_n_mldu is not None
    snaps_mldu = saldos_31_12(db, ids_empresa=ids, mldu=True) if precisa_mldu else {}
    snaps_principal = snaps_mldu if holding_mldu else snaps_cheio
    from app.services.forecast_mes_fechado import corte_por_fechamento

    cortes = {a: corte_por_fechamento(db, a) for a in (ano, ano - 1)}
    bloco = montar_bloco_geracao(
        ano=ano,
        nodes=nodes,
        rec_n=rec_n,
        desp_n=desp_n,
        rec_n1=rec_n1,
        desp_n1=desp_n1,
        snapshots=snaps_principal,
        hoje=hoje,
        cortes=cortes,
    )
    if rec_n_mldu is not None:
        bloco["mldu"] = montar_bloco_geracao(
            ano=ano,
            nodes=nodes,
            rec_n=rec_n_mldu,
            desp_n=desp_n_mldu or [],
            rec_n1=rec_n1_mldu or [],
            desp_n1=desp_n1_mldu or [],
            snapshots=snaps_mldu,
            hoje=hoje,
            cortes=cortes,
        )
    else:
        bloco["mldu"] = None
    return bloco


def montar_bloco_geracao(
    *,
    ano: int,
    nodes: List[dict],
    rec_n: List[dict],
    desp_n: List[dict],
    rec_n1: List[dict],
    desp_n1: List[dict],
    snapshots: Dict[int, float],
    hoje: date | datetime | None = None,
    cortes: Optional[Dict[int, Optional[int]]] = None,
) -> Dict[str, Any]:
    real_n, orc_n = serie_liquido_visao(nodes, rec_n, desp_n)
    real_n1, orc_n1 = serie_liquido_visao(nodes, rec_n1, desp_n1)
    fluxo_n = fluxo_ytd_ytg(real_n, orc_n, corte_caixa(ano, hoje, cortes))
    fluxo_n1 = fluxo_ytd_ytg(real_n1, orc_n1, corte_caixa(ano - 1, hoje, cortes))
    fluxos = {ano: fluxo_n, ano - 1: fluxo_n1}
    n = _bloco_ano(ano=ano, fluxo=fluxo_n, snapshots=snapshots, fluxos_cadeia=fluxos)
    n1 = _bloco_ano(ano=ano - 1, fluxo=fluxo_n1, snapshots=snapshots, fluxos_cadeia=fluxos)
    return {
        **n,
        "legenda": _legenda(n),
        "ytd_n1": n1["ytd"],
        "ytg_n1": n1["ytg"],
        "geracao_n1": n1["geracao"],
        "abertura_n1": n1["abertura"],
        "posicao_fim_n1": n1["posicao_fim"],
        "tem_abertura_n1": n1["tem_abertura"],
        "corte_n1": n1["corte"],
    }
