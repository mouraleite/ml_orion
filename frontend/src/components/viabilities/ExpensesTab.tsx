"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useUnsavedChanges } from "@/contexts/UnsavedChangesContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Save, Activity } from "lucide-react";
import { apoioService } from "@/services/apoio";

interface ExpensesTabProps {
  phaseId: number;
  project?: any;
  onUpdateProject?: (updates: Record<string, any>) => void;
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

  const handleBlur = () => {
    setIsFocused(false);
    setLocalValue(format(value));
  };

  return (
    <input
      type="text"
      className={className}
      value={localValue}
      disabled={disabled}
      placeholder={placeholder}
      onFocus={() => setIsFocused(true)}
      onChange={handleChange}
      onBlur={handleBlur}
    />
  );
}

export function ExpensesTab({ phaseId, project, onUpdateProject, isReadonly }: ExpensesTabProps) {
  const [data, setData] = useState<any>({
    marketing_valor: 5.0,
    marketing_tipo: "%",
    comercial_valor: 1.0,
    comercial_tipo: "%",
    adm_valor: 3.0,
    adm_tipo: "%",
    curva_marketing_json: { meses: [] },
    curva_comercial_json: { meses: [] },
    curva_adm_json: { meses: [] },
  });
  const [curves, setCurves] = useState<any[]>([]);
  const [economicIndicators, setEconomicIndicators] = useState<any[]>([]);
  const [realIpca, setRealIpca] = useState<any | null>(null);
  const [vgvTotal, setVgvTotal] = useState(0);
  const { setHasUnsavedChanges } = useUnsavedChanges();
  const [initialData, setInitialData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [res, curvesRes, revRes, indRes, ipcaRes] = await Promise.all([
          api.get(`/viabilities/phases/${phaseId}/expenses`).catch(() => ({ data: {} })),
          api.get("/curves/").catch(() => ({ data: [] })),
          api.get(`/viabilities/phases/${phaseId}/revenue`).catch(() => ({ data: { vgv_total: 0 } })),
          apoioService.getIndicadores().catch(() => []),
          api.get("/market-indices/ipca").catch(() => ({ data: null })),
        ]);
        
        const dbData = res.data || {};
        const defaultData = {
          marketing_valor: 5.0, marketing_tipo: "%",
          comercial_valor: 4.0, comercial_tipo: "%",
          comissao_corretagem_valor: 0.0,
          adm_valor: 3.0, adm_tipo: "%",
          curva_marketing_json: { meses: [] },
          curva_comercial_json: { meses: [] },
          curva_adm_json: { meses: [] },
          extra_expenses_json: []
        };
        const mergedData = { ...defaultData, ...dbData };
        if (!mergedData.curva_marketing_json) mergedData.curva_marketing_json = { meses: [] };
        if (!mergedData.curva_comercial_json) mergedData.curva_comercial_json = { meses: [] };
        if (!mergedData.curva_adm_json) mergedData.curva_adm_json = { meses: [] };
        setData(mergedData);
        setInitialData(mergedData);
        setCurves(curvesRes.data);
        setEconomicIndicators(indRes || []);
        setRealIpca(ipcaRes.data || null);
        if (revRes.data && revRes.data.vgv_total) {
          setVgvTotal(revRes.data.vgv_total);
        }
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
      await api.put(`/viabilities/phases/${phaseId}/expenses`, data);
      setMessage("Despesas salvas com sucesso!");
      setInitialData(data);
      setHasUnsavedChanges(false);
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      alert("Erro ao salvar despesas.");
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
    const realData = indicatorType === "IPCA" ? realIpca : null; // ExpensesTab only uses IPCA
    const realValue = realData?.ultimo_mes?.mensal ?? null;
    const realLabel = `IPCA Real BCB (${realValue != null ? realValue.toFixed(2) + "% a.m." : "..."}) — ${realData?.ultimo_mes?.data || ""}`;
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
              if (realValue != null && onUpdateProject) onUpdateProject({ [valueField]: realValue, [typeField]: "% a.m." });
              return;
            }
            if (val === "custom" || val === "") return;
            const ind = indicators.find(i => i.id === Number(val));
            if (ind && onUpdateProject) {
              onUpdateProject({ [valueField]: ind.valor, [typeField]: ind.tipo_unidade });
            }
          }}
          disabled={isReadonly}
        >
          <option value="" disabled className="text-slate-400">
            {indicators.length === 0 && !realData ? "Nenhum cenário..." : "Selecione um cenário..."}
          </option>
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
          onChange={(val: number) => onUpdateProject && onUpdateProject({ [valueField]: val })}
          disabled={isReadonly}
        />
        <select
          className="ml-select h-7 w-20 text-xs"
          value={project?.[typeField] || "% a.a."}
          onChange={(e) => onUpdateProject && onUpdateProject({ [typeField]: e.target.value })}
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
              const normalizedType = (c.tipo || "").trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
              const normalizedFilter = filterType.trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
              if (!normalizedType || !normalizedFilter) return false;
              return normalizedType.includes(normalizedFilter) || normalizedFilter.includes(normalizedType);
            }).map(c => (
              <option key={c.id} value={c.id}>{c.nome}</option>
            ))}
          </select>
          {hasCurve ? (
            <span className="text-xs text-green-600 font-medium flex items-center gap-1">
              <Activity className="w-3 h-3" /> Curva Aplicada ({jsonValue.meses.length} meses)
            </span>
          ) : (
            <span className="text-xs text-slate-400">Nenhuma curva</span>
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
            <option value="">Aplicar curva padrão...</option>
            {curves.map(c => (
              <option key={c.id} value={c.id}>{c.nome}</option>
            ))}
          </select>
          {hasCurve ? (
            <span className="text-xs text-green-600 font-medium flex items-center gap-1">
              <Activity className="w-3 h-3" /> Curva Aplicada ({jsonValue.meses.length} meses)
            </span>
          ) : (
            <span className="text-xs text-slate-400">Nenhuma curva</span>
          )}
        </div>
      );
  };

  const handleAddExtraExpense = () => {
    const arr = [...(data.extra_expenses_json || [])];
    arr.push({ nome: "", valor: 0, tipo: "R$", curva_json: null });
    setData({ ...data, extra_expenses_json: arr });
  };

  const handleRemoveExtraExpense = (idx: number) => {
    const arr = [...(data.extra_expenses_json || [])];
    arr.splice(idx, 1);
    setData({ ...data, extra_expenses_json: arr });
  };

  const handleExtraExpenseChange = (idx: number, field: string, value: any) => {
    const arr = [...(data.extra_expenses_json || [])];
    arr[idx][field] = value;
    setData({ ...data, extra_expenses_json: arr });
  };

  const calcValue = (val: number, type: string) => type === "%" ? vgvTotal * (val / 100) : val;

  const mktCalc = calcValue(data.marketing_valor || 0, data.marketing_tipo || "%");
  const comCalc = calcValue(data.comercial_valor || 0, data.comercial_tipo || "%");
  const admCalc = calcValue(data.adm_valor || 0, data.adm_tipo || "%");
  const comissaoCalc = vgvTotal * ((data.comissao_corretagem_valor || 0) / 100);

  const extraExpensesTotal = (data.extra_expenses_json || []).reduce((acc: number, curr: any) => {
    return acc + calcValue(curr.valor || 0, curr.tipo || "R$");
  }, 0);

  const totalDespesas = mktCalc + comCalc + admCalc + comissaoCalc + extraExpensesTotal;

  const formatCurrency = (val: number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-300">
      
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Despesas Comerciais e Administrativas</h2>
          <p className="text-sm text-slate-500">Defina as verbas de Marketing, Vendas e Administração.</p>
        </div>
        <div className="flex items-center gap-2">
          {message && <span className="text-sm text-green-600 font-medium">{message}</span>}
          <Button onClick={handleSave} disabled={isLoading || isReadonly} className="flex items-center gap-2">
            <Save className="w-4 h-4" />
            {isLoading ? "Salvando..." : "Salvar Despesas"}
          </Button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b pb-2">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Verbas / Orçamento (EXPENSES)</h3>
            <div className="flex items-center gap-2">
              {renderIndexerConfig(!!project?.aplicar_ipca_despesas, "IPCA", "ipca_projetado_valor", "ipca_projetado_tipo")}
              <label className="flex items-center gap-2 text-sm cursor-pointer border-l pl-3 ml-1">
                <button 
                  onClick={() => !isReadonly && onUpdateProject && onUpdateProject({ aplicar_ipca_despesas: !project?.aplicar_ipca_despesas })}
                  disabled={isReadonly}
                  className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${project?.aplicar_ipca_despesas ? 'bg-brand-green' : 'bg-slate-300'} ${isReadonly ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition ${project?.aplicar_ipca_despesas ? 'translate-x-5' : 'translate-x-1'}`} />
                </button>
                <span className="text-xs text-slate-500 font-medium">IPCA</span>
              </label>
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Marketing</label>
              <div className="flex-1 flex items-center gap-2 pr-6">
                <select 
                  className="ml-select w-20 text-sm h-9" 
                  value={data.marketing_tipo || "%"} 
                  disabled={isReadonly}
                  onChange={e => setData({...data, marketing_tipo: e.target.value})}
                >
                  <option value="R$">R$</option>
                  <option value="%">%</option>
                </select>
                <NumericInput 
                  className="ml-input w-full h-9 font-mono"
                  value={data.marketing_valor}
                  onChange={(val: number) => setData({ ...data, marketing_valor: val })}
                  disabled={isReadonly}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {(data.marketing_tipo || "%" ) === "%" 
                  ? `Equivale a ${formatCurrency(mktCalc)} do VGV`
                  : `Equivale a ${vgvTotal > 0 ? ((data.marketing_valor || 0) / vgvTotal * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) : '0,00'}% do VGV`}
              </p>
            </div>
            
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Comercial</label>
              <div className="flex-1 flex items-center gap-2 pr-6">
                <select 
                  className="ml-select w-20 text-sm h-9" 
                  value={data.comercial_tipo || "%"} 
                  disabled={isReadonly}
                  onChange={e => setData({...data, comercial_tipo: e.target.value})}
                >
                  <option value="R$">R$</option>
                  <option value="%">%</option>
                </select>
                <NumericInput 
                  className="ml-input w-full h-9 font-mono"
                  value={data.comercial_valor}
                  onChange={(val: number) => setData({ ...data, comercial_valor: val })}
                  disabled={isReadonly}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {(data.comercial_tipo || "%" ) === "%" 
                  ? `Equivale a ${formatCurrency(comCalc)} do VGV`
                  : `Equivale a ${vgvTotal > 0 ? ((data.comercial_valor || 0) / vgvTotal * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) : '0,00'}% do VGV`}
              </p>
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Despesas Administrativas</label>
              <div className="flex-1 flex items-center gap-2 pr-6">
                <select 
                  className="ml-select w-20 text-sm h-9" 
                  value={data.adm_tipo || "%"} 
                  disabled={isReadonly}
                  onChange={e => setData({...data, adm_tipo: e.target.value})}
                >
                  <option value="R$">R$</option>
                  <option value="%">%</option>
                </select>
                <NumericInput 
                  className="ml-input w-full h-9 font-mono"
                  value={data.adm_valor}
                  onChange={(val: number) => setData({ ...data, adm_valor: val })}
                  disabled={isReadonly}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {(data.adm_tipo || "%" ) === "%" 
                  ? `Equivale a ${formatCurrency(admCalc)} do VGV`
                  : `Equivale a ${vgvTotal > 0 ? ((data.adm_valor || 0) / vgvTotal * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) : '0,00'}% do VGV`}
              </p>
            </div>

            {/* Comissões */}
            <div className="space-y-2 pt-4 border-t border-slate-100">
              <h4 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Comissões</h4>
              <div className="space-y-1 bg-slate-50 p-4 border rounded-md">
                <label className="text-sm font-medium text-slate-700">Comissão de Venda (Corretagem)</label>
                <div className="flex-1 flex items-center gap-2 pr-6">
                  <span className="w-20 text-sm h-9 flex items-center justify-center bg-slate-200 text-slate-500 rounded-md border border-slate-300">%</span>
                  <NumericInput 
                    className="ml-input w-full h-9 font-mono"
                    value={data.comissao_corretagem_valor}
                    onChange={(val: number) => setData({ ...data, comissao_corretagem_valor: val })}
                    disabled={isReadonly}
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Equivale a {formatCurrency(comissaoCalc)} do VGV
                </p>
                <div className="mt-3 text-xs text-brand-primary bg-brand-primary/10 p-2 rounded border border-brand-primary/20">
                  A curva de desembolso das Comissões acompanha automaticamente a Velocidade de Vendas.
                </div>
              </div>
            </div>

            {/* Despesas Extras Dinâmicas */}
            {data.extra_expenses_json && data.extra_expenses_json.map((extra: any, idx: number) => (
              <div key={idx} className="space-y-1 p-3 border rounded-md relative bg-slate-50/50 group">
                <button 
                  onClick={() => handleRemoveExtraExpense(idx)} 
                  className="absolute top-2 right-2 text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                  disabled={isReadonly}
                >×</button>
                <div className="pr-6">
                  <Input 
                    placeholder="Nome da despesa extra..."
                    value={extra.nome}
                    disabled={isReadonly}
                    onChange={(e) => handleExtraExpenseChange(idx, "nome", e.target.value)}
                    className="mb-2 h-8 text-sm font-medium border-transparent hover:border-slate-300 focus:border-brand-primary"
                  />
                  <div className="flex gap-2">
                    <select 
                      className="ml-select w-20 text-sm h-10" 
                      value={extra.tipo || "R$"} 
                      disabled={isReadonly}
                      onChange={e => handleExtraExpenseChange(idx, "tipo", e.target.value)}
                    >
                      <option value="R$">R$</option>
                      <option value="%">%</option>
                    </select>
                    <NumericInput 
                      className="ml-input w-full h-10 font-mono"
                      value={extra.valor}
                      disabled={isReadonly}
                      onChange={(val: number) => handleExtraExpenseChange(idx, "valor", val)}
                    />
                  </div>
                  {(extra.tipo || "%" ) === "%" && <p className="text-xs text-slate-500 mt-1">Equivale a {formatCurrency(calcValue(extra.valor, "%"))} do VGV</p>}
                </div>
              </div>
            ))}
            
            {!isReadonly && (
              <Button variant="outline" size="sm" onClick={handleAddExtraExpense} className="w-full border-dashed text-slate-500 hover:text-slate-700 hover:border-slate-400">
                + Adicionar Despesa Extra
              </Button>
            )}

            <div className="pt-4 border-t flex flex-col gap-1 text-sm text-slate-600">
              <div className="flex justify-between">
                <span>Marketing:</span>
                <span>{formatCurrency(mktCalc)}</span>
              </div>
              <div className="flex justify-between">
                <span>Comercial:</span>
                <span>{formatCurrency(comCalc)}</span>
              </div>
              <div className="flex justify-between">
                <span>Comissões:</span>
                <span>{formatCurrency(comissaoCalc)}</span>
              </div>
              <div className="flex justify-between">
                <span>Despesas Administrativas:</span>
                <span>{formatCurrency(admCalc)}</span>
              </div>
              {data.extra_expenses_json?.map((e: any, i: number) => (
                <div key={i} className="flex justify-between">
                  <span>{e.nome || `Despesa Extra ${i + 1}`}:</span>
                  <span>{formatCurrency(calcValue(e.valor || 0, e.tipo || "R$"))}</span>
                </div>
              ))}
            </div>

            <div className="pt-4 border-t flex justify-between items-center text-slate-900 mt-2">
              <span className="font-bold">Total EXPENSES:</span>
              <span className="font-bold text-lg">
                {formatCurrency(totalDespesas)}
              </span>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between border-b pb-2">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Desembolso Financeiro / Curva</h3>
          </div>
          
          <div className="space-y-3 bg-slate-50 p-4 rounded-lg border border-slate-200">
            <p className="text-xs text-slate-500 mb-2">
              Selecione a curva padrão que ditará a velocidade de desembolso de cada despesa.
            </p>
            {renderCurveSelector("Marketing", "curva_marketing_json", "marketing")}
            {renderCurveSelector("Comercial", "curva_comercial_json", "comercial")}
            {renderCurveSelector("Administração", "curva_adm_json", "administração de despesas")}
            
            {/* Curvas extras */}
            {data.extra_expenses_json && data.extra_expenses_json.map((extra: any, idx: number) => (
              <div key={`curve-${idx}`}>
                {renderCurveSelectorExtra(extra.nome || `Despesa Extra ${idx + 1}`, "extra_expenses_json", idx)}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
