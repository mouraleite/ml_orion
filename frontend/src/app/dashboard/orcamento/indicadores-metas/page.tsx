"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { orcamentoService } from "@/services/orcamento";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId, isDepartmentContextId } from "@/lib/useActiveDepartmentId";
import { DesvioLegend } from "@/components/orcamento/DesvioLegend";
import { DesvioExecStrip } from "@/components/orcamento/DesvioExecStrip";
import { OrcamentoFlyoutFilterBar } from "@/components/orcamento/OrcamentoFlyoutFilterBar";
import { OrcamentoHeroStrip, OrcamentoSecondaryMetric } from "@/components/orcamento/OrcamentoHeroStrip";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { formatMoedaK, formatPerc, MATERIALITY_THRESHOLD, isDesvioFavoravel } from "@/lib/orcamentoDesvioUi";
import { buildOrcamentoHref } from "@/lib/orcamentoNavigation";
import { useEmpresaCadastroFilter } from "@/hooks/useEmpresaCadastroFilter";

export default function IndicadoresMetasPage() {
  const deptId = useActiveDepartmentId();
  const { holdingMldu, setHoldingMldu, canUseHoldingMldu } = useHoldingMldu("orcamento");
  const [ano, setAno] = useState(new Date().getFullYear());
  const [modo, setModo] = useState<"orcado" | "forecast">("orcado");
  const [meses, setMeses] = useState<string[]>([]);
  const { filtroEmpresaIds, setFiltroEmpresaIds, empresaOpcoes, empresaIdsKey } = useEmpresaCadastroFilter();
  const [forecastId, setForecastId] = useState<number | undefined>();
  const [forecasts, setForecasts] = useState<any[]>([]);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isDepartmentContextId(deptId)) return;
    orcamentoService.getForecastsDisponiveis(ano, deptId, false).then((r) => {
      setForecasts(r.forecasts || []);
      if (r.forecasts?.length && !forecastId) setForecastId(r.forecasts[0].id);
    }).catch(() => {});
  }, [ano, deptId]);

  const load = useCallback(async () => {
    if (!isDepartmentContextId(deptId)) return;
    setLoading(true);
    try {
      const res = await orcamentoService.getDashboardExecutivo(
        ano, deptId, false, modo, modo === "forecast" ? forecastId : undefined, meses, holdingMldu,
        empresaIdsKey ? empresaIdsKey.split(",") : [],
      );
      setData(res);
    } finally {
      setLoading(false);
    }
  }, [ano, deptId, modo, forecastId, meses, holdingMldu, empresaIdsKey]);

  useEffect(() => { load(); }, [load]);

  const k = data?.kpis || {};
  const refLabel = modo === "orcado" ? "orçado" : "forecast";
  const modoLabel = modo === "orcado" ? "Orçado" : "Forecast";
  const resultadoRef = k.resultado_referencia ?? 0;
  const resultadoReal = k.resultado_realizado ?? 0;
  const varRes = resultadoReal - resultadoRef;
  const varPerc = resultadoRef !== 0 ? varRes / Math.abs(resultadoRef) : 0;
  const favoravel = isDesvioFavoravel(varRes, "RESULTADO");
  const material = Math.abs(varPerc) >= MATERIALITY_THRESHOLD;
  const mesesHref = meses.length ? meses : undefined;

  return (
    <div className="space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Indicadores e Metas</h1>
        <p className="text-slate-500 text-sm mt-1">KPIs vs {refLabel} — metas derivadas do orçamento/forecast ativo</p>
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
        forecasts={forecasts}
        forecastId={forecastId || ""}
        onForecastIdChange={(id) => setForecastId(id || undefined)}
        onRefresh={load}
        loading={loading}
      />

      {holdingMldu && <HoldingMlduBanner avisos={data?.holding_avisos} />}

      {loading ? (
        <AppLoadingState />
      ) : (
        <>
          <OrcamentoHeroStrip
            refLabel={modoLabel}
            refVal={resultadoRef}
            realVal={resultadoReal}
            varRs={varRes}
            varPerc={k.resultado_desvio_perc ?? varPerc}
            favoravel={favoravel}
            material={material}
            refCaption="Resultado líquido"
            caption="Metas = valores de referência do período filtrado"
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <OrcamentoSecondaryMetric
              title="Despesas (realizado)"
              realVal={formatMoedaK(k.desp_realizado ?? 0)}
              refVal={`${modoLabel}: ${formatMoedaK(k.desp_referencia ?? 0)}`}
              desvio={k.desp_desvio_perc}
              invert
            />
            <OrcamentoSecondaryMetric
              title="Receitas (realizado)"
              realVal={formatMoedaK(k.rec_realizado ?? 0)}
              refVal={`${modoLabel}: ${formatMoedaK(k.rec_referencia ?? 0)}`}
              desvio={k.rec_desvio_perc}
            />
            <OrcamentoSecondaryMetric
              title="VGV (realizado)"
              realVal={formatMoedaK(k.vgv_realizado ?? 0)}
              refVal={`${modoLabel}: ${formatMoedaK(k.vgv_referencia ?? 0)}`}
              desvio={k.vgv_desvio_perc}
            />
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-1 px-1 text-[11px] text-slate-500 tabular-nums">
            <span>Unidades: <strong className="text-slate-700">{(k.unidades_realizado ?? 0).toLocaleString("pt-BR")}</strong> <span className="text-slate-400">({modoLabel}: {(k.unidades_referencia ?? 0).toLocaleString("pt-BR")})</span></span>
            <span>Ticket médio: <strong className="text-slate-700">{formatMoedaK(k.ticket_medio_realizado ?? 0)}</strong> <span className="text-slate-400">({modoLabel}: {formatMoedaK(k.ticket_medio_referencia ?? 0)})</span></span>
          </div>
          <DesvioExecStrip
            narrative={`Resultado ${varRes >= 0 ? "acima" : "abaixo"} da meta em ${formatMoedaK(Math.abs(varRes))} (${formatPerc(varPerc)}).`}
            favoravel={favoravel}
            varRs={varRes}
            varPerc={varPerc}
            refLabel={refLabel}
          />
          <DesvioLegend />
        </>
      )}

      <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-600">Metas = valores de {refLabel} do período. Metas customizadas por departamento podem ser cadastradas em fase posterior.</p>
        <Link href={buildOrcamentoHref("analitico1", { ano, modo, meses: mesesHref })} className="text-xs font-semibold text-ml-green hover:underline">
          Abrir Analítico I →
        </Link>
      </div>
    </div>
  );
}
