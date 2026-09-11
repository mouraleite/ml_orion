"use client";
import React, { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { isDiretorUser } from "@/lib/roles";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { integracaoService, IntegracaoLog, Pendencia } from "@/services/integracao";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { RefreshCw, AlertTriangle, CheckCircle, XCircle, Clock } from "lucide-react";

export default function IntegracaoSiengePage() {
  const { user } = useAuth();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<"PENDENCIAS" | "LOGS">("PENDENCIAS");
  const [logs, setLogs] = useState<IntegracaoLog[]>([]);
  const [pendencias, setPendencias] = useState<Pendencia[]>([]);
  const [loading, setLoading] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);

  // Reprocess dates
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(1); // 1st of current month
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split("T")[0];
  });

  useEffect(() => {
    if (!user) return;
    if (!isDiretorUser(user)) {
      router.push("/dashboard");
      return;
    }
    fetchData();
  }, [user, activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === "LOGS") {
        const res = await integracaoService.getLogs(0, 50);
        setLogs(res.items);
      } else {
        const res = await integracaoService.getPendencias(0, 50);
        setPendencias(res.items);
      }
    } catch (error) {
      console.error("Erro ao buscar dados", error);
    } finally {
      setLoading(false);
    }
  };

  const handleReprocess = async () => {
    if (!startDate || !endDate) {
      alert("Selecione data de início e fim.");
      return;
    }
    setReprocessing(true);
    try {
      await integracaoService.reprocessar({ start_date: startDate, end_date: endDate });
      alert("Reprocessamento iniciado! O processo roda em segundo plano. Verifique a aba de Logs em alguns instantes.");
      setActiveTab("LOGS");
    } catch (err) {
      console.error(err);
      alert("Erro ao iniciar reprocessamento.");
    } finally {
      setReprocessing(false);
    }
  };

  const formatDate = (isoString: string) => {
    if (!isoString) return "-";
    return new Date(isoString).toLocaleString("pt-BR");
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(val);
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto space-y-6 animate-in fade-in duration-300">
      <div className="flex justify-between items-start gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <RefreshCw className="w-6 h-6 text-brand-orange" />
            Integração Sienge (Pipeline)
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Gerenciamento de sincronização diária e pendências de reconciliação.
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-col md:flex-row gap-4 items-end">
        <div className="flex-1 w-full">
          <label className="block text-xs font-medium text-slate-500 mb-1">Data Início (Reprocessamento)</label>
          <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>
        <div className="flex-1 w-full">
          <label className="block text-xs font-medium text-slate-500 mb-1">Data Fim (Reprocessamento)</label>
          <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>
        <div className="flex-none w-full md:w-auto">
          <Button 
            onClick={handleReprocess} 
            disabled={reprocessing}
            className="w-full gap-2 bg-brand-orange hover:bg-brand-orange/90 text-white"
          >
            {reprocessing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Sincronizar Manualmente
          </Button>
        </div>
      </div>

      <div className="flex overflow-x-auto border-b border-slate-200 hide-scrollbar">
        <button
          onClick={() => setActiveTab("PENDENCIAS")}
          className={`whitespace-nowrap px-6 py-3 font-medium text-sm border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "PENDENCIAS"
              ? "border-brand-green text-brand-green"
              : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          Pendências de Reconciliação
          {pendencias.length > 0 && (
            <span className="bg-red-100 text-red-600 py-0.5 px-2 rounded-full text-xs">{pendencias.length}</span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("LOGS")}
          className={`whitespace-nowrap px-6 py-3 font-medium text-sm border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "LOGS"
              ? "border-brand-green text-brand-green"
              : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
          }`}
        >
          <Clock className="w-4 h-4" />
          Histórico de Execuções (Logs)
        </button>
      </div>

      {activeTab === "PENDENCIAS" && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200 text-sm text-slate-600">
            Estes registros vieram do Sienge, porém o <strong>Código do Centro de Custo</strong> ou <strong>Categoria Financeira</strong> não existem no cadastro do ERP ML. 
            Corrija o cadastro e efetue uma nova Sincronização.
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-white text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-semibold">Data Recebimento</th>
                  <th className="px-4 py-3 font-semibold">ID Sienge (Trace)</th>
                  <th className="px-4 py-3 font-semibold">Tipo</th>
                  <th className="px-4 py-3 font-semibold">Mês/Ano</th>
                  <th className="px-4 py-3 font-semibold">CC Sienge</th>
                  <th className="px-4 py-3 font-semibold">Plano Sienge</th>
                  <th className="px-4 py-3 font-semibold text-right">Valor</th>
                  <th className="px-4 py-3 font-semibold text-right">VGV</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={8}>
                      <AppLoadingState />
                    </td>
                  </tr>
                ) : pendencias.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-10">
                      <div className="flex flex-col items-center text-center gap-2">
                        <CheckCircle className="w-8 h-8 text-brand-green" />
                        <p className="text-sm font-medium text-slate-600">Nenhuma pendência encontrada</p>
                        <p className="text-xs text-slate-400">A reconciliação está em dia.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  pendencias.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 text-slate-500">{formatDate(p.data_integracao)}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">{p.id_sienge}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                          p.tipo === 'Despesa' ? 'bg-red-100 text-red-700' :
                          p.tipo === 'Receita' ? 'bg-brand-green/10 text-brand-green' :
                          'bg-slate-100 text-slate-700'
                        }`}>
                          {p.tipo || "Indefinido"}
                        </span>
                      </td>
                      <td className="px-4 py-3">{p.mes}/{p.ano}</td>
                      <td className="px-4 py-3 font-medium text-red-600">{p.produto_id_sienge || "-"}</td>
                      <td className="px-4 py-3 font-medium text-red-600">{p.plano_financeiro_id_sienge || "-"}</td>
                      <td className="px-4 py-3 text-right font-medium text-slate-700">{formatCurrency(p.valor)}</td>
                      <td className="px-4 py-3 text-right text-slate-600">{formatCurrency(p.vgv)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === "LOGS" && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-semibold">Início</th>
                  <th className="px-4 py-3 font-semibold">Fim</th>
                  <th className="px-4 py-3 font-semibold">Processo</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold text-right">Volume</th>
                  <th className="px-4 py-3 font-semibold">Erros</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={6}>
                      <AppLoadingState />
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-10">
                      <div className="text-center text-sm text-slate-400 bg-slate-50 rounded-lg border border-dashed border-slate-200 py-6 mx-4">
                        Nenhum histórico encontrado.
                      </div>
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 text-slate-500">{formatDate(log.inicio)}</td>
                      <td className="px-4 py-3 text-slate-500">{formatDate(log.fim || "")}</td>
                      <td className="px-4 py-3 font-medium text-slate-700">{log.processo}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-1.5">
                          {log.status === "SUCESSO" ? <CheckCircle className="w-4 h-4 text-brand-green" /> : 
                           log.status === "PARCIAL" ? <AlertTriangle className="w-4 h-4 text-amber-500" /> : 
                           <XCircle className="w-4 h-4 text-red-500" />}
                          <span className="font-medium text-slate-700">{log.status}</span>
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">{log.volume_processado}</td>
                      <td className="px-4 py-3 text-xs font-mono text-red-500 max-w-xs truncate" title={log.erros || ""}>
                        {log.erros || "-"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
