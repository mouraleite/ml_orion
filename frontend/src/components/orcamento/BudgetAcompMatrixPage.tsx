"use client";

import React, { useState, useEffect, useCallback, useMemo, Fragment } from "react";
import Link from "next/link";
import { LucideIcon, AlertTriangle, ArrowUpDown } from "lucide-react";
import { orcamentoService } from "@/services/orcamento";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId, isDepartmentContextId } from "@/lib/useActiveDepartmentId";
import { DesvioLegend } from "@/components/orcamento/DesvioLegend";
import { DesvioExecStrip } from "@/components/orcamento/DesvioExecStrip";
import { DesvioBadgeBrand } from "@/components/orcamento/DesvioBadgeBrand";
import { SemaforoDesvio } from "@/components/orcamento/SemaforoDesvio";
import {
  MESES_STR,
  buildExecInsights,
  computeItemDesvio,
  formatMoedaCompact,
  isDesvioFavoravel,
  rowHighlightClass,
  type DesvioTipo,
} from "@/lib/orcamentoDesvioUi";
import { filterItensByPlanoNome } from "@/lib/orcamentoPlanFilters";
import { OrcamentoDeepLinks } from "@/components/orcamento/OrcamentoDeepLinks";
import { OrcamentoFlyoutFilterBar } from "@/components/orcamento/OrcamentoFlyoutFilterBar";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { useEmpresaCadastroFilter } from "@/hooks/useEmpresaCadastroFilter";
import { filterItensPorEmpresaIds } from "@/lib/gridFilters";

const MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

export interface BudgetAcompMatrixPageProps {
  title: string;
  subtitle: string;
  icon: LucideIcon;
  iconGradient: string;
  source: "despesas" | "receitas";
  desvioTipo: DesvioTipo;
  matchPlano: (nome: string) => boolean;
  emptyMessage?: string;
  deepLinkTarget?: "analitico1" | "realizadoCp";
}

