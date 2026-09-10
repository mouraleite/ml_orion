"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useUnsavedChanges } from "@/contexts/UnsavedChangesContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Save, Activity } from "lucide-react";
import { apoioService } from "@/services/apoio";

interface ConstructionTabProps {
  phaseId: number;
  project: any;
  onUpdateProject: (updates: Record<string, any>) => void;
  isReadonly?: boolean;
}

function NumericInput({ value, onChange, className, disabled, placeholder }: any) {
  const format = (v: number) => {
    if (v === null || v === undefined || isNaN(v)) return "";
    return v.toLocaleString('pt-BR', { maximumFractionDigits: 2 });
  };
  
  const [localValue, setLocalValue] = useState(format(value));
  const [isFocused, setIsFocused] = useState(false);
  
  useEffect(() => {
    if (!isFocused) {
      setLocalValue(format(value));
    }
  }, [value, isFocused]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let val = e.target.value;
    val = val.replace(/[^\d,\-]/g, "");
    setLocalValue(val);
    
    const parsedStr = val.replace(",", ".");
    const parsed = parseFloat(parsedStr);
    onChange(isNaN(parsed) ? 0 : parsed);
  };

  return (
    <input 
      type="text" 
      className={className} 
      value={localValue} 
      onChange={handleChange}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      disabled={disabled}
      placeholder={placeholder}
    />
  );
}

