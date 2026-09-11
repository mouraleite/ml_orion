"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { Input } from "@/components/ui/Input";
import { apoioService } from "@/services/apoio";
import { Plus, Trash2, Save, Calculator } from "lucide-react";

export default function ImpostosPage() {
  const [regimes, setRegimes] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);
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
    setSavingId(regime.id);
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
      setTimeout(() => setSavingId(null), 1500);
    } catch (error) {
      alert("Erro ao salvar regime tributário.");
      setSavingId(null);
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

  const cargaValues = regimes.map(calculateTotal);
  const avgCarga = cargaValues.length
    ? cargaValues.reduce((a, b) => a + b, 0) / cargaValues.length
    : 0;
  const maxCarga = cargaValues.length ? Math.max(...cargaValues) : 0;

  return (
    <div className="p-6 md:p-8 max-w-[1400px] mx-auto animate-in fade-in duration-300 space-y-6">
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

      {regimes.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-10 text-center space-y-3">
          <div className="mx-auto w-12 h-12 rounded-full bg-slate-50 border border-dashed border-slate-200 flex items-center justify-center">
            <Calculator className="w-5 h-5 text-slate-400" />
          </div>
          <p className="text-sm text-slate-600 font-medium">Nenhum regime cadastrado</p>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">Clique em &quot;Novo Regime&quot; para começar.</p>
          <Button onClick={handleAdd} className="gap-2 mt-2">
            <Plus className="w-4 h-4" /> Novo Regime
          </Button>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Regimes</p>
              <p className="text-2xl font-bold text-slate-800 mt-1">{regimes.length}</p>
              <p className="text-xs text-slate-400 mt-1">cadastrados no sistema</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Carga média</p>
              <p className="text-2xl font-bold text-slate-800 mt-1">
                {avgCarga.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%
              </p>
              <p className="text-xs text-slate-400 mt-1">média dos totais (visual)</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Maior carga</p>
              <p className="text-2xl font-bold text-slate-800 mt-1">
                {maxCarga.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%
              </p>
              <p className="text-xs text-slate-400 mt-1">maior soma entre regimes</p>
            </div>
          </div>

          <div className="bg-emerald-50/60 border border-brand-green/20 rounded-xl px-4 py-3 text-sm text-slate-700">
            O total da carga é a <span className="font-semibold">soma das alíquotas</span> (PIS + COFINS + IRPJ + CSLL + Outros) — somente visualização.
          </div>

          <div className="grid grid-cols-1 gap-4">
            {regimes.map(reg => (
              <div
                key={reg.id}
                className="bg-white rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-colors flex flex-col"
              >
                <div className="p-5 flex-1 space-y-4">
                  <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <Input
                        value={reg.nome}
                        onChange={(e) => handleUpdate(reg.id, "nome", e.target.value)}
                        className="font-bold text-slate-800 h-10 bg-transparent border-transparent hover:border-slate-300 focus:bg-white max-w-md text-lg"
                        placeholder="Nome do Regime (Ex: RET 4%)"
                      />
                      <p className="text-xs text-slate-500 mt-1">
                        Ajuste as alíquotas abaixo e salve o regime.
                      </p>
                    </div>
                    <span className="shrink-0 text-xs font-semibold text-brand-green bg-brand-green/10 border border-brand-green/20 px-2.5 py-1 rounded-full self-start">
                      {calculateTotal(reg).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}% carga
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">PIS (%)</label>
                      <Input type="number" step="0.01" className="h-9 text-sm font-mono" value={reg.pis} onChange={(e) => handleUpdate(reg.id, "pis", parseFloat(e.target.value) || 0)} />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">COFINS (%)</label>
                      <Input type="number" step="0.01" className="h-9 text-sm font-mono" value={reg.cofins} onChange={(e) => handleUpdate(reg.id, "cofins", parseFloat(e.target.value) || 0)} />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">IRPJ (%)</label>
                      <Input type="number" step="0.01" className="h-9 text-sm font-mono" value={reg.irpj} onChange={(e) => handleUpdate(reg.id, "irpj", parseFloat(e.target.value) || 0)} />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">CSLL (%)</label>
                      <Input type="number" step="0.01" className="h-9 text-sm font-mono" value={reg.csll} onChange={(e) => handleUpdate(reg.id, "csll", parseFloat(e.target.value) || 0)} />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">Outros (%)</label>
                      <Input type="number" step="0.01" className="h-9 text-sm font-mono" value={reg.outros} onChange={(e) => handleUpdate(reg.id, "outros", parseFloat(e.target.value) || 0)} />
                    </div>
                  </div>
                </div>

                <div className="px-5 py-4 border-t border-slate-100 bg-slate-50 flex gap-2">
                  <Button
                    onClick={() => handleSave(reg)}
                    className="flex-1 gap-2"
                    disabled={isSaving}
                  >
                    <Save className="w-4 h-4" />
                    {savingId === reg.id
                      ? (isSaving ? "Salvando..." : "Salvo")
                      : "Salvar regime"}
                  </Button>
                  <Button
                    variant="ghost"
                    className="gap-2 text-red-500 hover:text-red-600 hover:bg-red-50"
                    onClick={() => handleDelete(reg.id)}
                    title="Excluir"
                  >
                    <Trash2 className="w-4 h-4" />
                    Excluir
                  </Button>
                </div>
              </div>
            ))}

            <button
              type="button"
              onClick={handleAdd}
              className="min-h-[120px] rounded-xl border-2 border-dashed border-slate-300 bg-slate-50/70 hover:bg-slate-100 hover:border-brand-green/40 transition-colors flex flex-col items-center justify-center gap-2 text-slate-500 hover:text-brand-green"
            >
              <Plus className="w-7 h-7" />
              <span className="text-sm font-semibold">Adicionar novo regime</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