export function BudgetAcompMatrixPage({
  title,
  subtitle,
  icon: Icon,
  source,
  desvioTipo,
  matchPlano,
  emptyMessage = "Nenhum plano encontrado para os filtros desta visão.",
  deepLinkTarget = "analitico1",
}: BudgetAcompMatrixPageProps) {
  const deptId = useActiveDepartmentId();
  const { holdingMldu, setHoldingMldu, canUseHoldingMldu } = useHoldingMldu("orcamento");
  const [ano, setAno] = useState(new Date().getFullYear());
  const [modo, setModo] = useState<"orcado" | "forecast">("orcado");
  const [forecastId, setForecastId] = useState<number | "">("");
  const [meses, setMeses] = useState<string[]>([]);
  const { filtroEmpresaIds, setFiltroEmpresaIds, empresaOpcoes } = useEmpresaCadastroFilter();
  const [sortByDesvio, setSortByDesvio] = useState(true);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isDepartmentContextId(deptId)) return;
    setData(null);
    setLoading(true);
    setError(null);
    try {
      const fn = source === "despesas"
        ? orcamentoService.getAcompanhamentoDespesas
        : orcamentoService.getAcompanhamentoReceitas;
      const res = await fn(ano, deptId, false, forecastId || undefined, holdingMldu);
      setData(res);
      if (forecastId === "" && res.active_forecast_id) setForecastId(res.active_forecast_id);
    } catch {
      setData(null);
      setError(`Erro ao carregar ${title.toLowerCase()}.`);
    } finally {
      setLoading(false);
    }
  }, [ano, forecastId, deptId, holdingMldu, source, title]);

  useEffect(() => { load(); }, [load]);

  const ref = modo;
  const getProdNome = useCallback(
    (id: number) => data?.opcoes_produtos?.find((p: any) => p.id === id)?.nome || String(id),
    [data?.opcoes_produtos],
  );
  const getPlanoNome = useCallback(
    (id: number) => data?.opcoes_planos?.find((p: any) => p.id === id)?.nome || String(id),
    [data?.opcoes_planos],
  );

  const filteredItens = useMemo(() => {
    const byEmpresa = filterItensPorEmpresaIds(
      data?.itens || [],
      data?.opcoes_produtos || [],
      filtroEmpresaIds,
    );
    const raw = filterItensByPlanoNome(byEmpresa, getPlanoNome, matchPlano);
    if (!sortByDesvio) return raw;
    return [...raw].sort((a, b) => {
      const da = computeItemDesvio(a, ref);
      const db = computeItemDesvio(b, ref);
      return db.absVarRs - da.absVarRs;
    });
  }, [data?.itens, data?.opcoes_produtos, filtroEmpresaIds, getPlanoNome, matchPlano, sortByDesvio, ref]);

  const insights = useMemo(
    () => buildExecInsights(filteredItens, ref, desvioTipo),
    [filteredItens, ref, desvioTipo],
  );

  const visibleMonthsIdx = MESES_STR.map((m, i) => i).filter(
    (i) => meses.length === 0 || meses.includes(MESES_STR[i]),
  );
  const colMonths = [...visibleMonthsIdx.map((i) => MESES_STR[i]), "total"];
  const refLabel = modo === "orcado" ? "orçado" : "forecast";
  const inverted = desvioTipo === "DESPESAS";

  return (
    <div className="space-y-4 pb-10 flex flex-col h-[calc(100vh-120px)]">
      <div className="shrink-0">
        <h1 className="text-2xl font-bold text-slate-800">{title}</h1>
        <p className="text-slate-500 text-sm mt-1">{subtitle}</p>
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
        <button
          type="button"
          onClick={() => setSortByDesvio((v) => !v)}
          className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium border rounded-lg ${sortByDesvio ? "bg-ml-green text-white border-ml-green" : "bg-white text-slate-600 border-slate-200"}`}
        >
          <ArrowUpDown className="w-4 h-4" />
          Maior desvio
        </button>
      </OrcamentoFlyoutFilterBar>

      {holdingMldu && <HoldingMlduBanner avisos={data?.holding_avisos} />}

      {error && (
        <div className="flex items-center gap-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl px-4 py-3 text-sm shrink-0">
          <AlertTriangle className="w-5 h-5 shrink-0" />{error}
        </div>
      )}

      {!loading && filteredItens.length > 0 && (
        <>
          <DesvioExecStrip
            narrative={insights.narrative}
            favoravel={insights.favoravel}
            varRs={insights.varRs}
            varPerc={insights.varPerc}
            materialCount={insights.materialCount}
            comDesvioCount={insights.comDesvioCount}
            refLabel={refLabel}
            n={insights.realTotal}
            ref={insights.refTotal}
            tipo={desvioTipo}
          />
          <DesvioLegend />
        </>
      )}

      {loading ? (
        <div className="flex-1 flex items-center justify-center bg-white rounded-2xl border border-slate-200">
          <AppLoadingState />
        </div>
      ) : filteredItens.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-400 bg-white rounded-2xl border border-slate-200 gap-3">
          <Icon className="w-12 h-12 opacity-20" />
          <p>{emptyMessage}</p>
          <Link href="/dashboard/orcamento/resumo-geral" className="text-sm text-ml-green font-semibold hover:underline">
            Ver resumo geral →
          </Link>
        </div>
      ) : (
        <div className="flex-1 overflow-auto bg-white rounded-2xl border border-slate-200 shadow-sm">
          <table className="w-full text-left border-collapse min-w-max text-xs">
            <thead className="bg-slate-100 text-slate-600 uppercase font-semibold sticky top-0 z-30">
              <tr>
                <th className="px-3 py-3 min-w-[180px] sticky left-0 bg-slate-100 z-40">Produto</th>
                <th className="px-3 py-3 min-w-[160px] sticky left-[180px] bg-slate-100 z-40 shadow-[1px_0_0_0_#e2e8f0]">Plano</th>
                <th className="px-3 py-3 min-w-[90px] sticky left-[340px] bg-slate-100 z-40 shadow-[1px_0_0_0_#e2e8f0]">Métrica</th>
                {visibleMonthsIdx.map((i) => <th key={MESES[i]} className="px-3 py-3 text-right">{MESES[i]}</th>)}
                <th className="px-3 py-3 text-right bg-slate-200">Total</th>
                <th className="px-3 py-3 w-24">Detalhe</th>
              </tr>
            </thead>
            <tbody>
              {filteredItens.map((item: any, idx: number) => {
                const d = computeItemDesvio(item, ref);
                const fav = isDesvioFavoravel(d.varRs, desvioTipo);
                const highlight = rowHighlightClass(d.varPerc, fav);
                const desvioKey = modo === "orcado" ? "desvio_orcado" : "desvio_forecast";
                const rows = [
                  { label: modo === "orcado" ? "Orçado" : "Forecast", key: ref, cls: "bg-white" },
                  { label: "Realizado", key: "realizado", cls: "bg-slate-50/80" },
                  { label: "Desvio %", key: desvioKey, cls: "bg-orange-50/40", isPerc: true },
                ];
                return (
                  <Fragment key={`${item.produto_id}-${item.plano_financeiro_id}-${idx}`}>
                    {rows.map((row, ri) => (
                      <tr key={ri} className={`border-b border-slate-100 hover:bg-slate-50/80 ${ri === 0 ? highlight : ""} ${row.cls}`}>
                        {ri === 0 && (
                          <td rowSpan={3} className="px-3 py-2 font-semibold text-slate-700 sticky left-0 bg-inherit z-20 align-top max-w-[180px] truncate" title={getProdNome(item.produto_id)}>
                            {getProdNome(item.produto_id)}
                          </td>
                        )}
                        {ri === 0 && (
                          <td rowSpan={3} className="px-3 py-2 text-slate-600 sticky left-[180px] bg-inherit z-20 align-top max-w-[160px] truncate shadow-[1px_0_0_0_#e2e8f0]" title={getPlanoNome(item.plano_financeiro_id)}>
                            {getPlanoNome(item.plano_financeiro_id)}
                          </td>
                        )}
                        <td className="px-3 py-2 text-slate-500 font-medium sticky left-[340px] bg-inherit z-20 shadow-[1px_0_0_0_#e2e8f0]">{row.label}</td>
                        {colMonths.map((m) => (
                          <td key={m} className={`px-3 py-2 text-right tabular-nums ${m === "total" ? "font-bold border-l border-slate-200" : ""}`}>
                            {row.isPerc ? (
                              <span className="inline-flex items-center justify-end gap-1.5">
                                {m === "total" ? <SemaforoDesvio n={d.real} ref={d.ref} tipo={desvioTipo} /> : null}
                                <DesvioBadgeBrand value={item[row.key]?.[m] || 0} inverted={inverted} />
                              </span>
                            ) : formatMoedaCompact(item[row.key]?.[m] || 0)}
                          </td>
                        ))}
                        {ri === 0 && (
                          <td rowSpan={3} className="px-2 py-2 align-top">
                            <OrcamentoDeepLinks
                              variant="compact"
                              params={{
                                ano,
                                modo,
                                meses: meses.length ? meses : undefined,
                                produto: item.produto_id,
                                plano: item.plano_financeiro_id,
                                expand: deepLinkTarget === "analitico1",
                              }}
                            />
                          </td>
                        )}
                      </tr>
                    ))}
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