export function ConstructionTab({ phaseId, project, onUpdateProject, isReadonly }: ConstructionTabProps) {
  const [data, setData] = useState<any>({
    custo_obras: 0,
    custo_obras_tipo: "R$",
    custo_projetos: 0,
    custo_projetos_tipo: "%",
    aquisicao_area: 0,
    aquisicao_area_tipo: "R$",
    adm_obras: 0,
    adm_obras_tipo: "%",
    curva_obras_json: { meses: [] },
    curva_projetos_json: { meses: [] },
    curva_aquisicao_json: { meses: [] },
    curva_adm_obras_json: { meses: [] },
  });
  const [curves, setCurves] = useState<any[]>([]);
  const [economicIndicators, setEconomicIndicators] = useState<any[]>([]);
  const [realMarketData, setRealMarketData] = useState<{ ipca: any | null; incc: any | null }>({ ipca: null, incc: null });
  const [vgvTotal, setVgvTotal] = useState(0);
  const { setHasUnsavedChanges } = useUnsavedChanges();
  const [initialData, setInitialData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [res, curvesRes, revRes, indRes, ipcaRes, inccRes] = await Promise.all([
          api.get(`/viabilities/phases/${phaseId}/construction`).catch(() => ({ data: {} })),
          api.get("/curves/").catch(() => ({ data: [] })),
          api.get(`/viabilities/phases/${phaseId}/revenue`).catch(() => ({ data: { vgv_total: 0 } })),
          apoioService.getIndicadores().catch(err => { console.error("Error fetching indicadores:", err); return []; }),
          api.get("/market-indices/ipca").catch(() => ({ data: null })),
          api.get("/market-indices/incc").catch(() => ({ data: null })),
        ]);
        console.log("API Responses - Construction:", res.data, "Curves:", curvesRes.data, "Indicators:", indRes);
        
        const dbData = res.data || {};
        const defaultData = {
          custo_obras: 0, custo_obras_tipo: "R$",
          custo_projetos: 0, custo_projetos_tipo: "%",
          custo_aquisicao: 0, custo_aquisicao_tipo: "%",
          custo_adm_obras: 0, custo_adm_obras_tipo: "%",
          curva_obras_json: { meses: [] },
          curva_projetos_json: { meses: [] },
          curva_aquisicao_json: { meses: [] },
          curva_adm_obras_json: { meses: [] }
        };
        const mergedData = { ...defaultData, ...dbData };
        
        if (!mergedData.curva_obras_json) mergedData.curva_obras_json = { meses: [] };
        if (!mergedData.curva_projetos_json) mergedData.curva_projetos_json = { meses: [] };
        if (!mergedData.curva_aquisicao_json) mergedData.curva_aquisicao_json = { meses: [] };
        if (!mergedData.curva_adm_obras_json) mergedData.curva_adm_obras_json = { meses: [] };
        
        setData(mergedData);
        setInitialData(mergedData);
        setCurves(curvesRes.data);
        setEconomicIndicators(indRes || []);
        setRealMarketData({
          ipca: ipcaRes.data || null,
          incc: inccRes.data || null,
        });
        if (revRes.data && revRes.data.vgv_total) {
          setVgvTotal(revRes.data.vgv_total);
        }
      } catch (e) {
        console.error("fetchData Error in ConstructionTab:", e);
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
      await api.put(`/viabilities/phases/${phaseId}/construction`, data);
      setMessage("Dados de Obra salvos com sucesso!");
      setInitialData(data);
      setHasUnsavedChanges(false);
      setTimeout(() => setMessage(""), 3000);
    } catch (error: any) {
      console.error("Save error:", error.response?.data || error);
      alert(`Erro ao salvar dados: ${JSON.stringify(error.response?.data?.detail || error.message)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApplyCurve = (field: string, curveId: string) => {
    if (!curveId) return;
    const curve = curves.find(c => c.id === Number(curveId));
    if (curve) {
      setData({ ...data, [field]: { 
        meses: curve.valores_meses_json.meses,
        curve_id: curve.id,
        curve_name: curve.nome,
        mes_inicio: 1
      } });
    }
  };

  const handleApplyCurveExtra = (field: string, idx: number, curveId: string) => {
    if (!curveId) return;
    const curve = curves.find(c => c.id === Number(curveId));
    if (curve) {
      const arr = [...(data[field] || [])];
      arr[idx] = { 
        ...arr[idx], 
        curva_json: {
          meses: curve.valores_meses_json.meses,
          curve_id: curve.id,
          curve_name: curve.nome,
          mes_inicio: 1
        } 
      };
      setData({ ...data, [field]: arr });
    }
  };

  const renderIndexerConfig = (isActive: boolean, indicatorType: "INCC" | "IPCA", valueField: string, typeField: string) => {
    if (!isActive) return null;
    const indicators = economicIndicators.filter(i => i.index_type === indicatorType);
    const realData = indicatorType === "IPCA" ? realMarketData.ipca : realMarketData.incc;
    const realValue = realData?.ultimo_mes?.mensal ?? null;
    const realLabel = indicatorType === "IPCA"
      ? `IPCA Real BCB (${realValue != null ? realValue.toFixed(2) + "% a.m." : "..."}) — ${realData?.ultimo_mes?.data || ""}`
      : `INCC-DI Real BCB (${realValue != null ? realValue.toFixed(2) + "% a.m." : "..."}) — ${realData?.ultimo_mes?.data || ""}`;

    const isRealSelected = project?.[valueField] === realValue && project?.[typeField] === "% a.m." && realValue != null;

    return (
      <div className="flex items-center gap-2 pr-3 mr-1 border-r border-slate-200 animate-in fade-in duration-200">
        <select
          className="ml-select h-7 text-xs w-auto max-w-[17rem]"
          value={
            isRealSelected
              ? "__real__"
              : (indicators.find(i => i.valor === project?.[valueField] && i.tipo_unidade === project?.[typeField])?.id
                || (project?.[valueField] === null || project?.[valueField] === undefined ? "" : "custom"))
          }
          onChange={(e) => {
            const val = e.target.value;
            if (val === "__real__") {
              if (realValue != null) onUpdateProject({ [valueField]: realValue, [typeField]: "% a.m." });
              return;
            }
            if (val === "custom" || val === "") return;
            const ind = indicators.find(i => i.id === Number(val));
            if (ind) onUpdateProject({ [valueField]: ind.valor, [typeField]: ind.tipo_unidade });
          }}
          disabled={isReadonly}
        >
          <option value="" disabled className="text-slate-400">
            {indicators.length === 0 && !realData ? "Nenhum cenário..." : "Selecione um cenário..."}
          </option>
          {/* Opção Real BCB no topo */}
          {realValue != null && (
            <option value="__real__">🟢 {realLabel}</option>
          )}
          {indicators.length > 0 && <option disabled>── Cenários Manuais ──</option>}
          {indicators.map(ind => (
            <option key={ind.id} value={ind.id}>{ind.nome} ({ind.valor}{ind.tipo_unidade})</option>
          ))}
          <option value="custom">Valor Personalizado</option>
        </select>
        
        <NumericInput 
          className="ml-input w-20 h-7 text-xs font-mono"
          value={project?.[valueField]}
          onChange={(val: number) => onUpdateProject({ [valueField]: val })}
          disabled={isReadonly}
        />
        <select
          className="ml-select h-7 w-20 text-xs"
          value={project?.[typeField] || "% a.a."}
          onChange={(e) => onUpdateProject({ [typeField]: e.target.value })}
          disabled={isReadonly}
        >
          <option value="% a.a.">% a.a.</option>
          <option value="% a.m.">% a.m.</option>
        </select>
      </div>
    );
  };

  const renderCurveSelector = (label: string, field: string, filterType: string) => {
    const jsonValue = data[field];
    const hasCurve = jsonValue && Array.isArray(jsonValue.meses) && jsonValue.meses.length > 0;
    
    const normalizeStr = (str?: string) => (str || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
    
    return (
      <div className="flex flex-col gap-2 p-3 bg-white border rounded-md shadow-sm">
        <p className="text-sm font-medium text-slate-700">{label}</p>
        <select
          disabled={isReadonly}
          className="ml-select w-full h-9 text-sm"
          value={jsonValue?.curve_id || ""}
          onChange={(e) => handleApplyCurve(field, e.target.value)}
        >
          <option value="">Aplicar curva padrão...</option>
          {curves.filter(c => {
            if (filterType === 'all') return true;
            const t1 = normalizeStr(c.tipo);
            const t2 = normalizeStr(filterType);
            if (!t1 || !t2) return false;
            return t1.includes(t2) || t2.includes(t1);
          }).map(c => (
            <option key={c.id} value={c.id}>{c.nome}</option>
          ))}
        </select>
        {hasCurve ? (
          <span className="text-xs text-green-600 font-medium flex items-center gap-1">
            <Activity className="w-3 h-3" /> Curva Aplicada ({jsonValue.meses.length} meses)
          </span>
        ) : (
          <span className="text-xs text-slate-400 block">Nenhuma curva</span>
        )}
      </div>
    );
  };

  const renderCurveSelectorExtra = (label: string, field: string, idx: number) => {
    const arr = data[field] || [];
    const item = arr[idx];
    const jsonValue = item?.curva_json;
    const hasCurve = jsonValue && Array.isArray(jsonValue.meses) && jsonValue.meses.length > 0;
    
    return (
      <div className="flex flex-col gap-2 p-3 bg-white border rounded-md shadow-sm">
        <p className="text-sm font-medium text-slate-700">{label}</p>
        <select
          disabled={isReadonly}
          className="ml-select w-full h-9 text-sm"
          value={jsonValue?.curve_id || ""}
          onChange={(e) => handleApplyCurveExtra(field, idx, e.target.value)}
        >
          <option value="">Aplicar curva...</option>
          {curves.map(c => (
            <option key={c.id} value={c.id}>{c.nome}</option>
          ))}
        </select>
        {hasCurve ? (
          <span className="text-xs text-green-600 font-medium flex items-center gap-1">
            <Activity className="w-3 h-3" /> Curva Aplicada ({jsonValue.meses.length} meses)
          </span>
        ) : (
          <span className="text-xs text-slate-400 block">Nenhuma curva</span>
        )}
      </div>
    );
  };

  const handleAddExtraConstruction = () => {
    const arr = [...(data.extra_constructions_json || [])];
    arr.push({ nome: "", valor: 0, tipo: "R$", curva_json: null });
    setData({ ...data, extra_constructions_json: arr });
  };

  const handleRemoveExtraConstruction = (idx: number) => {
    const arr = [...(data.extra_constructions_json || [])];
    arr.splice(idx, 1);
    setData({ ...data, extra_constructions_json: arr });
  };

  const calcValue = (val: any, type: string) => { const v = Number(val) || 0; return type === "%" ? vgvTotal * (v / 100) : v; };

  const custoObrasCalc = calcValue(data.custo_obras || 0, data.custo_obras_tipo || "R$");
  const custoProjetosCalc = calcValue(data.custo_projetos || 0, data.custo_projetos_tipo || "%");
  const aquisicaoCalc = calcValue(data.aquisicao_area || 0, data.aquisicao_area_tipo || "R$");
  const admObrasCalc = calcValue(data.adm_obras || 0, data.adm_obras_tipo || "%");

  const extraConstructionsTotal = (data.extra_constructions_json || []).reduce((acc: number, curr: any) => {
    return acc + calcValue(curr.valor || 0, curr.tipo || "R$");
  }, 0);

  const totalCusto = custoObrasCalc + custoProjetosCalc + aquisicaoCalc + admObrasCalc + extraConstructionsTotal;

  const formatCurrency = (val: number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-300">
      
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Despesas e Cronograma de Obras</h2>
          <p className="text-sm text-slate-500">Defina o custo da construção e as curvas de avanço por linha.</p>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            {message && <span className="text-sm text-green-600 font-medium">{message}</span>}
              <Button onClick={handleSave} disabled={isLoading || isReadonly} className="flex items-center gap-2">
              <Save className="w-4 h-4" />
              {isLoading ? "Salvando..." : "Salvar Obra"}
            </Button>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider border-b pb-2">Custos Diretos (COSTS)</h3>
          
          <div className="space-y-4">
            <div className="space-y-1">
              <div className="flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-700">Obras de Infraestrutura</label>
                  <div className="flex items-center gap-2">
                    {renderIndexerConfig(!!project?.aplicar_incc_obras, "INCC", "incc_projetado_valor", "incc_projetado_tipo")}
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                      <button 
                        onClick={() => !isReadonly && onUpdateProject({ aplicar_incc_obras: !project?.aplicar_incc_obras })}
                        disabled={isReadonly}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${project?.aplicar_incc_obras ? 'bg-brand-green' : 'bg-slate-300'} ${isReadonly ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition ${project?.aplicar_incc_obras ? 'translate-x-5' : 'translate-x-1'}`} />
                      </button>
                      <span className="text-xs text-slate-500 font-medium">INCC</span>
                    </label>
                  </div>
                </div>
              </div>
              <div className="flex-1 flex items-center gap-2 pr-6">
                <select 
                  className="ml-select w-20 text-sm h-9"
                  value={data.custo_obras_tipo || "R$"}
                  onChange={(e) => setData({ ...data, custo_obras_tipo: e.target.value })}
                  disabled={isReadonly}
                >
                  <option value="R$">R$</option>
                  <option value="%">%</option>
                </select>
                <NumericInput 
                  className="ml-input w-full h-9 font-mono"
                  value={data.custo_obras}
                  onChange={(val: number) => setData({ ...data, custo_obras: val })}
                  disabled={isReadonly}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {data.custo_obras_tipo === "%" 
                  ? `Equivale a ${formatCurrency(custoObrasCalc)} do VGV`
                  : `Equivale a ${vgvTotal > 0 ? ((data.custo_obras || 0) / vgvTotal * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) : '0,00'}% do VGV`}
              </p>
            </div>
            
            <div className="space-y-1">
              <div className="flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-700">Projetos</label>
                  <div className="flex items-center gap-2">
                    {renderIndexerConfig(!!project?.aplicar_ipca_projetos, "IPCA", "ipca_projetado_valor", "ipca_projetado_tipo")}
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                      <button 
                        onClick={() => !isReadonly && onUpdateProject({ aplicar_ipca_projetos: !project?.aplicar_ipca_projetos })}
                        disabled={isReadonly}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${project?.aplicar_ipca_projetos ? 'bg-brand-green' : 'bg-slate-300'} ${isReadonly ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition ${project?.aplicar_ipca_projetos ? 'translate-x-5' : 'translate-x-1'}`} />
                      </button>
                      <span className="text-xs text-slate-500 font-medium">IPCA</span>
                    </label>
                  </div>
                </div>
              </div>
              <div className="flex-1 flex items-center gap-2 pr-6">
                <select 
                  className="ml-select w-20 text-sm h-9" 
                  value={data.custo_projetos_tipo || "%"} 
                  disabled={isReadonly}
                  onChange={e => setData({...data, custo_projetos_tipo: e.target.value})}
                >
                  <option value="R$">R$</option>
                  <option value="%">%</option>
                </select>
                <NumericInput 
                  className="ml-input w-full h-9 font-mono"
                  value={data.custo_projetos}
                  onChange={(val: number) => setData({ ...data, custo_projetos: val })}
                  disabled={isReadonly}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {data.custo_projetos_tipo === "%" 
                  ? `Equivale a ${formatCurrency(custoProjetosCalc)} do VGV`
                  : `Equivale a ${vgvTotal > 0 ? ((data.custo_projetos || 0) / vgvTotal * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) : '0,00'}% do VGV`}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-700">Aquisição de Área</label>
                  <div className="flex items-center gap-2">
                    {renderIndexerConfig(!!project?.aplicar_ipca_aquisicao, "IPCA", "ipca_projetado_valor", "ipca_projetado_tipo")}
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                      <button 
                        onClick={() => !isReadonly && onUpdateProject({ aplicar_ipca_aquisicao: !project?.aplicar_ipca_aquisicao })}
                        disabled={isReadonly}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${project?.aplicar_ipca_aquisicao ? 'bg-brand-green' : 'bg-slate-300'} ${isReadonly ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition ${project?.aplicar_ipca_aquisicao ? 'translate-x-5' : 'translate-x-1'}`} />
                      </button>
                      <span className="text-xs text-slate-500 font-medium">IPCA</span>
                    </label>
                  </div>
                </div>
              </div>
              <div className="flex-1 flex items-center gap-2 pr-6">
                <select 
                  className="ml-select w-20 text-sm h-9" 
                  value={data.aquisicao_area_tipo || "R$"} 
                  disabled={isReadonly}
                  onChange={e => setData({...data, aquisicao_area_tipo: e.target.value})}
                >
                  <option value="R$">R$</option>
                  <option value="%">%</option>
                </select>
                <NumericInput 
                  className="ml-input w-full h-9 font-mono"
                  value={data.aquisicao_area}
                  onChange={(val: number) => setData({ ...data, aquisicao_area: val })}
                  disabled={isReadonly}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {data.aquisicao_area_tipo === "%" 
                  ? `Equivale a ${formatCurrency(aquisicaoCalc)} do VGV`
                  : `Equivale a ${vgvTotal > 0 ? ((data.aquisicao_area || 0) / vgvTotal * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) : '0,00'}% do VGV`}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-700">Administração de Obras</label>
                  <div className="flex items-center gap-2">
                    {renderIndexerConfig(!!project?.aplicar_ipca_adm, "IPCA", "ipca_projetado_valor", "ipca_projetado_tipo")}
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                      <button 
                        onClick={() => !isReadonly && onUpdateProject({ aplicar_ipca_adm: !project?.aplicar_ipca_adm })}
                        disabled={isReadonly}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${project?.aplicar_ipca_adm ? 'bg-brand-green' : 'bg-slate-300'} ${isReadonly ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition ${project?.aplicar_ipca_adm ? 'translate-x-5' : 'translate-x-1'}`} />
                      </button>
                      <span className="text-xs text-slate-500 font-medium">IPCA</span>
                    </label>
                  </div>
                </div>
              </div>
              <div className="flex-1 flex items-center gap-2 pr-6">
                <select 
                  className="ml-select w-20 text-sm h-9" 
                  value={data.adm_obras_tipo || "%"} 
                  disabled={isReadonly}
                  onChange={e => setData({...data, adm_obras_tipo: e.target.value})}
                >
                  <option value="R$">R$</option>
                  <option value="%">%</option>
                </select>
                <NumericInput 
                  className="ml-input w-full h-9 font-mono"
                  value={data.adm_obras}
                  onChange={(val: number) => setData({ ...data, adm_obras: val })}
                  disabled={isReadonly}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {data.adm_obras_tipo === "%" 
                  ? `Equivale a ${formatCurrency(admObrasCalc)} do VGV`
                  : `Equivale a ${vgvTotal > 0 ? ((data.adm_obras || 0) / vgvTotal * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) : '0,00'}% do VGV`}
              </p>
            </div>

            {data.extra_constructions_json && data.extra_constructions_json.map((extra: any, idx: number) => (
              <div key={idx} className="space-y-1 p-3 border rounded-md relative bg-slate-50/50 group">
                <button 
                  onClick={() => handleRemoveExtraConstruction(idx)} 
                  className="absolute top-2 right-2 text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                  disabled={isReadonly}
                >×</button>
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <Input 
                      placeholder="Nome do custo extra..."
                      value={extra.nome}
                      disabled={isReadonly}
                      onChange={(e) => {
                        const newArr = [...data.extra_constructions_json];
                        newArr[idx].nome = e.target.value;
                        setData({ ...data, extra_constructions_json: newArr });
                      }}
                      className="h-8 w-2/3 text-sm font-medium border-transparent hover:border-slate-300 focus:border-brand-primary"
                    />
                    <select
                      className="ml-select text-xs h-7 w-24"
                      value={extra.correcao || "Nenhum"}
                      disabled={isReadonly}
                      onChange={(e) => {
                        const newArr = [...data.extra_constructions_json];
                        newArr[idx].correcao = e.target.value;
                        setData({ ...data, extra_constructions_json: newArr });
                      }}
                    >
                      <option value="Nenhum">Sem correção</option>
                      <option value="INCC">INCC</option>
                      <option value="IPCA">IPCA</option>
                    </select>
                  </div>
                  <div className="flex-1 flex items-center gap-2 pr-6">
                    <select 
                      className="ml-select w-20 text-sm h-9"
                      value={extra.tipo || "R$"}
                      onChange={(e) => {
                        const newArr = [...data.extra_constructions_json];
                        newArr[idx].tipo = e.target.value;
                        setData({ ...data, extra_constructions_json: newArr });
                      }}
                      disabled={isReadonly}
                    >
                      <option value="R$">R$</option>
                      <option value="%">%</option>
                    </select>
                    <NumericInput 
                      className="ml-input w-full h-9 font-mono"
                      value={extra.valor}
                      onChange={(val: number) => {
                        const newArr = [...data.extra_constructions_json];
                        newArr[idx].valor = val;
                        setData({ ...data, extra_constructions_json: newArr });
                      }}
                      disabled={isReadonly}
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {extra.tipo === "%" 
                      ? `Equivale a ${formatCurrency(calcValue(extra.valor, "%"))} do VGV`
                      : `Equivale a ${vgvTotal > 0 ? ((extra.valor || 0) / vgvTotal * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) : '0,00'}% do VGV`}
                  </p>
                </div>
              </div>
            ))}
            
            {!isReadonly && (
              <Button variant="outline" size="sm" onClick={handleAddExtraConstruction} className="w-full border-dashed text-slate-500 hover:text-slate-700 hover:border-slate-400">
                + Adicionar Custo Extra
              </Button>
            )}

            <div className="pt-4 border-t space-y-1 text-sm text-slate-600">
              <div className="flex justify-between">
                <span>Obras de Infraestrutura:</span>
                <span>{formatCurrency(custoObrasCalc)}</span>
              </div>
              <div className="flex justify-between">
                <span>Projetos:</span>
                <span>{formatCurrency(custoProjetosCalc)}</span>
              </div>
              <div className="flex justify-between">
                <span>Aquisição de Área:</span>
                <span>{formatCurrency(aquisicaoCalc)}</span>
              </div>
              <div className="flex justify-between">
                <span>Administração de Obras:</span>
                <span>{formatCurrency(admObrasCalc)}</span>
              </div>
              {(data.extra_constructions_json || []).map((extra: any, idx: number) => (
                <div key={idx} className="flex justify-between text-slate-500">
                  <span>{extra.nome || `Custo Extra ${idx + 1}`}:</span>
                  <span>{formatCurrency(calcValue(extra.valor, extra.tipo || "R$"))}</span>
                </div>
              ))}
              <div className="pt-2 mt-2 border-t flex justify-between items-center text-slate-900">
                <span className="font-bold">Total COSTS:</span>
                <span className="font-bold text-lg">{formatCurrency(totalCusto)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between border-b pb-2">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Desembolso Financeiro / Curva</h3>
          </div>
          
          <div className="space-y-3 bg-slate-50 p-4 rounded-lg border border-slate-200">
            <p className="text-xs text-slate-500 mb-2">
              Selecione a curva padrão que ditará a velocidade de desembolso de cada linha. O percentual será copiado para esta viabilidade, congelando o histórico.
            </p>
            {renderCurveSelector("Obras de Infraestrutura", "curva_obras_json", "obras de infraestrutura")}
            {renderCurveSelector("Projetos", "curva_projetos_json", "projetos")}
            {renderCurveSelector("Aquisição de Área", "curva_aquisicao_json", "aquisicao de area")}
            {renderCurveSelector("Administração de Obras", "curva_adm_obras_json", "administracao de obras")}
            
            {/* Curvas extras */}
            {data.extra_constructions_json && data.extra_constructions_json.map((extra: any, idx: number) => (
              <div key={`curve-${idx}`}>
                {renderCurveSelectorExtra(extra.nome || `Custo Extra ${idx + 1}`, "extra_constructions_json", idx)}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
