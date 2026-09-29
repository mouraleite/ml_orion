"use client";

import React, { useState, useEffect, useCallback, Fragment, useMemo, useRef } from "react";
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
import {
  RealizadoDespesasDrillTable,
  ParcelaDespesa,
} from "@/components/orcamento/RealizadoDespesasDrillTable";
import {
  Layers, ChevronDown, ChevronRight, AlertTriangle, BarChart2, Receipt,
} from "lucide-react";
import { OrcamentoFlyoutFilterBar } from "@/components/orcamento/OrcamentoFlyoutFilterBar";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { useEmpresaCadastroFilter } from "@/hooks/useEmpresaCadastroFilter";
import { filterItensPorEmpresaIds } from "@/lib/gridFilters";

const MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const MESES_STR = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

type MesMap = Record<string, number>;

interface PlanoAgg {
  plano_id: number;
  plano_nome: string;
  orcado: MesMap;
  forecast: MesMap;
  realizado: MesMap;
}

const emptyMesMap = (): MesMap =>
  Object.fromEntries([...MESES_STR, "total"].map((m) => [m, 0]));

const formatMoeda = (v: number) => {
  if (!v) return "R$ 0";
  return v.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
};

function aggregateByPlano(itens: any[]): PlanoAgg[] {
  const map = new Map<number, PlanoAgg>();

  for (const item of itens) {
    const plid = item.plano_financeiro_id;
    if (!plid) continue;
    if (!map.has(plid)) {
      map.set(plid, {
        plano_id: plid,
        plano_nome: String(plid),
        orcado: emptyMesMap(),
        forecast: emptyMesMap(),
        realizado: emptyMesMap(),
      });
    }
    const row = map.get(plid)!;
    for (const tp of ["orcado", "forecast", "realizado"] as const) {
      const src = item[tp] || {};
      for (const m of [...MESES_STR, "total"]) {
        row[tp][m] += src[m] || 0;
      }
    }
  }

  return Array.from(map.values()).sort((a, b) =>
    a.plano_nome.localeCompare(b.plano_nome, "pt-BR", { numeric: true }),
  );
}

