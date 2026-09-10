"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { AlertTriangle } from "lucide-react";
import { orcamentoService } from "@/services/orcamento";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId, isDepartmentContextId } from "@/lib/useActiveDepartmentId";
import { DesvioLegend } from "@/components/orcamento/DesvioLegend";
import { DesvioExecStrip } from "@/components/orcamento/DesvioExecStrip";
import { DesvioBadgeBrand } from "@/components/orcamento/DesvioBadgeBrand";
import {
  MESES_STR,
  buildExecInsights,
  formatMoedaCompact,
  isDesvioFavoravel,
  rowHighlightClass,
} from "@/lib/orcamentoDesvioUi";
import { recebimentoGrupoKey } from "@/lib/orcamentoPlanFilters";
import { OrcamentoFlyoutFilterBar } from "@/components/orcamento/OrcamentoFlyoutFilterBar";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { useEmpresaCadastroFilter } from "@/hooks/useEmpresaCadastroFilter";
import { filterItensPorEmpresaIds } from "@/lib/gridFilters";

const MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

type MesMap = Record<string, number>;

function emptyMesMap(): MesMap {
  return Object.fromEntries([...MESES_STR, "total"].map((m) => [m, 0]));
}

function aggregateByGrupo(itens: any[], getPlanoNome: (id: number) => string) {
  const map = new Map<string, { grupo: string; orcado: MesMap; forecast: MesMap; realizado: MesMap }>();

  for (const item of itens) {
    const plId = item.plano_financeiro_id;
    if (!plId) continue;
    const grupo = recebimentoGrupoKey(getPlanoNome(plId));
    if (!map.has(grupo)) {
      map.set(grupo, { grupo, orcado: emptyMesMap(), forecast: emptyMesMap(), realizado: emptyMesMap() });
    }
    const row = map.get(grupo)!;
    for (const tp of ["orcado", "forecast", "realizado"] as const) {
      const src = item[tp] || {};
      for (const m of [...MESES_STR, "total"]) {
        row[tp][m] += src[m] || 0;
      }
    }
  }

  return Array.from(map.values()).sort((a, b) => a.grupo.localeCompare(b.grupo, "pt-BR"));
}

export default function RecebimentoGrupoPage() {
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

  const load = useCallback(async () => {
    if (!isDepartmentContextId(deptId)) return;
    setLoading(true);
    setError(null);
    try {
      const res = await orcamentoService.getAcompanhamentoReceitas(ano, deptId, false, forecastId || undefined, holdingMldu);
      setData(res);
      if (forecastId === "" && res.active_forecast_id) setForecastId(res.active_forecast_id);
    } catch {
      setError("Erro ao carregar recebimento por grupo.");
    } finally {
      setLoading(false);
    }
  }, [ano, forecastId, deptId, holdingMldu]);

  useEffect(() => { load(); }, [load]);

  const ref = modo;
  const getPlanoNome = useCallback(
    (id: number) => data?.opcoes_planos?.find((p: any) => p.id === id)?.nome || String(id),
    [data?.opcoes_planos],
  );

  const grupos = useMemo(() => {
    const itens = filterItensPorEmpresaIds(
      data?.itens || [],
      data?.opcoes_produtos || [],
      filtroEmpresaIds,
    );
    return aggregateByGrupo(itens, getPlanoNome);
  }, [data?.itens, data?.opcoes_produtos, filtroEmpresaIds, getPlanoNome]);

  const insights = useMemo(
    () => buildExecInsights(grupos, ref, "RECEITAS"),
    [grupos, ref],
  );

  const visibleMonthsIdx = MESES_STR.map((m, i) => i).filter(
    (i) => meses.length === 0 || meses.includes(MESES_STR[i]),
  );
  const colMonths = [...visibleMonthsIdx.map((i) => MESES_STR[i]), "total"];
  const refLabel = modo === "orcado" ? "orçado" : "forecast";

  return (
    <div className="space-y-4 pb-10 flex flex-col h-[calc(100vh-120px)]">
      <div className="shrink-0">
        <h1 className="text-2xl font-bold text-slate-800">Recebimento por Grupo</h1>
        <p className="text-slate-500 text-sm mt-1">
          Receitas agrupadas por condição de recebimento (à vista, sinal, parcelado…)
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
      />

      {holdingMldu && <HoldingMlduBanner avisos={data?.holding_avisos} />}

      {error && (
        <div className="flex items-center gap-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl px-4 py-3 text-sm">
          <AlertTriangle className="w-5 h-5" />{error}
        </div>
      )}

      {!loading && grupos.length > 0 && (
        <>
          <DesvioExecStrip {...insights} refLabel={refLabel} narrative={insights.narrative} />
          <DesvioLegend />
        </>
      )}

      {loading ? (
        <div className="flex-1 flex items-center justify-center bg-white rounded-2xl border">
          <AppLoadingState />
        </div>
      ) : grupos.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-slate-400 bg-white rounded-2xl border">Sem receitas para agrupar.</div>
      ) : (
        <div className="flex-1 overflow-auto bg-white rounded-2xl border border-slate-200 shadow-sm">
          <table className="w-full text-left border-collapse min-w-max text-xs">
            <thead className="bg-slate-100 uppercase font-semibold text-slate-600 sticky top-0 z-30">
              <tr>
                <th className="px-3 py-3 min-w-[200px] sticky left-0 bg-slate-100 z-40">Grupo</th>
                <th className="px-3 py-3 min-w-[90px] sticky left-[200px] bg-slate-100 z-40">Métrica</th>
                {visibleMonthsIdx.map((i) => <th key={MESES[i]} className="px-3 py-3 text-right">{MESES[i]}</th>)}
                <th className="px-3 py-3 text-right bg-slate-200">Total</th>
              </tr>
            </thead>
            <tbody>
              {grupos.map((g) => {
                const varRs = (g.realizado.total ?? 0) - (g[ref].total ?? 0);
                const varPerc = g[ref].total ? varRs / Math.abs(g[ref].total) : 0;
                const fav = isDesvioFavoravel(varRs, "RECEITAS");
                const highlight = rowHighlightClass(varPerc, fav);
                const desvioRow = Object.fromEntries(
                  colMonths.map((m) => {
                    const r = g[ref][m] ?? 0;
                    const rl = g.realizado[m] ?? 0;
                    return [m, r !== 0 ? (rl - r) / Math.abs(r) : 0];
                  }),
                );
                const rows = [
                  { label: modo === "orcado" ? "Orçado" : "Forecast", src: g[ref] },
                  { label: "Realizado", src: g.realizado },
                  { label: "Desvio %", src: desvioRow, isPerc: true },
                ];
                return rows.map((row, ri) => (
                  <tr key={`${g.grupo}-${ri}`} className={`border-b border-slate-100 ${ri === 0 ? highlight : ""}`}>
                    {ri === 0 && (
                      <td rowSpan={3} className="px-3 py-2 font-semibold text-slate-700 sticky left-0 bg-inherit z-20">{g.grupo}</td>
                    )}
                    <td className="px-3 py-2 text-slate-500 sticky left-[200px] bg-inherit z-20">{row.label}</td>
                    {colMonths.map((m) => (
                      <td key={m} className={`px-3 py-2 text-right tabular-nums ${m === "total" ? "font-bold border-l border-slate-200" : ""}`}>
                        {row.isPerc
                          ? <DesvioBadgeBrand value={row.src[m] || 0} />
                          : formatMoedaCompact(row.src[m] || 0)}
                      </td>
                    ))}
                  </tr>
                ));
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
