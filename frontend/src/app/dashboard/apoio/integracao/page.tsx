"use client";
import React, { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { isDiretorUser } from "@/lib/roles";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
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
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
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

      <Card className="p-4 border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 items-end bg-white">
        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-500 mb-1">Data Início (Reprocessamento)</label>
          <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>
        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-500 mb-1">Data Fim (Reprocessamento)</label>
          <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>
        <div className="flex-none">
          <Button 
            onClick={handleReprocess} 
            disabled={reprocessing}
            className="w-full gap-2 bg-brand-orange hover:bg-brand-orange/90 text-white"
          >
            {reprocessing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Sincronizar Manualmente
          </Button>
        </div>
      </Card>

      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab("PENDENCIAS")}
            className={`whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
              activeTab === "PENDENCIAS"
                ? "border-brand-orange text-brand-orange"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            Pendências de Reconciliação
            {activeTab === "PENDENCIAS" && pendencias.length > 0 && (
              <span className="bg-red-100 text-red-600 py-0.5 px-2 rounded-full text-xs">{pendencias.length}</span>
            )}
          </button>
          <button
            onClick={() => setActiveTab("LOGS")}
            className={`whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
              activeTab === "LOGS"
                ? "border-brand-orange text-brand-orange"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            <Clock className="w-4 h-4" />
            Histórico de Execuções (Logs)
          </button>
        </nav>
      </div>

      {activeTab === "PENDENCIAS" && (
        <Card className="overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200 text-sm text-slate-600">
            Estes registros vieram do Sienge, porém o <strong>Código do Centro de Custo</strong> ou <strong>Categoria Financeira</strong> não existem no cadastro do ERP ML. 
            Corrija o cadastro e efetue uma nova Sincronização.
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-white text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-medium">Data Recebimento</th>
                  <th className="px-4 py-3 font-medium">ID Sienge (Trace)</th>
                  <th className="px-4 py-3 font-medium">Tipo</th>
                  <th className="px-4 py-3 font-medium">Mês/Ano</th>
                  <th className="px-4 py-3 font-medium">CC Sienge</th>
                  <th className="px-4 py-3 font-medium">Plano Sienge</th>
                  <th className="px-4 py-3 font-medium text-right">Valor</th>
                  <th className="px-4 py-3 font-medium text-right">VGV</th>
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
                    <td colSpan={8} className="px-4 py-8 text-center text-slate-500 flex flex-col items-center">
                      <CheckCircle className="w-8 h-8 text-green-500 mb-2" />
                      Nenhuma pendência encontrada. Excelente!
                    </td>
                  </tr>
                ) : (
                  pendencias.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 text-slate-500">{formatDate(p.data_integracao)}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">{p.id_sienge}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                          p.tipo === 'Despesa' ? 'bg-red-100 text-red-700' :
                          p.tipo === 'Receita' ? 'bg-green-100 text-green-700' :
                          'bg-blue-100 text-blue-700'
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
        </Card>
      )}

      {activeTab === "LOGS" && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-medium">Início</th>
                  <th className="px-4 py-3 font-medium">Fim</th>
                  <th className="px-4 py-3 font-medium">Processo</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium text-right">Volume</th>
                  <th className="px-4 py-3 font-medium">Erros</th>
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
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                      Nenhum histórico encontrado.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 text-slate-500">{formatDate(log.inicio)}</td>
                      <td className="px-4 py-3 text-slate-500">{formatDate(log.fim || "")}</td>
                      <td className="px-4 py-3 font-medium text-slate-700">{log.processo}</td>
                      <td className="px-4 py-3 flex items-center gap-1">
                        {log.status === "SUCESSO" ? <CheckCircle className="w-4 h-4 text-green-500" /> : 
                         log.status === "PARCIAL" ? <AlertTriangle className="w-4 h-4 text-yellow-500" /> : 
                         <XCircle className="w-4 h-4 text-red-500" />}
                        <span className="font-medium text-slate-700">{log.status}</span>
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
        </Card>
      )}
    </div>
  );
}
