"""Forecast de vendas → forecast de receitas (linha "Receita de Venda de Lotes").

Corrige a injeção que nunca rodou (procurava o plano 1.01.01.01; no banco é 1010101):
- plano: 1010101 / 1.01.01.01, ou o nome "Receita de Venda de Lotes";
- parcelas: lê "60x", "36X", "A VISTA" como o motor de viabilidade (número de parcelas
  pelo dígito; à vista no mês da venda; parcelado a partir do mês seguinte; entrada
  em perc_entrada/parcelas_entrada a partir do mês da venda);
- realizado: só INC-* (recebimentos do sync atual) e FCST-INC-* (parcelas em aberto),
  com a categoria do plano. SP-MIG-* (carga antiga do SharePoint) fica de fora, senão
  o realizado entraria em dobro;
- recorte: só os produtos que estão no forecast de vendas, nunca a empresa toda;
- vendas de meses que já passaram não são projetadas de novo: elas já estão no
  Sienge como recebimento (INC-*) ou parcela em aberto (FCST-INC-*); projetar as
  duas contaria em dobro. Só entram as vendas do mês atual em diante;
- soma no banco (GROUP BY), sem carregar as linhas em memória.
Linhas digitadas à mão (is_auto_generated = False) continuam tendo prioridade.
"""
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, Optional

from sqlalchemy import Numeric, and_, cast, extract, func, or_
from sqlalchemy.orm import Session

from app.models.actual_transaction import ActualTransaction
from app.models.departamento import DepartamentoCostCenter
from app.models.financial_plan import FinancialPlan
from app.models.forecast import Forecast, ForecastItem, ForecastVendaItem
from app.models.payment_plan import PaymentPlan

CODIGOS_PLANO_VENDA_LOTES = ("1010101", "1.01.01.01")
NOME_PLANO_VENDA_LOTES = "Receita de Venda de Lotes"
OBS_AUTO = "Injetado automaticamente do Forecast de Vendas"
_MESES_ATTR = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def plano_receita_venda_lotes(db: Session) -> Optional[FinancialPlan]:
    plano = (
        db.query(FinancialPlan)
        .filter(FinancialPlan.db_id.in_(CODIGOS_PLANO_VENDA_LOTES))
        .order_by(FinancialPlan.id)
        .first()
    )
    if plano:
        return plano
    return (
        db.query(FinancialPlan)
        .filter(func.lower(FinancialPlan.name) == NOME_PLANO_VENDA_LOTES.lower())
        .order_by(FinancialPlan.id)
        .first()
    )


def _condicoes(condicoes_json) -> list:
    """Mesma leitura de _parse_condicoes do motor de viabilidade."""
    if not isinstance(condicoes_json, list) or not condicoes_json:
        return [{"perc": 100.0, "inst": 1, "perc_entrada": 0.0, "parcelas_entrada": 1}]
    planas = []
    for item in condicoes_json:
        if isinstance(item, dict) and isinstance(item.get("condicoes"), list):
            planas.extend(item["condicoes"])
        elif isinstance(item, dict):
            planas.append(item)
    out = []
    for c in planas:
        nome = str(c.get("nome", "1")).upper().replace("A VISTA", "1").replace("À VISTA", "1")
        m = re.search(r"\d+", nome)
        inst = int(m.group()) if m else 1
        out.append({
            "perc": float(c.get("perc", 0.0) or 0.0),
            "inst": inst if inst > 0 else 1,
            "perc_entrada": float(c.get("perc_entrada", 0.0) or 0.0),
            "parcelas_entrada": max(1, int(c.get("parcelas_entrada", 1) or 1)),
        })
    return out or [{"perc": 100.0, "inst": 1, "perc_entrada": 0.0, "parcelas_entrada": 1}]


