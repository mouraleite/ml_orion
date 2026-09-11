"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { Input } from "@/components/ui/Input";
import { apoioService } from "@/services/apoio";
import { Plus, Trash2, Save, Calculator } from "lucide-react";
import { Card } from "@/components/ui/Card";

export default function ImpostosPage() {
  const [regimes, setRegimes] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const data = await apoioService.getTaxRegimes();
      setRegimes(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAdd = async () => {
    const nome = prompt("Digite o nome para o novo Regime Tributário (ex: RET, Lucro Presumido):");
    if (!nome) return;

    try {
      await apoioService.createTaxRegime({
        nome,
        pis: 0,
        cofins: 0,
        irpj: 0,
        csll: 0,
        outros: 0
      });
      fetchData();
    } catch (error) {
      alert("Erro ao criar regime tributário.");
    }
  };

  const handleDelete = async (id: number) => {
    if (!(await confirmDialog("Tem certeza que deseja excluir este Regime Tributário?", { variant: "danger" }))) return;
    try {
      await apoioService.deleteTaxRegime(id);
      fetchData();
    } catch (error) {
      alert("Erro ao excluir regime tributário.");
    }
  };

  const handleUpdate = (id: number, field: string, value: any) => {
    setRegimes(prev => prev.map(reg => reg.id === id ? { ...reg, [field]: value } : reg));
  };

  const handleSave = async (regime: any) => {
    setIsSaving(true);
    setMessage("");
    try {
      await apoioService.updateTaxRegime(regime.id, {
        nome: regime.nome,
        pis: parseFloat(regime.pis) || 0,
        cofins: parseFloat(regime.cofins) || 0,
        irpj: parseFloat(regime.irpj) || 0,
        csll: parseFloat(regime.csll) || 0,
        outros: parseFloat(regime.outros) || 0
      });
      setMessage(`"${regime.nome}" salvo com sucesso!`);
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      alert("Erro ao salvar regime tributário.");
    } finally {
      setIsSaving(false);
    }
  };

  const calculateTotal = (reg: any) => {
    return (parseFloat(reg.pis) || 0) + (parseFloat(reg.cofins) || 0) + (parseFloat(reg.irpj) || 0) + (parseFloat(reg.csll) || 0) + (parseFloat(reg.outros) || 0);
  };

  if (isLoading) {
    return <AppLoadingState />;
  }

  return (
    <div className="p-8 max-w-[1400px] mx-auto animate-in fade-in duration-300 space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Calculator className="w-6 h-6 text-brand-green" />
            Regimes Tributários
          </h1>
          <p className="text-slate-500 text-sm mt-1">Crie os regimes de impostos com as alíquotas separadas (PIS, COFINS, etc) para utilizar nos estudos.</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {message && (
            <div className="px-3 py-1.5 bg-brand-green/10 text-brand-green border border-brand-green/20 rounded-lg font-medium text-sm animate-in fade-in">
              {message}
            </div>
          )}
          <Button onClick={handleAdd} className="gap-2 shrink-0">
            <Plus className="w-4 h-4" /> Novo Regime
          </Button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-800">Cadastros atuais</h3>
          <span className="text-xs font-medium text-slate-500 bg-white border border-slate-200 px-2 py-0.5 rounded-full">
            {regimes.length} {regimes.length === 1 ? "regime" : "regimes"}
          </span>
        </div>

        <div className="p-4 space-y-3">
          {regimes.length === 0 ? (
            <div className="p-8 text-center space-y-2 bg-slate-50 rounded-lg border border-dashed border-slate-200">
              <p className="text-sm font-medium text-slate-600">Nenhum regime cadastrado</p>
              <p className="text-xs text-slate-400">Clique em &quot;Novo Regime&quot; para começar.</p>
            </div>
          ) : (
            regimes.map(reg => (
              <Card key={reg.id} className="p-4 group hover:border-brand-green/40 transition-colors flex flex-col gap-4">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-slate-100 pb-3">
                  <Input 
                    value={reg.nome} 
                    onChange={(e) => handleUpdate(reg.id, "nome", e.target.value)}
                    className="font-semibold text-slate-800 h-9 bg-transparent border-transparent hover:border-slate-300 focus:bg-white max-w-sm text-base"
                    placeholder="Nome do Regime (Ex: RET 4%)"
                  />
                  
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-slate-500 uppercase">Total da Carga:</span>
                    <span className="text-sm font-bold bg-brand-green/10 px-3 py-1 rounded-md text-brand-green">
                      {calculateTotal(reg).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%
                    </span>
                    <div className="hidden sm:block w-px h-6 bg-slate-200 mx-1"></div>
                    <Button onClick={() => handleSave(reg)} size="sm" variant="secondary" className="gap-2" disabled={isSaving}>
                      <Save className="w-3.5 h-3.5" /> Salvar
                    </Button>
                    <button 
                      onClick={() => handleDelete(reg.id)}
                      className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                      title="Excluir"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-500 uppercase">PIS (%)</label>
                    <Input type="number" step="0.01" className="h-8 text-sm font-mono" value={reg.pis} onChange={(e) => handleUpdate(reg.id, "pis", parseFloat(e.target.value) || 0)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-500 uppercase">COFINS (%)</label>
                    <Input type="number" step="0.01" className="h-8 text-sm font-mono" value={reg.cofins} onChange={(e) => handleUpdate(reg.id, "cofins", parseFloat(e.target.value) || 0)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-500 uppercase">IRPJ (%)</label>
                    <Input type="number" step="0.01" className="h-8 text-sm font-mono" value={reg.irpj} onChange={(e) => handleUpdate(reg.id, "irpj", parseFloat(e.target.value) || 0)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-500 uppercase">CSLL (%)</label>
                    <Input type="number" step="0.01" className="h-8 text-sm font-mono" value={reg.csll} onChange={(e) => handleUpdate(reg.id, "csll", parseFloat(e.target.value) || 0)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-500 uppercase">Outros (%)</label>
                    <Input type="number" step="0.01" className="h-8 text-sm font-mono" value={reg.outros} onChange={(e) => handleUpdate(reg.id, "outros", parseFloat(e.target.value) || 0)} />
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
