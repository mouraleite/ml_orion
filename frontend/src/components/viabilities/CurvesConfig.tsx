"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useUnsavedChanges } from "@/contexts/UnsavedChangesContext";
import { Button } from "@/components/ui/Button";
import { Save, CalendarDays, TrendingUp } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

interface CurvesConfigProps {
  phaseId: number;
  isReadonly?: boolean;
}

const EXPECTED_CURVES = [
  { field: 'curva_obras_json', label: 'Obras de Infraestrutura', color: '#F5883A', source: 'construction' as const },
  { field: 'curva_projetos_json', label: 'Projetos', color: '#FF5144', source: 'construction' as const },
  { field: 'curva_aquisicao_json', label: 'Aquisição de Área', color: '#91A89C', source: 'construction' as const },
  { field: 'curva_adm_obras_json', label: 'Administração de Obras', color: '#FFABA4', source: 'construction' as const },
  { field: 'velocidade_vendas_json', label: 'Velocidade de Vendas', color: '#2E864D', source: 'revenue' as const },
  { field: 'curva_marketing_json', label: 'Marketing', color: '#F9C094', source: 'expenses' as const },
  { field: 'curva_comercial_json', label: 'Comercial/Vendas', color: '#255742', source: 'expenses' as const },
  { field: 'curva_adm_json', label: 'Despesas Administrativas', color: '#94BD9B', source: 'expenses' as const },
];

