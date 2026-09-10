import re

# We will rewrite the entire SummaryTab.tsx with the new features.
# I will output the new file directly.

new_content = """"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { TrendingUp, DollarSign, Activity, AlertCircle, Save, Calendar, Users, EyeOff, Eye } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface SummaryTabProps {
  phaseId: number;
  userRole?: string;
}

export function SummaryTab({ phaseId, userRole }: SummaryTabProps) {
  const [data, setData] = useState<any>(null); // Current results
  const [physicalData, setPhysicalData] = useState<any>(null);
  const [datesData, setDatesData] = useState<any>(null);
  const [exchangesData, setExchangesData] = useState<any>(null);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingSnapshot, setIsSavingSnapshot] = useState(false);
  const [snapshotMessage, setSnapshotMessage] = useState("");

  const [viewMode, setViewMode] = useState<"Global" | "Empreendedor" | "Parceiro" | "Investidor">("Global");
  const [showComparisons, setShowComparisons] = useState(true);

  const fetchSnapshots = async () => {
    try {
      const res = await api.get(`/viabilities/phases/${phaseId}/snapshots`);
      setSnapshots(res.data);
    } catch (e) {
      console.error("Erro ao buscar snapshots:", e);
    }
  };

  useEffect(() => {
    const fetchResults = async () => {
      setIsLoading(true);
      try {
        const res = await api.get(`/viabilities/phases/${phaseId}/results`);
        setData(res.data);
        
        const physRes = await api.get(`/viabilities/phases/${phaseId}/physical_data`);
        setPhysicalData(physRes.data);
        
        try {
            const datesRes = await api.get(`/viabilities/phases/${phaseId}/dates`);
            setDatesData(datesRes.data);
        } catch (e) {
            console.error("No dates found");
        }
        
        try {
            const exchRes = await api.get(`/viabilities/phases/${phaseId}/exchanges`);
            setExchangesData(exchRes.data);
        } catch (e) {
            console.error("No exchanges found");
        }

      } catch (e) {
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchResults();
    fetchSnapshots();
  }, [phaseId]);

  const handleCreateSnapshot = async () => {
    setIsSavingSnapshot(true);
    setSnapshotMessage("");
    try {
      await api.post(`/viabilities/phases/${phaseId}/snapshots`, { is_baseline: true });
      setSnapshotMessage("Versão congelada com sucesso!");
      fetchSnapshots();
      setTimeout(() => setSnapshotMessage(""), 3000);
    } catch (error) {
      alert("Erro ao congelar versão.");
    } finally {
      setIsSavingSnapshot(false);
    }
  };

  if (isLoading) {
    return <div className="p-8 text-center text-slate-500">Calculando viabilidade matemática...</div>;
  }

  if (!data || !data.indicators) {
    return <div className="p-8 text-center text-red-500">Erro ao calcular resultados.</div>;
  }

  // Multiplier logic
  const getMultiplier = () => {
      if (viewMode === "Global" || !exchangesData) return 1;
      if (viewMode === "Empreendedor") return (exchangesData.perc_parceria_empreendedor || 0) / 100;
      if (viewMode === "Parceiro") return (exchangesData.perc_parceria_terrenista || 0) / 100;
      if (viewMode === "Investidor") return (exchangesData.perc_parceria_investidor || 0) / 100;
      return 1;
  };
  const multiplier = getMultiplier();

  const formatCurrency = (val: number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);
  const formatPerc = (val: number) => (val || 0).toFixed(2) + "%";
  const formatDate = (val: string) => val ? new Date(val).toLocaleDateString('pt-BR', {timeZone: 'UTC'}) : "-";
  const formatArea = (val: number) => (val || 0).toLocaleString('pt-BR', {maximumFractionDigits: 2});

  // Prepare columns (Current + Snapshots)
  let columns = [
      {
          id: "current",
          title: "CENÁRIO ATUAL",
          isCurrent: true,
          ind: data.indicators,
          phys: physicalData,
          dates: datesData,
          monthly_cashflow: data.monthly_cashflow || []
      },
      ...snapshots.map((s, idx) => ({
          id: `snap_${s.id}`,
          title: `CENÁRIO ${idx + 1} ${s.is_baseline ? '(Oficial)' : ''}`,
          isCurrent: false,
          ind: s.snapshot_data?.indicators || {},
          phys: s.snapshot_data?.physical_data || {},
          dates: s.snapshot_data?.dates || {},
          monthly_cashflow: s.snapshot_data?.monthly_cashflow || []
      }))
  ];

  if (!showComparisons) {
      columns = [columns[0]];
  }

  // Helper to get totals from cashflow for a specific column
  const getCashflowTotal = (cashflow: any[], field: string) => {
      return cashflow.reduce((acc, month) => acc + (month[field] || 0), 0) * multiplier;
  };

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b pb-4 gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Dashboard de Resultados</h2>
          <p className="text-sm text-slate-500">Comparativo de Cenários, DRE e Indicadores de Rentabilidade.</p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex bg-slate-100 p-1 rounded-lg">
              {["Global", "Empreendedor", "Parceiro", "Investidor"].map((mode) => (
                  <button
                      key={mode}
                      onClick={() => setViewMode(mode as any)}
                      className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${viewMode === mode ? 'bg-white text-ml-dark shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                  >
                      {mode}
                  </button>
              ))}
          </div>
          
          <Button 
            variant="outline" 
            onClick={() => setShowComparisons(!showComparisons)}
            className="flex items-center gap-2"
          >
              {showComparisons ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              {showComparisons ? "Ocultar Comparações" : "Comparar Cenários"}
          </Button>

          {snapshotMessage && <span className="text-sm text-green-600 font-medium">{snapshotMessage}</span>}
          {(userRole === 'ADMIN' || userRole === 'DIRETOR') && (
            <Button onClick={handleCreateSnapshot} disabled={isSavingSnapshot} className="bg-ml-dark hover:bg-slate-800 text-white flex items-center gap-2">
              <Save className="w-4 h-4" />
              {isSavingSnapshot ? "Salvando..." : "Salvar Novo Cenário"}
            </Button>
          )}
        </div>
      </div>

      <div className="overflow-x-auto pb-4">
          <table className="w-full min-w-[1000px] border-collapse text-sm">
              <thead>
                  <tr>
                      <th className="text-left py-3 px-4 font-bold text-slate-700 bg-slate-50 border-b border-slate-200 uppercase" colSpan={2}>
                          DADOS GERAIS {viewMode !== "Global" ? `(Ótica: ${viewMode})` : ""}
                      </th>
                      {columns.map(col => (
                          <th key={col.id} className={`text-right py-3 px-4 font-bold uppercase border-b border-slate-200 ${col.isCurrent ? 'bg-indigo-50 text-indigo-800' : 'bg-slate-50 text-slate-700'}`}>
                              {col.title}
                          </th>
                      ))}
                  </tr>
              </thead>
              <tbody>
                  {/* Físicos */}
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Número de Lotes</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium w-24">Unidades</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-indigo-50/30 text-indigo-900' : 'text-slate-800'}`}>
                              {((col.phys?.qtde_lotes_residenciais || 0) + (col.phys?.qtde_lotes_comerciais || 0)) * (viewMode !== "Global" ? multiplier : 1)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Área Total</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">m²</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-indigo-50/30 text-indigo-900' : 'text-slate-800'}`}>
                              {formatArea((col.phys?.area_total || 0) * (viewMode !== "Global" ? multiplier : 1))}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">VGV Líquido Projetado</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">R$</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-indigo-50/30 text-indigo-900' : 'text-slate-800'}`}>
                              {formatCurrency((col.ind?.vgv_total || 0) * multiplier)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Ticket Médio Projetado</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">R$</td>
                      {columns.map(col => {
                          const lotes = (col.phys?.qtde_lotes_residenciais || 0) + (col.phys?.qtde_lotes_comerciais || 0);
                          const vgv = col.ind?.vgv_total || 0;
                          const ticketMedio = lotes > 0 ? vgv / lotes : 0;
                          return (
                              <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-indigo-50/30 text-indigo-900' : 'text-slate-800'}`}>
                                  {formatCurrency(ticketMedio)}
                              </td>
                          );
                      })}
                  </tr>

                  {/* Datas */}
                  <tr>
                      <th className="text-left py-3 px-4 mt-6 font-bold text-slate-700 bg-slate-50 border-y border-slate-200 uppercase" colSpan={2}>
                          DATAS CHAVE
                      </th>
                      {columns.map(col => (
                          <th key={col.id} className={`py-3 px-4 border-y border-slate-200 ${col.isCurrent ? 'bg-indigo-50 text-indigo-800' : 'bg-slate-50 text-slate-700'}`}></th>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Registro (RI)</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">Data</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-indigo-50/30 text-indigo-900' : 'text-slate-800'}`}>
                              {formatDate(col.dates?.data_registro)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Lançamento</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">Data</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-indigo-50/30 text-indigo-900' : 'text-slate-800'}`}>
                              {formatDate(col.dates?.data_lancamento)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Início de Obras</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">Data</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-indigo-50/30 text-indigo-900' : 'text-slate-800'}`}>
                              {formatDate(col.dates?.data_inicio_obras)}
                          </td>
                      ))}
                  </tr>

                  {/* DRE */}
                  <tr>
                      <th className="text-left py-3 px-4 mt-6 font-bold text-red-600 bg-slate-50 border-y border-slate-200 uppercase" colSpan={2}>
                          DRE {viewMode !== "Global" ? viewMode.toUpperCase() : "EMPREENDIMENTO"}
                      </th>
                      {columns.map(col => (
                          <th key={col.id} className={`py-3 px-4 border-y border-slate-200 ${col.isCurrent ? 'bg-indigo-50 text-indigo-800' : 'bg-slate-50 text-slate-700'}`}></th>
                      ))}
                  </tr>
                  
                  {/* Receita Bruta */}
                  <tr className="bg-slate-50">
                      <td className="py-2 px-4 border-b border-slate-200 font-bold text-slate-800">RECEITA BRUTA</td>
                      <td className="py-2 px-4 border-b border-slate-200 text-slate-400 font-medium">R$</td>
                      {columns.map(col => {
                          const val = getCashflowTotal(col.monthly_cashflow, "Receitas");
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-200 text-right font-bold ${col.isCurrent ? 'bg-indigo-50 text-indigo-900' : 'text-slate-900'}`}>
                              {formatCurrency(val)}
                          </td>
                      )})}
                  </tr>

                  {/* Redutores */}
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600 font-medium">REDUTOR DE RECEITA (Impostos)</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">R$</td>
                      {columns.map(col => {
                          const val = getCashflowTotal(col.monthly_cashflow, "Impostos");
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium text-red-600 ${col.isCurrent ? 'bg-indigo-50/30' : ''}`}>
                              ({formatCurrency(val)})
                          </td>
                      )})}
                  </tr>
                  
                  {/* Receita Líquida */}
                  <tr className="bg-orange-50/50">
                      <td className="py-2 px-4 border-b border-orange-100 font-bold text-orange-800">RECEITA LÍQUIDA</td>
                      <td className="py-2 px-4 border-b border-orange-100 text-orange-400 font-medium">R$</td>
                      {columns.map(col => {
                          const rec = getCashflowTotal(col.monthly_cashflow, "Receitas");
                          const imp = getCashflowTotal(col.monthly_cashflow, "Impostos");
                          const liq = rec - imp;
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-orange-100 text-right font-bold text-orange-900 ${col.isCurrent ? 'bg-indigo-50/50' : ''}`}>
                              {formatCurrency(liq)}
                          </td>
                      )})}
                  </tr>

                  {/* Custo */}
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 font-bold text-slate-700 pt-4">CUSTO</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium pt-4">R$</td>
                      {columns.map(col => {
                          const obras = getCashflowTotal(col.monthly_cashflow, "Obras");
                          const terreno = getCashflowTotal(col.monthly_cashflow, "Terreno");
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold text-slate-800 pt-4 ${col.isCurrent ? 'bg-indigo-50/30' : ''}`}>
                              ({formatCurrency(obras + terreno)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Aquisição Área / Permuta Financeira</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = getCashflowTotal(col.monthly_cashflow, "Terreno");
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-slate-600 ${col.isCurrent ? 'bg-indigo-50/30' : ''}`}>
                              ({formatCurrency(val)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-500 pl-8">Obras de Infraestrutura</td>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = getCashflowTotal(col.monthly_cashflow, "Obras");
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-100 text-right text-slate-600 ${col.isCurrent ? 'bg-indigo-50/30' : ''}`}>
                              ({formatCurrency(val)})
                          </td>
                      )})}
                  </tr>
                  
                  {/* Margem Bruta */}
                  <tr className="bg-orange-100/50">
                      <td className="py-2 px-4 border-b border-orange-200 font-bold text-orange-900">MARGEM BRUTA</td>
                      <td className="py-2 px-4 border-b border-orange-200 text-orange-600 font-medium">R$</td>
                      {columns.map(col => {
                          const rec = getCashflowTotal(col.monthly_cashflow, "Receitas");
                          const imp = getCashflowTotal(col.monthly_cashflow, "Impostos");
                          const obras = getCashflowTotal(col.monthly_cashflow, "Obras");
                          const terreno = getCashflowTotal(col.monthly_cashflow, "Terreno");
                          const mb = (rec - imp) - (obras + terreno);
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-orange-200 text-right font-bold text-orange-900 ${col.isCurrent ? 'bg-indigo-50/50' : ''}`}>
                              {formatCurrency(mb)}
                          </td>
                      )})}
                  </tr>
                  <tr className="bg-orange-50/30">
                      <td className="py-2 px-4 border-b border-orange-100 font-medium italic text-orange-800">MARGEM BRUTA (%)</td>
                      <td className="py-2 px-4 border-b border-orange-100 text-orange-400 font-medium">%</td>
                      {columns.map(col => {
                          const rec = getCashflowTotal(col.monthly_cashflow, "Receitas");
                          const imp = getCashflowTotal(col.monthly_cashflow, "Impostos");
                          const obras = getCashflowTotal(col.monthly_cashflow, "Obras");
                          const terreno = getCashflowTotal(col.monthly_cashflow, "Terreno");
                          const liq = rec - imp;
                          const mb = liq - (obras + terreno);
                          const perc = rec > 0 ? (mb / rec) * 100 : 0;
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-orange-100 text-right font-medium italic text-orange-800 ${col.isCurrent ? 'bg-indigo-50/30' : ''}`}>
                              {formatPerc(perc)}
                          </td>
                      )})}
                  </tr>

                  {/* DV&A */}
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 font-bold text-slate-700 pt-4">DV&A (Despesas Operacionais)</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium pt-4">R$</td>
                      {columns.map(col => {
                          const desp = getCashflowTotal(col.monthly_cashflow, "Despesas");
                          const funding = getCashflowTotal(col.monthly_cashflow, "Funding");
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold text-slate-800 pt-4 ${col.isCurrent ? 'bg-indigo-50/30' : ''}`}>
                              ({formatCurrency(desp + funding)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Despesas / Marketing / Comissões</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const desp = getCashflowTotal(col.monthly_cashflow, "Despesas");
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-slate-600 ${col.isCurrent ? 'bg-indigo-50/30' : ''}`}>
                              ({formatCurrency(desp)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-500 pl-8">Funding (Juros / Estruturação)</td>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = getCashflowTotal(col.monthly_cashflow, "Funding");
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-100 text-right text-slate-600 ${col.isCurrent ? 'bg-indigo-50/30' : ''}`}>
                              ({formatCurrency(val)})
                          </td>
                      )})}
                  </tr>

                  {/* Lucro Operacional */}
                  <tr className="bg-orange-100/50">
                      <td className="py-2 px-4 border-b border-orange-200 font-bold text-orange-900">LUCRO LÍQUIDO OPERACIONAL</td>
                      <td className="py-2 px-4 border-b border-orange-200 text-orange-600 font-medium">R$</td>
                      {columns.map(col => {
                          const ll = (col.ind?.lucro_liquido || 0) * multiplier;
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-orange-200 text-right font-bold text-orange-900 ${col.isCurrent ? 'bg-indigo-50/50' : ''}`}>
                              {formatCurrency(ll)}
                          </td>
                      )})}
                  </tr>

                  {/* KPIs */}
                  <tr>
                      <th className="text-left py-3 px-4 mt-6 font-bold text-slate-700 bg-slate-50 border-y border-slate-200 uppercase" colSpan={2}>
                          INDICADORES DE RENTABILIDADE {viewMode !== "Global" ? `(${viewMode})` : ""}
                      </th>
                      {columns.map(col => (
                          <th key={col.id} className={`py-3 px-4 border-y border-slate-200 ${col.isCurrent ? 'bg-indigo-50 text-indigo-800' : 'bg-slate-50 text-slate-700'}`}></th>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">TIR MENSAL</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">% a.m.</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold ${col.isCurrent ? 'bg-indigo-50/30 text-indigo-900' : 'text-slate-900'}`}>
                              {formatPerc(col.ind?.tir_am)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">TIR ANUAL</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">% a.a.</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold ${col.isCurrent ? 'bg-indigo-50/30 text-indigo-900' : 'text-slate-900'}`}>
                              {formatPerc(col.ind?.tir_aa)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">EXPOSIÇÃO MÁXIMA DE CAIXA</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">R$</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold text-red-600 ${col.isCurrent ? 'bg-indigo-50/30' : ''}`}>
                              ({formatCurrency(Math.abs((col.ind?.exposicao_maxima || 0) * multiplier))})
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">VPL (12% a.a.)</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">R$</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold ${col.ind?.vpl >= 0 ? 'text-green-600' : 'text-red-600'} ${col.isCurrent ? 'bg-indigo-50/30' : ''}`}>
                              {formatCurrency((col.ind?.vpl || 0) * multiplier)}
                          </td>
                      ))}
                  </tr>
              </tbody>
          </table>
      </div>
    </div>
  );
}
"""

with open(r'c:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML\frontend\src\components\viabilities\SummaryTab.tsx', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("done")
