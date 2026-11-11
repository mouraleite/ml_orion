"""Camada de leitura Consolidação MLDU (Onda C) — pondera valores por % efetivo."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.company import Company, CompanyOwnershipLink, CompanyOwnershipPeriod
from app.models.cost_center import CostCenter
from app.services.calculations import calculo_saldo_despesas, calculo_variacao_perc, calculo_variacao_rs
from app.services.mldu_ownership import effective_for_company
from app.services.mldu_ownership_periods import compute_effective_as_of
from app.services.periodos import MESES_STR

MONTHLY_KEYS = list(MESES_STR) + ["total_anual", "total"]



def _copia(obj):
    """Cópia profunda de dados em formato JSON (dict/list), bem mais rápida que deepcopy.

    11/11/2026: deepcopy era ~1/3 do tempo da DFC gerencial. As linhas aqui só
    têm dicts, listas e valores simples; o resto é imutável e pode ser reaproveitado.
    """
    if isinstance(obj, dict):
        return {k: _copia(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_copia(v) for v in obj]
    return obj

def _cc_is_parceria(nome: str | None) -> bool:
    """CC de parceria (ex.: '... - PARCERIA GAP'): caixa 100% do parceiro, MLDU = 0."""
    if not nome:
        return False
    return "PARCERIA" in str(nome).upper()


def _participacao_cc_factor(custom: dict | None) -> float:
    """Fator 0..1 da coluna Participação do CC. Vazio/inválido = 1.0 (não muda o consolidado)."""
    if not custom:
        return 1.0
    raw = custom.get("Participação")
    if raw is None or raw is False or raw == "":
        return 1.0
    try:
        if isinstance(raw, str):
            raw = raw.replace("%", "").replace(",", ".").strip()
            if raw == "":
                return 1.0
        pct = float(raw)
    except (TypeError, ValueError):
        return 1.0
    if pct < 0:
        pct = 0.0
    if pct > 100:
        pct = 100.0
    return pct / 100.0


def build_produto_empresa_map(db: Session) -> dict[int, str]:
    out: dict[int, str] = {}
    for cc in db.query(CostCenter).all():
        emp = ""
        if cc.custom_data and cc.custom_data.get("__id_empresa") is not None:
            emp = str(cc.custom_data.get("__id_empresa"))
        out[cc.id] = emp
    return out


def build_produto_participacao_map(db: Session) -> dict[int, float]:
    return {cc.id: _participacao_cc_factor(cc.custom_data) for cc in db.query(CostCenter).all()}


def build_produto_parceria_map(db: Session) -> dict[int, bool]:
    return {cc.id: _cc_is_parceria(cc.nome) for cc in db.query(CostCenter).all()}


def build_empresa_factor_map(db: Session) -> dict[str, float]:
    """Multiplicador 0..1 indexado por id_sienge (e fallback str(db_id))."""
    factors: dict[str, float] = {}
    for company in db.query(Company).all():
        mult = effective_for_company(company) / 100.0
        if company.id_sienge:
            factors[str(company.id_sienge)] = mult
        factors[str(company.id)] = mult
    return factors


class HoldingContext:
    def __init__(self, db: Session):
        self.db = db
        self.produto_empresa = build_produto_empresa_map(db)
        self.produto_participacao = build_produto_participacao_map(db)
        self.produto_parceria = build_produto_parceria_map(db)
        self.empresa_factors = build_empresa_factor_map(db)
        self.warnings: list[str] = []
        self.fatores_por_produto: dict[int, float] = {}
        self._companies_by_sienge = {str(c.id_sienge): c for c in db.query(Company).all() if c.id_sienge}
        self._companies_by_id = {c.id: c for c in db.query(Company).all()}
        self._links_by_child = {link.child_company_id: link for link in db.query(CompanyOwnershipLink).all()}
        counts: dict[int, int] = {}
        for period in db.query(CompanyOwnershipPeriod).all():
            counts[period.link_id] = counts.get(period.link_id, 0) + 1
        self._temporal_link_ids = {lid for lid, n in counts.items() if n >= 2}
        self._effective_as_of_cache: dict[tuple[int, int], dict[int, float]] = {}

    def _company_for_emp(self, emp_id: str) -> Company | None:
        if not emp_id:
            return None
        if emp_id in self._companies_by_sienge:
            return self._companies_by_sienge[emp_id]
        if emp_id.isdigit():
            return self._companies_by_id.get(int(emp_id))
        return None

    def produto_is_temporal(self, produto_id: int | None) -> bool:
        if not produto_id or not self._temporal_link_ids:
            return False
        company = self._company_for_emp(self.produto_empresa.get(produto_id, ""))
        if not company or company.usa_participacao_manual:
            return False
        current = company.id
        seen: set[int] = set()
        while current and current not in seen:
            seen.add(current)
            link = self._links_by_child.get(current)
            if not link:
                break
            if link.id in self._temporal_link_ids:
                return True
            current = link.parent_company_id
        return False

    def factor_for_produto_mes(self, produto_id: int | None, ano: int, mes: int) -> float:
        if produto_id and self.produto_parceria.get(produto_id):
            return 0.0
        if not self.produto_is_temporal(produto_id):
            return self.factor_for_produto(produto_id)
        company = self._company_for_emp(self.produto_empresa.get(produto_id or 0, ""))
        if not company:
            return self.factor_for_produto(produto_id)
        key = (int(ano), int(mes))
        if key not in self._effective_as_of_cache:
            self._effective_as_of_cache[key] = compute_effective_as_of(self.db, int(ano), int(mes))
        emp_pct = self._effective_as_of_cache[key].get(company.id, 0.0)
        return (emp_pct / 100.0) * self.produto_participacao.get(produto_id or 0, 1.0)

    def factor_for_produto(self, produto_id: int | None) -> float:
        if produto_id is None:
            return 0.0
        if produto_id in self.fatores_por_produto:
            return self.fatores_por_produto[produto_id]
        if self.produto_parceria.get(produto_id):
            self.fatores_por_produto[produto_id] = 0.0
            return 0.0

        emp_id = self.produto_empresa.get(produto_id, "")
        if not emp_id:
            self.warnings.append(f"Centro de custo {produto_id} sem id_empresa — valor zerado na consolidação.")
            factor = 0.0
        else:
            factor = self.empresa_factors.get(emp_id, 0.0)
            if factor == 0.0:
                self.warnings.append(f"Empresa {emp_id} (centro {produto_id}) com 0% MLDU — valor zerado.")
            else:
                factor = factor * self.produto_participacao.get(produto_id, 1.0)

        self.fatores_por_produto[produto_id] = factor
        return factor


def _scale_number(value: Any, factor: float) -> float:
    if value is None:
        return 0.0
    try:
        return float(value) * factor
    except (TypeError, ValueError):
        return 0.0


def scale_monthly_row(row: dict, factor: float) -> dict:
    out = dict(row)
    for key in MESES_STR:
        if key in out:
            out[key] = _scale_number(out[key], factor)
    if "total_anual" in out:
        out["total_anual"] = _scale_number(out["total_anual"], factor)
    if "total" in out:
        out["total"] = _scale_number(out["total"], factor)
    out["holding_fator_mldu"] = factor
    return out


def scale_monthly_row_by_month(row: dict, factor_for_mes) -> dict:
    out = dict(row)
    month_sum = 0.0
    has_months = False
    last_factor = 1.0
    for i, key in enumerate(MESES_STR, start=1):
        if key in out:
            has_months = True
            last_factor = factor_for_mes(i)
            out[key] = _scale_number(out[key], last_factor)
            month_sum += float(out[key] or 0)
    if has_months:
        if "total_anual" in out:
            out["total_anual"] = month_sum
        if "total" in out:
            out["total"] = month_sum
    out["holding_fator_mldu"] = last_factor
    return out


def _payload_ano(payload: dict, row: dict | None = None) -> int | None:
    raw = (row or {}).get("ano") if row else None
    if raw is None:
        raw = payload.get("ano")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _scale_monthly_for_ctx(ctx: HoldingContext, row: dict, payload: dict) -> dict:
    pid = row.get("produto_id")
    ano = _payload_ano(payload, row)
    if ano and ctx.produto_is_temporal(pid):
        return scale_monthly_row_by_month(row, lambda mes: ctx.factor_for_produto_mes(pid, ano, mes))
    return scale_monthly_row(row, ctx.factor_for_produto(pid))


def _scale_acom_despesas_for_ctx(ctx: HoldingContext, item: dict, payload: dict) -> dict:
    pid = item.get("produto_id")
    ano = _payload_ano(payload, item)
    if not (ano and ctx.produto_is_temporal(pid)):
        return scale_acompanhamento_despesas_item(item, ctx.factor_for_produto(pid))
    out = _copia(item)
    for bucket in ("orcado", "forecast", "realizado"):
        for i, m in enumerate(MESES_STR, start=1):
            out[bucket][m] = _scale_number(out[bucket].get(m), ctx.factor_for_produto_mes(pid, ano, i))
        out[bucket]["total"] = sum(float(out[bucket][m] or 0) for m in MESES_STR)
    out["saldo_orcado"] = {
        m: calculo_saldo_despesas(out["orcado"][m], out["realizado"][m]) for m in MESES_STR + ["total"]
    }
    out["saldo_forecast"] = {
        m: calculo_saldo_despesas(out["forecast"][m], out["realizado"][m]) for m in MESES_STR + ["total"]
    }
    out["desvio_orcado"] = {
        m: calculo_variacao_perc(out["realizado"][m], out["orcado"][m]) for m in MESES_STR + ["total"]
    }
    out["desvio_forecast"] = {
        m: calculo_variacao_perc(out["realizado"][m], out["forecast"][m]) for m in MESES_STR + ["total"]
    }
    out["holding_fator_mldu"] = ctx.factor_for_produto_mes(pid, ano, 12)
    return out


def _scale_acom_receitas_for_ctx(ctx: HoldingContext, item: dict, payload: dict) -> dict:
    pid = item.get("produto_id")
    ano = _payload_ano(payload, item)
    if not (ano and ctx.produto_is_temporal(pid)):
        return scale_acompanhamento_receitas_item(item, ctx.factor_for_produto(pid))
    out = _copia(item)
    for bucket in ("orcado", "forecast", "realizado"):
        for i, m in enumerate(MESES_STR, start=1):
            out[bucket][m] = _scale_number(out[bucket].get(m), ctx.factor_for_produto_mes(pid, ano, i))
        out[bucket]["total"] = sum(float(out[bucket][m] or 0) for m in MESES_STR)
    out["saldo_orcado"] = {
        m: calculo_variacao_rs(out["realizado"][m], out["orcado"][m]) for m in MESES_STR + ["total"]
    }
    out["saldo_forecast"] = {
        m: calculo_variacao_rs(out["forecast"][m], out["realizado"][m]) for m in MESES_STR + ["total"]
    }
    out["desvio_orcado"] = {
        m: calculo_variacao_perc(out["realizado"][m], out["orcado"][m]) for m in MESES_STR + ["total"]
    }
    out["desvio_forecast"] = {
        m: calculo_variacao_perc(out["realizado"][m], out["forecast"][m]) for m in MESES_STR + ["total"]
    }
    out["holding_fator_mldu"] = ctx.factor_for_produto_mes(pid, ano, 12)
    return out


def scale_venda_mes_row(mes_row: dict, factor: float) -> dict:
    out = dict(mes_row)
    out["vgv"] = _scale_number(out.get("vgv"), factor)
    out["ticket_medio"] = _scale_number(out.get("ticket_medio"), factor)
    out["holding_fator_mldu"] = factor
    return out


def scale_venda_grouped_row(row: dict, factor: float) -> dict:
    out = dict(row)
    out["meses"] = [scale_venda_mes_row(m, factor) for m in row.get("meses", [])]
    out["holding_fator_mldu"] = factor
    return out


def scale_acompanhamento_despesas_item(item: dict, factor: float) -> dict:
    out = _copia(item)
    for bucket in ("orcado", "forecast", "realizado"):
        for m in MESES_STR + ["total"]:
            out[bucket][m] = _scale_number(out[bucket].get(m), factor)
    out["saldo_orcado"] = {
        m: calculo_saldo_despesas(out["orcado"][m], out["realizado"][m]) for m in MESES_STR + ["total"]
    }
    out["saldo_forecast"] = {
        m: calculo_saldo_despesas(out["forecast"][m], out["realizado"][m]) for m in MESES_STR + ["total"]
    }
    out["desvio_orcado"] = {
        m: calculo_variacao_perc(out["realizado"][m], out["orcado"][m]) for m in MESES_STR + ["total"]
    }
    out["desvio_forecast"] = {
        m: calculo_variacao_perc(out["realizado"][m], out["forecast"][m]) for m in MESES_STR + ["total"]
    }
    out["holding_fator_mldu"] = factor
    return out


def scale_acompanhamento_receitas_item(item: dict, factor: float) -> dict:
    out = _copia(item)
    for bucket in ("orcado", "forecast", "realizado"):
        for m in MESES_STR + ["total"]:
            out[bucket][m] = _scale_number(out[bucket].get(m), factor)
    out["saldo_orcado"] = {
        m: calculo_variacao_rs(out["realizado"][m], out["orcado"][m]) for m in MESES_STR + ["total"]
    }
    out["saldo_forecast"] = {
        m: calculo_variacao_rs(out["realizado"][m], out["forecast"][m]) for m in MESES_STR + ["total"]
    }
    out["desvio_orcado"] = {
        m: calculo_variacao_perc(out["realizado"][m], out["orcado"][m]) for m in MESES_STR + ["total"]
    }
    out["desvio_forecast"] = {
        m: calculo_variacao_perc(out["realizado"][m], out["forecast"][m]) for m in MESES_STR + ["total"]
    }
    out["holding_fator_mldu"] = factor
    return out


def _scale_venda_bucket_month(bucket: dict, factor: float) -> None:
    bucket["vgv"] = _scale_number(bucket.get("vgv"), factor)
    unidades = bucket.get("unidades") or 0
    bucket["ticket"] = bucket["vgv"] / unidades if unidades else 0.0


def scale_acompanhamento_vendas_item(item: dict, factor: float) -> dict:
    out = _copia(item)
    for subcat in ("vendas", "distratos"):
        for source in ("orcado", "forecast", "realizado"):
            for m in MESES_STR:
                _scale_venda_bucket_month(out[subcat][source][m], factor)
            out[subcat][source]["total"]["vgv"] = sum(out[subcat][source][m]["vgv"] for m in MESES_STR)
            total_u = out[subcat][source]["total"].get("unidades") or 0
            out[subcat][source]["total"]["ticket"] = (
                out[subcat][source]["total"]["vgv"] / total_u if total_u else 0.0
            )

        for m in MESES_STR:
            out[f"desvio_orcado_{subcat}"][m] = calculo_variacao_perc(
                out[subcat]["realizado"][m]["vgv"], out[subcat]["orcado"][m]["vgv"]
            )
            out[f"desvio_forecast_{subcat}"][m] = calculo_variacao_perc(
                out[subcat]["realizado"][m]["vgv"], out[subcat]["forecast"][m]["vgv"]
            )
            out[f"desvio_orcado_{subcat}_unid"][m] = calculo_variacao_perc(
                out[subcat]["realizado"][m]["unidades"], out[subcat]["orcado"][m]["unidades"]
            )
            out[f"desvio_forecast_{subcat}_unid"][m] = calculo_variacao_perc(
                out[subcat]["realizado"][m]["unidades"], out[subcat]["forecast"][m]["unidades"]
            )

        out[f"desvio_orcado_{subcat}"]["total"] = calculo_variacao_perc(
            out[subcat]["realizado"]["total"]["vgv"], out[subcat]["orcado"]["total"]["vgv"]
        )
        out[f"desvio_forecast_{subcat}"]["total"] = calculo_variacao_perc(
            out[subcat]["realizado"]["total"]["vgv"], out[subcat]["forecast"]["total"]["vgv"]
        )
        out[f"desvio_orcado_{subcat}_unid"]["total"] = calculo_variacao_perc(
            out[subcat]["realizado"]["total"]["unidades"], out[subcat]["orcado"]["total"]["unidades"]
        )
        out[f"desvio_forecast_{subcat}_unid"]["total"] = calculo_variacao_perc(
            out[subcat]["realizado"]["total"]["unidades"], out[subcat]["forecast"]["total"]["unidades"]
        )

    out["holding_fator_mldu"] = factor
    return out


def apply_holding_mldu_read_layer(
    db: Session,
    payload: dict[str, Any],
    *,
    item_kind: str,
) -> dict[str, Any]:
    ctx = HoldingContext(db)
    out = dict(payload)

    if item_kind == "monthly":
        out["itens"] = [_scale_monthly_for_ctx(ctx, row, out) for row in out.get("itens", [])]
        if "itens_base" in out:
            out["itens_base"] = [_scale_monthly_for_ctx(ctx, row, out) for row in out.get("itens_base", [])]

    elif item_kind == "venda_grouped":
        out["itens"] = [
            scale_venda_grouped_row(row, ctx.factor_for_produto(row.get("produto_id")))
            for row in out.get("itens", [])
        ]
        if "itens_base" in out:
            scaled_base = []
            for row in out.get("itens_base", []):
                factor = ctx.factor_for_produto(row.get("produto_id"))
                base_row = dict(row)
                base_row["vgv"] = _scale_number(base_row.get("vgv"), factor)
                base_row["ticket_medio"] = _scale_number(base_row.get("ticket_medio"), factor)
                base_row["holding_fator_mldu"] = factor
                scaled_base.append(base_row)
            out["itens_base"] = scaled_base

    elif item_kind == "visualizacao_monthly":
        out["itens"] = [_scale_monthly_for_ctx(ctx, row, out) for row in out.get("itens", [])]

    elif item_kind == "visualizacao_venda":
        scaled = []
        for row in out.get("itens", []):
            factor = ctx.factor_for_produto(row.get("produto_id"))
            item = dict(row)
            item["vgv"] = _scale_number(item.get("vgv"), factor)
            item["ticket_medio"] = _scale_number(item.get("ticket_medio"), factor)
            item["holding_fator_mldu"] = factor
            scaled.append(item)
        out["itens"] = scaled

    elif item_kind == "acom_despesas":
        out["itens"] = [_scale_acom_despesas_for_ctx(ctx, row, out) for row in out.get("itens", [])]

    elif item_kind == "acom_receitas":
        out["itens"] = [_scale_acom_receitas_for_ctx(ctx, row, out) for row in out.get("itens", [])]

    elif item_kind == "acom_vendas":
        out["itens"] = [
            scale_acompanhamento_vendas_item(row, ctx.factor_for_produto(row.get("produto_id")))
            for row in out.get("itens", [])
        ]

    else:
        raise ValueError(f"item_kind desconhecido: {item_kind}")

    out["holding_mldu"] = True
    out["holding_avisos"] = list(dict.fromkeys(ctx.warnings))
    out["holding_fatores_produto"] = ctx.fatores_por_produto
    return out


def maybe_apply_holding_mldu(
    db: Session,
    holding_mldu: bool,
    payload: dict[str, Any],
    *,
    item_kind: str,
) -> dict[str, Any]:
    if not holding_mldu:
        return payload
    return apply_holding_mldu_read_layer(db, payload, item_kind=item_kind)


def list_holding_factors(db: Session) -> dict[str, Any]:
    ctx = HoldingContext(db)
    empresas = []
    for company in db.query(Company).all():
        pct = effective_for_company(company)
        empresas.append(
            {
                "company_id": company.id,
                "id_sienge": company.id_sienge,
                "nome": company.nome_fantasia or company.razao_social,
                "participacao_efetiva_pct": round(pct, 6),
                "fator": round(pct / 100.0, 8),
                "fonte": "manual" if company.usa_participacao_manual else "calculado",
            }
        )
    produtos = []
    for cc in db.query(CostCenter).all():
        emp_id = ctx.produto_empresa.get(cc.id, "")
        factor = ctx.factor_for_produto(cc.id)
        produtos.append(
            {
                "produto_id": cc.id,
                "nome": cc.nome,
                "id_empresa": emp_id,
                "fator_mldu": factor,
            }
        )
    return {
        "empresas": empresas,
        "produtos": produtos,
        "avisos": ctx.warnings,
    }