def distribuir_venda_no_ano(vgv: float, mes_venda: int, condicoes_json) -> Dict[int, float]:
    """Recebimento nominal de uma venda, por mês do ano (1..12). Parcelas depois de dezembro
    pertencem aos anos seguintes e ficam fora do forecast deste ano."""
    meses: Dict[int, float] = defaultdict(float)
    if not vgv or vgv <= 0 or not (1 <= mes_venda <= 12):
        return meses

    def _soma(mes: int, valor: float):
        if 1 <= mes <= 12:
            meses[mes] += valor

    for c in _condicoes(condicoes_json):
        if c["perc"] <= 0:
            continue
        total = vgv * c["perc"] / 100.0
        entrada = total * c["perc_entrada"] / 100.0
        financiado = total - entrada
        pe = c["parcelas_entrada"]
        if entrada > 0:
            for p in range(pe):
                _soma(mes_venda + p, entrada / pe)
        inst = c["inst"]
        if entrada > 0 and inst > pe:
            inst -= pe
        if financiado <= 0 or inst <= 0:
            continue
        offset = 0 if (inst == 1 and entrada == 0) else (pe if entrada > 0 else 1)
        for j in range(inst):
            _soma(mes_venda + offset + j, financiado / inst)
    return meses


def _venda_ainda_nao_realizada(ano: int, mes: int, hoje=None) -> bool:
    """Venda prevista do mês atual em diante. Meses passados já estão no Sienge."""
    hoje = hoje or datetime.now()
    if ano > hoje.year:
        return True
    if ano < hoje.year:
        return False
    return mes >= hoje.month


def _produtos_do_departamento(db: Session, dept_id: Optional[int]) -> set:
    if not dept_id:
        return set()
    return {
        r[0]
        for r in db.query(DepartamentoCostCenter.cost_center_id).filter(
            DepartamentoCostCenter.departamento_id == dept_id,
            DepartamentoCostCenter.permitido.isnot(False),
        )
        if r[0]
    }


def realizado_e_em_aberto(db: Session, ano: int, produtos: Iterable[int], plano: FinancialPlan, hoje=None) -> Dict[int, Dict[int, float]]:
    """{produto: {mês: valor}} de recebimentos INC-* e parcelas em aberto FCST-INC-* do plano."""
    hoje = hoje or datetime.now()
    produtos = sorted({p for p in produtos if p})
    acc: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
    if not produtos or not plano or not plano.name:
        return acc
    mes_col = extract("month", ActualTransaction.transaction_date)
    for i in range(0, len(produtos), 500):
        q = (
            db.query(
                ActualTransaction.cost_center_id,
                mes_col,
                ActualTransaction.is_forecast,
                func.sum(cast(ActualTransaction.value, Numeric)),  # decimal exato (11/11/2026)
            )
            .filter(
                ActualTransaction.transaction_type == "INCOME",
                extract("year", ActualTransaction.transaction_date) == ano,
                ActualTransaction.cost_center_id.in_(produtos[i:i + 500]),
                func.lower(func.trim(ActualTransaction.category)) == plano.name.strip().lower(),
                or_(
                    and_(ActualTransaction.is_forecast == False, ActualTransaction.source_id.like("INC-%")),  # noqa: E712
                    and_(ActualTransaction.is_forecast == True, ActualTransaction.source_id.like("FCST-INC-%")),  # noqa: E712
                ),
            )
            .group_by(ActualTransaction.cost_center_id, mes_col, ActualTransaction.is_forecast)
        )
        for cc_id, mes, is_fcst, soma in q.all():
            mes = int(mes or 0)
            if not (1 <= mes <= 12):
                continue
            if is_fcst:
                # parcela em aberto: só vale do mês atual em diante; ano passado não tem "em aberto"
                if ano < hoje.year or (ano == hoje.year and mes < hoje.month):
                    continue
            acc[cc_id][mes] += float(soma or 0.0)
    return acc


