"use client";
import React, { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { isDiretorUser } from "@/lib/roles";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { auditoriaService, AuditoriaLog, AuditoriaFilterParams } from "@/services/auditoria";
import { Download, Search, RefreshCw, ShieldAlert } from "lucide-react";

export default function LogsDeAuditoriaPage() {
  const { user } = useAuth();
  const router = useRouter();
  
  const [logs, setLogs] = useState<AuditoriaLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  
  // Filtros
  const [filtroEvento, setFiltroEvento] = useState("");
  const [filtroTabela, setFiltroTabela] = useState("");
  const [filtroDataInicio, setFiltroDataInicio] = useState("");
  const [filtroDataFim, setFiltroDataFim] = useState("");
  const [filtroUsuarioId, setFiltroUsuarioId] = useState("");

  const [skip, setSkip] = useState(0);
  const limit = 50;

  useEffect(() => {
    if (!user) return;
    if (!isDiretorUser(user)) {
      router.push("/dashboard");
      return;
    }
    fetchLogs();
  }, [user, skip]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params: AuditoriaFilterParams = {
        skip,
        limit,
      };
      if (filtroEvento) params.evento = filtroEvento;
      if (filtroTabela) params.tabela_afetada = filtroTabela;
      if (filtroDataInicio) params.data_inicio = new Date(filtroDataInicio).toISOString();
      if (filtroDataFim) {
        const d = new Date(filtroDataFim);
        d.setHours(23, 59, 59, 999);
        params.data_fim = d.toISOString();
      }
      if (filtroUsuarioId) params.usuario_id = Number(filtroUsuarioId);

      const res = await auditoriaService.getLogs(params);
      setLogs(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error("Erro ao buscar logs", err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const params: AuditoriaFilterParams = {};
      if (filtroEvento) params.evento = filtroEvento;
      if (filtroTabela) params.tabela_afetada = filtroTabela;
      if (filtroDataInicio) params.data_inicio = new Date(filtroDataInicio).toISOString();
      if (filtroDataFim) {
        const d = new Date(filtroDataFim);
        d.setHours(23, 59, 59, 999);
        params.data_fim = d.toISOString();
      }
      if (filtroUsuarioId) params.usuario_id = Number(filtroUsuarioId);

      const blob = await auditoriaService.exportLogs(params);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `auditoria_export.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error("Erro ao exportar logs", err);
      alert("Falha ao exportar relatório.");
    }
  };

  const formatDate = (isoString: string) => {
    return new Date(isoString).toLocaleString("pt-BR");
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-brand-orange" />
            Logs de Auditoria
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Histórico imutável de alterações em orçamentos, forecasts e cadastros sensíveis.
          </p>
        </div>
        <Button variant="outline" onClick={handleExport} className="gap-2">
          <Download className="w-4 h-4" /> Exportar CSV
        </Button>
      </div>

      <Card className="p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Usuário ID</label>
            <Input 
              type="number"
              placeholder="Ex: 1" 
              value={filtroUsuarioId}
              onChange={(e) => setFiltroUsuarioId(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Tabela Afetada</label>
            <Input 
              placeholder="Ex: orcamentos" 
              value={filtroTabela}
              onChange={(e) => setFiltroTabela(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Evento</label>
            <Input 
              placeholder="Ex: Alteracao" 
              value={filtroEvento}
              onChange={(e) => setFiltroEvento(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Data Início</label>
            <Input 
              type="date"
              value={filtroDataInicio}
              onChange={(e) => setFiltroDataInicio(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Data Fim</label>
            <Input 
              type="date"
              value={filtroDataFim}
              onChange={(e) => setFiltroDataFim(e.target.value)}
            />
          </div>
        </div>
        <div className="flex justify-end">
          <Button 
            onClick={() => { setSkip(0); fetchLogs(); }}
            disabled={loading}
            className="gap-2"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Filtrar
          </Button>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-medium">Data/Hora</th>
                <th className="px-4 py-3 font-medium">Usuário</th>
                <th className="px-4 py-3 font-medium">Evento</th>
                <th className="px-4 py-3 font-medium">Tabela/ID</th>
                <th className="px-4 py-3 font-medium">Campo</th>
                <th className="px-4 py-3 font-medium w-64">Valor Anterior</th>
                <th className="px-4 py-3 font-medium w-64">Novo Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    Nenhum registro encontrado.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/50">
                    <td className="px-4 py-3 whitespace-nowrap text-slate-500">{formatDate(log.data_hora)}</td>
                    <td className="px-4 py-3 font-medium text-slate-700">{log.usuario_nome || `ID: ${log.usuario_id}`}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                        log.evento === 'Alteracao' ? 'bg-blue-100 text-blue-700' :
                        log.evento === 'Criacao' ? 'bg-green-100 text-green-700' :
                        log.evento === 'Exclusao' ? 'bg-red-100 text-red-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {log.evento}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {log.tabela_afetada} <span className="text-slate-400">#{log.registro_id}</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-brand-orange">{log.campo}</td>
                    <td className="px-4 py-3">
                      <div className="max-h-16 overflow-y-auto font-mono text-xs text-slate-500 break-all bg-red-50 p-1 rounded border border-red-100">
                        {log.valor_anterior || "-"}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="max-h-16 overflow-y-auto font-mono text-xs text-slate-700 break-all bg-green-50 p-1 rounded border border-green-100">
                        {log.novo_valor || "-"}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="p-4 border-t border-slate-200 flex justify-between items-center bg-slate-50">
          <span className="text-sm text-slate-500">
            Mostrando {skip + 1} até {Math.min(skip + limit, total)} de {total} registros
          </span>
          <div className="space-x-2">
            <Button 
              variant="outline" 
              size="sm" 
              disabled={skip === 0} 
              onClick={() => setSkip(skip - limit)}
            >
              Anterior
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              disabled={skip + limit >= total} 
              onClick={() => setSkip(skip + limit)}
            >
              Próxima
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
