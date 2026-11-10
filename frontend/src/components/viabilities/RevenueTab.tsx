"use client";
import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import { useUnsavedChanges } from "@/contexts/UnsavedChangesContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Save, Activity, Download, Upload } from "lucide-react";
import { apoioService } from "@/services/apoio";
import { baixarXlsx, lerPrimeiraAba } from '@/lib/planilha';

interface RevenueTabProps {
  phaseId: number;
  project: any;
  onUpdateProject: (updates: Record<string, any>) => void;
  isReadonly?: boolean;
}

export function RevenueTab({ phaseId, project, onUpdateProject, isReadonly }: RevenueTabProps) {
  const [data, setData] = useState<any>({
    vgv_total: 0,
    velocidade_vendas_json: { meses: [] },
    plano_ativo: "",
    condicoes_pagamento_json: [],
    sistema_amortizacao: "Sem Juros",
    taxa_juros_vendas: 0.0,
    indice_correcao_id: null,
    taxa_correcao_projetada: null,
    tipo_correcao_projetada: "% a.a.",
  });
  const { setHasUnsavedChanges } = useUnsavedChanges();
  const [initialData, setInitialData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [salesMatrixColumns, setSalesMatrixColumns] = useState(36);
  const [distributionMethod, setDistributionMethod] = useState<'proporcional' | 'cascata'>('proporcional');
  const [totalLotsAvailable, setTotalLotsAvailable] = useState<number>(0);
  
  const [globalPlans, setGlobalPlans] = useState<any[]>([]);
  const [curves, setCurves] = useState<any[]>([]);
  const [economicIndicators, setEconomicIndicators] = useState<any[]>([]);
  const [marketIndicesFocus, setMarketIndicesFocus] = useState<any[]>([]);

  const formatCurrency = (val: number) => {
    return val.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [res, globalRes, curvesRes, indRes, ipcaRes, physRes] = await Promise.all([
          api.get(`/viabilities/phases/${phaseId}/revenue`),
          apoioService.getPlanosPagamento(),
          api.get("/curves/"),
          apoioService.getIndicadores(),
          api.get("/market-indices/focus").catch(() => ({ data: [] })),
          api.get(`/viabilities/phases/${phaseId}/physical_data`).catch(() => ({ data: {} }))
        ]);
        
        const dbData = res.data;
        if (!dbData.velocidade_vendas_json) dbData.velocidade_vendas_json = { meses: [] };
        setData(dbData);
        setInitialData(dbData);
        
        const formattedGlobals = globalRes.map((p: any) => ({ nome: p.nome, condicoes: p.condicoes_json || [] }));
        setGlobalPlans(formattedGlobals);
        setCurves(curvesRes.data);
        setEconomicIndicators(indRes);
        setMarketIndicesFocus(ipcaRes.data || []);
        
        const pData = physRes.data || {};
        const totalLotes = (pData.qtde_lotes_residenciais || 0) + (pData.qtde_lotes_comerciais || 0) + (pData.qtde_lotes_mistos || 0);
        setTotalLotsAvailable(totalLotes);
      } catch (e) {
        console.error(e);
      }
    };
    fetchData();
  }, [phaseId]);

  
  useEffect(() => {
    if (initialData && data) {
      const isDirty = JSON.stringify(initialData) !== JSON.stringify(data);
      setHasUnsavedChanges(isDirty);
    }
  }, [data, initialData, setHasUnsavedChanges]);

  const handleSave = async () => {
    setIsLoading(true);
    setMessage("");
    try {
      await api.put(`/viabilities/phases/${phaseId}/revenue`, data);
      setMessage("Dados salvos com sucesso!");
      setInitialData(data);
      setHasUnsavedChanges(false);
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      alert("Erro ao salvar dados.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleApplyGlobalCurveToMatrix = () => {
    const curveId = data.velocidade_vendas_json?.curve_id;
    if (!curveId || !activePlanData) return;
    const curve = curves.find(c => c.id === Number(curveId));
    if (!curve) return;

    const curveMeses = curve.valores_meses_json?.meses || [];
    if (curveMeses.length === 0) return;

    // Método dos Maiores Restos (Hare-Niemeyer) para garantir distribuição exata sem sobras
    const distributeLots = (totalLots: number, weights: number[]) => {
      const totalWeight = weights.reduce((s, w) => s + w, 0);
      if (totalWeight === 0) return weights.map(() => 0);

      const exact = weights.map(w => (totalLots * w) / totalWeight);
      const allocated = exact.map(val => Math.floor(val));
      const remainders = exact.map((val, idx) => ({ idx, rem: val - Math.floor(val) }));

      let sumAllocated = allocated.reduce((s, v) => s + v, 0);
      let remaining = totalLots - sumAllocated;

      remainders.sort((a, b) => b.rem - a.rem);
      for (let i = 0; i < remaining && i < remainders.length; i++) {
        allocated[remainders[i].idx] += 1;
      }
      return allocated;
    };

    const condWeights = activePlanData.condicoes.map((cond: any) => Number(cond.perc) || 0);
    const condTargets = distributeLots(totalLotsAvailable, condWeights);

    const newCondicoes = JSON.parse(JSON.stringify(data.condicoes_pagamento_json));
    const plan = newCondicoes.find((p: any) => p.nome === data.plano_ativo);

    if (plan) {
      const curveWeights = curveMeses.map((m: any) => Number(m) || 0);
      
      if (distributionMethod === 'cascata') {
        const monthTotals = distributeLots(totalLotsAvailable, curveWeights);
        
        let conditionIdx = 0;
        let condRemaining = condTargets[0] || 0;
        
        plan.condicoes.forEach((cond: any) => {
          cond.curve_json = { meses: new Array(curveMeses.length).fill(0), mes_inicio: 1, is_raw_lots: true };
        });

        for (let mIdx = 0; mIdx < curveMeses.length; mIdx++) {
          let monthRemaining = monthTotals[mIdx];
          
          while (monthRemaining > 0 && conditionIdx < plan.condicoes.length) {
            const fillAmount = Math.min(monthRemaining, condRemaining);
            
            plan.condicoes[conditionIdx].curve_json.meses[mIdx] += fillAmount;
            
            monthRemaining -= fillAmount;
            condRemaining -= fillAmount;
            
            if (condRemaining === 0) {
              conditionIdx++;
              if (conditionIdx < plan.condicoes.length) {
                condRemaining = condTargets[conditionIdx];
              }
            }
          }
        }
      } else {
        plan.condicoes.forEach((cond: any, cIdx: number) => {
          const target = condTargets[cIdx];
          const newMeses = distributeLots(target, curveWeights);

          cond.curve_json = {
            meses: newMeses,
            mes_inicio: 1,
            is_raw_lots: true
          };
        });
      }

      if (curveMeses.length > salesMatrixColumns) {
        setSalesMatrixColumns(curveMeses.length);
      }
      
      setData({ ...data, condicoes_pagamento_json: newCondicoes });
    }
  };

  const openModal = () => {
    setIsModalOpen(true);
  };

  const activePlanData = data.condicoes_pagamento_json?.find((p: any) => p.nome === data.plano_ativo);
  const totalPerc = activePlanData?.condicoes?.reduce((sum: number, c: any) => sum + (Number(c.perc) || 0), 0) || 0;
  const isTotalValid = Math.abs(totalPerc - 100) < 0.01;

  const globalSumLots = activePlanData?.condicoes?.reduce((acc: number, cond: any) => {
    const meses = cond.curve_json?.meses || [];
    return acc + meses.reduce((s: number, v: number) => s + (v || 0), 0);
  }, 0) || 0;

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-300">
      
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Premissas de Receita</h2>
          <p className="text-sm text-slate-500">Defina o VGV e a distribuição do fluxo de recebimento.</p>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex flex-col gap-2 bg-slate-50 p-4 rounded-md border border-slate-200">
            {/* INFLAÇÃO */}
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <button 
                  onClick={() => {
                    const isEnabled = data.taxa_correcao_projetada != null;
                    if (!isEnabled && economicIndicators.length > 0) {
                      const ind = economicIndicators.find((i: any) => i.index_type === "INCC") || economicIndicators[0];
                      setData({ 
                        ...data,
                        origem_correcao: "PROJETADO",
                        indice_correcao_id: ind.id,
                        taxa_correcao_projetada: ind.valor,
                        tipo_correcao_projetada: ind.tipo_unidade,
                        nome_indice_mercado: null
                      });
                    } else {
                      setData({ ...data, indice_correcao_id: null, taxa_correcao_projetada: null, origem_correcao: null, nome_indice_mercado: null });
                    }
                  }}
                  disabled={isReadonly}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${data.taxa_correcao_projetada != null ? 'bg-brand-green' : 'bg-slate-300'} ${isReadonly ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${data.taxa_correcao_projetada != null ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
                <span className="font-semibold text-slate-700">Correção Monetária (Inflação)</span>
              </label>
              
              {data.taxa_correcao_projetada != null && (
                <div className="flex items-center gap-2 pl-4 border-l border-slate-200">
                  <select 
                     className="ml-select h-8 text-sm w-36"
                     value={data.origem_correcao || "PROJETADO"}
                     onChange={(e) => {
                       const val = e.target.value;
                       if (val === "PROJETADO") {
                         const ind = economicIndicators.find((i: any) => i.index_type === "INCC") || economicIndicators[0];
                         setData({ ...data, origem_correcao: val, indice_correcao_id: ind?.id || null, taxa_correcao_projetada: ind?.valor || null, tipo_correcao_projetada: ind?.tipo_unidade || "% a.a.", nome_indice_mercado: null });
                       } else {
                         const ind = marketIndicesFocus.find((i: any) => i.index_type === "INCC") || marketIndicesFocus[0];
                         setData({ ...data, origem_correcao: val, indice_correcao_id: null, taxa_correcao_projetada: ind?.valor || null, tipo_correcao_projetada: "% a.a.", nome_indice_mercado: ind?.index_type || null });
                       }
                     }}
                     disabled={isReadonly}
                  >
                    <option value="PROJETADO">Cadastro</option>
                    <option value="MERCADO">Mercado (BCB)</option>
                  </select>

                  {data.origem_correcao === "MERCADO" ? (
                    <select
                      className="ml-select h-8 min-w-[12rem] w-auto max-w-[22rem] text-sm"
                      value={data.nome_indice_mercado || ""}
                      onChange={(e) => {
                        const val = e.target.value;
                        const ind = marketIndicesFocus.find((i:any) => i.index_type === val);
                        if (ind) {
                          setData({ ...data, nome_indice_mercado: ind.index_type, taxa_correcao_projetada: ind.valor, tipo_correcao_projetada: "% a.a." });
                        }
                      }}
                      disabled={isReadonly}
                    >
                      {marketIndicesFocus.map((ind:any) => (
                        <option key={ind.index_type} value={ind.index_type}>{ind.index_type} - Focus ({ind.valor}% a.a.)</option>
                      ))}
                      {marketIndicesFocus.length === 0 && <option value="">Sem dados</option>}
                    </select>
                  ) : (
                    <select
                      className="ml-select h-8 min-w-[12rem] w-auto max-w-[22rem] text-sm"
                      value={data.indice_correcao_id || ""}
                      onChange={(e) => {
                        const val = e.target.value;
                        const ind = economicIndicators.find((i:any) => i.id === Number(val));
                        if (ind) {
                          setData({ ...data, indice_correcao_id: ind.id, taxa_correcao_projetada: ind.valor, tipo_correcao_projetada: ind.tipo_unidade });
                        }
                      }}
                      disabled={isReadonly}
                    >
                      <option value="">Selecione o Índice...</option>
                      {economicIndicators.map((ind:any) => (
                        <option key={ind.id} value={ind.id}>{ind.index_type ? `${ind.index_type} - ` : ''}{ind.nome} ({ind.valor}{ind.tipo_unidade})</option>
                      ))}
                    </select>
                  )}
                  <input 
                    type="number"
                    step="0.01"
                    className="ml-input w-20 h-8 text-sm"
                    value={data.taxa_correcao_projetada ?? ""}
                    onChange={(e) => setData({ ...data, taxa_correcao_projetada: e.target.value === "" ? null : parseFloat(e.target.value) })}
                    disabled={isReadonly}
                  />
                  <select
                    className="ml-select h-8 w-24 text-sm"
                    value={data.tipo_correcao_projetada || "% a.a."}
                    onChange={(e) => setData({ ...data, tipo_correcao_projetada: e.target.value })}
                    disabled={isReadonly || data.origem_correcao === "MERCADO"}
                  >
                    <option value="% a.a.">% a.a.</option>
                    <option value="% a.m.">% a.m.</option>
                  </select>
                </div>
              )}
            </div>

            {/* JUROS E AMORTIZAÇÃO */}
            <div className="flex items-center gap-4 mt-2">
              <label className="flex items-center gap-2 text-sm">
                <span className="font-semibold text-slate-700">Sistema de Amortização:</span>
              </label>
              <select
                className="ml-select h-8 w-36 text-sm"
                value={data.sistema_amortizacao || "Sem Juros"}
                onChange={(e) => setData({ ...data, sistema_amortizacao: e.target.value })}
                disabled={isReadonly}
              >
                <option value="Sem Juros">Sem Juros</option>
                <option value="Price">Tabela Price</option>
                <option value="SAC">Tabela SAC</option>
              </select>

              {data.sistema_amortizacao && data.sistema_amortizacao !== "Sem Juros" && (
                <div className="flex items-center gap-2 pl-4 border-l border-slate-200">
                  <label className="text-sm text-slate-600">Taxa:</label>
                  <input 
                    type="number"
                    step="0.01"
                    className="ml-input w-20 h-8 text-sm"
                    value={data.taxa_juros_vendas ?? ""}
                    onChange={(e) => setData({ ...data, taxa_juros_vendas: e.target.value === "" ? null : parseFloat(e.target.value) })}
                    disabled={isReadonly}
                  />
                  <span className="text-sm text-slate-500">% a.a.</span>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {message && <span className="text-sm text-green-600 font-medium">{message}</span>}
              <Button onClick={handleSave} disabled={isLoading || isReadonly} className="flex items-center gap-2">
              <Save className="w-4 h-4" />
              {isLoading ? "Salvando..." : "Salvar Receitas"}
            </Button>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Painel 1: Valor Geral */}
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider border-b pb-2">Volume Geral de Vendas (VGV)</h3>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">VGV Total Projetado (R$)</label>
            <div className="relative">
              <div className="pl-4 py-3 font-semibold text-lg text-slate-700 bg-slate-100 rounded-md border border-slate-200">
                {formatCurrency(data.vgv_total)}
              </div>
            </div>
            <p className="text-xs text-slate-500 mt-1">Calculado automaticamente pelos Dados Físicos.</p>
          </div>
        </div>

        {/* Painel 2: Condição de Pagamento */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b pb-2">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Condição de Pagamento (%)</h3>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={openModal} disabled={isReadonly}>
                Selecionar Planos
              </Button>
            </div>
          </div>
          
          {data.plano_ativo && activePlanData ? (
            <div className="bg-white border rounded-lg overflow-hidden">
              <div className="bg-slate-50 px-4 py-2 border-b flex justify-between items-center">
                <span className="font-semibold text-slate-700 break-words flex-1">Plano Ativo: {data.plano_ativo}</span>
                <span className={`text-xs font-bold px-2 py-1 rounded ${isTotalValid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  Total: {totalPerc.toFixed(1)}%
                </span>
              </div>
              <div className="p-4 space-y-2">
                {activePlanData.condicoes.map((cond: any, idx: number) => (
                  <div key={idx} className="flex flex-col gap-1 border-b border-slate-100 pb-2 mb-2 last:border-0 last:pb-0 last:mb-0">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-600 font-medium">{cond.nome}</span>
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          max="100"
                          className="w-16 h-7 px-1 text-right border border-slate-300 rounded font-semibold text-slate-700"
                          disabled={isReadonly}
                          value={cond.perc === 0 ? "0" : cond.perc || ""}
                          onChange={(e) => {
                            const newCondicoes = JSON.parse(JSON.stringify(data.condicoes_pagamento_json));
                            const plan = newCondicoes.find((p: any) => p.nome === data.plano_ativo);
                            if (plan && plan.condicoes[idx]) {
                              plan.condicoes[idx].perc = e.target.value === "" ? 0 : parseFloat(e.target.value);
                              setData({ ...data, condicoes_pagamento_json: newCondicoes });
                            }
                          }}
                        />
                        <span className="font-semibold text-slate-500">%</span>
                      </div>
                    </div>
                    <div className="flex gap-4 items-center text-xs text-slate-500">
                      <label className="flex items-center gap-1 cursor-pointer hover:text-slate-700">
                        <input 
                          type="checkbox" 
                          checked={cond.aplica_juros !== false} 
                          disabled={isReadonly}
                          onChange={(e) => {
                            const newCondicoes = JSON.parse(JSON.stringify(data.condicoes_pagamento_json));
                            const plan = newCondicoes.find((p: any) => p.nome === data.plano_ativo);
                            if (plan && plan.condicoes[idx]) {
                              plan.condicoes[idx].aplica_juros = e.target.checked;
                              setData({ ...data, condicoes_pagamento_json: newCondicoes });
                            }
                          }} 
                        />
                        Aplica Juros
                      </label>
                        <label className="flex items-center gap-1 cursor-pointer hover:text-slate-700">
                          <input 
                            type="checkbox" 
                            checked={cond.aplica_correcao !== false} 
                            disabled={isReadonly}
                            onChange={(e) => {
                              const newCondicoes = JSON.parse(JSON.stringify(data.condicoes_pagamento_json));
                              const plan = newCondicoes.find((p: any) => p.nome === data.plano_ativo);
                              if (plan && plan.condicoes[idx]) {
                                plan.condicoes[idx].aplica_correcao = e.target.checked;
                                setData({ ...data, condicoes_pagamento_json: newCondicoes });
                              }
                            }} 
                          />
                          Aplica Correção
                        </label>
                      </div>
                      
                      {/* Entradas */}
                      {cond.nome.toUpperCase() !== "A VISTA" && (
                        <div className="flex gap-4 items-center text-xs text-slate-600 mt-1 bg-slate-50 p-2 rounded">
                          <div className="flex items-center gap-2">
                            <label className="font-medium">Entrada (%):</label>
                            <input
                              type="number"
                              min="0"
                              max="100"
                              step="0.1"
                              className="w-16 h-6 px-1 border border-slate-300 rounded text-right"
                              disabled={isReadonly}
                              value={cond.perc_entrada || ""}
                              onChange={(e) => {
                                const newCondicoes = JSON.parse(JSON.stringify(data.condicoes_pagamento_json));
                                const plan = newCondicoes.find((p: any) => p.nome === data.plano_ativo);
                                if (plan && plan.condicoes[idx]) {
                                  plan.condicoes[idx].perc_entrada = e.target.value === "" ? 0 : parseFloat(e.target.value);
                                  setData({ ...data, condicoes_pagamento_json: newCondicoes });
                                }
                              }}
                              placeholder="0"
                            />
                          </div>
                          <div className="flex items-center gap-2">
                            <label className="font-medium">Parcelas Entrada:</label>
                            <input
                              type="number"
                              min="1"
                              max="12"
                              step="1"
                              className="w-12 h-6 px-1 border border-slate-300 rounded text-right"
                              disabled={isReadonly}
                              value={cond.parcelas_entrada || ""}
                              onChange={(e) => {
                                const newCondicoes = JSON.parse(JSON.stringify(data.condicoes_pagamento_json));
                                const plan = newCondicoes.find((p: any) => p.nome === data.plano_ativo);
                                if (plan && plan.condicoes[idx]) {
                                  plan.condicoes[idx].parcelas_entrada = e.target.value === "" ? 1 : parseInt(e.target.value, 10);
                                  setData({ ...data, condicoes_pagamento_json: newCondicoes });
                                }
                              }}
                              placeholder="1"
                            />
                          </div>
                        </div>
                      )}

                    </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-6 border-2 border-dashed rounded-lg text-center text-slate-500">
              Nenhum plano ativo. Clique em "Gerenciar Planos" para configurar.
            </div>
          )}
        </div>
      </div>

      {/* Modal de Seleção de Planos */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50 shrink-0">
              <h2 className="text-xl font-bold text-slate-800">Selecionar Plano de Pagamento</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600 font-bold text-xl">&times;</button>
            </div>
            
            <div className="p-6 overflow-y-auto flex-1 bg-slate-50/50">
              {globalPlans.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  <p>Nenhum plano cadastrado no módulo de Apoio.</p>
                  <p className="text-sm mt-2">Acesse Apoio &gt; Planos de Pagamento para cadastrar novos planos.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {globalPlans.map((plano, pIdx) => {
                    const isActive = data.plano_ativo === plano.nome;
                    const totalPerc = plano.condicoes.reduce((s: number, c: any) => s + (Number(c.perc) || 0), 0);
                    const isTotalValid = Math.abs(totalPerc - 100) < 0.01;

                    return (
                      <div key={pIdx} className={`bg-white rounded-lg border ${isActive ? 'border-brand-green ring-1 ring-brand-green' : 'border-slate-200'} shadow-sm overflow-hidden flex flex-col`}>
                        <div className="bg-slate-50 px-4 py-3 border-b flex items-center min-h-[64px] h-[64px]">
                          <span className="font-bold text-slate-700 text-sm leading-tight break-words" title={plano.nome}>{plano.nome}</span>
                        </div>
                        <div className="p-4 flex-1 space-y-2 overflow-y-auto max-h-[200px]">
                          {plano.condicoes.map((cond: any, cIdx: number) => (
                            <div key={cIdx} className="flex flex-col gap-1 border-b border-slate-50 pb-1 mb-1 last:border-0 last:pb-0 last:mb-0">
                              <div className="flex justify-between items-center text-xs">
                                <span className="text-slate-600 font-medium">{cond.nome}</span>
                                <span className="font-semibold">{Number(cond.perc).toFixed(1)}%</span>
                              </div>
                              <div className="flex gap-2 text-[10px] text-slate-400">
                                {cond.aplica_juros !== false ? <span className="text-blue-500 bg-blue-50 px-1 rounded">Juros</span> : <span className="line-through">Juros</span>}
                                {cond.aplica_correcao !== false ? <span className="text-orange-500 bg-orange-50 px-1 rounded">Correção</span> : <span className="line-through">Correção</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="p-4 border-t bg-slate-50 space-y-3">
                          <div className="flex justify-between items-center text-xs">
                            <span className="font-semibold text-slate-500">Total:</span>
                            <span className={`font-bold ${isTotalValid ? 'text-green-600' : 'text-red-500'}`}>
                              {totalPerc.toFixed(1)}%
                            </span>
                          </div>
                          <Button 
                            variant={isActive ? "primary" : "outline"}
                            className="w-full text-sm"
                            onClick={() => {
                              // Define este plano como o único em condicoes_pagamento_json e ativa ele
                              setData({
                                ...data,
                                condicoes_pagamento_json: [JSON.parse(JSON.stringify(plano))],
                                plano_ativo: plano.nome
                              });
                              setIsModalOpen(false);
                            }}
                          >
                            {isActive ? "Plano Atual" : "Selecionar"}
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            
            <div className="px-6 py-4 border-t bg-white flex justify-end gap-3 shrink-0">
              <Button variant="outline" onClick={() => setIsModalOpen(false)}>Fechar</Button>
            </div>
          </div>
        </div>
      )}

      {/* Matriz de Vendas */}
      {activePlanData ? (
        <div className="mt-12 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50 flex-wrap gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-800">Velocidade de Vendas (Matriz de Lotes)</h2>
              <p className="text-sm text-slate-500">Distribua os lotes no tempo ou aplique uma curva padrão automaticamente.</p>
            </div>
            
            <div className="flex items-center gap-3 bg-white p-2 border border-slate-200 rounded-lg shadow-sm">
              <select
                disabled={isReadonly}
                className="ml-select h-9 text-sm border-slate-200 rounded-md min-w-[200px]"
                value={data.velocidade_vendas_json?.curve_id || ""}
                onChange={(e) => setData({ ...data, velocidade_vendas_json: { ...data.velocidade_vendas_json, curve_id: e.target.value } })}
              >
                <option value="">Selecione uma curva padrão...</option>
                {curves.filter(c => c.classificacao === 'Receita').map(c => (
                  <option key={c.id} value={c.id}>{c.nome}</option>
                ))}
              </select>

              <select
                disabled={isReadonly}
                className="ml-select h-9 text-sm border-slate-200 rounded-md bg-slate-50"
                value={distributionMethod}
                onChange={(e) => setDistributionMethod(e.target.value as 'proporcional' | 'cascata')}
              >
                <option value="proporcional">Método Proporcional</option>
                <option value="cascata">Acelerar Curtos (Cascata)</option>
              </select>

              <Button 
                variant="primary" 
                size="sm" 
                onClick={handleApplyGlobalCurveToMatrix} 
                disabled={isReadonly || !data.velocidade_vendas_json?.curve_id}
              >
                Aplicar Curva
              </Button>
            </div>
          </div>
          
          <div className="p-6 overflow-auto max-h-[calc(100vh-300px)]">
            <table className="w-full text-sm text-left border-collapse">
              <thead>
                <tr>
                  <th className="border-b p-2 font-semibold text-slate-700 bg-white sticky left-0 z-10 min-w-[150px]">Condição</th>
                  <th className="border-b p-2 font-semibold text-slate-700 bg-white sticky left-[150px] z-10 min-w-[100px] text-center shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">Total Lotes</th>
                  {Array.from({ length: salesMatrixColumns }).map((_, i) => (
                    <th key={i} className="border-b p-2 font-semibold text-slate-700 text-center min-w-[60px]">Mês {i + 1}</th>
                  ))}
                  <th className="border-b p-2 text-center bg-white sticky right-0 min-w-[120px]">
                    <Button variant="outline" size="sm" onClick={() => setSalesMatrixColumns(c => c + 12)}>+ 12 Meses</Button>
                  </th>
                </tr>
              </thead>
              <tbody>
                {activePlanData.condicoes.map((cond: any, cIdx: number) => {
                  const meses = cond.curve_json?.meses || [];
                  const sumLots = meses.reduce((acc: number, val: number) => acc + (val || 0), 0);
                  return (
                    <tr key={cIdx} className="hover:bg-slate-50/50">
                      <td className="border-b p-2 font-medium text-slate-600 bg-white sticky left-0 z-10">{cond.nome}</td>
                      <td className="border-b p-2 text-center bg-white sticky left-[150px] z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] font-bold text-xs">
                         <span className="text-slate-700">
                           {sumLots}
                         </span>
                      </td>
                      {Array.from({ length: salesMatrixColumns }).map((_, mIdx) => (
                        <td key={mIdx} className="border-b p-1">
                          <input
                            type="number"
                            min="0"
                            className="w-full h-8 text-center border border-slate-200 rounded text-xs"
                            value={meses[mIdx] || ""}
                            onChange={(e) => {
                              const val = e.target.value === "" ? 0 : parseFloat(e.target.value);
                              const newCondicoes = JSON.parse(JSON.stringify(data.condicoes_pagamento_json));
                              const plan = newCondicoes.find((p: any) => p.nome === data.plano_ativo);
                              if (plan && plan.condicoes[cIdx]) {
                                const curMeses = plan.condicoes[cIdx].curve_json?.meses || [];
                                const newMeses = [...curMeses];
                                while(newMeses.length <= mIdx) newMeses.push(0);
                                newMeses[mIdx] = val;
                                
                                plan.condicoes[cIdx].curve_json = {
                                  meses: newMeses,
                                  mes_inicio: 1,
                                  is_raw_lots: true
                                };
                                setData({ ...data, condicoes_pagamento_json: newCondicoes });
                              }
                            }}
                          />
                        </td>
                      ))}
                      <td className="border-b p-2 bg-white sticky right-0"></td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="bg-slate-50 font-bold">
                  <td className="p-2 text-right sticky left-0 z-10 bg-slate-50 border-t text-slate-700">Total Geral:</td>
                  <td className="p-2 text-center sticky left-[150px] z-10 bg-slate-50 border-t shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] text-xs">
                    <span className={globalSumLots !== totalLotsAvailable ? "text-red-600" : "text-emerald-600"}>
                      {globalSumLots} / {totalLotsAvailable}
                    </span>
                  </td>
                  <td colSpan={salesMatrixColumns + 1} className="p-2 border-t text-xs text-slate-500">
                    {globalSumLots !== totalLotsAvailable && (
                      <span className="text-red-500 bg-red-50 px-2 py-1 rounded">A soma total de lotes deve ser exatamente igual a {totalLotsAvailable}</span>
                    )}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
          
          <div className="px-6 py-4 border-t bg-slate-50 flex items-center gap-3">
            <Button
              variant="outline"
              onClick={() => {
                const wsData: any[][] = [["Condição", ...Array.from({ length: salesMatrixColumns }).map((_, i) => `Mês ${i + 1}`)]];
                activePlanData.condicoes.forEach((cond: any) => {
                  const meses = cond.curve_json?.meses || [];
                  const rowData = [cond.nome];
                  for (let i = 0; i < salesMatrixColumns; i++) {
                    rowData.push(meses[i] || 0);
                  }
                  wsData.push(rowData);
                });
                void baixarXlsx(wsData, "MatrizVendas", `matriz_vendas_${data.plano_ativo.replace(/\s+/g, '_')}.xlsx`, [20, ...Array(salesMatrixColumns).fill(10)]);
              }}
              className="text-sm"
              disabled={isReadonly}
            >
              <Download className="w-4 h-4 mr-2" />
              Baixar Modelo
            </Button>
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              className="text-sm"
              disabled={isReadonly}
            >
              <Upload className="w-4 h-4 mr-2" />
              Importar Planilha
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = async (evt) => {
                  try {
                    const rows: any[][] = await lerPrimeiraAba(evt.target?.result as ArrayBuffer, file.name);
                    
                    const dataRows = rows.slice(1).filter(r => r.length >= 1 && r[0]);
                    const newCondicoes = JSON.parse(JSON.stringify(data.condicoes_pagamento_json));
                    const plan = newCondicoes.find((p: any) => p.nome === data.plano_ativo);
                    
                    if (plan) {
                      let updatedCount = 0;
                      let maxMonthsFound = salesMatrixColumns;

                      dataRows.forEach(r => {
                        const condName = String(r[0]).trim();
                        const condIndex = plan.condicoes.findIndex((c: any) => String(c.nome).trim() === condName);
                        if (condIndex !== -1) {
                          const meses = r.slice(1).map(val => {
                            const parsed = parseFloat(String(val).replace(',', '.'));
                            return isNaN(parsed) ? 0 : Math.max(0, parsed);
                          });
                          
                          if (meses.length > maxMonthsFound) maxMonthsFound = meses.length;
                          
                          plan.condicoes[condIndex].curve_json = {
                            meses: meses,
                            mes_inicio: 1,
                            is_raw_lots: true
                          };
                          updatedCount++;
                        }
                      });
                      
                      if (maxMonthsFound > salesMatrixColumns) {
                        setSalesMatrixColumns(maxMonthsFound);
                      }
                      
                      setData({ ...data, condicoes_pagamento_json: newCondicoes });
                      alert(`✅ ${updatedCount} condições atualizadas com sucesso!`);
                    }
                  } catch (err) {
                    alert("Erro ao ler a planilha. Verifique o formato do arquivo.");
                    console.error(err);
                  }
                };
                reader.readAsArrayBuffer(file);
                e.target.value = '';
              }}
            />
          </div>
        </div>
      ) : (
        <div className="mt-12 p-12 border-2 border-dashed border-slate-200 rounded-xl flex flex-col items-center justify-center bg-slate-50 text-slate-500">
           <p>Selecione um plano de pagamento para configurar a Velocidade de Vendas.</p>
        </div>
      )}
    </div>
  );
}
