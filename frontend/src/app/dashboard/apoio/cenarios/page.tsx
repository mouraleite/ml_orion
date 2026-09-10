"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { apoioService } from "@/services/apoio";
import { Save, AlertCircle, RefreshCw, Plus, TrendingUp, TrendingDown, Clock, Building2 } from "lucide-react";

export default function CenariosPage() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const data = await apoioService.getCenarios();
      setScenarios(data);
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
      const data = await apoioService.seedCenarios();
      setScenarios(data);
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
      const dbScenarios = await apoioService.getCenarios();
      
      // Delete missing
      const stateIds = scenarios.map(s => s.id).filter(id => id);
      const toDelete = dbScenarios.filter(s => !stateIds.includes(s.id));
      for (const s of toDelete) {
        await apoioService.deleteCenario(s.id);
      }
      
      // Update or create
      for (const s of scenarios) {
        if (!s.nome || s.nome.trim() === "") continue; // Skip empty names
        
        const payload = {
          nome: s.nome,
          vgv_multiplier: s.vgv_multiplier ?? 1.0,
          construction_cost_multiplier: s.construction_cost_multiplier ?? 1.0,
          sales_speed_multiplier: s.sales_speed_multiplier ?? 1.0
        };

        if (s.id) {
          await apoioService.updateCenario(s.id, payload);
        } else {
          await apoioService.createCenario(payload);
        }
      }
      
      setMessage("Cenários salvos com sucesso!");
      setTimeout(() => setMessage(""), 3000);
      await fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || "Erro ao salvar cenários.");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <AppLoadingState />;
  }

  // Helper to convert float multiplier to percentage string for input
  const toPercentage = (val: number | undefined) => {
    if (val === undefined || val === null) return "0";
    return ((val - 1) * 100).toFixed(0);
  };

  // Helper to convert percentage string to float multiplier
  const fromPercentage = (val: string) => {
    const num = parseFloat(val) || 0;
    return 1 + (num / 100);
  };

  return (
    <div className="p-8 max-w-[1600px] animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Cenários Globais (Simulações)</h1>
          <p className="text-slate-500 text-sm mt-1">Configure variáveis macroeconômicas de estresse para os estudos de viabilidade e motor matemático.</p>
        </div>
        
        <div className="flex items-center gap-3">
          {scenarios.length === 0 && (
            <Button variant="outline" onClick={handleSeed} className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4" /> Semear Cenários Padrão
            </Button>
          )}
          <Button variant="outline" onClick={() => setScenarios([...scenarios, { nome: "Novo Cenário", vgv_multiplier: 1.0, construction_cost_multiplier: 1.0, sales_speed_multiplier: 1.0 }])} className="flex items-center gap-2 border-dashed">
            <Plus className="w-4 h-4" /> Novo Cenário
          </Button>
          {message && <span className="text-sm text-green-600 font-medium">{message}</span>}
          <Button onClick={handleSaveAll} disabled={isSaving} className="flex items-center gap-2">
            <Save className="w-4 h-4" /> {isSaving ? "Salvando..." : "Salvar Alterações"}
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-6 items-stretch">
        {scenarios.map((scenario, sIdx) => {
          return (
            <div key={sIdx} className="w-[360px] bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col justify-between">
              <div className="p-5 flex-1 flex flex-col gap-5">
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Nome do Cenário</label>
                  <input 
                    className="ml-input w-full text-base font-semibold border-slate-200"
                    value={scenario.nome}
                    placeholder="Ex: Otimista"
                    onChange={(e) => {
                      const newScenarios = [...scenarios];
                      newScenarios[sIdx].nome = e.target.value;
                      setScenarios(newScenarios);
                    }}
                  />
                </div>

                <div className="h-px bg-slate-100 w-full" />

                {/* Parametros */}
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-slate-700">
                      <div className="w-6 h-6 rounded-md bg-green-50 flex items-center justify-center">
                        <TrendingUp className="w-3.5 h-3.5 text-green-600" />
                      </div>
                      <span className="text-sm font-medium">Variação VGV (%)</span>
                    </div>
                    <input 
                      type="number"
                      className="ml-input w-24 text-right"
                      value={toPercentage(scenario.vgv_multiplier)}
                      onChange={(e) => {
                        const newScenarios = [...scenarios];
                        newScenarios[sIdx].vgv_multiplier = fromPercentage(e.target.value);
                        setScenarios(newScenarios);
                      }}
                    />
                  </div>

                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-slate-700">
                      <div className="w-6 h-6 rounded-md bg-orange-50 flex items-center justify-center">
                        <Building2 className="w-3.5 h-3.5 text-orange-600" />
                      </div>
                      <span className="text-sm font-medium">Custo de Obra (%)</span>
                    </div>
                    <input 
                      type="number"
                      className="ml-input w-24 text-right"
                      value={toPercentage(scenario.construction_cost_multiplier)}
                      onChange={(e) => {
                        const newScenarios = [...scenarios];
                        newScenarios[sIdx].construction_cost_multiplier = fromPercentage(e.target.value);
                        setScenarios(newScenarios);
                      }}
                    />
                  </div>

                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-slate-700">
                      <div className="w-6 h-6 rounded-md bg-blue-50 flex items-center justify-center">
                        <Clock className="w-3.5 h-3.5 text-blue-600" />
                      </div>
                      <span className="text-sm font-medium">Velocidade Vendas (%)</span>
                    </div>
                    <input 
                      type="number"
                      className="ml-input w-24 text-right"
                      value={toPercentage(scenario.sales_speed_multiplier)}
                      onChange={(e) => {
                        const newScenarios = [...scenarios];
                        newScenarios[sIdx].sales_speed_multiplier = fromPercentage(e.target.value);
                        setScenarios(newScenarios);
                      }}
                    />
                  </div>
                </div>

              </div>
              <div className="bg-slate-50 px-5 py-3 border-t flex justify-between items-center gap-2">
                <span className="text-[11px] font-medium text-slate-400">ID: {scenario.id || "Não salvo"}</span>
                <button onClick={() => setScenarios(scenarios.filter((_, i) => i !== sIdx))} className="text-red-500 hover:text-red-700 text-xs font-semibold uppercase tracking-wider" title="Excluir Cenário">Excluir</button>
              </div>
            </div>
          );
        })}
        
        <div className="w-[360px] flex items-center justify-center border-2 border-dashed border-slate-300 rounded-xl bg-slate-50/50 hover:bg-slate-100 transition-colors cursor-pointer min-h-[140px]" onClick={() => {
          setScenarios([...scenarios, { nome: `Novo Cenário ${scenarios.length + 1}`, vgv_multiplier: 1.0, construction_cost_multiplier: 1.0, sales_speed_multiplier: 1.0 }]);
        }}>
          <div className="text-center text-slate-500 font-medium">
            <div className="text-3xl mb-2">+</div>
            Adicionar Cenário
          </div>
        </div>
      </div>
    </div>
  );
}
