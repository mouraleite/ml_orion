"use client";

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { getPendencias, mapearPendencias, runMigration, runForecastMigration, MigrationMapping } from '@/services/migration';
import { apoioService } from '@/services/apoio';
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

export default function MigracaoSharePoint() {
  const [pendencias, setPendencias] = useState<MigrationMapping[]>([]);
  const [centros, setCentros] = useState<any[]>([]);
  const [planos, setPlanos] = useState<any[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [selecoes, setSelecoes] = useState<Record<number, number>>({});
  
  const [message, setMessage] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      const [pendData, ccData, fpData] = await Promise.all([
        getPendencias(),
        apoioService.getCentrosCusto(),
        apoioService.getPlanosFinanceiros()
      ]);
      setPendencias(pendData);
      setCentros(ccData.filter(c => c.status === 'Ativo'));
      setPlanos(fpData.filter(p => p.flAtiva === 'S' || p.status === 'Ativo'));
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

  const handleSelect = (id: number, val: string) => {
    if (val) {
      setSelecoes(prev => ({ ...prev, [id]: parseInt(val) }));
    } else {
      const newSel = { ...selecoes };
      delete newSel[id];
      setSelecoes(newSel);
    }
  };

  const handleSalvar = async () => {
    const payload = Object.entries(selecoes).map(([id, id_destino]) => ({
      id: parseInt(id),
      id_destino
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
      setMessage("Rotina iniciada em background! Acompanhe o terminal ou retorne em alguns minutos para ver se há novas pendências.");
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

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Carga Inicial SharePoint</h1>
          <p className="text-gray-500 dark:text-gray-400">
            A rotina automática lê as planilhas da pasta do servidor. Se houver divergência de nomes, resolva aqui.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRun}
            disabled={submitting}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium transition-colors"
          >
            {submitting ? 'Aguarde...' : 'Iniciar Leitura das Pastas'}
          </button>
          <button
            onClick={handleRunForecast}
            disabled={submitting}
            className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md font-medium transition-colors"
          >
            {submitting ? 'Aguarde...' : 'Importar Forecasts (SharePoint)'}
          </button>
        </div>
      </div>

      {message && (
        <div className="p-4 bg-blue-50 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 rounded-lg">
          {message}
        </div>
      )}

      <Card>
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Pendências de Mapeamento (De-Para)</h2>
            <button
              onClick={handleSalvar}
              disabled={Object.keys(selecoes).length === 0 || submitting}
              className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-4 py-2 rounded-md font-medium transition-colors"
            >
              Salvar Selecionados
            </button>
          </div>

          {loading ? (
            <AppLoadingState />
          ) : pendencias.length === 0 ? (
            <p className="text-gray-500 py-4">Nenhuma pendência encontrada. Tudo pronto para a carga!</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nome na Planilha</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vincular com ERP ML</th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {pendencias.map(p => (
                    <tr key={p.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {p.tipo === 'CENTRO_CUSTO' ? 'Obra / CC' : 'Plano Financeiro'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        {p.nome_origem}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <select
                          className="w-full bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                          value={selecoes[p.id] || ''}
                          onChange={(e) => handleSelect(p.id, e.target.value)}
                        >
                          <option value="">-- Selecione para vincular --</option>
                          {p.tipo === 'CENTRO_CUSTO' 
                            ? centros.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)
                            : planos.map(fp => <option key={fp.id} value={fp.id}>{fp.db_sienge_id} - {fp.name}</option>)
                          }
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
