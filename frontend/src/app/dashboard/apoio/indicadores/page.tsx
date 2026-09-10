"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { Input } from "@/components/ui/Input";
import { apoioService } from "@/services/apoio";
import { Plus, Trash2, Save, Activity } from "lucide-react";
import { Card } from "@/components/ui/Card";

export default function IndicadoresPage() {
  const [indicators, setIndicators] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const data = await apoioService.getIndicadores();
      setIndicators(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAdd = async (type: string) => {
    const nome = prompt(`Digite o nome para o novo cenário de ${type}:`);
    if (!nome) return;

    try {
      await apoioService.createIndicador({
        nome,
        index_type: type,
        valor: 0,
        tipo_unidade: "% a.a."
      });
      fetchData();
    } catch (error) {
      alert("Erro ao criar indicador.");
    }
  };

  const handleDelete = async (id: number) => {
    if (!(await confirmDialog("Tem certeza que deseja excluir este cenário?", { variant: "danger" }))) return;
    try {
      await apoioService.deleteIndicador(id);
      fetchData();
    } catch (error) {
      alert("Erro ao excluir indicador.");
    }
  };

  const handleUpdate = (id: number, field: string, value: any) => {
    setIndicators(prev => prev.map(ind => ind.id === id ? { ...ind, [field]: value } : ind));
  };

  const handleSave = async (indicator: any) => {
    setIsSaving(true);
    setMessage("");
    try {
      await apoioService.updateIndicador(indicator.id, {
        nome: indicator.nome,
        valor: parseFloat(indicator.valor) || 0,
        tipo_unidade: indicator.tipo_unidade
      });
      setMessage(`"${indicator.nome}" salvo com sucesso!`);
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      alert("Erro ao salvar indicador.");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <AppLoadingState />;
  }

  const ipcas = indicators.filter(i => i.index_type === "IPCA");
  const inccs = indicators.filter(i => i.index_type === "INCC");
  const igpms = indicators.filter(i => i.index_type === "IGP-M");

  const renderList = (type: string, list: any[]) => (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
        <div>
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-brand-primary" />
            Cenários de {type}
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Opções que aparecerão na tela de Viabilidade ao corrigir {type === "IPCA" ? "Receitas" : "Obras"}.
          </p>
        </div>
        <Button onClick={() => handleAdd(type)} variant="outline" size="sm" className="gap-2">
          <Plus className="w-4 h-4" /> Novo Cenário
        </Button>
      </div>

      {list.length === 0 ? (
        <div className="p-6 text-center text-sm text-slate-400 bg-slate-50 rounded-lg border border-dashed">
          Nenhum cenário cadastrado para {type}.
        </div>
      ) : (
        <div className="grid gap-3">
          {list.map(ind => (
            <Card key={ind.id} className="p-4 flex items-center justify-between group hover:border-brand-primary transition-colors">
              <div className="flex-1 pr-4">
                <Input 
                  value={ind.nome} 
                  onChange={(e) => handleUpdate(ind.id, "nome", e.target.value)}
                  className="font-semibold text-slate-800 h-8 bg-transparent border-transparent hover:border-slate-300 focus:bg-white"
                  placeholder="Nome do Cenário"
                />
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <Input 
                    type="number" 
                    step="0.01" 
                    className="w-24 h-8 font-mono text-sm"
                    value={ind.valor}
                    onChange={(e) => handleUpdate(ind.id, "valor", e.target.value)}
                  />
                  <select
                    className="ml-select h-8 w-24 text-sm"
                    value={ind.tipo_unidade}
                    onChange={(e) => handleUpdate(ind.id, "tipo_unidade", e.target.value)}
                  >
                    <option value="% a.a.">% a.a.</option>
                    <option value="% a.m.">% a.m.</option>
                  </select>
                </div>
                
                <div className="w-px h-6 bg-slate-200 mx-2"></div>
                
                <Button onClick={() => handleSave(ind)} size="sm" variant="secondary" className="gap-2" disabled={isSaving}>
                  <Save className="w-3.5 h-3.5" /> Salvar
                </Button>
                <button 
                  onClick={() => handleDelete(ind.id)}
                  className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                  title="Excluir"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="p-8 max-w-[900px] animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Índices Projetados</h1>
          <p className="text-slate-500 text-sm mt-1">Crie cenários (Otimista, Pessimista, Padrão) para as taxas de projeção.</p>
        </div>
        
        {message && <div className="px-4 py-2 bg-green-50 text-green-700 rounded-md font-medium text-sm animate-in fade-in">{message}</div>}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-6 space-y-10">
        {renderList("IPCA", ipcas)}
        {renderList("INCC", inccs)}
        {renderList("IGP-M", igpms)}
      </div>
    </div>
  );
}
