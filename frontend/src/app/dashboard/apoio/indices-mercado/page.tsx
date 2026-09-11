"use client";

import { useEffect, useState, useCallback } from "react";
import toast from "react-hot-toast";
import { api } from "@/lib/api";
import { TrendingUp, TrendingDown, RefreshCw, Activity, CalendarDays, Info } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
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
  const parts = d.split("/");
  if (parts.length === 3) {
    const months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
    return `${months[parseInt(parts[1]) - 1]}/${parts[2].slice(-2)}`;
  }
  return d;
};

const fmtAtualizadoEm = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

const TAB_META: Record<"IPCA" | "INCC" | "IGP-M", { label: string; hint: string }> = {
  IPCA: { label: "IPCA", hint: "Série 433 (IPCA mensal — IBGE)." },
  INCC: { label: "INCC-DI", hint: "Série 192 (INCC-DI mensal — FGV)." },
  "IGP-M": { label: "IGP-M", hint: "Série 189 (IGP-M mensal — FGV)." },
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
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null);

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
      setLastUpdatedAt(new Date().toISOString());
      if (forceRefresh) {
        toast.success("Índices atualizados com o BCB.");
      }
    } catch {
      const msg = "Não foi possível conectar ao BCB. Verifique sua conexão e tente novamente.";
      setError(msg);
      if (forceRefresh) toast.error(msg);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const activeData = activeTab === "IPCA" ? ipca : activeTab === "INCC" ? incc : igpm;
  const focusDisponivel = activeTab === "IPCA" || activeTab === "IGP-M";
  const focusProj = activeTab === "IPCA" ? focus?.IPCA?.[0] : activeTab === "IGP-M" ? focus?.["IGP-M"]?.[0] : null;
  const focusLabel = activeTab === "IPCA" ? "IPCA Focus" : activeTab === "IGP-M" ? "IGP-M Focus" : "Focus";
  const tabMeta = TAB_META[activeTab];

  if (isLoading) {
    return <AppLoadingState />;
  }

  if (error && !ipca && !incc && !igpm) {
    return (
      <div className="p-8 max-w-[900px]">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700 font-medium">{error}</p>
          <Button onClick={() => fetchAll(true)} className="mt-4" variant="danger">
            Tentar Novamente
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-[900px] animate-in fade-in duration-300">
      {/* Header — mesmo padrão de Índices Projetados */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Índices de Mercado</h1>
          <p className="text-slate-500 text-sm mt-1">
            Dados reais do Banco Central do Brasil (BCB/SGS) atualizados automaticamente.
          </p>
          {lastUpdatedAt && (
            <p className="text-xs text-slate-400 mt-1.5">
              Última atualização nesta tela: {fmtAtualizadoEm(lastUpdatedAt)}
            </p>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchAll(true)}
          disabled={isRefreshing}
          className="gap-2 shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
          {isRefreshing ? "Atualizando..." : "Atualizar Dados"}
        </Button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-6 space-y-8">
        {/* Seletor de índice */}
        <div className="flex flex-wrap gap-2 border-b border-slate-100 pb-4">
          {(["IPCA", "INCC", "IGP-M"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-semibold rounded-md border transition-colors ${
                activeTab === tab
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white text-slate-600 border-slate-200 hover:border-brand-primary hover:text-slate-800"
              }`}
            >
              {TAB_META[tab].label}
            </button>
          ))}
        </div>

        {activeData ? (
          <>
            {/* Resumo */}
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <Activity className="w-4 h-4 text-brand-primary" />
                    Resumo — {tabMeta.label}
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">{tabMeta.hint}</p>
                </div>
                <span className="text-xs text-slate-400 bg-slate-50 border border-slate-200 rounded-md px-2 py-1">
                  {activeData.fonte}
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Card className="p-4 space-y-1">
                  <p className="text-xs text-slate-500 font-medium uppercase tracking-wider flex items-center gap-1">
                    <CalendarDays className="w-3.5 h-3.5" /> Último Mês
                  </p>
                  <p className="text-slate-400 text-xs">{activeData.ultimo_mes.data || "—"}</p>
                  <p
                    className={`text-2xl font-bold ${
                      (activeData.ultimo_mes.mensal ?? 0) >= 0 ? "text-slate-800" : "text-red-600"
                    }`}
                  >
                    {fmtPerc(activeData.ultimo_mes.mensal)}
                  </p>
                  <p className="text-xs text-slate-400">variação mensal</p>
                </Card>

                <Card className="p-4 space-y-1">
                  <p className="text-xs text-slate-500 font-medium uppercase tracking-wider flex items-center gap-1">
                    <TrendingUp className="w-3.5 h-3.5" /> Acum. Ano
                  </p>
                  <p className="text-slate-400 text-xs">
                    Jan–{activeData.ultimo_mes.data?.split("/")[0] || "—"}
                  </p>
                  <p className="text-2xl font-bold text-slate-800">
                    {fmtPerc(activeData.ultimo_mes.acumulado_ano)}
                  </p>
                  <p className="text-xs text-slate-400">acumulado no ano</p>
                </Card>

                <Card className="p-4 space-y-1 border-brand-primary/30">
                  <p className="text-xs text-slate-700 font-medium uppercase tracking-wider flex items-center gap-1">
                    <Activity className="w-3.5 h-3.5 text-brand-primary" /> Acum. 12 Meses
                  </p>
                  <p className="text-slate-400 text-xs">últimos 12 meses</p>
                  <p className="text-2xl font-bold text-slate-800">
                    {fmtPerc(activeData.ultimo_mes.acumulado_12m)}
                  </p>
                  <p className="text-xs text-slate-400">acumulado 12m</p>
                </Card>

                <Card className="p-4 space-y-1">
                  <p className="text-xs text-slate-500 font-medium uppercase tracking-wider flex items-center gap-1">
                    <Info className="w-3.5 h-3.5 text-brand-primary" /> {focusLabel}
                  </p>
                  {focusDisponivel ? (
                    <>
                      <p className="text-slate-400 text-xs">
                        {focusProj?.DataReferencia ? `Ref. ${focusProj.DataReferencia}` : "Projeção anual"}
                      </p>
                      <p className="text-2xl font-bold text-slate-800">
                        {focusProj?.Mediana != null ? fmtPerc(focusProj.Mediana) : "—"}
                      </p>
                      <p className="text-xs text-slate-400">mediana Focus</p>
                    </>
                  ) : (
                    <>
                      <p className="text-slate-400 text-xs">Boletim Focus</p>
                      <p className="text-2xl font-bold text-slate-400">—</p>
                      <p className="text-xs text-slate-400">sem série Focus para INCC</p>
                    </>
                  )}
                </Card>
              </div>
            </div>

            {/* Histórico */}
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <Activity className="w-4 h-4 text-brand-primary" />
                    Histórico Mensal — {activeData.indicador}
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Valores mensais e acumulados publicados pelo BCB/SGS.
                  </p>
                </div>
              </div>

              {activeData.historico.length === 0 ? (
                <div className="p-6 text-center text-sm text-slate-400 bg-slate-50 rounded-lg border border-dashed">
                  Nenhum histórico disponível para {tabMeta.label}.
                </div>
              ) : (
                <div className="rounded-lg border border-slate-200 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-slate-50 border-b border-slate-200">
                          <th className="text-left py-3 px-4 font-semibold text-slate-600 uppercase text-xs tracking-wider">
                            Período
                          </th>
                          <th className="text-right py-3 px-4 font-semibold text-slate-600 uppercase text-xs tracking-wider">
                            Mensal (%)
                          </th>
                          <th className="text-right py-3 px-4 font-semibold text-slate-600 uppercase text-xs tracking-wider">
                            Acum. Ano (%)
                          </th>
                          <th className="text-right py-3 px-4 font-semibold text-slate-600 uppercase text-xs tracking-wider">
                            Acum. 12m (%)
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...activeData.historico].reverse().map((item, idx) => (
                          <tr
                            key={item.data}
                            className={`border-b border-slate-50 hover:bg-slate-50 transition-colors ${
                              idx === 0 ? "bg-brand-primary/5 font-semibold" : ""
                            }`}
                          >
                            <td className="py-2.5 px-4 text-slate-700">{fmtData(item.data)}</td>
                            <td
                              className={`py-2.5 px-4 text-right font-mono ${
                                item.valor >= 0 ? "text-slate-800" : "text-red-600"
                              }`}
                            >
                              <span className="flex items-center justify-end gap-1">
                                {item.valor >= 0 ? (
                                  <TrendingUp className="w-3 h-3 text-green-500" />
                                ) : (
                                  <TrendingDown className="w-3 h-3 text-red-500" />
                                )}
                                {fmtPerc(item.valor, 2)}
                              </span>
                            </td>
                            <td className="py-2.5 px-4 text-right font-mono text-slate-600">
                              {fmtPerc(item.acumulado_ano, 2)}
                            </td>
                            <td
                              className={`py-2.5 px-4 text-right font-mono font-semibold ${
                                idx === 0 ? "text-slate-900" : "text-slate-700"
                              }`}
                            >
                              {fmtPerc(item.acumulado_12m, 2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            <p className="text-xs text-slate-400 text-center pt-2 border-t border-slate-100">
              Fonte: Banco Central do Brasil — BCB/SGS. {tabMeta.hint} Cache renovado a cada 1 hora.
              {focus && focusDisponivel && <span> Projeção Focus: {focus.fonte}.</span>}
            </p>
          </>
        ) : (
          <div className="p-6 text-center text-sm text-slate-400 bg-slate-50 rounded-lg border border-dashed">
            Nenhum dado carregado para {tabMeta.label}.
          </div>
        )}
      </div>
    </div>
  );
}
