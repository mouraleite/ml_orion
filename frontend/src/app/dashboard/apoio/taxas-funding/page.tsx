"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { Input } from "@/components/ui/Input";
import { Save, Building2, FileText, Landmark, ShieldCheck, CheckCircle, Search } from "lucide-react";

export default function TaxasFundingPage() {
  const [rates, setRates] = useState<any>({
    CVM: { ICVM_400: 0.0005, ICVM_476: 0.0003, Mínimo: 809.16 },
    ANBIMA: { Taxa_Registro: 0.000044, Min_400: 15700, Max_400: 109910, Min_476: 1568, Max_476: 3136 },
    B3: { Registro: [], Custodia: [] },
    Securitizadoras: {
      "Vórtx (Não Guarda-Chuva)": { Agente_Fiduciario_Implantacao: 16000, Agente_Fiduciario_Recorrente: 10000, Instituicao_Custodiante: 5000, Registro_Lastro: 5000, Liquidante: 500 },
      "Oliveira Trust (Guarda-Chuva)": { Agente_Fiduciario_Implantacao: 15000, Agente_Fiduciario_Recorrente: 4000, Instituicao_Custodiante: 5000, Registro_Lastro: 5000, Liquidante: 500 },
      "Vórtx (Guarda-Chuva)": { Agente_Fiduciario_Implantacao: 16000, Agente_Fiduciario_Recorrente: 10000, Instituicao_Custodiante: 0, Registro_Lastro: 0, Liquidante: 500 }
    },
    Prestador_GrossUp: { "Opea - Estruturação": 0.0965, "Opea - Administração": 0.1953, "Oliveira Trust": 0.1633, "Vórtx": 0.1633 }
  });
  
  const [activeTab, setActiveTab] = useState("CVM_ANBIMA");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [secSearch, setSecSearch] = useState("");

  useEffect(() => {
    fetchRates();
  }, []);

  const fetchRates = async () => {
    setIsLoading(true);
    try {
      const res = await api.get(`/apoio/system-settings/funding_rates`);
      if (res.data && res.data.value) {
        setRates(res.data.value);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setMessage("");

    try {
      await api.post(`/apoio/system-settings`, {
        key: "funding_rates",
        value: rates
      });
      setMessage("Taxas salvas com sucesso!");
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      alert("Erro ao salvar as taxas no banco de dados.");
    } finally {
      setIsSaving(false);
    }
  };

  const updateRate = (category: string, field: string, value: string) => {
    setRates((prev: any) => ({
      ...prev,
      [category]: {
        ...prev[category],
        [field]: parseFloat(value) || 0
      }
    }));
  };

  const updateSecuritizadora = (secName: string, field: string, value: string) => {
    setRates((prev: any) => ({
      ...prev,
      Securitizadoras: {
        ...prev.Securitizadoras,
        [secName]: {
          ...prev.Securitizadoras[secName],
          [field]: parseFloat(value) || 0
        }
      }
    }));
  };

  const addSecuritizadora = () => {
    const name = window.prompt("Digite o nome da nova Securitizadora:");
    if (!name || name.trim() === "") return;
    
    if (rates.Securitizadoras && rates.Securitizadoras[name]) {
      alert("Já existe uma Securitizadora com este nome.");
      return;
    }

    setRates((prev: any) => ({
      ...prev,
      Securitizadoras: {
        ...prev.Securitizadoras,
        [name]: {
          Agente_Fiduciario_Implantacao: 0,
          Agente_Fiduciario_Recorrente: 0,
          Instituicao_Custodiante: 0,
          Registro_Lastro: 0,
          Liquidante: 0
        }
      }
    }));
  };

  const removeSecuritizadora = async (secName: string) => {
    if (!(await confirmDialog(`Tem certeza que deseja excluir a securitizadora "${secName}"?`, { variant: "danger" }))) return;
    
    setRates((prev: any) => {
      const newSec = { ...prev.Securitizadoras };
      delete newSec[secName];
      return {
        ...prev,
        Securitizadoras: newSec
      };
    });
  };


  const updateB3 = (type: "Registro" | "Custodia", index: number, field: "max" | "rate", value: string) => {
    const newB3 = { ...rates.B3 };
    newB3[type][index][field] = parseFloat(value) || 0;
    setRates((prev: any) => ({ ...prev, B3: newB3 }));
  };

  const addB3Row = (type: "Registro" | "Custodia") => {
    const newB3 = { ...rates.B3 };
    newB3[type].push({ max: 0, rate: 0 });
    setRates((prev: any) => ({ ...prev, B3: newB3 }));
  };

  const removeB3Row = (type: "Registro" | "Custodia", index: number) => {
    const newB3 = { ...rates.B3 };
    newB3[type].splice(index, 1);
    setRates((prev: any) => ({ ...prev, B3: newB3 }));
  };

  if (isLoading) return <AppLoadingState />;

  const tabs = [
    { id: "CVM_ANBIMA", label: "CVM & ANBIMA", icon: Landmark },
    { id: "B3", label: "B3 (Registro e Custódia)", icon: Building2 },
    { id: "Securitizadoras", label: "Securitizadoras", icon: ShieldCheck },
    { id: "GrossUp", label: "Taxas Gross Up", icon: FileText },
  ] as const;

  return (
    <div className="p-8 space-y-6 animate-in fade-in duration-300 max-w-[1400px] mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Landmark className="w-6 h-6 text-brand-green" />
            Taxas de Funding (CRI)
          </h1>
          <p className="text-slate-500 mt-1 text-sm">
            Configure as tabelas de preços da B3, CVM, ANBIMA e Securitizadoras de forma amigável.
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {message && (
            <span className="text-sm font-medium text-brand-green bg-brand-green/10 border border-brand-green/20 px-3 py-1.5 rounded-lg inline-flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 shrink-0" />
              {message}
            </span>
          )}
          <Button onClick={handleSave} disabled={isSaving} className="gap-2 shrink-0">
            <Save className="w-4 h-4" />
            {isSaving ? "Salvando..." : "Salvar Configurações"}
          </Button>
        </div>
      </div>

      <div className="flex overflow-x-auto border-b border-slate-200 hide-scrollbar">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setActiveTab(id)}
            className={`whitespace-nowrap px-6 py-3 font-medium text-sm border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === id
                ? "border-brand-green text-brand-green"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>
      <p className="text-xs text-slate-500 -mt-2">
        Edite a aba ativa e clique em Salvar Configurações para persistir todas as abas.
      </p>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6">
          
          {/* CVM e ANBIMA */}
          {activeTab === "CVM_ANBIMA" && (
            <div className="space-y-8 animate-in fade-in">
              <div className="space-y-4">
                <h3 className="text-base font-bold text-slate-800 border-b border-slate-200 pb-2">Taxas CVM</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <label className="text-sm font-medium text-slate-700">ICVM 400 (Decimal)</label>
                    <Input type="number" step="0.0001" value={rates.CVM?.ICVM_400} onChange={(e) => updateRate("CVM", "ICVM_400", e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium text-slate-700">ICVM 476 (Decimal)</label>
                    <Input type="number" step="0.0001" value={rates.CVM?.ICVM_476} onChange={(e) => updateRate("CVM", "ICVM_476", e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium text-slate-700">Mínimo (R$)</label>
                    <Input type="number" step="0.01" value={rates.CVM?.Mínimo} onChange={(e) => updateRate("CVM", "Mínimo", e.target.value)} />
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-base font-bold text-slate-800 border-b border-slate-200 pb-2">Taxas ANBIMA</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <label className="text-sm font-medium text-slate-700">Taxa de Registro</label>
                    <Input type="number" step="0.000001" value={rates.ANBIMA?.Taxa_Registro} onChange={(e) => updateRate("ANBIMA", "Taxa_Registro", e.target.value)} />
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                  <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
                    <h4 className="font-semibold text-slate-700 text-sm">Limites ICVM 400 (R$)</h4>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-xs text-slate-500">Mínimo</label>
                        <Input type="number" value={rates.ANBIMA?.Min_400} onChange={(e) => updateRate("ANBIMA", "Min_400", e.target.value)} />
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs text-slate-500">Máximo</label>
                        <Input type="number" value={rates.ANBIMA?.Max_400} onChange={(e) => updateRate("ANBIMA", "Max_400", e.target.value)} />
                      </div>
                    </div>
                  </div>

                  <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
                    <h4 className="font-semibold text-slate-700 text-sm">Limites ICVM 476 (R$)</h4>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-xs text-slate-500">Mínimo</label>
                        <Input type="number" value={rates.ANBIMA?.Min_476} onChange={(e) => updateRate("ANBIMA", "Min_476", e.target.value)} />
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs text-slate-500">Máximo</label>
                        <Input type="number" value={rates.ANBIMA?.Max_476} onChange={(e) => updateRate("ANBIMA", "Max_476", e.target.value)} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* B3 */}
          {activeTab === "B3" && (
            <div className="space-y-8 animate-in fade-in">
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2 gap-3 flex-wrap">
                  <h3 className="text-base font-bold text-slate-800">Tabela Escalonada: Registro B3</h3>
                  <Button variant="outline" size="sm" onClick={() => addB3Row("Registro")}>+ Adicionar Faixa</Button>
                </div>
                <div className="bg-slate-50 rounded-lg border border-slate-200 p-4">
                  {(!rates.B3?.Registro || rates.B3.Registro.length === 0) ? (
                    <div className="py-8 text-center text-sm text-slate-400 border border-dashed border-slate-200 rounded-lg bg-white">
                      Nenhuma faixa de registro. Clique em &quot;Adicionar Faixa&quot;.
                    </div>
                  ) : (
                    <>
                      <div className="grid grid-cols-12 gap-4 mb-2 px-2">
                        <div className="col-span-5 text-xs font-bold text-slate-500 uppercase tracking-wider">Volume Máximo (R$)</div>
                        <div className="col-span-5 text-xs font-bold text-slate-500 uppercase tracking-wider">Taxa Decimal</div>
                        <div className="col-span-2"></div>
                      </div>
                      {rates.B3.Registro.map((row: any, i: number) => (
                        <div key={i} className="grid grid-cols-12 gap-4 items-center mb-2">
                          <div className="col-span-5">
                            <Input type="number" value={row.max} onChange={(e) => updateB3("Registro", i, "max", e.target.value)} />
                          </div>
                          <div className="col-span-5">
                            <Input type="number" step="0.000001" value={row.rate} onChange={(e) => updateB3("Registro", i, "rate", e.target.value)} />
                          </div>
                          <div className="col-span-2 flex justify-end">
                            <Button variant="ghost" className="text-red-500 hover:text-red-700 hover:bg-red-50" onClick={() => removeB3Row("Registro", i)}>Remover</Button>
                          </div>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2 gap-3 flex-wrap">
                  <h3 className="text-base font-bold text-slate-800">Tabela Escalonada: Custódia B3</h3>
                  <Button variant="outline" size="sm" onClick={() => addB3Row("Custodia")}>+ Adicionar Faixa</Button>
                </div>
                <div className="bg-slate-50 rounded-lg border border-slate-200 p-4">
                  {(!rates.B3?.Custodia || rates.B3.Custodia.length === 0) ? (
                    <div className="py-8 text-center text-sm text-slate-400 border border-dashed border-slate-200 rounded-lg bg-white">
                      Nenhuma faixa de custódia. Clique em &quot;Adicionar Faixa&quot;.
                    </div>
                  ) : (
                    <>
                      <div className="grid grid-cols-12 gap-4 mb-2 px-2">
                        <div className="col-span-5 text-xs font-bold text-slate-500 uppercase tracking-wider">Volume Máximo (R$)</div>
                        <div className="col-span-5 text-xs font-bold text-slate-500 uppercase tracking-wider">Taxa Decimal</div>
                        <div className="col-span-2"></div>
                      </div>
                      {rates.B3.Custodia.map((row: any, i: number) => (
                        <div key={i} className="grid grid-cols-12 gap-4 items-center mb-2">
                          <div className="col-span-5">
                            <Input type="number" value={row.max} onChange={(e) => updateB3("Custodia", i, "max", e.target.value)} />
                          </div>
                          <div className="col-span-5">
                            <Input type="number" step="0.000001" value={row.rate} onChange={(e) => updateB3("Custodia", i, "rate", e.target.value)} />
                          </div>
                          <div className="col-span-2 flex justify-end">
                            <Button variant="ghost" className="text-red-500 hover:text-red-700 hover:bg-red-50" onClick={() => removeB3Row("Custodia", i)}>Remover</Button>
                          </div>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Securitizadoras */}
          {activeTab === "Securitizadoras" && (
            <div className="space-y-6 animate-in fade-in">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2 gap-3 flex-wrap">
                <h3 className="text-base font-bold text-slate-800">Custos Fixos por Securitizadora</h3>
                <Button variant="outline" size="sm" onClick={addSecuritizadora}>+ Nova Securitizadora</Button>
              </div>

              <div className="relative max-w-sm">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <Input
                  type="search"
                  placeholder="Buscar securitizadora..."
                  value={secSearch}
                  onChange={(e) => setSecSearch(e.target.value)}
                  className="pl-9"
                />
              </div>
              
              <div className="grid gap-4">
                {Object.keys(rates.Securitizadoras || {}).length === 0 ? (
                  <div className="py-8 text-center text-sm text-slate-400 border border-dashed border-slate-200 rounded-lg bg-slate-50">
                    Nenhuma securitizadora cadastrada.
                  </div>
                ) : (
                  (() => {
                    const secNames = Object.keys(rates.Securitizadoras || {}).filter((name) => {
                      const q = secSearch.trim().toLowerCase();
                      if (!q) return true;
                      return name.toLowerCase().includes(q);
                    });
                    if (secNames.length === 0) {
                      return (
                        <div className="py-8 text-center text-sm text-slate-400 border border-dashed border-slate-200 rounded-lg bg-slate-50">
                          Nenhuma securitizadora encontrada para a busca.
                        </div>
                      );
                    }
                    return secNames.map((secName) => (
                    <div key={secName} className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="font-bold text-brand-green text-sm">{secName}</h4>
                        <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700 hover:bg-red-50 h-8" onClick={() => removeSecuritizadora(secName)}>
                          Excluir
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                        <div className="space-y-1">
                          <label className="text-xs text-slate-500 font-medium">Fiduciário (Implantação)</label>
                          <Input type="number" value={rates.Securitizadoras[secName].Agente_Fiduciario_Implantacao} onChange={(e) => updateSecuritizadora(secName, "Agente_Fiduciario_Implantacao", e.target.value)} />
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs text-slate-500 font-medium">Fiduciário (Recorrente)</label>
                          <Input type="number" value={rates.Securitizadoras[secName].Agente_Fiduciario_Recorrente} onChange={(e) => updateSecuritizadora(secName, "Agente_Fiduciario_Recorrente", e.target.value)} />
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs text-slate-500 font-medium">Instituição Custodiante</label>
                          <Input type="number" value={rates.Securitizadoras[secName].Instituicao_Custodiante} onChange={(e) => updateSecuritizadora(secName, "Instituicao_Custodiante", e.target.value)} />
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs text-slate-500 font-medium">Registro de Lastro</label>
                          <Input type="number" value={rates.Securitizadoras[secName].Registro_Lastro} onChange={(e) => updateSecuritizadora(secName, "Registro_Lastro", e.target.value)} />
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs text-slate-500 font-medium">Agente Liquidante</label>
                          <Input type="number" value={rates.Securitizadoras[secName].Liquidante} onChange={(e) => updateSecuritizadora(secName, "Liquidante", e.target.value)} />
                        </div>
                      </div>
                    </div>
                    ));
                  })()
                )}
              </div>
            </div>
          )}

          {/* Gross Up */}
          {activeTab === "GrossUp" && (
            <div className="space-y-4 animate-in fade-in">
              <h3 className="text-base font-bold text-slate-800 border-b border-slate-200 pb-2">Prestador Gross Up (%)</h3>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                {Object.keys(rates.Prestador_GrossUp || {}).map((prestador) => (
                  <div key={prestador} className="space-y-1.5 bg-slate-50 p-4 rounded-lg border border-slate-200">
                    <label className="text-sm font-medium text-slate-700">{prestador}</label>
                    <Input 
                      type="number" step="0.0001"
                      value={rates.Prestador_GrossUp[prestador]} 
                      onChange={(e) => updateRate("Prestador_GrossUp", prestador, e.target.value)} 
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
