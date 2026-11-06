"use client";

import React, { useState, useEffect, useCallback, Fragment, useRef, useMemo } from "react";
import Link from "next/link";
import { orcamentoService } from "@/services/orcamento";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId, isDepartmentContextId } from "@/lib/useActiveDepartmentId";
import { useOrcamentoDeepLinkFilters } from "@/lib/orcamentoNavigation";
import {
  buildExecInsights,
  computeItemDesvio,
  isDesvioFavoravel,
  rowHighlightClass,
} from "@/lib/orcamentoDesvioUi";
import { DesvioLegend } from "@/components/orcamento/DesvioLegend";
import { DesvioExecStrip } from "@/components/orcamento/DesvioExecStrip";
import { DesvioBadgeBrand } from "@/components/orcamento/DesvioBadgeBrand";
import {
  RealizadoDespesasDrillTable,
  ParcelaDespesa,
} from "@/components/orcamento/RealizadoDespesasDrillTable";
import {
  BarChart2, TrendingUp, TrendingDown,
  ChevronDown, ChevronRight, AlertTriangle, Receipt, Layers,
} from "lucide-react";
import { OrcamentoFlyoutFilterBar } from "@/components/orcamento/OrcamentoFlyoutFilterBar";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { useEmpresaCadastroFilter } from "@/hooks/useEmpresaCadastroFilter";
import { filterItensPorEmpresaIds } from "@/lib/gridFilters";

const MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const MESES_STR = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

const formatMoeda = (v: number) => {
  if (!v) return "R$ 0";
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 0, maximumFractionDigits: 0 });
};

function DesvBadge({ value }: { value: number }) {
  return <DesvioBadgeBrand value={value} inverted />;
}

function itemKey(produtoId: number, planoId: number) {
  return `${produtoId}-${planoId}`;
}

