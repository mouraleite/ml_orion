"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useUnsavedChanges } from "@/contexts/UnsavedChangesContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Save, Plus, Trash2 } from "lucide-react";

interface ExchangesTabProps {
  phaseId: number;
  isReadonly?: boolean;
}

export function ExchangesTab({ phaseId, isReadonly }: ExchangesTabProps) {
  const [data, setData] = useState<any>({
    modalidade: "Dinheiro",
    perc_permuta_financeira: 0.0,
    valor_terreno_fixo: 0.0,
    perc_area_terrenista: 100.0,
    perc_area_investidor: 0.0,
    perc_area_empreendedor: 0.0,
    perc_parceria_terrenista: 38.5,
    perc_parceria_investidor: 0.0,
    perc_parceria_empreendedor: 61.5,
    abertura_terrenistas_json: [] as { nome: string; percentual: number }[],
    rateios_config_json: {} as Record<string, boolean>,
  });
  
  const [constructionData, setConstructionData] = useState<any>(null);
  const [expensesData, setExpensesData] = useState<any>(null);

  const { setHasUnsavedChanges } = useUnsavedChanges();
  const [initialData, setInitialData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [resExch, resConst, resExp] = await Promise.all([
          api.get(`/viabilities/phases/${phaseId}/exchanges`),
          api.get(`/viabilities/phases/${phaseId}/construction`).catch(() => ({ data: null })),
          api.get(`/viabilities/phases/${phaseId}/expenses`).catch(() => ({ data: null }))
        ]);
        
        setData(resExch.data);
        setInitialData(resExch.data);
        setConstructionData(resConst.data);
        setExpensesData(resExp.data);
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
      await api.put(`/viabilities/phases/${phaseId}/exchanges`, data);
      setMessage("Permutas salvas com sucesso!");
      setInitialData(data);
      setHasUnsavedChanges(false);
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      alert("Erro ao salvar permutas.");
    } finally {
      setIsLoading(false);
    }
  };

  const updateRateio = (key: string, value: boolean) => {
    setData({
      ...data,
      rateios_config_json: {
        ...(data.rateios_config_json || {}),
        [key]: value
      }
    });
  };

  const addTerrenista = () => {
    setData({
      ...data,
      abertura_terrenistas_json: [
        ...(data.abertura_terrenistas_json || []),
        { nome: "", percentual: 0 }
      ]
    });
  };

  const removeTerrenista = (idx: number) => {
    const newArr = [...(data.abertura_terrenistas_json || [])];
    newArr.splice(idx, 1);
    setData({ ...data, abertura_terrenistas_json: newArr });
  };

  const updateTerrenista = (idx: number, field: string, val: any) => {
    const newArr = [...(data.abertura_terrenistas_json || [])];
    newArr[idx] = { ...newArr[idx], [field]: val };
    setData({ ...data, abertura_terrenistas_json: newArr });
  };

  const renderToggle = (key: string) => {
    const isChecked = data.rateios_config_json?.[key] || false;
    return (
      <button
        onClick={() => !isReadonly && updateRateio(key, !isChecked)}
        disabled={isReadonly}
        className={`w-12 h-6 rounded-full p-1 transition-colors duration-200 ease-in-out focus:outline-none ${isChecked ? 'bg-green-600' : 'bg-slate-300'}`}
      >
        <div className={`w-4 h-4 rounded-full bg-white shadow-md transform transition-transform duration-200 ease-in-out ${isChecked ? 'translate-x-6' : 'translate-x-0'}`} />
      </button>
    );
  };

  const toggleModalidade = (mod: string) => {
    let mods = data.modalidade ? String(data.modalidade).split(",").map((s: string) => s.trim()).filter(Boolean) : [];
    if (mods.includes(mod)) {
      mods = mods.filter((m: string) => m !== mod);
    } else {
      mods.push(mod);
    }
    setData({ ...data, modalidade: mods.join(", ") });
  };

  const isModalidadeSelected = (mod: string) => {
    return data.modalidade ? data.modalidade.includes(mod) : false;
  };

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-300 pb-32">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Permutas e Parcerias</h2>
          <p className="text-sm text-slate-500">Defina a estrutura societária e rateio de verbas do empreendimento.</p>
        </div>
        <div className="flex items-center gap-4">
          {message && <span className="text-sm text-green-600 font-medium">{message}</span>}
          <Button onClick={handleSave} disabled={isLoading || isReadonly} className="flex items-center gap-2">
            <Save className="w-4 h-4" />
            {isLoading ? "Salvando..." : "Salvar Permutas"}
          </Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-1 gap-8">
        
        {/* LADO ESQUERDO */}
        <div className="space-y-8">
          
          {/* Composição na Área */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider border-b pb-2">Composição na Área</h3>
            <div className="grid grid-cols-3 gap-4 bg-slate-50 p-6 rounded-lg border border-slate-200">
              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Proprietários Originais</label>
                <div className="relative">
                  <Input type="number" value={data.perc_area_terrenista} disabled={isReadonly}
                    onChange={e => setData({...data, perc_area_terrenista: e.target.value === '' ? '' : parseFloat(e.target.value)})} />
                  <span className="absolute right-3 top-2.5 text-xs text-slate-500">%</span>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Investido</label>
                <div className="relative">
                  <Input type="number" value={data.perc_area_investidor} disabled={isReadonly}
                    onChange={e => setData({...data, perc_area_investidor: e.target.value === '' ? '' : parseFloat(e.target.value)})} />
                  <span className="absolute right-3 top-2.5 text-xs text-slate-500">%</span>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Loteador</label>
                <div className="relative">
                  <Input type="number" value={data.perc_area_empreendedor} disabled={isReadonly}
                    onChange={e => setData({...data, perc_area_empreendedor: e.target.value === '' ? '' : parseFloat(e.target.value)})} />
                  <span className="absolute right-3 top-2.5 text-xs text-slate-500">%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Composição Parceria (VGV) */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider border-b pb-2">Percentual Parceria (VGV Ponderada)</h3>
            <div className="grid grid-cols-3 gap-4 bg-slate-50 p-6 rounded-lg border border-slate-200">
              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Proprietário (Terrenista)</label>
                <div className="relative">
                  <Input type="number" value={data.perc_parceria_terrenista} disabled={isReadonly}
                    onChange={e => setData({...data, perc_parceria_terrenista: e.target.value === '' ? '' : parseFloat(e.target.value)})} />
                  <span className="absolute right-3 top-2.5 text-xs text-slate-500">%</span>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Investidor</label>
                <div className="relative">
                  <Input type="number" value={data.perc_parceria_investidor} disabled={isReadonly}
                    onChange={e => setData({...data, perc_parceria_investidor: e.target.value === '' ? '' : parseFloat(e.target.value)})} />
                  <span className="absolute right-3 top-2.5 text-xs text-slate-500">%</span>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-700 block mb-1">Empreendedor</label>
                <div className="relative">
                  <Input type="number" value={data.perc_parceria_empreendedor} disabled={isReadonly}
                    onChange={e => setData({...data, perc_parceria_empreendedor: e.target.value === '' ? '' : parseFloat(e.target.value)})} />
                  <span className="absolute right-3 top-2.5 text-xs text-slate-500">%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Rateio de Verbas */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider border-b pb-2">Rateio de Verbas</h3>
            
            <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-medium">
                  <tr>
                    <th className="px-4 py-3">Custos</th>
                    <th className="px-4 py-3 text-center">Rateio</th>
                    <th className="px-4 py-3 text-right">Proprietário</th>
                    <th className="px-4 py-3 text-right">Investidor</th>
                    <th className="px-4 py-3 text-right">Empreendedor</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {/* Obras Fixas */}
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-700">Aquisição de Área</td>
                    <td className="px-4 py-3 text-center">{renderToggle("aquisicao_area")}</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["aquisicao_area"] ? data.perc_parceria_terrenista : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["aquisicao_area"] ? data.perc_parceria_investidor : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["aquisicao_area"] ? data.perc_parceria_empreendedor : 100}%</td>
                  </tr>
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-700">Projetos</td>
                    <td className="px-4 py-3 text-center">{renderToggle("custo_projetos")}</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["custo_projetos"] ? data.perc_parceria_terrenista : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["custo_projetos"] ? data.perc_parceria_investidor : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["custo_projetos"] ? data.perc_parceria_empreendedor : 100}%</td>
                  </tr>
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-700">Obras de Infraestrutura</td>
                    <td className="px-4 py-3 text-center">{renderToggle("custo_obras")}</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["custo_obras"] ? data.perc_parceria_terrenista : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["custo_obras"] ? data.perc_parceria_investidor : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["custo_obras"] ? data.perc_parceria_empreendedor : 100}%</td>
                  </tr>
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-700">Administração de Obras</td>
                    <td className="px-4 py-3 text-center">{renderToggle("adm_obras")}</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["adm_obras"] ? data.perc_parceria_terrenista : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["adm_obras"] ? data.perc_parceria_investidor : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["adm_obras"] ? data.perc_parceria_empreendedor : 100}%</td>
                  </tr>
                  {/* Obras Extras */}
                  {constructionData?.extra_constructions_json?.map((ec: any, idx: number) => {
                    const key = `extra_obra_${idx}`;
                    return (
                      <tr key={key} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-medium text-slate-700">{ec.nome || ec.descricao || `Extra Obras ${idx+1}`}</td>
                        <td className="px-4 py-3 text-center">{renderToggle(key)}</td>
                        <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.[key] ? data.perc_parceria_terrenista : 0}%</td>
                        <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.[key] ? data.perc_parceria_investidor : 0}%</td>
                        <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.[key] ? data.perc_parceria_empreendedor : 100}%</td>
                      </tr>
                    );
                  })}
                  
                  {/* Header Despesas */}
                  <tr className="bg-slate-100">
                    <th className="px-4 py-2 text-xs uppercase text-slate-600 font-bold" colSpan={5}>Despesas</th>
                  </tr>

                  {/* Despesas Fixas */}
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-700">Despesas Administrativas</td>
                    <td className="px-4 py-3 text-center">{renderToggle("adm")}</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["adm"] ? data.perc_parceria_terrenista : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["adm"] ? data.perc_parceria_investidor : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["adm"] ? data.perc_parceria_empreendedor : 100}%</td>
                  </tr>
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-700">Comercial</td>
                    <td className="px-4 py-3 text-center">{renderToggle("comercial")}</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["comercial"] ? data.perc_parceria_terrenista : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["comercial"] ? data.perc_parceria_investidor : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["comercial"] ? data.perc_parceria_empreendedor : 100}%</td>
                  </tr>
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-700">Marketing</td>
                    <td className="px-4 py-3 text-center">{renderToggle("marketing")}</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["marketing"] ? data.perc_parceria_terrenista : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["marketing"] ? data.perc_parceria_investidor : 0}%</td>
                    <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.["marketing"] ? data.perc_parceria_empreendedor : 100}%</td>
                  </tr>
                  {/* Despesas Extras */}
                  {expensesData?.extra_expenses_json?.map((ee: any, idx: number) => {
                    const key = `extra_despesa_${idx}`;
                    return (
                      <tr key={key} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-medium text-slate-700">{ee.nome || ee.descricao || `Extra Despesa ${idx+1}`}</td>
                        <td className="px-4 py-3 text-center">{renderToggle(key)}</td>
                        <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.[key] ? data.perc_parceria_terrenista : 0}%</td>
                        <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.[key] ? data.perc_parceria_investidor : 0}%</td>
                        <td className="px-4 py-3 text-right text-slate-500">{data.rateios_config_json?.[key] ? data.perc_parceria_empreendedor : 100}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Abertura de Parceiros */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b pb-2">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Abertura de Parceiros</h3>
              <Button size="sm" variant="outline" onClick={addTerrenista} disabled={isReadonly} className="h-7 text-xs flex gap-1">
                <Plus className="w-3 h-3" /> Adicionar
              </Button>
            </div>
            <div className="space-y-2">
              {(!data.abertura_terrenistas_json || data.abertura_terrenistas_json.length === 0) && (
                <p className="text-sm text-slate-500 italic">Nenhum parceiro detalhado.</p>
              )}
              {data.abertura_terrenistas_json?.map((terr: any, idx: number) => (
                <div key={idx} className="flex gap-2 items-center">
                  <Input 
                    placeholder="Nome (ex: Tadeu)" 
                    value={terr.nome} 
                    disabled={isReadonly}
                    onChange={e => updateTerrenista(idx, 'nome', e.target.value)} 
                    className="flex-1"
                  />
                  <select
                    className="ml-select w-32"
                    value={terr.tipo || "Proprietário"}
                    disabled={isReadonly}
                    onChange={e => updateTerrenista(idx, 'tipo', e.target.value)}
                  >
                    <option value="Proprietário">Proprietário</option>
                    <option value="Investidor">Investidor</option>
                    <option value="Empreendedor">Empreendedor</option>
                  </select>
                  <div className="relative w-36">
                    <Input 
                      type="number" 
                      value={terr.percentual} 
                      disabled={isReadonly}
                      onChange={e => updateTerrenista(idx, 'percentual', e.target.value === '' ? '' : parseFloat(e.target.value))} 
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-500">%</span>
                  </div>
                  {!isReadonly && (
                    <button onClick={() => removeTerrenista(idx)} className="p-2 text-red-500 hover:bg-red-50 rounded">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Modalidade Antiga (Caso precise) */}
          <div className="space-y-4">
             <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider border-b pb-2">Modalidade do Terreno</h3>
             <div className="bg-slate-50 p-6 rounded-lg border border-slate-200 space-y-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={isModalidadeSelected("Dinheiro")}
                    disabled={isReadonly}
                    onChange={() => toggleModalidade("Dinheiro")}
                    className="w-4 h-4 text-slate-900 rounded border-slate-300 focus:ring-slate-900"
                  />
                  <span className="text-sm text-slate-700">Compra em Dinheiro (Fixo)</span>
                </label>
                {isModalidadeSelected("Dinheiro") && (
                  <div className="ml-6 flex items-center gap-2">
                    <span className="text-sm text-slate-500">Valor (R$):</span>
                    <Input 
                      type="number" 
                      value={data.valor_terreno_fixo} 
                      disabled={isReadonly}
                      onChange={e => setData({...data, valor_terreno_fixo: e.target.value === '' ? '' : parseFloat(e.target.value)})}
                      className="w-40"
                    />
                  </div>
                )}

                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={isModalidadeSelected("Permuta Financeira")}
                    disabled={isReadonly}
                    onChange={() => toggleModalidade("Permuta Financeira")}
                    className="w-4 h-4 text-slate-900 rounded border-slate-300 focus:ring-slate-900"
                  />
                  <span className="text-sm text-slate-700">Permuta Financeira (% VGV)</span>
                </label>
                {isModalidadeSelected("Permuta Financeira") && (
                  <div className="ml-6 space-y-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={data.rateios_config_json?.vincular_permuta_parceria !== false}
                        disabled={isReadonly}
                        onChange={() => updateRateio("vincular_permuta_parceria", data.rateios_config_json?.vincular_permuta_parceria === false)}
                        className="w-4 h-4 text-slate-900 rounded border-slate-300 focus:ring-slate-900"
                      />
                      <span className="text-sm text-slate-700">Usar percentual definido na Parceria (Proprietário)</span>
                    </label>

                    <div className="flex items-center gap-2">
                      <span className="text-sm text-slate-500">Percentual (%):</span>
                      <Input 
                        type="number" 
                        value={data.rateios_config_json?.vincular_permuta_parceria !== false ? data.perc_parceria_terrenista : data.perc_permuta_financeira} 
                        disabled={isReadonly || data.rateios_config_json?.vincular_permuta_parceria !== false}
                        onChange={e => setData({...data, perc_permuta_financeira: e.target.value === '' ? '' : parseFloat(e.target.value)})}
                        className="w-32"
                      />
                    </div>
                  </div>
                )}

                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={isModalidadeSelected("Permuta Física")}
                    disabled={isReadonly}
                    onChange={() => toggleModalidade("Permuta Física")}
                    className="w-4 h-4 text-slate-900 rounded border-slate-300 focus:ring-slate-900"
                  />
                  <span className="text-sm text-slate-700">Permuta Física (Unidades)</span>
                </label>
                {isModalidadeSelected("Permuta Física") && (
                  <div className="ml-6 flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-slate-500">Qtd. Unidades:</span>
                      <Input 
                        type="number" 
                        value={data.permuta_fisica_unidades} 
                        disabled={isReadonly}
                        onChange={e => setData({...data, permuta_fisica_unidades: e.target.value === '' ? '' : parseInt(e.target.value)})}
                        className="w-24"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-slate-500">Valor Médio (R$):</span>
                      <Input 
                        type="number" 
                        value={data.permuta_fisica_valor_unidade} 
                        disabled={isReadonly}
                        onChange={e => setData({...data, permuta_fisica_valor_unidade: e.target.value === '' ? '' : parseFloat(e.target.value)})}
                        className="w-32"
                      />
                    </div>
                  </div>
                )}
             </div>
          </div>

        </div>

      </div>
    </div>
  );
}
