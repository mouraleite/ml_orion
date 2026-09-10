"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { TrendingUp, TrendingDown, RefreshCw, Activity, BarChart3, CalendarDays, Info } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

// ── Types ───────────────────────────────────────────────────────────────────
interface HistoricoItem {
  data: string;
  valor: number;
  acumulado_12m: number;
  acumulado_ano: number;
}

interface IndiceData {
  indicador: string;
  fonte: string;
  ultimo_mes: {
    data: string | null;
    mensal: number | null;
    acumulado_12m: number | null;
    acumulado_ano: number | null;
  };
  historico: HistoricoItem[];
}

interface FocusData {
  fonte: string;
  IPCA: { Data: string; Mediana: number; DataReferencia: string }[];
  "IGP-M": { Data: string; Mediana: number; DataReferencia: string }[];
}

// ── Helpers ─────────────────────────────────────────────────────────────────
const fmtPerc = (v: number | null | undefined, decimals = 2) =>
  v != null ? `${v.toFixed(decimals)}%` : "—";

const fmtData = (d: string | null) => {
  if (!d) return "—";
  // BCB format: dd/mm/yyyy
  const parts = d.split("/");
  if (parts.length === 3) {
    const months = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
    return `${months[parseInt(parts[1]) - 1]}/${parts[2].slice(-2)}`;
  }
  return d;
};

