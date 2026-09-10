"use client";
import React, { useState, useEffect, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { orcamentoService } from "@/services/orcamento";
import { buildOrcamentoHref } from "@/lib/orcamentoNavigation";
import { OrcamentoDeepLinks } from "@/components/orcamento/OrcamentoDeepLinks";
import { DesvioLegend } from "@/components/orcamento/DesvioLegend";
import { DesvioExecStrip } from "@/components/orcamento/DesvioExecStrip";
import { isDesvioFavoravel, MATERIALITY_THRESHOLD } from "@/lib/orcamentoDesvioUi";
import {
  ChevronDown, ChevronRight, AlertTriangle,
} from "lucide-react";
import { OrcamentoFlyoutFilterBar } from "@/components/orcamento/OrcamentoFlyoutFilterBar";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId, isDepartmentContextId } from "@/lib/useActiveDepartmentId";
import { BudgetLoadingState, AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { OrcamentoHeroStrip, OrcamentoSecondaryMetric } from "@/components/orcamento/OrcamentoHeroStrip";
import { useEmpresaCadastroFilter } from "@/hooks/useEmpresaCadastroFilter";

const ResumoGeralCharts = dynamic(() => import("@/components/orcamento/ResumoGeralCharts"), {
  ssr: false,
  loading: () => <AppLoadingState />,
});

// ─── Formatters ─────────────────────────────────────────────────────────────
const fmtM = (v: number) =>
  v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 0, maximumFractionDigits: 0 });
const fmtP = (v: number) =>
  v == null ? "—" : `${(v * 100).toFixed(1).replace(".", ",")}%`;
const fmtN = (v: number) =>
  v == null ? "—" : v.toLocaleString("pt-BR");
const fmtK = (v: number) => {
  if (Math.abs(v) >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000)     return `R$ ${(v / 1_000).toFixed(0)}K`;
  return fmtM(v);
};

