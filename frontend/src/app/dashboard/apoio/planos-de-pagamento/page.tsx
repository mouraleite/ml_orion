"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { apoioService } from "@/services/apoio";
import { Save, AlertCircle, RefreshCw, Plus, CreditCard } from "lucide-react";

export default function PlanosDePagamentoPage() {
  const [plans, setPlans] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const data = await apoioService.getPlanosPagamento();
      setPlans(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSeed = async () => {
    setIsLoading(true);
    try {
      const data = await apoioService.seedPlanosPagamento();
      setPlans(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveAll = async () => {
    setIsSaving(true);
    setMessage("");
    try {
      // Create, update, or delete plans based on current state vs DB state.
      // To keep it simple, we can delete all existing and recreate them, OR
      // we can do proper sync. Since we have IDs, we update existing, create new, and delete missing.

      const dbPlans = await apoioService.getPlanosPagamento();

      // Delete missing
      const stateIds = plans.map(p => p.id).filter(id => id);
      const toDelete = dbPlans.filter(p => !stateIds.includes(p.id));
      for (const p of toDelete) {
        await apoioService.deletePlanoPagamento(p.id);
      }

      // Update or create
      for (const p of plans) {
        if (p.id) {
          await apoioService.updatePlanoPagamento(p.id, { nome: p.nome, condicoes_json: p.condicoes_json || p.condicoes });
        } else {
          await apoioService.createPlanoPagamento({ nome: p.nome, condicoes_json: p.condicoes_json || p.condicoes });
        }
      }

      setMessage("Planos salvos com sucesso!");
      setTimeout(() => setMessage(""), 3000);
      await fetchData();
    } catch (error) {
      alert("Erro ao salvar planos.");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <AppLoadingState />;
  }

  const planValidity = plans.map((plano) => {
    const conds = plano.condicoes_json || plano.condicoes || [];
    const totalPerc = conds.reduce((s: number, c: any) => s + (Number(c.perc) || 0), 0);
    const isTotalValid = Math.abs(totalPerc - 100) < 0.01;
    return { totalPerc, isTotalValid };
  });
  const invalidCount = planValidity.filter((p) => !p.isTotalValid).length;

  return (
    <div className="p-6 md:p-8 max-w-[1600px] mx-auto animate-in fade-in duration-300 space-y-6">
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <CreditCard className="w-6 h-6 text-brand-green" />
            Planos de Pagamento
          </h1>
          <p className="text-slate-500 text-sm mt-1">Gerencie os templates globais de planos de pagamento e suas condições.</p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {message && (
            <span className="text-sm font-medium text-brand-green bg-brand-green/10 border border-brand-green/20 px-3 py-1.5 rounded-lg">
              {message}
            </span>
          )}
          {plans.length === 0 && (
            <Button variant="outline" onClick={handleSeed} className="gap-2">
              <RefreshCw className="w-4 h-4" /> Semear Planos Padrão
            </Button>
          )}
          <Button variant="outline" onClick={() => setPlans([...plans, { nome: "Novo Plano", condicoes_json: [{ nome: "Sinal", perc: 100 }] }])} className="gap-2 border-dashed">
            <Plus className="w-4 h-4" /> Novo Plano
          </Button>
          <Button onClick={handleSaveAll} disabled={isSaving} className="gap-2">
            <Save className="w-4 h-4" /> {isSaving ? "Salvando..." : "Salvar Alterações"}
          </Button>
        </div>
      </div>

      {plans.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-10 text-center space-y-3">
          <div className="mx-auto w-12 h-12 rounded-full bg-slate-50 border border-dashed border-slate-200 flex items-center justify-center">
            <CreditCard className="w-5 h-5 text-slate-400" />
          </div>
          <p className="text-sm font-medium text-slate-600">Nenhum plano de pagamento cadastrado</p>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">Use &quot;Semear Planos Padrão&quot; ou crie um novo plano.</p>
          <div className="flex items-center justify-center gap-2 flex-wrap mt-2">
            <Button variant="outline" onClick={handleSeed} className="gap-2">
              <RefreshCw className="w-4 h-4" /> Semear Planos Padrão
            </Button>
            <Button onClick={() => setPlans([...plans, { nome: "Novo Plano", condicoes_json: [{ nome: "Sinal", perc: 100 }] }])} className="gap-2">
              <Plus className="w-4 h-4" /> Novo Plano
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Planos</p>
              <p className="text-2xl font-bold text-slate-800 mt-1">{plans.length}</p>
              <p className="text-xs text-slate-400 mt-1">templates cadastrados</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">% inválido</p>
              <p className={`text-2xl font-bold mt-1 ${invalidCount > 0 ? "text-red-600" : "text-slate-800"}`}>
                {invalidCount}
              </p>
              <p className="text-xs text-slate-400 mt-1">soma ≠ 100%</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Regra</p>
              <p className="text-sm text-slate-700 mt-2 leading-relaxed">
                A soma das porcentagens de cada plano deve ser exatamente <span className="font-semibold">100%</span>.
              </p>
            </div>
          </div>

          {invalidCount > 0 && (
            <div className="flex items-center gap-2 px-4 py-3 bg-red-50 text-red-700 border border-red-100 rounded-xl text-sm font-medium">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {invalidCount} {invalidCount === 1 ? "plano está inválido" : "planos estão inválidos"} (soma das porcentagens ≠ 100%). Ajuste as condições antes de salvar.
            </div>
          )}

          <div className="flex flex-wrap gap-4 items-stretch">
            {plans.map((plano, pIdx) => {
              const conds = plano.condicoes_json || plano.condicoes || [];
              const { totalPerc, isTotalValid } = planValidity[pIdx];

              return (
                <div
                  key={pIdx}
                  className={`w-[320px] bg-white rounded-xl border shadow-sm overflow-hidden flex flex-col ${
                    isTotalValid ? "border-slate-200 hover:border-slate-300" : "border-red-200"
                  } transition-colors`}
                >
                  <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex justify-between items-start gap-2">
                    <textarea
                      className="font-bold text-slate-800 bg-transparent border-none outline-none focus:ring-1 focus:ring-brand-green rounded px-1 w-full text-sm leading-tight resize-none"
                      value={plano.nome}
                      rows={2}
                      onChange={(e) => {
                        const newPlans = [...plans];
                        newPlans[pIdx].nome = e.target.value;
                        setPlans(newPlans);
                      }}
                      placeholder="Nome do Plano"
                    />
                    <button onClick={() => setPlans(plans.filter((_, i) => i !== pIdx))} className="text-red-400 hover:text-red-600 shrink-0 p-1" title="Excluir Plano">&times;</button>
                  </div>
                  <div className="p-4 flex-1 space-y-3">
                    {conds.map((cond: any, cIdx: number) => (
                      <div key={cIdx} className="flex flex-col gap-1 border-b border-slate-100 pb-2 mb-2 last:border-0 last:pb-0 last:mb-0">
                        <div className="flex gap-2 items-center">
                          <input
                            className="ml-input flex-1 text-sm py-1.5 px-2 border rounded"
                            value={cond.nome}
                            placeholder="Condição"
                            onChange={(e) => {
                              const newPlans = [...plans];
                              (newPlans[pIdx].condicoes_json || newPlans[pIdx].condicoes)[cIdx].nome = e.target.value;
                              setPlans(newPlans);
                            }}
                          />
                          <div className="relative w-20 shrink-0">
                            <input
                              type="number" step="0.1"
                              className="ml-input text-sm py-1.5 pl-2 pr-6 border rounded w-full"
                              value={cond.perc}
                              onChange={(e) => {
                                const newPlans = [...plans];
                                (newPlans[pIdx].condicoes_json || newPlans[pIdx].condicoes)[cIdx].perc = parseFloat(e.target.value) || 0;
                                setPlans(newPlans);
                              }}
                            />
                            <span className="absolute right-2 top-1.5 text-xs text-slate-400">%</span>
                          </div>
                          <button onClick={() => {
                            const newPlans = [...plans];
                            if (newPlans[pIdx].condicoes_json) {
                              newPlans[pIdx].condicoes_json = newPlans[pIdx].condicoes_json.filter((_: any, i: number) => i !== cIdx);
                            } else if (newPlans[pIdx].condicoes) {
                              newPlans[pIdx].condicoes = newPlans[pIdx].condicoes.filter((_: any, i: number) => i !== cIdx);
                            }
                            setPlans(newPlans);
                          }} className="text-slate-400 hover:text-red-500 font-bold">&times;</button>
                        </div>
                        <div className="flex gap-4 items-center text-xs text-slate-500 ml-1">
                          <label className="flex items-center gap-1.5 cursor-pointer hover:text-slate-700">
                            <input type="checkbox" className="ml-checkbox" checked={cond.aplica_juros !== false} onChange={(e) => {
                              const newPlans = [...plans];
                              (newPlans[pIdx].condicoes_json || newPlans[pIdx].condicoes)[cIdx].aplica_juros = e.target.checked;
                              setPlans(newPlans);
                            }} />
                            Aplica Juros
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer hover:text-slate-700">
                            <input type="checkbox" className="ml-checkbox" checked={cond.aplica_correcao !== false} onChange={(e) => {
                              const newPlans = [...plans];
                              (newPlans[pIdx].condicoes_json || newPlans[pIdx].condicoes)[cIdx].aplica_correcao = e.target.checked;
                              setPlans(newPlans);
                            }} />
                            Aplica Correção
                          </label>
                        </div>
                      </div>
                    ))}

                    <Button variant="outline" size="sm" className="w-full text-xs py-1.5 h-8 border-dashed mt-2" onClick={() => {
                      const newPlans = [...plans];
                      const targetArr = newPlans[pIdx].condicoes_json || newPlans[pIdx].condicoes;
                      targetArr.push({ nome: "Nova Condição", perc: 0 });
                      setPlans(newPlans);
                    }}>+ Condição</Button>
                  </div>

                  <div className="px-4 py-3 border-t border-slate-100 bg-slate-50 flex flex-col gap-2">
                    <div className="flex justify-between items-center text-sm">
                      <span className="font-semibold text-slate-500">Soma Total:</span>
                      <span className={`font-bold ${isTotalValid ? "text-brand-green" : "text-red-500"}`}>
                        {Number(totalPerc.toFixed(2))}%
                      </span>
                    </div>
                    {!isTotalValid && (
                      <div className="flex items-center gap-1 text-xs text-red-500 bg-red-50 p-2 rounded border border-red-100">
                        <AlertCircle className="w-3 h-3 shrink-0" />
                        <span>A soma das porcentagens deve ser exatamente 100%.</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            <button
              type="button"
              onClick={() => {
                setPlans([...plans, { nome: `Novo Plano ${plans.length + 1}`, condicoes_json: [] }]);
              }}
              className="w-[320px] min-h-[220px] rounded-xl border-2 border-dashed border-slate-300 bg-slate-50/70 hover:bg-slate-100 hover:border-brand-green/40 transition-colors flex flex-col items-center justify-center gap-2 text-slate-500 hover:text-brand-green"
            >
              <Plus className="w-8 h-8" />
              <span className="text-sm font-semibold">Adicionar Plano</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