export function CurvesConfig({ phaseId, isReadonly }: CurvesConfigProps) {
  const [constructionData, setConstructionData] = useState<any>(null);
  const [expensesData, setExpensesData] = useState<any>(null);
  const [revenueData, setRevenueData] = useState<any>(null);
  
  const [datesData, setDatesData] = useState<any>(null);
  const [baseDate, setBaseDate] = useState<Date | null>(null);
  const { setHasUnsavedChanges } = useUnsavedChanges();
  const [initialData, setInitialData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");

  const CURVE_DATE_MAPPING: Record<string, string> = {
    'curva_obras_json': 'data_inicio_obras',
    'curva_projetos_json': 'data_inicio_projetos',
    'curva_aquisicao_json': 'data_inicio_aquisicao',
    'velocidade_vendas_json': 'data_lancamento',
    'curva_marketing_json': 'data_inicio_mkt',
    'curva_comercial_json': 'data_inicio_comercial',
  };

  const fetchAll = async () => {
    try {
      const [constructionRes, expensesRes, revenueRes, datesRes] = await Promise.all([
        api.get(`/viabilities/phases/${phaseId}/construction`).catch(() => ({ data: {} })),
        api.get(`/viabilities/phases/${phaseId}/expenses`).catch(() => ({ data: {} })),
        api.get(`/viabilities/phases/${phaseId}/revenue`).catch(() => ({ data: {} })),
        api.get(`/viabilities/phases/${phaseId}/dates`).catch(() => ({ data: {} })),
      ]);
      
      const cData = constructionRes.data;
      const eData = expensesRes.data;
      const rData = revenueRes.data;
      const dData = datesRes.data;

      // Calcular a data base (Mês 1)
      const dateFields = [
        dData.data_registro, dData.data_lancamento, dData.data_inicio_obras,
        dData.data_inicio_projetos, dData.data_inicio_aquisicao, dData.data_inicio_comercial, dData.data_inicio_mkt
      ].filter(Boolean);
      
      let base: Date | null = null;
      if (dateFields.length > 0) {
        dateFields.forEach(d => {
          const parsed = new Date(d + 'T12:00:00');
          if (!base || parsed < base) base = parsed;
        });
      }
      setBaseDate(base);
      setDatesData(dData);

      const getOffset = (targetDateStr: string | null) => {
        if (!base || !targetDateStr) return 1;
        const target = new Date(targetDateStr + 'T12:00:00');
        const months = (target.getFullYear() - base.getFullYear()) * 12 + (target.getMonth() - base.getMonth());
        return Math.max(1, months + 1);
      };

      const origC = JSON.parse(JSON.stringify(constructionRes.data));
      const origE = JSON.parse(JSON.stringify(expensesRes.data));
      const origR = JSON.parse(JSON.stringify(revenueRes.data));

      // Auto-aplicar os deslocamentos
      if (dData.data_inicio_obras && cData.curva_obras_json) cData.curva_obras_json.mes_inicio = getOffset(dData.data_inicio_obras);
      if (dData.data_inicio_projetos && cData.curva_projetos_json) cData.curva_projetos_json.mes_inicio = getOffset(dData.data_inicio_projetos);
      if (dData.data_inicio_aquisicao && cData.curva_aquisicao_json) cData.curva_aquisicao_json.mes_inicio = getOffset(dData.data_inicio_aquisicao);
      if (dData.data_lancamento && rData.velocidade_vendas_json) rData.velocidade_vendas_json.mes_inicio = getOffset(dData.data_lancamento);
      if (dData.data_inicio_mkt && eData.curva_marketing_json) eData.curva_marketing_json.mes_inicio = getOffset(dData.data_inicio_mkt);
      if (dData.data_inicio_comercial && eData.curva_comercial_json) eData.curva_comercial_json.mes_inicio = getOffset(dData.data_inicio_comercial);

      setConstructionData(cData);
      setExpensesData(eData);
      setRevenueData(rData);
      setInitialData({
        construction: origC,
        expenses: origE,
        revenue: origR
      });
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchAll();
  }, [phaseId]);

  useEffect(() => {
    if (initialData && constructionData && expensesData && revenueData) {
      const currentData = {
        construction: constructionData,
        expenses: expensesData,
        revenue: revenueData
      };
      const isDirty = JSON.stringify(initialData) !== JSON.stringify(currentData);
      setHasUnsavedChanges(isDirty);

      if (isDirty && !isLoading) {
        const timer = setTimeout(() => {
          handleSave();
        }, 1500);
        return () => clearTimeout(timer);
      }
    }
  }, [constructionData, expensesData, revenueData, initialData]);

  const handleSave = async () => {
    setIsLoading(true);
    setMessage("");
    try {
      await Promise.all([
        api.put(`/viabilities/phases/${phaseId}/construction`, constructionData).catch(e => console.error(e)),
        api.put(`/viabilities/phases/${phaseId}/expenses`, expensesData).catch(e => console.error(e)),
        api.put(`/viabilities/phases/${phaseId}/revenue`, revenueData).catch(e => console.error(e)),
      ]);
      setMessage("Deslocamentos salvos com sucesso!");
      setInitialData({
        construction: JSON.parse(JSON.stringify(constructionData)),
        expenses: JSON.parse(JSON.stringify(expensesData)),
        revenue: JSON.parse(JSON.stringify(revenueData))
      });
      setHasUnsavedChanges(false);
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      alert("Erro ao salvar dados das curvas.");
    } finally {
      setIsLoading(false);
    }
  };

  const updateMesInicio = (source: string, field: string, value: number) => {
    if (source === 'construction') {
      setConstructionData((prev: any) => ({ ...prev, [field]: { ...prev[field], mes_inicio: value } }));
    } else if (source === 'expenses') {
      setExpensesData((prev: any) => ({ ...prev, [field]: { ...prev[field], mes_inicio: value } }));
    } else if (source === 'revenue') {
      setRevenueData((prev: any) => ({ ...prev, [field]: { ...prev[field], mes_inicio: value } }));
    }
  };

  const getTotalValue = (field: string) => {
    const vgv = revenueData?.vgv_total || 0;
    const c = constructionData || {};
    const e = expensesData || {};
    
    if (field === 'velocidade_vendas_json') return vgv;
    if (field === 'curva_obras_json') return c.custo_obras_tipo === '%' ? vgv * (c.custo_obras / 100) : c.custo_obras || 0;
    if (field === 'curva_projetos_json') return c.custo_projetos_tipo === '%' ? vgv * (c.custo_projetos / 100) : c.custo_projetos || 0;
    if (field === 'curva_aquisicao_json') return c.aquisicao_area_tipo === '%' ? vgv * (c.aquisicao_area / 100) : c.aquisicao_area || 0;
    if (field === 'curva_adm_obras_json') return c.adm_obras_tipo === '%' ? vgv * (c.adm_obras / 100) : c.adm_obras || 0;
    
    if (field === 'curva_marketing_json') return e.marketing_tipo === '%' ? vgv * (e.marketing_valor / 100) : e.marketing_valor || 0;
    if (field === 'curva_comercial_json') return e.comercial_tipo === '%' ? vgv * (e.comercial_valor / 100) : e.comercial_valor || 0;
    if (field === 'curva_adm_json') return e.adm_tipo === '%' ? vgv * (e.adm_valor / 100) : e.adm_valor || 0;
    
    return 0;
  };

  const getChartData = (jsonValue: any, totalAmount: number) => {
    if (!jsonValue || !jsonValue.meses || jsonValue.meses.length === 0) return [];
    
    const offset = Math.max(0, (jsonValue.mes_inicio || 1) - 1);
    const meses = jsonValue.meses;
    
    const formatLabel = (index: number) => {
      if (!baseDate) return `M${index + 1}`;
      const d = new Date(baseDate.getFullYear(), baseDate.getMonth() + index, 1);
      const m = d.toLocaleString('pt-BR', { month: 'short' }).substring(0, 3);
      const monthStr = m.charAt(0).toUpperCase() + m.slice(1);
      const yearStr = d.getFullYear().toString().substring(2);
      return `${monthStr} ${yearStr}`;
    };

    const data: { mes: string; label: string; percentual: number; valor: number }[] = [];
    for (let i = 0; i < offset; i++) {
      data.push({ mes: `M${i + 1}`, label: formatLabel(i), percentual: 0, valor: 0 });
    }
    for (let i = 0; i < meses.length; i++) {
      const perc = typeof meses[i] === 'number' ? meses[i] : Number(meses[i]);
      data.push({
        mes: `M${offset + i + 1}`,
        label: formatLabel(offset + i),
        percentual: perc,
        valor: (perc / 100) * totalAmount,
      });
    }
    return data;
  };

  const appliedCurves = EXPECTED_CURVES.filter(c => {
    const data = c.source === 'construction' ? constructionData : c.source === 'expenses' ? expensesData : revenueData;
    return data && data[c.field] && data[c.field].curve_id;
  });

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-300">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Deslocamento de Curvas</h2>
          <p className="text-sm text-slate-500">
            Abaixo estão as curvas que você <strong>já selecionou</strong> nas abas anteriores. <br/>
            Use o campo <strong>Mês de Início</strong> para deslocar a curva no cronograma da viabilidade.
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm font-medium">
          {isLoading && <span className="text-slate-500 flex items-center gap-2"><div className="w-4 h-4 border-2 border-brand-primary border-t-transparent rounded-full animate-spin"></div> Salvando...</span>}
          {message && !isLoading && <span className="text-green-600 flex items-center gap-1"><Save className="w-4 h-4" /> {message}</span>}
        </div>
      </div>

      {!constructionData || !expensesData || !revenueData ? (
        <AppLoadingState />
      ) : appliedCurves.length === 0 ? (
        <div className="text-center py-12 text-slate-500 border-2 border-dashed rounded-lg bg-slate-50">
          <p className="font-semibold text-lg">Nenhuma curva aplicada ainda.</p>
          <p className="text-sm mt-2 max-w-md mx-auto">Vá até as abas de <strong>Obras</strong>, <strong>Despesas</strong> ou <strong>Receitas</strong> e selecione uma curva padrão nos respectivos campos. Elas aparecerão aqui automaticamente.</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-8">
          {appliedCurves.map(c => {
            const data = c.source === 'construction' ? constructionData : c.source === 'expenses' ? expensesData : revenueData;
            const jsonValue = data[c.field];
            const totalAmount = getTotalValue(c.field);
            const chartData = getChartData(jsonValue, totalAmount);
            
            const linkedDateField = CURVE_DATE_MAPPING[c.field];
            const hasLinkedDate = datesData && linkedDateField && datesData[linkedDateField];

            return (
              <div key={c.field} className="space-y-4 bg-slate-50 p-6 rounded-xl border border-slate-200 transition-all hover:shadow-md">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: c.color }} />
                    <h3 className="font-bold text-slate-900">{c.label}</h3>
                  </div>
                  {jsonValue.mes_inicio > 1 && (
                    <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">
                      Início M{jsonValue.mes_inicio}
                    </span>
                  )}
                  {totalAmount > 0 && (
                    <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full font-medium border border-slate-200">
                      Total: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(totalAmount)}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <label className="block text-xs text-slate-500 mb-1">Curva Padrão Aplicada</label>
                    <div className="h-9 px-3 bg-white border border-slate-200 rounded-md flex items-center text-sm font-medium text-slate-700 truncate" title={jsonValue.curve_name}>
                      {jsonValue.curve_name || "Curva Desconhecida"}
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1 flex items-center gap-1">
                      <CalendarDays className="w-3 h-3" /> Mês Início
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={120}
                      className={`ml-input ${hasLinkedDate ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : ''}`}
                      value={jsonValue.mes_inicio || 1}
                      disabled={isReadonly || !!hasLinkedDate}
                      onChange={(e) => updateMesInicio(c.source, c.field, Math.max(1, parseInt(e.target.value) || 1))}
                      title={hasLinkedDate ? "Calculado automaticamente a partir da aba Datas." : ""}
                    />
                    {hasLinkedDate && (
                      <span className="text-[10px] text-brand-primary mt-1 block leading-tight">
                        Definido pela aba de Datas
                      </span>
                    )}
                  </div>
                </div>

                <div className="h-56 mt-2 bg-white p-4 rounded-lg border border-slate-100">
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                        <XAxis dataKey="label" tick={{fontSize: 9}} interval="preserveStartEnd" minTickGap={20} />
                        <YAxis 
                          tickFormatter={(val) => {
                            if (val >= 1000000) return `R$ ${(val / 1000000).toFixed(1)}M`;
                            if (val >= 1000) return `R$ ${(val / 1000).toFixed(0)}k`;
                            return `R$ ${val}`;
                          }} 
                          width={60} 
                          tick={{fontSize: 10}} 
                        />
                        <Tooltip 
                          formatter={(value: any, name: any, props: any) => [
                            new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value as number) + ` (${props.payload.percentual.toFixed(2)}%)`, 
                            'Valor Projetado'
                          ]} 
                          labelFormatter={(label: any, payload: any) => {
                            if (payload && payload.length > 0) {
                              return `${payload[0].payload.mes} (${label})`;
                            }
                            return label;
                          }}
                          contentStyle={{ borderRadius: '8px', fontSize: '12px' }}
                        />
                        <Bar dataKey="valor" fill={c.color} radius={[2, 2, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-slate-400 text-sm gap-2">
                      <TrendingUp className="w-8 h-8 opacity-30" />
                      Sem dados para exibir.
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
