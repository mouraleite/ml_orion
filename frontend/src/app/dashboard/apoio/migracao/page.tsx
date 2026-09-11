"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import {
  getPendencias,
  mapearPendencias,
  runMigration,
  runForecastMigration,
  MigrationMapping,
} from "@/services/migration";
import { apoioService } from "@/services/apoio";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { FolderOpen, CloudDownload, Save, Search } from "lucide-react";

export default function MigracaoSharePoint() {
  const [pendencias, setPendencias] = useState<MigrationMapping[]>([]);
  const [centros, setCentros] = useState<any[]>([]);
  const [planos, setPlanos] = useState<any[]>([]);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [selecoes, setSelecoes] = useState<Record<number, number>>({});
  const [busca, setBusca] = useState("");

  const [message, setMessage] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [pendData, ccData, fpData] = await Promise.all([
        getPendencias(),
        apoioService.getCentrosCusto(),
        apoioService.getPlanosFinanceiros(),
      ]);
      setPendencias(pendData);
      setCentros(ccData.filter((c) => c.status === "Ativo"));
      setPlanos(fpData.filter((p) => p.flAtiva === "S" || p.status === "Ativo"));
    } catch (error) {
      console.error(error);
      setMessage("Erro ao carregar dados.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!message) return;
    const t = setTimeout(() => setMessage(""), 5000);
    return () => clearTimeout(t);
  }, [message]);

  const handleSelect = (id: number, val: string) => {
    if (val) {
      setSelecoes((prev) => ({ ...prev, [id]: parseInt(val) }));
    } else {
      const newSel = { ...selecoes };
      delete newSel[id];
      setSelecoes(newSel);
    }
  };

  const handleSalvar = async () => {
    const payload = Object.entries(selecoes).map(([id, id_destino]) => ({
      id: parseInt(id),
      id_destino,
    }));

    if (payload.length === 0) return;

    try {
      setSubmitting(true);
      await mapearPendencias(payload);
      setMessage("Mapeamentos salvos com sucesso.");
      setSelecoes({});
      await loadData();
    } catch (error) {
      setMessage("Erro ao salvar mapeamentos.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRun = async () => {
    try {
      setSubmitting(true);
      await runMigration();
      setMessage(
        "Rotina iniciada em background! Acompanhe o terminal ou retorne em alguns minutos para ver se há novas pendências."
      );
    } catch (error) {
      setMessage("Erro ao iniciar rotina.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRunForecast = async () => {
    try {
      setSubmitting(true);
      await runForecastMigration();
      setMessage("Rotina de Forecast iniciada em background! Acompanhe o terminal ou retorne em alguns minutos.");
    } catch (error) {
      setMessage("Erro ao iniciar rotina de forecast.");
    } finally {
      setSubmitting(false);
    }
  };

  const term = busca.trim().toLowerCase();
  const pendenciasFiltradas = term
    ? pendencias.filter((p) => {
        const nome = (p.nome_origem || "").toLowerCase();
        const tipo = (p.tipo || "").toLowerCase();
        const tipoLabel = p.tipo === "CENTRO_CUSTO" ? "obra / cc" : "plano financeiro";
        return nome.includes(term) || tipo.includes(term) || tipoLabel.includes(term);
      })
    : pendencias;

  const selecoesCount = Object.keys(selecoes).length;
  const isErrorMessage = message.toLowerCase().includes("erro");

  return (
    <div className="p-8 max-w-[1400px] mx-auto animate-in fade-in duration-300 space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <FolderOpen className="w-6 h-6 text-brand-orange" />
            Carga Inicial SharePoint
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            A rotina automática lê as planilhas da pasta do servidor. Se houver divergência de nomes, resolva aqui.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 shrink-0">
          <Button onClick={handleRun} disabled={submitting} className="gap-2">
            <FolderOpen className="w-4 h-4" />
            {submitting ? "Aguarde..." : "Iniciar Leitura das Pastas"}
          </Button>
          <Button onClick={handleRunForecast} disabled={submitting} variant="outline" className="gap-2">
            <CloudDownload className="w-4 h-4" />
            {submitting ? "Aguarde..." : "Importar Forecasts (SharePoint)"}
          </Button>
        </div>
      </div>

      {message && (
        <div
          className={`px-4 py-3 rounded-lg text-sm font-medium border ${
            isErrorMessage
              ? "bg-amber-50 text-amber-800 border-amber-200"
              : "bg-brand-green/10 text-brand-green border-brand-green/20"
          }`}
        >
          {message}
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-800">
              Pendências de Mapeamento (De-Para)
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Vincule nomes da planilha aos cadastros do ERP ML antes de concluir a carga.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {pendencias.length > 0 && (
              <span className="text-xs font-medium text-slate-500 bg-white border border-slate-200 px-2 py-0.5 rounded-full">
                {pendencias.length} pendências
              </span>
            )}
            {selecoesCount > 0 && (
              <span className="text-xs font-medium text-brand-green bg-brand-green/10 border border-brand-green/20 px-2 py-0.5 rounded-full">
                {selecoesCount} selecionados para salvar
              </span>
            )}
            <Button
              onClick={handleSalvar}
              disabled={selecoesCount === 0 || submitting}
              variant="secondary"
              size="sm"
              className="gap-2"
            >
              <Save className="w-3.5 h-3.5" />
              Salvar Selecionados
            </Button>
          </div>
        </div>

        <div className="p-4 space-y-3">
          {!loading && pendencias.length > 0 && (
            <div className="relative max-w-sm">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="search"
                placeholder="Buscar por nome ou tipo..."
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                className="ml-input pl-9 h-9 text-sm w-full"
              />
            </div>
          )}
          {loading ? (
            <AppLoadingState />
          ) : pendencias.length === 0 ? (
            <div className="p-8 text-center space-y-1 bg-slate-50 rounded-lg border border-dashed border-slate-200">
              <p className="text-sm font-medium text-slate-600">Nenhuma pendência encontrada</p>
              <p className="text-xs text-slate-400">Tudo pronto para a carga.</p>
            </div>
          ) : pendenciasFiltradas.length === 0 ? (
            <div className="p-8 text-center space-y-1 bg-slate-50 rounded-lg border border-dashed border-slate-200">
              <p className="text-sm font-medium text-slate-600">Nenhuma pendência encontrada para a busca</p>
            </div>
          ) : (
            <div className="rounded-lg border border-slate-200 overflow-hidden">
              <div className="overflow-x-auto max-h-[560px]">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 z-10">
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="text-left py-3 px-4 font-semibold text-slate-600 uppercase text-xs tracking-wider">
                        Tipo
                      </th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-600 uppercase text-xs tracking-wider">
                        Nome na Planilha
                      </th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-600 uppercase text-xs tracking-wider">
                        Vincular com ERP ML
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendenciasFiltradas.map((p) => (
                      <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                        <td className="py-2.5 px-4 text-slate-600">
                          {p.tipo === "CENTRO_CUSTO" ? "Obra / CC" : "Plano Financeiro"}
                        </td>
                        <td className="py-2.5 px-4 font-medium text-slate-800">{p.nome_origem}</td>
                        <td className="py-2.5 px-4">
                          <select
                            className="ml-select h-9 text-sm"
                            value={selecoes[p.id] || ""}
                            onChange={(e) => handleSelect(p.id, e.target.value)}
                          >
                            <option value="">-- Selecione para vincular --</option>
                            {p.tipo === "CENTRO_CUSTO"
                              ? centros.map((c) => (
                                  <option key={c.id} value={c.id}>
                                    {c.nome}
                                  </option>
                                ))
                              : planos.map((fp) => (
                                  <option key={fp.id} value={fp.id}>
                                    {fp.db_sienge_id} - {fp.name}
                                  </option>
                                ))}
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