export default function AnaliticoGastos2Page() {
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

  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [drillCache, setDrillCache] = useState<Record<number, ParcelaDespesa[]>>({});
  const [drillLoading, setDrillLoading] = useState<Set<number>>(new Set());
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
      const res = await orcamentoService.getAcompanhamentoDespesas(
        ano, deptId, false, forecastId || undefined, holdingMldu,
      );
      if (seq !== loadSeq.current) return;
      setData(res);
      if (forecastId === "" && res.active_forecast_id) setForecastId(res.active_forecast_id);
    } catch {
      if (seq !== loadSeq.current) return;
      setData(null);
      setError("Erro ao carregar analítico de gastos II.");
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

  const visibleMonthsIdx = MESES_STR.map((m, i) => i).filter(
    (i) => meses.length === 0 || meses.includes(MESES_STR[i]),
  );
  const visibleMesesStr = visibleMonthsIdx.map((i) => MESES_STR[i]);
  const showTotalCol = meses.length === 0 || visibleMesesStr.length > 1;

  const getPlanoNome = useCallback(
    (id: number) => data?.opcoes_planos?.find((p: any) => p.id === id)?.nome || String(id),
    [data?.opcoes_planos],
  );

  const planoRows = useMemo(() => {
    const itens = filterItensPorEmpresaIds(
      data?.itens || [],
      data?.opcoes_produtos || [],
      filtroEmpresaIds,
    );
    const rows = aggregateByPlano(itens);
    return rows.map((r) => ({ ...r, plano_nome: getPlanoNome(r.plano_id) }));
  }, [data?.itens, data?.opcoes_produtos, filtroEmpresaIds, getPlanoNome]);

  const refKey = modo;

  const execInsights = useMemo(() => {
    if (!planoRows.length) return null;
    const asItems = planoRows.map((r) => ({
      orcado: r.orcado,
      forecast: r.forecast,
      realizado: r.realizado,
    }));
    return buildExecInsights(asItems, refKey, "DESPESAS");
  }, [planoRows, refKey]);

  const loadDrill = useCallback(async (planoId: number) => {
    if (!isDepartmentContextId(deptId)) return;
    setDrillLoading((prev) => new Set(prev).add(planoId));
    try {
      const res = await orcamentoService.getRealizadoDespesas(ano, deptId, {
        holdingMldu,
        planoId,
      });
      setDrillCache((prev) => ({ ...prev, [planoId]: res.transacoes || [] }));
    } catch {
      setDrillCache((prev) => ({ ...prev, [planoId]: [] }));
    } finally {
      setDrillLoading((prev) => {
        const next = new Set(prev);
        next.delete(planoId);
        return next;
      });
    }
  }, [ano, deptId, holdingMldu]);

  useEffect(() => {
    if (deepLinkApplied.current || loading || !planoRows.length) return;
    const { plano, expand } = deepLink;
    if (expand && plano) {
      setExpanded((prev) => new Set(prev).add(plano));
      if (!drillCache[plano]) void loadDrill(plano);
      deepLinkApplied.current = true;
    }
  }, [loading, planoRows, deepLink, drillCache, loadDrill]);

  const toggleExpand = (planoId: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(planoId)) {
        next.delete(planoId);
      } else {
        next.add(planoId);
        if (!drillCache[planoId]) void loadDrill(planoId);
      }
      return next;
    });
  };

  const drillFiltered = (rows: ParcelaDespesa[]) => {
    const byEmpresa = filterItensPorEmpresaIds(rows, data?.opcoes_produtos || [], filtroEmpresaIds);
    if (!meses.length) return byEmpresa;
    return byEmpresa.filter((r) => r.mes && meses.includes(r.mes));
  };

  const modoLabel = modo === "orcado" ? "Orçado" : "Forecast";
  const colSpanCount =
    1 + visibleMesesStr.length * 3 + (showTotalCol ? 3 : 0);

  return (
    <div className="w-max min-w-full">
      <div className="sticky left-0 z-20 w-[100cqw] max-w-[100cqw] space-y-4 bg-slate-50 px-6 md:px-8 pt-6 md:pt-8 pb-4">
      <div className="shrink-0">
        <h1 className="text-2xl font-bold text-slate-800">Analítico de Gastos II</h1>
        <p className="text-slate-500 text-sm mt-1">
          Saídas por plano financeiro — consolidado de todos os produtos
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
          href="/dashboard/orcamento/analitico-gastos-1"
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <BarChart2 className="w-4 h-4" />
          Analítico I
        </Link>
      </OrcamentoFlyoutFilterBar>

      {holdingMldu && (
        <div className="shrink-0">
          <HoldingMlduBanner avisos={data?.holding_avisos} />
        </div>
      )}

      <div className="flex items-start gap-2 text-xs text-slate-500 bg-blue-50 border border-blue-100 rounded-xl px-4 py-2.5 shrink-0">
        <Receipt className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
        <span>
          Expanda um plano para ver parcelas pagas (Contas a Pagar). Totais consolidam todos os centros de custo do departamento.
        </span>
      </div>

      {error && (
        <div className="flex items-center gap-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl px-4 py-3 text-sm shrink-0">
          <AlertTriangle className="w-5 h-5 shrink-0" />{error}
        </div>
      )}

      {!loading && execInsights && planoRows.length > 0 && (
        <>
          <DesvioExecStrip
            narrative={execInsights.narrative}
            favoravel={execInsights.favoravel}
            varRs={execInsights.varRs}
            varPerc={execInsights.varPerc}
            materialCount={execInsights.materialCount}
            comDesvioCount={execInsights.comDesvioCount}
            refLabel={modoLabel.toLowerCase()}
          />
          <DesvioLegend className="shrink-0" />
        </>
      )}
      </div>

      {loading ? (
        <div className="flex-1 min-h-0 flex items-center justify-center bg-white rounded-2xl border border-slate-200 shadow-sm">
          <AppLoadingState />
        </div>
      ) : planoRows.length === 0 ? (
        <div className="flex-1 min-h-0 flex flex-col items-center justify-center text-slate-400 bg-white rounded-2xl border border-slate-200 shadow-sm gap-3">
          <Layers className="w-12 h-12 opacity-20" />
          <p>Nenhuma despesa encontrada.</p>
        </div>
      ) : (
        <div className="mx-6 md:mx-8 mb-6 bg-white rounded-2xl border border-slate-200 shadow-sm">
          <table className="w-full text-left border-collapse min-w-max text-xs">
            <thead className="bg-slate-100 text-slate-600 uppercase font-semibold sticky top-0 z-30 shadow-sm">
              <tr>
                <th rowSpan={2} className="px-2 py-2 w-8 sticky left-6 md:left-8 bg-slate-100 z-40" />
                <th
                  rowSpan={2}
                  className="px-3 py-3 min-w-[260px] sticky left-14 md:left-16 bg-slate-100 shadow-[1px_0_0_0_#e2e8f0] z-40 align-bottom"
                >
                  Plano financeiro
                </th>
                {visibleMonthsIdx.map((i) => (
                  <th
                    key={MESES[i]}
                    colSpan={3}
                    className="px-2 py-2 text-center border-l border-slate-200"
                  >
                    {MESES[i]}
                  </th>
                ))}
                {showTotalCol && (
                  <th colSpan={3} className="px-2 py-2 text-center border-l-2 border-slate-300 bg-slate-200">
                    Total
                  </th>
                )}
              </tr>
              <tr>
                {visibleMonthsIdx.map((i) => (
                  <Fragment key={`sub-${MESES[i]}`}>
                    <th className="px-2 py-1.5 text-right border-l border-slate-200 text-[10px] whitespace-nowrap">
                      {modoLabel}
                    </th>
                    <th className="px-2 py-1.5 text-right text-[10px] whitespace-nowrap">Realizado</th>
                    <th className="px-2 py-1.5 text-right text-[10px] whitespace-nowrap">Variação</th>
                  </Fragment>
                ))}
                {showTotalCol && (
                  <>
                    <th className="px-2 py-1.5 text-right border-l-2 border-slate-300 bg-slate-200/80 text-[10px]">
                      {modoLabel}
                    </th>
                    <th className="px-2 py-1.5 text-right bg-slate-200/80 text-[10px]">Realizado</th>
                    <th className="px-2 py-1.5 text-right bg-slate-200/80 text-[10px]">Variação</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {planoRows.map((row) => {
                const isOpen = expanded.has(row.plano_id);
                const drillRows = drillCache[row.plano_id] || [];

                const totalRef = visibleMesesStr.reduce(
                  (s, m) => s + (row[refKey][m] || 0),
                  0,
                );
                const totalReal = visibleMesesStr.reduce(
                  (s, m) => s + (row.realizado[m] || 0),
                  0,
                );
                const insightItem = {
                  orcado: row.orcado,
                  forecast: row.forecast,
                  realizado: row.realizado,
                };
                const d = computeItemDesvio(insightItem, refKey);
                const fav = isDesvioFavoravel(d.varRs, "DESPESAS");
                const highlight = rowHighlightClass(d.varPerc, fav);

                return (
                  <Fragment key={row.plano_id}>
                    <tr className={`border-b border-slate-200 hover:bg-slate-50/80 transition-colors ${highlight}`}>
                      <td className="px-1 py-2 sticky left-6 md:left-8 bg-white shadow-[1px_0_0_0_#e2e8f0] z-20">
                        <button
                          type="button"
                          onClick={() => toggleExpand(row.plano_id)}
                          className="p-1 rounded hover:bg-slate-200 text-slate-500"
                          title="Ver parcelas pagas (Contas a Pagar)"
                        >
                          {isOpen ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                        </button>
                      </td>
                      <td
                        className="px-3 py-2 font-medium text-slate-700 sticky left-14 md:left-16 bg-white shadow-[1px_0_0_0_#e2e8f0] z-20 max-w-[320px]"
                        title={row.plano_nome}
                      >
                        <span className="line-clamp-2">{row.plano_nome}</span>
                      </td>

                      {visibleMesesStr.map((m) => {
                        const refVal = row[refKey][m] || 0;
                        const realVal = row.realizado[m] || 0;
                        const varVal = refVal - realVal;
                        return (
                          <Fragment key={m}>
                            <td className="px-2 py-2 text-right tabular-nums border-l border-slate-100 text-slate-600">
                              {formatMoeda(refVal)}
                            </td>
                            <td className="px-2 py-2 text-right tabular-nums font-medium text-slate-800">
                              {formatMoeda(realVal)}
                            </td>
                            <td
                              className={`px-2 py-2 text-right tabular-nums font-medium ${
                                varVal >= 0 ? "text-emerald-600" : "text-red-600"
                              }`}
                            >
                              {formatMoeda(varVal)}
                            </td>
                          </Fragment>
                        );
                      })}

                      {showTotalCol && (() => {
                        const refVal =
                          meses.length > 0
                            ? totalRef
                            : row[refKey].total ?? totalRef;
                        const realVal =
                          meses.length > 0
                            ? totalReal
                            : row.realizado.total ?? totalReal;
                        const varVal = refVal - realVal;
                        return (
                          <>
                            <td className="px-2 py-2 text-right tabular-nums border-l-2 border-slate-200 bg-slate-50 font-semibold">
                              {formatMoeda(refVal)}
                            </td>
                            <td className="px-2 py-2 text-right tabular-nums bg-slate-50 font-bold text-slate-800">
                              {formatMoeda(realVal)}
                            </td>
                            <td
                              className={`px-2 py-2 text-right tabular-nums bg-slate-50 font-bold ${
                                varVal >= 0 ? "text-emerald-600" : "text-red-600"
                              }`}
                            >
                              {formatMoeda(varVal)}
                            </td>
                          </>
                        );
                      })()}
                    </tr>

                    {isOpen && (
                      <tr className="bg-slate-50/90 border-b-2 border-slate-300">
                        <td colSpan={colSpanCount + 2} className="px-4 py-3">
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                            <div className="text-xs font-semibold text-slate-600 uppercase tracking-wide flex items-center gap-2">
                              <Receipt className="w-4 h-4 text-slate-500" />
                              Parcelas pagas — {row.plano_nome}
                            </div>
                          </div>
                          <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
                            <RealizadoDespesasDrillTable
                              transacoes={drillFiltered(drillRows)}
                              loading={drillLoading.has(row.plano_id)}
                              compact
                              showProdutoPlano
                              mesesVisiveis={visibleMesesStr.length ? visibleMesesStr : MESES_STR}
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