// ── Component ────────────────────────────────────────────────────────────────
export default function IndicesMercadoPage() {
  const [ipca, setIpca] = useState<IndiceData | null>(null);
  const [incc, setIncc] = useState<IndiceData | null>(null);
  const [igpm, setIgpm] = useState<IndiceData | null>(null);
  const [focus, setFocus] = useState<FocusData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"IPCA" | "INCC" | "IGP-M">("IPCA");

  const fetchAll = useCallback(async (forceRefresh = false) => {
    forceRefresh ? setIsRefreshing(true) : setIsLoading(true);
    setError(null);
    try {
      if (forceRefresh) {
        await api.post("/market-indices/cache/clear");
      }
      const [ipcaRes, inccRes, igpmRes, focusRes] = await Promise.all([
        api.get("/market-indices/ipca"),
        api.get("/market-indices/incc"),
        api.get("/market-indices/igpm"),
        api.get("/market-indices/focus").catch(() => ({ data: null })),
      ]);
      setIpca(ipcaRes.data);
      setIncc(inccRes.data);
      setIgpm(igpmRes.data);
      setFocus(focusRes.data);
    } catch (e: any) {
      setError("Não foi possível conectar ao BCB. Verifique sua conexão e tente novamente.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const activeData = activeTab === "IPCA" ? ipca : activeTab === "INCC" ? incc : igpm;
  const focusProj = activeTab === "IPCA" ? focus?.IPCA?.[0] : focus?.["IGP-M"]?.[0];
  const focusLabel = activeTab === "IPCA" ? "IPCA Focus" : "IGP-M Focus";

  // ── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return <AppLoadingState />;
  }

  // ── Error ──────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="p-8 max-w-[900px]">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700 font-medium">{error}</p>
          <Button onClick={() => fetchAll(true)} className="mt-4 bg-red-600 hover:bg-red-700 text-white">
            Tentar Novamente
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-[1000px] animate-in fade-in duration-300 space-y-6">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-ml-green" />
            Índices de Mercado
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Dados reais do Banco Central do Brasil (BCB/SGS) atualizados automaticamente.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => fetchAll(true)}
          disabled={isRefreshing}
          className="flex items-center gap-2 shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
          {isRefreshing ? "Atualizando..." : "Atualizar Dados"}
        </Button>
      </div>

      {/* ── Tabs ───────────────────────────────────────────────────────────── */}
      <div className="flex bg-slate-100 p-1 rounded-lg w-fit">
        {(["IPCA", "INCC", "IGP-M"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-5 py-2 text-sm font-semibold rounded-md transition-all ${
              activeTab === tab
                ? "bg-white text-ml-dark shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab === "INCC" ? "INCC-DI" : tab}
          </button>
        ))}
      </div>

      {/* ── KPI Cards ──────────────────────────────────────────────────────── */}
      {activeData && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Último Mês */}
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider flex items-center gap-1">
                <CalendarDays className="w-3.5 h-3.5" /> Último Mês
              </p>
              <p className="text-slate-400 text-xs mt-1">{activeData.ultimo_mes.data || "—"}</p>
              <p className={`text-2xl font-bold mt-1 ${(activeData.ultimo_mes.mensal ?? 0) >= 0 ? "text-slate-800" : "text-red-600"}`}>
                {fmtPerc(activeData.ultimo_mes.mensal)}
              </p>
              <p className="text-xs text-slate-400 mt-1">mensal</p>
            </div>

            {/* Acumulado Ano */}
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider flex items-center gap-1">
                <TrendingUp className="w-3.5 h-3.5" /> Acum. Ano
              </p>
              <p className="text-slate-400 text-xs mt-1">Jan–{activeData.ultimo_mes.data?.split("/")[0] || "—"}</p>
              <p className="text-2xl font-bold mt-1 text-slate-800">
                {fmtPerc(activeData.ultimo_mes.acumulado_ano)}
              </p>
              <p className="text-xs text-slate-400 mt-1">acumulado no ano</p>
            </div>

            {/* Acumulado 12m */}
            <div className="bg-white rounded-xl border border-ml-green/30 bg-ml-green/5 p-4 shadow-sm">
              <p className="text-xs text-ml-dark font-medium uppercase tracking-wider flex items-center gap-1">
                <Activity className="w-3.5 h-3.5" /> Acum. 12 Meses
              </p>
              <p className="text-slate-400 text-xs mt-1">últimos 12 meses</p>
              <p className="text-2xl font-bold mt-1 text-ml-very-dark">
                {fmtPerc(activeData.ultimo_mes.acumulado_12m)}
              </p>
              <p className="text-xs text-slate-400 mt-1">acumulado 12m</p>
            </div>

            {/* Focus Projeção */}
            <div className="bg-white rounded-xl border border-amber-200 bg-amber-50/50 p-4 shadow-sm">
              <p className="text-xs text-amber-700 font-medium uppercase tracking-wider flex items-center gap-1">
                <Info className="w-3.5 h-3.5" /> {focusLabel}
              </p>
              <p className="text-slate-400 text-xs mt-1">
                {focusProj?.DataReferencia ? `Ref. ${focusProj.DataReferencia}` : "Projeção anual"}
              </p>
              <p className="text-2xl font-bold mt-1 text-amber-700">
                {focusProj?.Mediana != null ? fmtPerc(focusProj.Mediana) : "—"}
              </p>
              <p className="text-xs text-amber-600 mt-1">mediana Focus</p>
            </div>
          </div>

          {/* ── Tabela Histórica ───────────────────────────────────────────── */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-bold text-slate-800">
                Histórico Mensal — {activeData.indicador}
              </h2>
              <span className="text-xs text-slate-400 bg-slate-50 border border-slate-200 rounded px-2 py-1">
                {activeData.fonte}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left py-3 px-6 font-semibold text-slate-600 uppercase text-xs tracking-wider">Período</th>
                    <th className="text-right py-3 px-6 font-semibold text-slate-600 uppercase text-xs tracking-wider">Mensal (%)</th>
                    <th className="text-right py-3 px-6 font-semibold text-slate-600 uppercase text-xs tracking-wider">Acum. Ano (%)</th>
                    <th className="text-right py-3 px-6 font-semibold text-slate-600 uppercase text-xs tracking-wider">Acum. 12m (%)</th>
                  </tr>
                </thead>
                <tbody>
                  {[...activeData.historico].reverse().map((item, idx) => (
                    <tr
                      key={item.data}
                      className={`border-b border-slate-50 hover:bg-slate-50 transition-colors ${idx === 0 ? "bg-ml-green/5 font-semibold" : ""}`}
                    >
                      <td className="py-2.5 px-6 text-slate-700">{fmtData(item.data)}</td>
                      <td className={`py-2.5 px-6 text-right font-mono ${item.valor >= 0 ? "text-slate-800" : "text-red-600"}`}>
                        <span className="flex items-center justify-end gap-1">
                          {item.valor >= 0
                            ? <TrendingUp className="w-3 h-3 text-green-500" />
                            : <TrendingDown className="w-3 h-3 text-red-500" />
                          }
                          {fmtPerc(item.valor, 2)}
                        </span>
                      </td>
                      <td className="py-2.5 px-6 text-right font-mono text-slate-600">{fmtPerc(item.acumulado_ano, 2)}</td>
                      <td className={`py-2.5 px-6 text-right font-mono font-semibold ${idx === 0 ? "text-ml-very-dark" : "text-slate-700"}`}>
                        {fmtPerc(item.acumulado_12m, 2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* ── Nota Rodapé ───────────────────────────────────────────────── */}
          <p className="text-xs text-slate-400 text-center">
            Fonte: Banco Central do Brasil — BCB/SGS.
            {activeTab === "IPCA" ? " Série 433 (IPCA mensal - IBGE)." : activeTab === "INCC" ? " Série 192 (INCC-DI mensal - FGV)." : " Série 189 (IGP-M mensal - FGV)."}
            {" "}Cache renovado a cada 1 hora.
            {focus && (
              <span> Projeção Focus: {focus.fonte}.</span>
            )}
          </p>
        </>
      )}
    </div>
  );
}