export default function AnaliticoGastosPage() {
  const deptId = useActiveDepartmentId();
  const { holdingMldu, setHoldingMldu, canUseHoldingMldu } = useHoldingMldu("orcamento");
  const [ano, setAno] = useState(new Date().getFullYear());
  const [modo, setModo] = useState<"orcado" | "forecast">("orcado");
  const [forecastId, setForecastId] = useState<number | "">("");
  const [meses, setMeses] = useState<string[]>([]);
  const { filtroEmpresaIds, setFiltroEmpresaIds, empresaOpcoes } = useEmpresaCadastroFilter();

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [drillCache, setDrillCache] = useState<Record<string, ParcelaDespesa[]>>({});
  const [drillLoading, setDrillLoading] = useState<Set<string>>(new Set());
  const deepLinkApplied = useRef(false);
  const loadSeq = useRef(0);

  const deepLink = useOrcamentoDeepLinkFilters({
    setAno,
    setModo,
    setMeses,
  });

  const load = useCallback(async () => {
    if (!isDepartmentContextId(deptId)) return;
    const seq = ++loadSeq.current;
    setData(null);
    setLoading(true);
    setError(null);
    try {
      const res = await orcamentoService.getAcompanhamentoDespesas(ano, deptId, false, forecastId || undefined, holdingMldu);
      if (seq !== loadSeq.current) return;
      setData(res);
      if (forecastId === "" && res.active_forecast_id) setForecastId(res.active_forecast_id);
    } catch {
      if (seq !== loadSeq.current) return;
      setData(null);
      setError("Erro ao carregar analítico de gastos.");
    } finally {
      if (seq === loadSeq.current) setLoading(false);
    }
  }, [ano, forecastId, deptId, holdingMldu]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    setExpanded(new Set());
    setDrillCache({});
    deepLinkApplied.current = false;
  }, [ano, deptId, holdingMldu, meses]);

  const visibleMonthsIdx = MESES_STR.map((m, i) => i).filter(i => meses.length === 0 || meses.includes(MESES_STR[i]));
  const visibleMesesStr = visibleMonthsIdx.map(i => MESES_STR[i]);
  const colMonths = [...visibleMesesStr, "total"];

  const getProdNome = useCallback((id: number) => data?.opcoes_produtos?.find((p: any) => p.id === id)?.nome || id, [data?.opcoes_produtos]);
  const getPlanoNome = useCallback((id: number) => data?.opcoes_planos?.find((p: any) => p.id === id)?.nome || id, [data?.opcoes_planos]);

  const loadDrill = useCallback(async (produtoId: number, planoId: number) => {
    if (!isDepartmentContextId(deptId)) return;
    const key = itemKey(produtoId, planoId);
    setDrillLoading(prev => new Set(prev).add(key));
    try {
      const res = await orcamentoService.getRealizadoDespesas(ano, deptId, {
        holdingMldu,
        produtoId: produtoId,
        planoId: planoId,
      });
      setDrillCache(prev => ({ ...prev, [key]: res.transacoes || [] }));
    } catch {
      setDrillCache(prev => ({ ...prev, [key]: [] }));
    } finally {
      setDrillLoading(prev => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  }, [ano, deptId, holdingMldu]);

  useEffect(() => {
    if (deepLinkApplied.current || loading || !data?.itens?.length) return;
    const { produto, plano, expand } = deepLink;
    if (expand && produto && plano) {
      const key = itemKey(produto, plano);
      setExpanded((prev) => new Set(prev).add(key));
      if (!drillCache[key]) void loadDrill(produto, plano);
      deepLinkApplied.current = true;
    }
  }, [loading, data, deepLink, drillCache, loadDrill]);

  const toggleExpand = (produtoId: number, planoId: number) => {
    const key = itemKey(produtoId, planoId);
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
        if (!drillCache[key]) void loadDrill(produtoId, planoId);
      }
      return next;
    });
  };

  const rawItens = useMemo(
    () => filterItensPorEmpresaIds(
      data?.itens || [],
      data?.opcoes_produtos || [],
      filtroEmpresaIds,
    ),
    [data?.itens, data?.opcoes_produtos, filtroEmpresaIds],
  );
  const ref = modo;

  const execInsights = useMemo(
    () => (rawItens.length ? buildExecInsights(rawItens, ref, "DESPESAS") : null),
    [rawItens, ref],
  );

  const drillFiltered = (rows: ParcelaDespesa[]) => {
    const byEmpresa = filterItensPorEmpresaIds(rows, data?.opcoes_produtos || [], filtroEmpresaIds);
    if (!meses.length) return byEmpresa;
    return byEmpresa.filter(r => r.mes && meses.includes(r.mes));
  };

  return (
    <div className="space-y-6 pb-10 flex flex-col h-[calc(100vh-120px)]">
      <div className="shrink-0">
        <h1 className="text-2xl font-bold text-slate-800">Analítico de Gastos I</h1>
        <p className="text-slate-500 text-sm mt-1">
          Despesas por Produto e Plano — expanda o realizado para ver parcelas de Contas a Pagar
        </p>
      </div>
      <OrcamentoFlyoutFilterBar
        holdingMldu={holdingMldu}
        onHoldingMlduChange={setHoldingMldu}
        canUseHoldingMldu={canUseHoldingMldu}
        empresaOpcoes={empresaOpcoes}
        filtroEmpresaIds={filtroEmpresaIds}
        onEmpresaChange={setFiltroEmpresaIds}
        meses={meses}
        onMesesChange={setMeses}
        ano={ano}
        onAnoChange={setAno}
        modo={modo}
        onModoChange={setModo}
        onRefresh={load}
        loading={loading}
      >
        <Link
          href="/dashboard/orcamento/analitico-gastos-2"
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <Layers className="w-4 h-4" />
          Analítico II
        </Link>
        <Link
          href="/dashboard/orcamento/realizado-despesas"
          title="Abre o realizado detalhado de Contas a Pagar (credor, documento e valor)"
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <Receipt className="w-4 h-4" />
          Realizado detalhado
        </Link>
      </OrcamentoFlyoutFilterBar>

      {holdingMldu && <HoldingMlduBanner avisos={data?.holding_avisos} />}

      {error && (
        <div className="flex items-center gap-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl px-4 py-3 text-sm shrink-0">
          <AlertTriangle className="w-5 h-5 shrink-0" />{error}
        </div>
      )}

      {!loading && execInsights && rawItens.length > 0 && (
        <>
          <DesvioExecStrip
            narrative={execInsights.narrative}
            favoravel={execInsights.favoravel}
            varRs={execInsights.varRs}
            varPerc={execInsights.varPerc}
            materialCount={execInsights.materialCount}
            comDesvioCount={execInsights.comDesvioCount}
            refLabel={modo === "orcado" ? "orçado" : "forecast"}
            n={execInsights.realTotal}
            ref={execInsights.refTotal}
            tipo="DESPESAS"
          />
          <DesvioLegend className="shrink-0" />
        </>
      )}

      {loading ? (
        <div className="flex-1 flex items-center justify-center bg-white rounded-2xl border border-slate-200 shadow-sm">
          <AppLoadingState />
        </div>
      ) : rawItens.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-400 bg-white rounded-2xl border border-slate-200 shadow-sm gap-3">
          <BarChart2 className="w-12 h-12 opacity-20" />
          <p>Nenhuma despesa encontrada.</p>
        </div>
      ) : (
        <div className="flex-1 overflow-auto bg-white rounded-2xl border border-slate-200 shadow-sm">
          <table className="w-full text-left border-collapse min-w-max text-xs">
            <thead className="bg-slate-100 text-slate-600 uppercase font-semibold sticky top-0 z-30 shadow-sm">
              <tr>
                <th className="px-3 py-3 w-8 sticky left-0 bg-slate-100 z-40" />
                <th className="px-3 py-3 min-w-[180px] sticky left-8 bg-slate-100 shadow-[1px_0_0_0_#e2e8f0] z-40">Produto</th>
                <th className="px-3 py-3 min-w-[140px] sticky left-[212px] bg-slate-100 shadow-[1px_0_0_0_#e2e8f0] z-40">Plano Financeiro</th>
                <th className="px-3 py-3 min-w-[100px] sticky left-[352px] bg-slate-100 shadow-[1px_0_0_0_#e2e8f0] z-40">Métrica</th>
                {visibleMonthsIdx.map(i => <th key={MESES[i]} className="px-3 py-3 text-right">{MESES[i]}</th>)}
                <th className="px-3 py-3 text-right bg-slate-200">Total</th>
              </tr>
            </thead>
            <tbody>
              {rawItens.map((item: any, idx: number) => {
                const key = itemKey(item.produto_id, item.plano_financeiro_id);
                const isOpen = expanded.has(key);
                const drillRows = drillCache[key] || [];
                const d = computeItemDesvio(item, ref);
                const fav = isDesvioFavoravel(d.varRs, "DESPESAS");
                const highlight = rowHighlightClass(d.varPerc, fav);

                const rows = [
                  { label: modo === "orcado" ? "Orçado" : "Forecast", key: ref, cls: "bg-white" },
                  { label: "Realizado", key: "realizado", cls: "bg-slate-50", isRealizado: true },
                  { label: "Saldo", key: modo === "orcado" ? "saldo_orcado" : "saldo_forecast", cls: "bg-emerald-50/50", isSaldo: true },
                  { label: "Desvio %", key: modo === "orcado" ? "desvio_orcado" : "desvio_forecast", cls: "bg-orange-50/50", isPerc: true },
                ];

                return (
                  <Fragment key={idx}>
                    {rows.map((row, ri) => (
                      <tr key={`${idx}-${ri}`} className={`hover:bg-slate-100/50 transition-colors border-b border-slate-200 ${row.cls} ${ri === 0 ? highlight : ""}`}>
                        {ri === 0 && (
                          <td rowSpan={4} className="px-1 py-2 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-20 align-top">
                            <button
                              type="button"
                              onClick={() => toggleExpand(item.produto_id, item.plano_financeiro_id)}
                              className="p-1 rounded hover:bg-slate-200 text-slate-500"
                              title="Ver parcelas pagas (Contas a Pagar)"
                            >
                              {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                            </button>
                          </td>
                        )}
                        {ri === 0 && (
                          <td rowSpan={4} className="px-3 py-2 font-semibold text-slate-700 sticky left-8 bg-white shadow-[1px_0_0_0_#e2e8f0] z-20 align-top max-w-[180px] truncate" title={getProdNome(item.produto_id)}>
                            {getProdNome(item.produto_id)}
                          </td>
                        )}
                        {ri === 0 && (
                          <td rowSpan={4} className="px-3 py-2 text-slate-500 align-top sticky left-[212px] bg-white shadow-[1px_0_0_0_#e2e8f0] z-20 max-w-[140px] truncate" title={getPlanoNome(item.plano_financeiro_id)}>
                            {getPlanoNome(item.plano_financeiro_id)}
                          </td>
                        )}
                        <td className={`px-3 py-2 text-slate-500 font-medium whitespace-nowrap sticky left-[352px] shadow-[1px_0_0_0_#e2e8f0] z-20 ${row.cls}`}>
                          <span className="inline-flex items-center gap-1.5">
                            {row.label}
                            {"isRealizado" in row && row.isRealizado && (
                              <Receipt className="w-3 h-3 text-slate-400" />
                            )}
                          </span>
                        </td>
                        {colMonths.map(m => (
                          <td key={m} className={`px-3 py-2 text-right tabular-nums ${m === "total" ? "font-bold border-l border-slate-200" : ""}`}>
                            {"isPerc" in row && row.isPerc
                              ? <DesvBadge value={item[row.key]?.[m] || 0} />
                              : (
                                <span className={"isSaldo" in row && row.isSaldo ? ((item[row.key]?.[m] || 0) >= 0 ? "text-emerald-600 font-medium" : "text-red-600 font-medium") : ""}>
                                  {formatMoeda(item[row.key]?.[m] || 0)}
                                </span>
                              )}
                          </td>
                        ))}
                      </tr>
                    ))}

                    {isOpen && (
                      <tr className="bg-slate-50/90 border-b-2 border-slate-300">
                        <td colSpan={4 + colMonths.length} className="px-4 py-3">
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                            <div className="text-xs font-semibold text-slate-600 uppercase tracking-wide flex items-center gap-2">
                              <Receipt className="w-4 h-4 text-slate-500" />
                              Parcelas pagas — Contas a Pagar
                            </div>
                          </div>
                          <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
                            <RealizadoDespesasDrillTable
                              transacoes={drillFiltered(drillRows)}
                              loading={drillLoading.has(key)}
                              compact
                              mesesVisiveis={visibleMesesStr}
                            />
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