def injetar_vendas_em_receitas(forecast_vendas: Forecast, db: Session, hoje=None) -> dict:
    """Recalcula as linhas automáticas de Receita de Venda de Lotes do forecast de receitas.
    Devolve um resumo (para log e testes)."""
    resumo = {"plano": None, "produtos": 0, "linhas": 0, "total": 0.0}
    plano = plano_receita_venda_lotes(db)
    if not plano:
        return resumo
    resumo["plano"] = plano.db_id or plano.name
    ano = forecast_vendas.ano
    dept_id = forecast_vendas.departamento_id

    acumulador: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))

    itens = db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id == forecast_vendas.id).all()
    planos_ids = {i.plano_venda_id for i in itens if i.plano_venda_id}
    planos = {p.id: p for p in db.query(PaymentPlan).filter(PaymentPlan.id.in_(planos_ids)).all()} if planos_ids else {}
    produtos = set()
    for iv in itens:
        if not iv.produto_id:
            continue
        produtos.add(iv.produto_id)
        if not iv.vgv or iv.vgv <= 0:
            continue
        if not _venda_ainda_nao_realizada(ano, int(iv.mes or 0), hoje):
            continue
        plano_venda = planos.get(iv.plano_venda_id)
        cond = plano_venda.condicoes_json if plano_venda else None
        for mes, valor in distribuir_venda_no_ano(float(iv.vgv), int(iv.mes or 0), cond).items():
            acumulador[iv.produto_id][mes] += valor

    for cc_id, meses in realizado_e_em_aberto(db, ano, produtos, plano, hoje).items():
        for mes, valor in meses.items():
            acumulador[cc_id][mes] += valor

    if not produtos:
        return resumo

    f_receitas = db.query(Forecast).filter(
        Forecast.ano == ano,
        Forecast.descricao == forecast_vendas.descricao,
        Forecast.departamento_id == dept_id,
        Forecast.tipo == "RECEITAS",
    ).first()
    if not f_receitas:
        f_receitas = Forecast(
            descricao=forecast_vendas.descricao,
            ano=ano,
            tipo="RECEITAS",
            versao_numero=forecast_vendas.versao_numero,
            status="Rascunho",
            usuario_criador_id=forecast_vendas.usuario_criador_id,
            departamento_id=dept_id,
            versao_base_orcamento_id=forecast_vendas.versao_base_orcamento_id,
            versao_base_forecast_id=forecast_vendas.versao_base_forecast_id,
        )
        db.add(f_receitas)
        db.flush()

    produtos_lista = sorted(produtos)
    manuais = {
        r[0]
        for r in db.query(ForecastItem.produto_id).filter(
            ForecastItem.forecast_id == f_receitas.id,
            ForecastItem.plano_financeiro_id == plano.id,
            ForecastItem.produto_id.in_(produtos_lista),
            ForecastItem.is_auto_generated == False,  # noqa: E712
        )
    }
    db.query(ForecastItem).filter(
        ForecastItem.forecast_id == f_receitas.id,
        ForecastItem.plano_financeiro_id == plano.id,
        ForecastItem.produto_id.in_(produtos_lista),
        ForecastItem.is_auto_generated == True,  # noqa: E712
    ).delete(synchronize_session=False)

    novos = []
    for p_id in produtos_lista:
        if p_id in manuais:
            continue
        meses = acumulador.get(p_id) or {}
        total = sum(meses.values())
        if total <= 0.01:
            continue
        campos = {attr: float(meses.get(i + 1, 0.0)) for i, attr in enumerate(_MESES_ATTR)}
        novos.append(ForecastItem(
            forecast_id=f_receitas.id,
            produto_id=p_id,
            plano_financeiro_id=plano.id,
            total_anual=total,
            observacao=OBS_AUTO,
            is_auto_generated=True,
            **campos,
        ))
        resumo["total"] += total
    if novos:
        db.bulk_save_objects(novos)
    db.commit()
    resumo["produtos"] = len(produtos_lista)
    resumo["linhas"] = len(novos)
    return resumo