// ─── Drill-down Row ──────────────────────────────────────────────────────────
function DrillRow({
  produto,
  modo,
  mesesSelecionados,
  ano,
}: {
  produto: any;
  modo: string;
  mesesSelecionados: string[];
  ano: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const [expandedPlanos, setExpandedPlanos] = useState<Set<number>>(new Set());

  const togglePlano = (i: number) => setExpandedPlanos(prev => {
    const next = new Set(prev);
    next.has(i) ? next.delete(i) : next.add(i);
    return next;
  });

  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-slate-50 hover:bg-slate-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
          <span className="font-semibold text-slate-700">{produto.produto_nome}</span>
          <span className="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full">{produto.planos?.length} planos</span>
        </div>
      </button>

      {expanded && (
        <div className="divide-y divide-slate-100">
          {produto.planos?.map((plano: any, pi: number) => {
            const isMesExpanded = expandedPlanos.has(pi);
            const total = plano.meses?.["total"] || {};
            const ref = total[modo] || 0;
            const real = total["realizado"] || 0;
            const desvio = ref ? (real - ref) / ref : 0;

            return (
              <div key={pi}>
                <button
                  onClick={() => togglePlano(pi)}
                  className={`w-full flex items-center justify-between px-6 py-3 hover:bg-slate-50 transition-colors text-left ${plano.categoria === "RECEITAS" ? "border-l-4 border-green-400" : "border-l-4 border-red-400"}`}
                >
                  <div className="flex items-center gap-2">
                    {isMesExpanded ? <ChevronDown className="w-3 h-3 text-slate-300" /> : <ChevronRight className="w-3 h-3 text-slate-300" />}
                    <span className="text-sm font-medium text-slate-600">{plano.plano_nome}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${plano.categoria === "RECEITAS" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                      {plano.categoria}
                    </span>
                  </div>
                  <div className="flex items-center gap-6 text-xs tabular-nums">
                    <span className="text-slate-500">{fmtM(ref)}</span>
                    <span className="font-semibold text-slate-700">{fmtM(real)}</span>
                    <span className={`font-bold ${desvio >= 0 ? "text-emerald-600" : "text-red-600"}`}>{fmtP(desvio)}</span>
                    {plano.categoria === "DESPESAS" && plano.plano_id && (
                      <OrcamentoDeepLinks
                        variant="compact"
                        params={{
                          ano,
                          modo: modo as "orcado" | "forecast",
                          meses: mesesSelecionados.length ? mesesSelecionados : undefined,
                          produto: produto.produto_id,
                          plano: plano.plano_id,
                          expand: true,
                        }}
                      />
                    )}
                  </div>
                </button>

                {isMesExpanded && (
                  <div className="overflow-x-auto bg-white px-6 pb-3">
                    <table className="w-full text-xs mt-2">
                      <thead>
                        <tr className="text-slate-400 border-b border-slate-100">
                          <th className="text-left py-2 font-semibold">Período</th>
                          <th className="text-right py-2 font-semibold">{modo === "orcado" ? "Orçado" : "Forecast"}</th>
                          <th className="text-right py-2 font-semibold">Realizado</th>
                          <th className="text-right py-2 font-semibold">Desvio</th>
                        </tr>
                      </thead>
                      <tbody>
                        {["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"].map((m, mi) => {
                          if (mesesSelecionados.length > 0 && !mesesSelecionados.includes(m)) return null;
                          const mv = plano.meses?.[m] || {};
                          const mRef = mv[modo] || 0;
                          const mReal = mv["realizado"] || 0;
                          const mDesvio = mRef ? (mReal - mRef) / mRef : 0;
                          return (
                            <tr key={m} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/50">
                              <td className="py-2 text-slate-500 font-medium">{["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"][mi]}</td>
                              <td className="text-right py-2 tabular-nums text-slate-600">{fmtM(mRef)}</td>
                              <td className="text-right py-2 tabular-nums font-medium text-slate-700">{fmtM(mReal)}</td>
                              <td className={`text-right py-2 tabular-nums font-bold ${mDesvio >= 0 ? "text-emerald-600" : "text-red-600"}`}>{fmtP(mDesvio)}</td>
                            </tr>
                          );
                        })}
                        {mesesSelecionados.length > 0 && (
                          <tr className="border-t-2 border-slate-100 bg-slate-50/50">
                            <td className="py-2.5 text-slate-700 font-bold">Acumulado Selecionado</td>
                            <td className="text-right py-2.5 tabular-nums text-slate-700 font-bold">{fmtM(ref)}</td>
                            <td className="text-right py-2.5 tabular-nums text-slate-800 font-bold">{fmtM(real)}</td>
                            <td className={`text-right py-2.5 tabular-nums font-bold ${desvio >= 0 ? "text-emerald-600" : "text-red-600"}`}>{fmtP(desvio)}</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Main Dashboard Page ──────────────────────────────────────────────────────
export default function DashboardExecutivoPage() {
  const deptId = useActiveDepartmentId();
  const { holdingMldu, setHoldingMldu, canUseHoldingMldu } = useHoldingMldu("orcamento");
  const [ano, setAno] = useState(new Date().getFullYear());
  const [modo, setModo] = useState<"orcado" | "forecast">("orcado");
  const [chartView, setChartView] = useState<"despesas" | "receitas" | "resultado" | "vgv">("resultado");
  const [meses, setMeses] = useState<string[]>([]);
  const { filtroEmpresaIds, setFiltroEmpresaIds, empresaOpcoes, empresaIdsKey } = useEmpresaCadastroFilter();
  const [data, setData] = useState<any>(null);
  
  const [forecastsDisponiveis, setForecastsDisponiveis] = useState<any[]>([]);
  const [versaoForecastId, setVersaoForecastId] = useState<number | undefined>(undefined);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loadSeq = useRef(0);

  const carregarForecasts = useCallback(async () => {
    if (!isDepartmentContextId(deptId)) return;
    try {
      const res = await orcamentoService.getForecastsDisponiveis(ano, deptId, false);
      setForecastsDisponiveis(res.forecasts || []);
      if (res.forecasts?.length > 0 && !versaoForecastId) {
        setVersaoForecastId(res.forecasts[0].id);
      }
    } catch (e) {
      console.error("Erro ao carregar forecasts:", e);
    }
  }, [ano, deptId]);

  useEffect(() => { carregarForecasts(); }, [carregarForecasts]);

  const load = useCallback(async () => {
    if (!isDepartmentContextId(deptId)) return;
    const seq = ++loadSeq.current;
    setLoading(true);
    setError(null);
    try {
      const res = await orcamentoService.getDashboardExecutivo(
        ano, 
        deptId, 
        false, 
        modo, 
        modo === "forecast" ? versaoForecastId : undefined,
        meses,
        holdingMldu,
        empresaIdsKey ? empresaIdsKey.split(",") : [],
      );
      if (seq !== loadSeq.current) return;
      setData(res);
    } catch (e: any) {
      if (seq !== loadSeq.current) return;
      setError("Erro ao carregar o Dashboard. Verifique se há orçamentos cadastrados para o ano selecionado.");
    } finally {
      if (seq === loadSeq.current) setLoading(false);
    }
  }, [ano, modo, versaoForecastId, deptId, meses, holdingMldu, empresaIdsKey]);

  useEffect(() => { load(); }, [load]);

  const kpis = data?.kpis || {};
  const chart = data?.chart_mensal || [];
  const ranking = data?.ranking_desvios || [];
  const drillDown = data?.drill_down || [];

  const modoLabel = modo === "orcado" ? "Orçado" : "Forecast";

  // Chart series config
  const chartConfigs = {
    resultado: {
      title: "Resultado Líquido (Receitas − Despesas)",
      bars: [
        { key: "resultado_ref", name: modoLabel, color: "#64748b" },
        { key: "resultado_real", name: "Realizado", color: "#2E864D" },
      ],
    },
    despesas: {
      title: "Despesas",
      bars: [
        { key: "desp_orcado", name: "Orçado", color: "#64748b" },
        { key: "desp_forecast", name: "Forecast", color: "#F5883A" },
        { key: "desp_realizado", name: "Realizado", color: "#FF5144" },
      ],
    },
    receitas: {
      title: "Receitas",
      bars: [
        { key: "rec_orcado", name: "Orçado", color: "#64748b" },
        { key: "rec_forecast", name: "Forecast", color: "#F5883A" },
        { key: "rec_realizado", name: "Realizado", color: "#2E864D" },
      ],
    },
    vgv: {
      title: "VGV de Vendas",
      bars: [
        { key: "vgv_orcado", name: "Orçado", color: "#64748b" },
        { key: "vgv_forecast", name: "Forecast", color: "#F5883A" },
        { key: "vgv_realizado", name: "Realizado", color: "#255742" },
      ],
    },
  };
  const cfg = chartConfigs[chartView];
  const resultadoMaterial = Math.abs(kpis.resultado_desvio_perc ?? 0) >= MATERIALITY_THRESHOLD;
  const resultadoVarRs = (kpis.resultado_realizado ?? 0) - (kpis.resultado_referencia ?? 0);
  const resultadoFavoravel = isDesvioFavoravel(resultadoVarRs, "RESULTADO");

  // ─── WATERFALL DATA CALCULATION ──────────────────────────────
  const orcadoTotal = kpis.resultado_referencia || 0;
  const realizadoTotal = kpis.resultado_realizado || 0;
  
  const varReceitas = (kpis.rec_realizado || 0) - (kpis.rec_referencia || 0);
  const varDespesas = (kpis.desp_referencia || 0) - (kpis.desp_realizado || 0); // Positivo se gastou menos

  const waterfallData = [
    { 
      name: modoLabel, 
      start: 0, 
      end: orcadoTotal, 
      val: orcadoTotal,
      fill: "#64748b" 
    },
    { 
      name: "Var. Receitas", 
      start: orcadoTotal, 
      end: orcadoTotal + varReceitas, 
      val: varReceitas,
      fill: varReceitas >= 0 ? "#2E864D" : "#FF5144" 
    },
    { 
      name: "Var. Despesas", 
      start: orcadoTotal + varReceitas, 
      end: orcadoTotal + varReceitas + varDespesas, 
      val: varDespesas,
      fill: varDespesas >= 0 ? "#2E864D" : "#FF5144" 
    },
    { 
      name: "Realizado", 
      start: 0, 
      end: realizadoTotal, 
      val: realizadoTotal,
      fill: "#2E864D" 
    }
  ];

  // Prepare recharts data for waterfall (stacked bars trick)
  const wfChartData = waterfallData.map(d => ({
    name: d.name,
    transparent: Math.min(d.start, d.end),
    value: Math.abs(d.end - d.start),
    actualValue: d.val,
    fill: d.fill
  }));

  const mesesHref = meses.length ? meses : undefined;

  return (
    <div className="space-y-5 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Dashboard de Orçamento</h1>
        <p className="text-slate-500 text-sm mt-1">Orçado × Realizado · {ano}</p>
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
        forecasts={forecastsDisponiveis}
        forecastId={versaoForecastId || ""}
        onForecastIdChange={(id) => setVersaoForecastId(id || undefined)}
        onRefresh={load}
        loading={loading}
      />

      {holdingMldu && <HoldingMlduBanner avisos={data?.holding_avisos} />}

      {error && (
        <div className="flex items-center gap-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl px-4 py-3 text-sm">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          {error}
        </div>
      )}

      {loading && !data ? (
        <div className="rounded-xl border border-slate-200 bg-white">
          <BudgetLoadingState />
        </div>
      ) : data ? (
        <div className="space-y-3">
          <OrcamentoHeroStrip
            refLabel={modoLabel}
            refVal={kpis.resultado_referencia || 0}
            realVal={kpis.resultado_realizado || 0}
            varRs={resultadoVarRs}
            varPerc={kpis.resultado_desvio_perc ?? 0}
            favoravel={resultadoFavoravel}
            material={resultadoMaterial}
            refCaption="Resultado líquido"
            caption="Comparação do resultado no período filtrado"
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <OrcamentoSecondaryMetric
              title="Despesas (realizado)"
              realVal={fmtK(kpis.desp_realizado || 0)}
              refVal={`${modoLabel}: ${fmtK(kpis.desp_referencia || 0)}`}
              desvio={kpis.desp_desvio_perc}
              invert
              href={buildOrcamentoHref("analitico1", { ano, modo, meses: mesesHref })}
              linkLabel="Analítico →"
            />
            <OrcamentoSecondaryMetric
              title="Receitas (realizado)"
              realVal={fmtK(kpis.rec_realizado || 0)}
              refVal={`${modoLabel}: ${fmtK(kpis.rec_referencia || 0)}`}
              desvio={kpis.rec_desvio_perc}
              href={`/dashboard/orcamento/receitas?ano=${ano}`}
              linkLabel="Receitas →"
            />
            <OrcamentoSecondaryMetric
              title="VGV (realizado)"
              realVal={fmtK(kpis.vgv_realizado || 0)}
              refVal={`${modoLabel}: ${fmtK(kpis.vgv_referencia || 0)}`}
              desvio={kpis.vgv_desvio_perc}
              href={`/dashboard/orcamento/vendas?ano=${ano}`}
              linkLabel="Vendas →"
            />
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-1 px-1 text-[11px] text-slate-500 tabular-nums">
            <span>Unidades: <strong className="text-slate-700">{fmtN(kpis.unidades_realizado || 0)}</strong> <span className="text-slate-400">({modoLabel}: {fmtN(kpis.unidades_referencia || 0)})</span></span>
            <span>Ticket médio: <strong className="text-slate-700">{fmtK(kpis.ticket_medio_realizado || 0)}</strong> <span className="text-slate-400">({modoLabel}: {fmtK(kpis.ticket_medio_referencia || 0)})</span></span>
            <Link href={`/dashboard/orcamento/geracao-caixa?ano=${ano}`} className="font-semibold text-ml-green hover:underline">
              Geração de caixa →
            </Link>
          </div>
        </div>
      ) : null}

      {data && kpis.resultado_referencia != null && (
        <>
          <DesvioExecStrip
            narrative={`Resultado líquido ${fmtP(kpis.resultado_desvio_perc ?? 0)} vs ${modoLabel.toLowerCase()}. Despesas ${(kpis.desp_desvio_perc ?? 0) <= 0 ? "dentro ou abaixo" : "acima"} da referência (${fmtP(kpis.desp_desvio_perc ?? 0)}).`}
            favoravel={resultadoFavoravel}
            varRs={resultadoVarRs}
            varPerc={kpis.resultado_desvio_perc ?? 0}
            refLabel={modoLabel.toLowerCase()}
          />
          <DesvioLegend />
        </>
      )}

      {/* ── Chart + Waterfall ─────────────────────────────────────── */}
      <ResumoGeralCharts
        loading={loading}
        hasData={Boolean(data)}
        wfChartData={wfChartData}
        chart={chart}
        chartView={chartView}
        onChartViewChange={setChartView}
        cfg={cfg}
        meses={meses}
      />
      
      {/* ── Ranking ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-3 bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-3">
          <h2 className="font-bold text-slate-700 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            Top 10 Maiores Desvios
          </h2>

          {loading && !data ? (
            <div className="space-y-2">
              {[...Array(6)].map((_, i) => <div key={i} className="h-8 rounded-lg bg-slate-100 animate-pulse" />)}
            </div>
          ) : ranking.length === 0 ? (
            <div className="text-center py-8 text-slate-400 text-sm">Sem desvios a exibir.</div>
          ) : (
            <div className="overflow-x-auto -mx-2">
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="text-slate-400 border-b border-slate-100">
                    <th className="text-left px-4 py-2">#</th>
                    <th className="text-left px-3 py-2">Produto</th>
                    <th className="text-left px-3 py-2">Plano</th>
                    <th className="text-right px-3 py-2">Referência</th>
                    <th className="text-right px-3 py-2">Realizado</th>
                    <th className="text-right px-3 py-2">Variação</th>
                    <th className="px-4 py-2">%</th>
                    <th className="text-right px-3 py-2">Detalhe</th>
                  </tr>
                </thead>
                <tbody>
                  {ranking.map((item: any, i: number) => {
                    const isDesp = item.tipo === "DESPESAS";
                    const isPos = item.variacao_rs > 0;
                    const good = isDesp ? !isPos : isPos;
                    return (
                      <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                        <td className="px-4 py-2.5">
                          <span className={`w-5 h-5 inline-flex items-center justify-center rounded-full text-[10px] font-bold ${i < 3 ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"}`}>{i + 1}</span>
                        </td>
                        <td className="px-3 py-2.5 font-medium text-slate-700 truncate max-w-[140px]">{item.produto_nome}</td>
                        <td className="px-3 py-2.5 text-slate-500 truncate max-w-[120px]">{item.plano_nome}</td>
                        <td className="text-right px-3 py-2.5 tabular-nums text-slate-600">{fmtK(item.referencia ?? 0)}</td>
                        <td className="text-right px-3 py-2.5 tabular-nums font-medium text-slate-700">{fmtK(item.realizado ?? 0)}</td>
                        <td className={`text-right px-3 py-2.5 font-semibold tabular-nums ${good ? "text-emerald-700" : "text-red-700"}`}>{fmtK(item.variacao_rs)}</td>
                        <td className="px-4 py-2.5">
                          <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${good ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>{fmtP(item.variacao_perc)}</span>
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          {item.tipo === "DESPESAS" && item.produto_id && (
                            <OrcamentoDeepLinks
                              variant="compact"
                              params={{
                                ano,
                                modo,
                                meses: meses.length ? meses : undefined,
                                produto: item.produto_id,
                                plano: item.plano_financeiro_id || undefined,
                                expand: Boolean(item.plano_financeiro_id),
                              }}
                            />
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ── Drill-down ─────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
        <h2 className="font-bold text-slate-700 flex items-center gap-2">
          <ChevronRight className="w-4 h-4 text-slate-400" />
          Drill-down: Produto → Plano → Mês
        </h2>
        <p className="text-xs text-slate-400">Clique em um produto para expandir seus planos financeiros. Clique no plano para ver a abertura mensal.</p>

        {loading && !data ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => <div key={i} className="h-12 rounded-xl bg-slate-100 animate-pulse" />)}
          </div>
        ) : drillDown.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-sm">Nenhum dado para exibir no drill-down.</div>
        ) : (
          <div className="space-y-2">
            {drillDown.map((produto: any) => (
              <DrillRow key={produto.produto_id} produto={produto} modo={modo} mesesSelecionados={meses} ano={ano} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
