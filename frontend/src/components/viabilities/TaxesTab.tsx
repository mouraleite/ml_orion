"use client";
import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";
import { useUnsavedChanges } from "@/contexts/UnsavedChangesContext";
import { apoioService } from "@/services/apoio";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Save, Calculator } from "lucide-react";
import { Card } from "@/components/ui/Card";

interface TaxesTabProps {
  phaseId: number;
  isReadonly?: boolean;
}

export function TaxesTab({ phaseId, isReadonly }: TaxesTabProps) {
  const [data, setData] = useState<any>({
    regime_tributario: "RET",
    aliquota_pis: 0.65,
    aliquota_cofins: 3.0,
    aliquota_irpj: 0.0,
    aliquota_csll: 0.0,
    aliquota_outros: 0.0,
    aliquota_total: 3.65,
    incidencia_sobre: "Recebimento",
  });
  const [taxRegimes, setTaxRegimes] = useState<any[]>([]);
  const [vgvTotal, setVgvTotal] = useState(0);
  const [vgvLiquido, setVgvLiquido] = useState(0);
  const { setHasUnsavedChanges } = useUnsavedChanges();
  const [initialData, setInitialData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [projectedRevenue, setProjectedRevenue] = useState<number | null>(null);
  const [projectedTaxesDRE, setProjectedTaxesDRE] = useState<number | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [res, regimesRes, revRes, resultsRes] = await Promise.all([
          api.get(`/viabilities/phases/${phaseId}/taxes`).catch(() => ({ data: {} })),
          apoioService.getTaxRegimes().catch(() => []),
          api.get(`/viabilities/phases/${phaseId}/revenue`).catch(() => ({ data: { vgv_total: 0 } })),
          api.get(`/viabilities/phases/${phaseId}/results`).catch(() => ({ data: null }))
        ]);
        
        setTaxRegimes(regimesRes);
        setVgvTotal(revRes.data?.vgv_total || 0);

        if (res.data && Object.keys(res.data).length > 0) {
          setData(res.data);
          setInitialData(res.data);
        }
        
        if (resultsRes.data?.monthly_cashflow) {
            let totalRev = 0;
            let totalTaxes = 0;
            resultsRes.data.monthly_cashflow.forEach((c: any) => {
                totalRev += c.Receitas || 0;
                totalTaxes += c.Impostos || 0;
            });
            setProjectedRevenue(totalRev);
            setProjectedTaxesDRE(totalTaxes);
        }
        
        // Pega o VGV Líquido retornado pelo motor (após dedução da comissão)
        if (resultsRes.data?.indicators?.vgv_total) {
            setVgvLiquido(resultsRes.data.indicators.vgv_total);
        } else {
            setVgvLiquido(revRes.data?.vgv_total || 0);
        }
      } catch (error) {
        console.error("Erro ao buscar impostos:", error);
      } finally {
        setIsLoading(false);
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
      const payload = {
        ...data,
        aliquota_total: currentTotal
      };
      await api.put(`/viabilities/phases/${phaseId}/taxes`, payload);
      setMessage("Impostos salvos com sucesso!");
      setInitialData(data);
      setHasUnsavedChanges(false);
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      alert("Erro ao salvar impostos.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegimeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const regimeNome = e.target.value;
    const selectedRegime = taxRegimes.find(r => r.nome === regimeNome);
    
    if (selectedRegime) {
      setData({
        ...data,
        regime_tributario: selectedRegime.nome,
        aliquota_pis: selectedRegime.pis,
        aliquota_cofins: selectedRegime.cofins,
        aliquota_irpj: selectedRegime.irpj,
        aliquota_csll: selectedRegime.csll,
        aliquota_outros: selectedRegime.outros,
      });
    } else {
      setData({ ...data, regime_tributario: regimeNome });
    }
  };

  const currentTotal = useMemo(() => {
    return (parseFloat(data.aliquota_pis) || 0) +
           (parseFloat(data.aliquota_cofins) || 0) +
           (parseFloat(data.aliquota_irpj) || 0) +
           (parseFloat(data.aliquota_csll) || 0) +
           (parseFloat(data.aliquota_outros) || 0);
  }, [data.aliquota_pis, data.aliquota_cofins, data.aliquota_irpj, data.aliquota_csll, data.aliquota_outros]);

  const valorTotalProjetado = useMemo(() => {
    return (vgvLiquido * currentTotal) / 100;
  }, [vgvLiquido, currentTotal]);

  const formatCurrency = (val: number) => {
    return val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-300">
      
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Impostos</h2>
          <p className="text-sm text-slate-500">Defina o regime tributário e as alíquotas aplicáveis ao projeto.</p>
        </div>
        <div className="flex items-center gap-4">
          {message && <span className="text-sm text-green-600 font-medium">{message}</span>}
          <Button onClick={handleSave} disabled={isLoading || isReadonly} className="flex items-center gap-2">
            <Save className="w-4 h-4" />
            {isLoading ? "Salvando..." : "Salvar Impostos"}
          </Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider border-b pb-2">Premissas Tributárias</h3>
          
          <div className="bg-slate-50 p-6 rounded-lg border border-slate-200 space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Regime Tributário (Base do Apoio)</label>
                <select 
                  className="ml-select"
                  value={data.regime_tributario}
                  disabled={isReadonly}
                  onChange={handleRegimeChange}
                >
                  <option value="">Selecione...</option>
                  {taxRegimes.map(r => (
                    <option key={r.id} value={r.nome}>{r.nome}</option>
                  ))}
                  <option value="Personalizado">Personalizado</option>
                  <option value="RET">RET (Legado)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Incidência do Imposto</label>
                <select 
                  className="ml-select"
                  value={data.incidencia_sobre}
                  disabled={isReadonly}
                  onChange={(e) => setData({ ...data, incidencia_sobre: e.target.value })}
                >
                  <option value="Recebimento">Sobre o Recebimento (Caixa)</option>
                  <option value="Venda">Sobre a Venda (Competência)</option>
                </select>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-200">
              <h4 className="text-sm font-semibold text-slate-800 mb-4">Composição da Alíquota</h4>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-500 uppercase">PIS (%)</label>
                  <Input type="number" step="0.01" className="h-9" disabled={isReadonly} value={data.aliquota_pis} onChange={(e) => setData({ ...data, aliquota_pis: e.target.value === '' ? '' : parseFloat(e.target.value) })} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-500 uppercase">COFINS (%)</label>
                  <Input type="number" step="0.01" className="h-9" disabled={isReadonly} value={data.aliquota_cofins} onChange={(e) => setData({ ...data, aliquota_cofins: e.target.value === '' ? '' : parseFloat(e.target.value) })} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-500 uppercase">IRPJ (%)</label>
                  <Input type="number" step="0.01" className="h-9" disabled={isReadonly} value={data.aliquota_irpj} onChange={(e) => setData({ ...data, aliquota_irpj: e.target.value === '' ? '' : parseFloat(e.target.value) })} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-500 uppercase">CSLL (%)</label>
                  <Input type="number" step="0.01" className="h-9" disabled={isReadonly} value={data.aliquota_csll} onChange={(e) => setData({ ...data, aliquota_csll: e.target.value === '' ? '' : parseFloat(e.target.value) })} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-500 uppercase">Outros (%)</label>
                  <Input type="number" step="0.01" className="h-9" disabled={isReadonly} value={data.aliquota_outros} onChange={(e) => setData({ ...data, aliquota_outros: e.target.value === '' ? '' : parseFloat(e.target.value) })} />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
           <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider border-b pb-2 flex items-center gap-2">
            <Calculator className="w-4 h-4 text-brand-primary" />
            Totalizador
          </h3>

          <Card className="p-6 bg-slate-50 border border-slate-200">
            <div className="space-y-6">
              <div className="flex justify-between items-center border-b border-slate-200 pb-4">
                <span className="text-sm font-medium text-slate-500">Carga Tributária Total</span>
                <span className="text-2xl font-bold text-slate-800">
                  {currentTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%
                </span>
              </div>
              
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">VGV Nominal (Bruto)</span>
                <span className="font-semibold text-slate-700">{formatCurrency(vgvTotal)}</span>
              </div>

              {vgvLiquido < vgvTotal && (
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-500">(-) Comissões (Dedução)</span>
                  <span className="font-semibold text-red-500">-{formatCurrency(vgvTotal - vgvLiquido)}</span>
                </div>
              )}

              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">VGV Nominal (Líquido Base Impostos)</span>
                <span className="font-semibold text-slate-700">{formatCurrency(vgvLiquido)}</span>
              </div>

              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">Impostos (Base Nominal)</span>
                <span className="font-semibold text-slate-700">{formatCurrency(valorTotalProjetado)}</span>
              </div>

              {projectedRevenue !== null && projectedTaxesDRE !== null && (
                <div className="pt-4 border-t border-slate-200 space-y-4">
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-medium text-slate-700">Receita Líquida (DRE)</span>
                    <span className="font-bold text-slate-900">{formatCurrency(projectedRevenue)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-bold text-slate-700">Impostos Projetados (DRE)</span>
                    <span className="text-lg font-bold text-red-600">{formatCurrency(projectedTaxesDRE)}</span>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
