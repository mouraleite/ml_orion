"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { orcamentoService } from "@/services/orcamento";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId, isDepartmentContextId } from "@/lib/useActiveDepartmentId";
import { DesvioLegend } from "@/components/orcamento/DesvioLegend";
import { DesvioExecStrip } from "@/components/orcamento/DesvioExecStrip";
import { OrcamentoFlyoutFilterBar } from "@/components/orcamento/OrcamentoFlyoutFilterBar";
import { OrcamentoHeroStrip } from "@/components/orcamento/OrcamentoHeroStrip";
import { formatMoedaK, MATERIALITY_THRESHOLD, isDesvioFavoravel } from "@/lib/orcamentoDesvioUi";
import { useEmpresaCadastroFilter } from "@/hooks/useEmpresaCadastroFilter";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

const GeracaoCaixaChart = dynamic(() => import("@/components/orcamento/GeracaoCaixaChart"), {
  ssr: false,
  loading: () => <AppLoadingState />,
});

const MESES_LABEL = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

export default function GeracaoCaixaPage() {
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

  const chart = data?.chart_mensal || [];
  const kpis = data?.kpis || {};
  const refLabel = modo === "orcado" ? "orçado" : "forecast";

  const caixaChart = useMemo(() => chart.map((row: any, i: number) => ({
    mes: MESES_LABEL[i] || row.mes,
    referencia: modo === "orcado"
      ? (row.rec_orcado ?? 0) - (row.desp_orcado ?? 0)
      : (row.rec_forecast ?? 0) - (row.desp_forecast ?? 0),
    real: (row.rec_realizado ?? 0) - (row.desp_realizado ?? 0),
    entradas: row.rec_realizado ?? 0,
    saidas: row.desp_realizado ?? 0,
  })), [chart, modo]);

  const refCaixa = (kpis.rec_referencia ?? 0) - (kpis.desp_referencia ?? 0);
  const realCaixa = (kpis.rec_realizado ?? 0) - (kpis.desp_realizado ?? 0);
  const varCaixa = realCaixa - refCaixa;
  const varPerc = refCaixa !== 0 ? varCaixa / Math.abs(refCaixa) : 0;
  const favoravel = isDesvioFavoravel(varCaixa, "RESULTADO");
  const material = Math.abs(varPerc) >= MATERIALITY_THRESHOLD;

  return (
    <div className="space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Geração de Caixa</h1>
        <p className="text-slate-500 text-sm mt-1">Receitas − despesas por mês (referência vs realizado)</p>
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

      {!loading && (
        <>
          <OrcamentoHeroStrip
            refLabel={modo === "orcado" ? "Orçado" : "Forecast"}
            refVal={refCaixa}
            realVal={realCaixa}
            varRs={varCaixa}
            varPerc={varPerc}
            tipo="RESULTADO"
            favoravel={favoravel}
            material={material}
            refCaption="Geração de caixa"
            caption="Receitas − despesas no período filtrado"
          />
          <DesvioExecStrip
            narrative={`Geração de caixa ${favoravel ? "favorável" : "abaixo da referência"}: ${formatMoedaK(Math.abs(varCaixa))} ${varCaixa >= 0 ? "acima" : "abaixo"} do ${refLabel}.`}
            favoravel={favoravel}
            varRs={varCaixa}
            varPerc={varPerc}
            refLabel={refLabel}
            n={realCaixa}
            ref={refCaixa}
            tipo="RESULTADO"
          />
          <DesvioLegend />
        </>
      )}

      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <h2 className="font-bold text-slate-700 mb-4">Geração de caixa mensal (Receitas − Despesas)</h2>
        {loading ? (
          <AppLoadingState />
        ) : (
          <GeracaoCaixaChart data={caixaChart} modo={modo} />
        )}
      </div>

      <p className="text-xs text-slate-400">
        Fonte: dashboard executivo (receitas e despesas consolidadas). Para detalhe por plano, use{" "}
        <Link href="/dashboard/orcamento/analitico-gastos-1" className="text-ml-green font-semibold hover:underline">Analítico I</Link>.
      </p>
    </div>
  );
}
