"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { TrendingUp, DollarSign, Activity, AlertCircle, Save, Calendar, Users, EyeOff, Eye, Filter, Printer, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { Modal } from "@/components/ui/Modal";
import { ReportModal } from "./ReportModal";

interface SummaryTabProps {
  phaseId: number;
  userRole?: string;
  project?: any;
}

export function SummaryTab({ phaseId, userRole, project }: SummaryTabProps) {
  const [data, setData] = useState<any>(null); // Current results
  const [physicalData, setPhysicalData] = useState<any>(null);
  const [datesData, setDatesData] = useState<any>(null);
  const [exchangesData, setExchangesData] = useState<any>(null);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [familyRawData, setFamilyRawData] = useState<any[]>([]); // Other scenarios in the family
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingSnapshot, setIsSavingSnapshot] = useState(false);
  const [snapshotMessage, setSnapshotMessage] = useState("");

  const [viewMode, setViewMode] = useState<"Global" | "Empreendedor" | "Parceiro" | "Investidor">("Global");
  const [showComparisons, setShowComparisons] = useState(true);
  const [isSelectionModalOpen, setIsSelectionModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [hiddenColIds, setHiddenColIds] = useState<string[]>([]);

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
        const physRes = await api.get(`/viabilities/phases/${phaseId}/physical_data`);
        setPhysicalData(physRes.data);
        
        let mergedData = { ...res.data };
        
        setData(mergedData);
        
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

        // Fetch sibling scenarios (other clones in the same family)
        if (project?.id) {
          try {
            const scenRes = await api.get(`/viabilities/${project.id}/scenarios`);
            const siblings = scenRes.data.filter((m: any) => m.id !== project.id);
            
            const familyResults = await Promise.all(
              siblings.map(async (member: any) => {
                try {
                  const phaseRes = await api.get(`/viabilities/${member.id}/phases`);
                  if (!phaseRes.data.length) return null;
                  const memberPhaseId = phaseRes.data[0].id;
                  const [resResult, physResult, datesResult] = await Promise.allSettled([
                    api.get(`/viabilities/phases/${memberPhaseId}/results`),
                    api.get(`/viabilities/phases/${memberPhaseId}/physical_data`),
                    api.get(`/viabilities/phases/${memberPhaseId}/dates`),
                  ]);
                  
                  let memberData = resResult.status === 'fulfilled' ? resResult.value.data : null;
                  
                  return {
                    id: member.id,
                    project_name: member.project_name,
                    data: memberData,
                    physicalData: physResult.status === 'fulfilled' ? physResult.value.data : {},
                    datesData: datesResult.status === 'fulfilled' ? datesResult.value.data : {},
                  };
                } catch (e) {
                  console.error(`Erro ao buscar dados do cenário ${member.id}`, e);
                  return null;
                }
              })
            );
            setFamilyRawData(familyResults.filter(Boolean) as any[]);
          } catch (e) {
            console.error("Erro ao buscar cenários da família", e);
          }
        }

      } catch (e) {
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchResults();
    fetchSnapshots();
  }, [phaseId, project?.id]);

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

  const handleDeleteSnapshot = async (snapshotIdStr: string) => {
    if (!(await confirmDialog("Deseja realmente excluir esta coluna do comparativo?", { variant: "danger" }))) return;
    try {
      const sId = parseInt(snapshotIdStr.replace('snap_', ''));
      await api.delete(`/viabilities/snapshots/${sId}`);
      fetchSnapshots();
    } catch (error) {
      alert("Erro ao excluir coluna do comparativo.");
    }
  };

  if (isLoading) {
    return <div className="p-8 text-center text-slate-500">Calculando viabilidade matemática...</div>;
  }

  if (!data || !data.indicators) {
    return <div className="p-8 text-center text-red-500">Erro ao calcular resultados.</div>;
  }

  const partnerNames = (data as any).indicators_parceiros ? Object.keys((data as any).indicators_parceiros) : [];
  const viewModes = partnerNames.length > 0 ? ["Global", "Empreendedor", ...partnerNames] : ["Global", "Empreendedor", "Parceiro", "Investidor"];

  // Multiplier logic
  const getMultiplier = () => {
      if (viewMode === "Global") return 1;
      
      if (viewMode === "Empreendedor" && (data as any).indicators_empreendedor) return 1;
      if (partnerNames.includes(viewMode) && (data as any).indicators_parceiros?.[viewMode]) return 1;

      // Default percentages if exchangesData is not yet saved
      const percEmpreendedor = exchangesData?.perc_parceria_empreendedor ?? 61.5;
      const percParceiro = exchangesData?.perc_parceria_terrenista ?? 38.5;
      const percInvestidor = exchangesData?.perc_parceria_investidor ?? 0.0;

      if (viewMode === "Empreendedor") return percEmpreendedor / 100;
      if (viewMode === "Parceiro") return percParceiro / 100;
      if (viewMode === "Investidor") return percInvestidor / 100;
      return 1;
  };
  const multiplier = getMultiplier();

  const getIndForMode = (sourceData: any, mode: string) => {
      if (!sourceData) return {};
      if (mode === "Global") return sourceData.indicators || {};
      if (mode === "Empreendedor" && sourceData.indicators_empreendedor) return sourceData.indicators_empreendedor;
      if (sourceData.indicators_parceiros && sourceData.indicators_parceiros[mode]) return sourceData.indicators_parceiros[mode];
      return sourceData.indicators || {};
  };

  const getCashflowForMode = (sourceData: any, mode: string) => {
      if (!sourceData) return [];
      if (mode === "Global") return sourceData.monthly_cashflow || [];
      if (mode === "Empreendedor" && sourceData.monthly_cashflow_empreendedor) return sourceData.monthly_cashflow_empreendedor;
      if (sourceData.monthly_cashflow_parceiros && sourceData.monthly_cashflow_parceiros[mode]) return sourceData.monthly_cashflow_parceiros[mode];
      return sourceData.monthly_cashflow || [];
  };

  const formatCurrency = (val: any) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(val) || 0);
  const formatPerc = (val: any) => (Number(val) || 0).toFixed(2) + "%";
  const formatDate = (val: string) => val ? new Date(val).toLocaleDateString('pt-BR', {timeZone: 'UTC'}) : "-";
  const formatArea = (val: any) => (Number(val) || 0).toLocaleString('pt-BR', {maximumFractionDigits: 2});

  // Prepare columns (Current + Family Siblings + Snapshots)
  const allColumns = [
      {
          id: "current",
          title: "CENÁRIO ATUAL",
          isCurrent: true,
          isFamily: false,
          ind: getIndForMode(data, viewMode),
          phys: physicalData,
          dates: datesData,
          monthly_cashflow: getCashflowForMode(data, viewMode)
      },
      // Family sibling scenarios (other clones)
      ...familyRawData.map((member) => ({
          id: `family_${member.id}`,
          title: member.project_name,
          isCurrent: false,
          isFamily: true,
          ind: getIndForMode(member.data, viewMode),
          phys: member.physicalData || {},
          dates: member.datesData || {},
          monthly_cashflow: getCashflowForMode(member.data, viewMode)
      })),
      // Snapshots (frozen photos)
      ...snapshots.map((s, idx) => ({
          id: `snap_${s.id}`,
          title: `FOTO ${idx + 1} ${s.is_baseline ? '(Oficial)' : ''}`,
          isCurrent: false,
          isFamily: false,
          ind: getIndForMode(s.snapshot_data, viewMode),
          phys: s.snapshot_data?.physical_data || {},
          dates: s.snapshot_data?.dates || {},
          monthly_cashflow: getCashflowForMode(s.snapshot_data, viewMode)
      }))
  ];

  let columns = allColumns;

  if (!showComparisons) {
      columns = [allColumns[0]];
  } else {
      columns = allColumns.filter(col => !hiddenColIds.includes(col.id));
  }

  // Helper to get totals from cashflow for a specific column
  const getCashflowTotal = (cashflow: any[], field: string) => {
      return cashflow.reduce((acc, month) => acc + (month[field] || 0), 0) * multiplier;
  };

  // Custo financeiro do funding na DRE: juros e taxas. Devolver o principal é caixa, não despesa.
  const custoFinanceiro = (cashflow: any[]) =>
      getCashflowTotal(cashflow, "Funding_Despesas") - getCashflowTotal(cashflow, "Funding_Amortizacao");

  return (
    <div className="p-8 print:px-8 print:pt-4 print:pb-0 print:m-0 space-y-8 print:space-y-4 animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b pb-4 print:border-none print:pb-2 gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Dashboard de Resultados</h2>
          <p className="text-sm text-slate-500">Comparativo de Cenários, DRE e Indicadores de Rentabilidade.</p>
        </div>
        <div className="flex flex-wrap items-center gap-4 print:hidden">
          <div className="flex bg-slate-100 p-1 rounded-lg">
              {viewModes.map((mode) => (
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
            onClick={() => setIsReportModalOpen(true)}
            className="flex items-center gap-2"
          >
              <Printer className="w-4 h-4" />
              Gerar Relatório
          </Button>
          
          <Button 
            variant="outline" 
            onClick={() => setShowComparisons(!showComparisons)}
            className="flex items-center gap-2"
          >
              {showComparisons ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              {showComparisons ? "Ocultar Comparações" : "Comparar Cenários"}
          </Button>

          {showComparisons && allColumns.length > 1 && (
              <Button 
                variant="outline" 
                onClick={() => setIsSelectionModalOpen(true)}
                className="flex items-center gap-2 text-ml-dark border-ml-dark/20 hover:bg-ml-dark/5"
              >
                  <Filter className="w-4 h-4" />
                  Selecionar Cenários
              </Button>
          )}

          {snapshotMessage && <span className="text-sm text-green-600 font-medium">{snapshotMessage}</span>}
          {(userRole === 'ADMIN' || userRole === 'DIRETOR') && (
            <Button onClick={handleCreateSnapshot} disabled={isSavingSnapshot} className="bg-ml-dark hover:bg-slate-800 text-white flex items-center gap-2">
              <Save className="w-4 h-4" />
              {isSavingSnapshot ? "Fixando..." : "Fixar no Comparativo (Foto)"}
            </Button>
          )}
        </div>
      </div>

      <div className="overflow-auto max-h-[calc(100vh-250px)] pb-4 print:pb-0 print:mb-0 print:overflow-visible">
          <table className="w-full min-w-[1000px] print:min-w-0 border-collapse text-sm print:text-xs">
              <thead>
                  <tr>
                      <th className="text-left py-3 px-4 font-bold text-slate-700 bg-slate-50 border-b border-slate-200 uppercase" colSpan={2}>
                      </th>
                      {columns.map(col => (
                          <th key={col.id} className={`text-right py-3 px-4 font-bold uppercase border-b border-slate-200 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/20 text-ml-dark' : 'bg-slate-50 text-slate-700'}`}>
                              <div className="flex items-center justify-end gap-2">
                                {col.title}
                                {!col.isCurrent && !(col as any).isFamily && (userRole === 'ADMIN' || userRole === 'DIRETOR') && (
                                  <button onClick={() => handleDeleteSnapshot(col.id)} className="text-slate-400 hover:text-red-500 transition-colors" title="Excluir Coluna">
                                    <X className="w-4 h-4" />
                                  </button>
                                )}
                              </div>
                          </th>
                      ))}
                  </tr>
              </thead>
              <tbody className="print:break-inside-avoid">
                  {/* Físicos */}
                  <tr>
                      <th className="text-left py-3 px-4 font-bold text-slate-700 bg-slate-50 border-b border-slate-200 uppercase" colSpan={2}>
                          DADOS GERAIS {viewMode !== "Global" ? `(Ótica: ${viewMode})` : ""}
                      </th>
                      {columns.map(col => (
                          <th key={col.id} className={`py-3 px-4 border-b border-slate-200 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/20 text-ml-dark' : 'bg-slate-50 text-slate-700'}`}></th>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Empreendimento</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium w-24">Nome</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-800'}`}>
                              {project?.project_name || "-"}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Cidade</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium w-24">Local</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-800'}`}>
                              {project?.city || "-"}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Número de Lotes</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium w-24">Unidades</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-800'}`}>
                              {((col.phys?.qtde_lotes_residenciais || 0) + (col.phys?.qtde_lotes_comerciais || 0) + (col.phys?.qtde_lotes_mistos || 0))}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Área Total</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">m²</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-800'}`}>
                              {formatArea(col.phys?.area_total || 0)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Lotes Residenciais</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">m²</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-slate-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatArea(col.phys?.area_lotes_residenciais || 0)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Lotes Comerciais</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">m²</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-slate-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatArea(col.phys?.area_lotes_comerciais || 0)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Lotes Mistos</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">m²</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-slate-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatArea(col.phys?.area_lotes_mistos || 0)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Sistema Viário</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">m²</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-slate-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatArea(col.phys?.area_sistema_viario || 0)}
                          </td>
                      ))}
                  </tr>
                  <tr>
<td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Área Institucional</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">m²</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-slate-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatArea(col.phys?.area_institucional || 0)}
                          </td>
                      ))}
                  </tr>
                  <tr>
<td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Área Verde / APP</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">m²</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-slate-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatArea(col.phys?.area_verde || 0)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Sistema de Lazer</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">m²</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-slate-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatArea(col.phys?.sistema_lazer || 0)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-500 pl-8">Associação / Não Vendável</td>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-400 text-xs">m²</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-100 text-right text-slate-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatArea(col.phys?.area_associacao || 0)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">VGV Líquido Projetado</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">R$</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-800'}`}>
                              {formatCurrency((col.ind?.vgv_total || 0) * multiplier)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Ticket Médio Projetado</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">R$</td>
                      {columns.map(col => {
                          const lotes = (col.phys?.qtde_lotes_residenciais || 0) + (col.phys?.qtde_lotes_comerciais || 0) + (col.phys?.qtde_lotes_mistos || 0);
                          const vgv = col.ind?.vgv_total || 0;
                          const ticketMedio = lotes > 0 ? (vgv * (viewMode !== "Global" ? multiplier : 1)) / lotes : 0;
                          return (
                              <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-800'}`}>
                                  {formatCurrency(ticketMedio)}
                              </td>
                          );
                      })}
                  </tr>

                  </tbody>
                  <tbody className="print:break-inside-avoid">
                  {/* Datas */}
                  <tr>
                      <th className="text-left py-3 px-4 mt-6 font-bold text-slate-700 bg-slate-50 border-y border-slate-200 uppercase" colSpan={2}>
                          DATAS CHAVE
                      </th>
                      {columns.map(col => (
                          <th key={col.id} className={`py-3 px-4 border-y border-slate-200 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/20 text-ml-dark' : 'bg-slate-50 text-slate-700'}`}></th>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Registro (RI)</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">Data</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-800'}`}>
                              {formatDate(col.dates?.data_registro)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Lançamento</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">Data</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-800'}`}>
                              {formatDate(col.dates?.data_lancamento)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-600">Início de Obras</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">Data</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-800'}`}>
                              {formatDate(col.dates?.data_inicio_obras)}
                          </td>
                      ))}
                  </tr>

                  </tbody>
                  <tbody className="print:break-inside-avoid">
                  {/* DRE */}
                  <tr>
                      <th className="text-left py-3 px-4 mt-6 font-bold text-red-600 bg-slate-50 border-y border-slate-200 uppercase" colSpan={2}>
                          DRE {viewMode !== "Global" ? viewMode.toUpperCase() : "EMPREENDIMENTO"}
                      </th>
                      {columns.map(col => (
                          <th key={col.id} className={`py-3 px-4 border-y border-slate-200 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/20 text-ml-dark' : 'bg-slate-50 text-slate-700'}`}></th>
                      ))}
                  </tr>
                  
                  {/* Receita Bruta */}
                  <tr className="bg-slate-50">
                      <td className="py-2 px-4 border-b border-slate-200 font-bold text-slate-800">RECEITA BRUTA</td>
                      <td className="py-2 px-4 border-b border-slate-200 text-slate-400 font-medium">R$</td>
                      {columns.map(col => {
                          const val = getCashflowTotal(col.monthly_cashflow, "Receitas");
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-200 text-right font-bold ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/20 text-ml-very-dark' : 'text-slate-900'}`}>
                              {formatCurrency(val)}
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Receita Vendas</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = getCashflowTotal(col.monthly_cashflow, "Receitas_Vendas");
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-slate-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatCurrency(val)}
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Receita de Juros e CM</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = getCashflowTotal(col.monthly_cashflow, "Receitas_Juros");
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-slate-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatCurrency(val)}
                          </td>
                      )})}
                  </tr>

                  {/* Redutores */}
                  <tr className="bg-slate-50">
                      <td className="py-2 px-4 border-b border-slate-100 font-bold text-slate-800">REDUTOR RECEITA</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">R$</td>
                      {columns.map(col => {
                          const pis = getCashflowTotal(col.monthly_cashflow, "Impostos_PIS");
                          const cofins = getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS");
                          const outros = getCashflowTotal(col.monthly_cashflow, "Impostos_Outros");
                          const redutor = pis + cofins + outros;
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(redutor)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-500 pl-8">PIS</td>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = getCashflowTotal(col.monthly_cashflow, "Impostos_PIS");
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-100 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-500 pl-8">COFINS</td>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS");
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-100 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-500 pl-8">Outros Impostos (Redutor)</td>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = getCashflowTotal(col.monthly_cashflow, "Impostos_Outros");
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-100 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val)})
                          </td>
                      )})}
                  </tr>
                  
                  {/* Receita Líquida */}
                  <tr className="bg-slate-100">
                      <td className="py-2 px-4 border-b border-slate-200 font-bold text-slate-800">RECEITA LÍQUIDA</td>
                      <td className="py-2 px-4 border-b border-slate-200 text-slate-400 font-medium">R$</td>
                      {columns.map(col => {
                          const rec = getCashflowTotal(col.monthly_cashflow, "Receitas");
                          const pis = getCashflowTotal(col.monthly_cashflow, "Impostos_PIS");
                          const cofins = getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS");
                          const outros = getCashflowTotal(col.monthly_cashflow, "Impostos_Outros");
                          const liq = rec - (pis + cofins + outros);
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-200 text-right font-bold text-slate-900 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/15' : ''}`}>
                              {formatCurrency(liq)}
                          </td>
                      )})}
                  </tr>

                  {/* Custo */}
                  </tbody>
                  <tbody className="print:break-inside-avoid">
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 font-bold text-slate-700 pt-4">CUSTO</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium pt-4">R$</td>
                      {columns.map(col => {
                          const obras = getCashflowTotal(col.monthly_cashflow, "Obras");
                          const terreno = getCashflowTotal(col.monthly_cashflow, "Terreno");
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold text-red-600 pt-4 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(obras + terreno)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Terreno / Permuta Financeira</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = col.ind?.valor_terreno || 0;
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val * multiplier)})
                          </td>
                      )})}</tr>
                   <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Aquisição de Área (CAPEX)</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = col.ind?.dre_obras_aquisicao ?? col.ind?.aquisicao_area ?? 0;
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val * multiplier)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-500 pl-8">Projetos</td>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = col.ind?.dre_obras_projetos ?? col.ind?.custo_projetos ?? 0;
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-100 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val * multiplier)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Obras de Infraestrutura</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = col.ind?.dre_obras_infraestrutura ?? col.ind?.custo_obras ?? 0;
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val * multiplier)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-500 pl-8">Administração da Obra</td>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = col.ind?.dre_obras_adm ?? col.ind?.adm_obras ?? 0;
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-100 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val * multiplier)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Custos Extras de Obras</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = col.ind?.dre_obras_extras ?? col.ind?.extra_constructions_total ?? 0;
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val * multiplier)})
                          </td>
                      )})}
                  </tr>
                  
                  {/* Margem Bruta */}
                  </tbody>
                  <tbody className="print:break-inside-avoid">
                  <tr className="bg-slate-100">
                      <td className="py-2 px-4 border-b border-slate-200 font-bold text-slate-900">MARGEM BRUTA</td>
                      <td className="py-2 px-4 border-b border-slate-200 text-slate-400 font-medium">R$</td>
                      {columns.map(col => {
                          const rec = getCashflowTotal(col.monthly_cashflow, "Receitas");
                          const pis = getCashflowTotal(col.monthly_cashflow, "Impostos_PIS");
                          const cofins = getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS");
                          const outros = getCashflowTotal(col.monthly_cashflow, "Impostos_Outros");
                          const obras = getCashflowTotal(col.monthly_cashflow, "Obras");
                          const terreno = getCashflowTotal(col.monthly_cashflow, "Terreno");
                          const liq = rec - (pis + cofins + outros);
                          const mb = liq - (obras + terreno);
                          return (
                           <td key={col.id} className={`py-2 px-4 border-b border-slate-200 text-right font-bold text-slate-900 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/15' : ''}`}>
                              {formatCurrency(mb)}
                          </td>
                      )})}
                  </tr>
                  <tr className="bg-slate-50">
                       <td className="py-2 px-4 border-b border-slate-200 font-medium italic text-slate-800">MARGEM BRUTA (%)</td>
                       <td className="py-2 px-4 border-b border-slate-200 text-slate-400 font-medium">% RL</td>
                       {columns.map(col => {
                           const rec = getCashflowTotal(col.monthly_cashflow, "Receitas");
                           const pis = getCashflowTotal(col.monthly_cashflow, "Impostos_PIS");
                           const cofins = getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS");
                           const outros = getCashflowTotal(col.monthly_cashflow, "Impostos_Outros");
                           const obras = getCashflowTotal(col.monthly_cashflow, "Obras");
                           const terreno = getCashflowTotal(col.monthly_cashflow, "Terreno");
                           const liq = rec - (pis + cofins + outros);
                           const mb = liq - (obras + terreno);
                           const perc = liq > 0 ? (mb / liq) * 100 : 0;
                           return (
                           <td key={col.id} className={`py-2 px-4 border-b border-slate-200 text-right font-medium italic text-slate-800 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                               {formatPerc(perc)}
                           </td>
                       )})}
                   </tr>

                  {/* DV&A */}
                  </tbody>
                  <tbody className="print:break-inside-avoid">
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 font-bold text-slate-700 pt-4">DV&A (Despesas Operacionais)</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium pt-4">R$</td>
                      {columns.map(col => {
                          const desp = getCashflowTotal(col.monthly_cashflow, "Despesas");
                          const funding = custoFinanceiro(col.monthly_cashflow);
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold text-red-600 pt-4 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(desp + funding)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Marketing</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = col.ind?.marketing || 0;
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val * multiplier)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-500 pl-8">Comercial</td>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = (col.ind?.comercial || 0);
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-100 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val * multiplier)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Administrativas</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = col.ind?.adm_despesas || 0;
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val * multiplier)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-500 pl-8">Despesas Extras</td>
                      <td className="py-1 px-4 border-b border-slate-100 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = col.ind?.extra_expenses_total || 0;
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-100 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val * multiplier)})
                          </td>
                      )})}
                  </tr>
                  <tr>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-500 pl-8">Funding (Juros / Estruturação)</td>
                      <td className="py-1 px-4 border-b border-slate-50 text-slate-400 text-xs">R$</td>
                      {columns.map(col => {
                          const val = custoFinanceiro(col.monthly_cashflow);
                          return (
                          <td key={col.id} className={`py-1 px-4 border-b border-slate-50 text-right text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(val * multiplier)})
                          </td>
                      )})}
                  </tr>

                  {/* Lucro Operacional */}
                  </tbody>
                  <tbody className="print:break-inside-avoid">
                  <tr className="bg-slate-100">
                      <td className="py-2 px-4 border-b border-slate-200 font-bold text-slate-900">LUCRO OPERACIONAL</td>
                      <td className="py-2 px-4 border-b border-slate-200 text-slate-400 font-medium">R$</td>
                      {columns.map(col => {
                          const rec = getCashflowTotal(col.monthly_cashflow, "Receitas");
                          const pis = getCashflowTotal(col.monthly_cashflow, "Impostos_PIS");
                          const cofins = getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS");
                          const outros = getCashflowTotal(col.monthly_cashflow, "Impostos_Outros");
                          const obras = getCashflowTotal(col.monthly_cashflow, "Obras");
                          const terreno = getCashflowTotal(col.monthly_cashflow, "Terreno");
                          const desp = getCashflowTotal(col.monthly_cashflow, "Despesas");
                          const funding = custoFinanceiro(col.monthly_cashflow);
                          
                          const liq = rec - (pis + cofins + outros);
                          const mb = liq - (obras + terreno);
                          const lo = mb - (desp + funding);
                          
                          return (
                           <td key={col.id} className={`py-2 px-4 border-b border-slate-200 text-right font-bold text-slate-900 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/15' : ''}`}>
                              {formatCurrency(lo)}
                          </td>
                      )})}
                  </tr>
                  <tr className="bg-slate-50">
                       <td className="py-2 px-4 border-b border-slate-200 font-medium italic text-slate-800">LUCRO OPERACIONAL (%)</td>
                       <td className="py-2 px-4 border-b border-slate-200 text-slate-400 font-medium">% RL</td>
                       {columns.map(col => {
                           const rec = getCashflowTotal(col.monthly_cashflow, "Receitas");
                           const pis = getCashflowTotal(col.monthly_cashflow, "Impostos_PIS");
                           const cofins = getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS");
                           const outros = getCashflowTotal(col.monthly_cashflow, "Impostos_Outros");
                           const obras = getCashflowTotal(col.monthly_cashflow, "Obras");
                           const terreno = getCashflowTotal(col.monthly_cashflow, "Terreno");
                           const desp = getCashflowTotal(col.monthly_cashflow, "Despesas");
                           const funding = custoFinanceiro(col.monthly_cashflow);
                           
                           const liq = rec - (pis + cofins + outros);
                           const mb = liq - (obras + terreno);
                           const lo = mb - (desp + funding);
                           const perc = liq > 0 ? (lo / liq) * 100 : 0;
                           return (
                            <td key={col.id} className={`py-2 px-4 border-b border-slate-200 text-right font-medium italic text-slate-800 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                               {formatPerc(perc)}
                           </td>
                       )})}
                   </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 font-bold text-slate-700 pt-4">IRPJ / CSLL</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium pt-4">R$</td>
                      {columns.map(col => {
                          const irpj_csll = getCashflowTotal(col.monthly_cashflow, "Impostos_IRPJ_CSLL");
                          return (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold text-red-600 pt-4 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(irpj_csll)})
                          </td>
                      )})}
                  </tr>
                  <tr className="bg-slate-100">
                      <td className="py-2 px-4 border-b border-slate-200 font-bold text-slate-900 pt-4">LUCRO LÍQUIDO</td>
                      <td className="py-2 px-4 border-b border-slate-200 text-slate-400 font-medium pt-4">R$</td>
                      {columns.map(col => {
                          const rec = getCashflowTotal(col.monthly_cashflow, "Receitas");
                          const imp = getCashflowTotal(col.monthly_cashflow, "Impostos"); // All taxes
                          const obras = getCashflowTotal(col.monthly_cashflow, "Obras");
                          const terreno = getCashflowTotal(col.monthly_cashflow, "Terreno");
                          const desp = getCashflowTotal(col.monthly_cashflow, "Despesas");
                          const funding = custoFinanceiro(col.monthly_cashflow);
                          
                          const ll = rec - imp - obras - terreno - desp - funding;
                          
                          return (
                           <td key={col.id} className={`py-2 px-4 border-b border-slate-200 text-right font-bold text-slate-900 pt-4 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/15' : ''}`}>
                              {formatCurrency(ll)}
                          </td>
                      )})}
                  </tr>
                  <tr className="bg-slate-50">
                      <td className="py-2 px-4 border-b border-slate-200 font-medium italic text-slate-800">LUCRO LÍQUIDO (%)</td>
                      <td className="py-2 px-4 border-b border-slate-200 text-slate-400 font-medium">% RL</td>
                      {columns.map(col => {
                          const rec = getCashflowTotal(col.monthly_cashflow, "Receitas");
                          const pis = getCashflowTotal(col.monthly_cashflow, "Impostos_PIS");
                          const cofins = getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS");
                          const outros = getCashflowTotal(col.monthly_cashflow, "Impostos_Outros");
                          
                          const imp = getCashflowTotal(col.monthly_cashflow, "Impostos");
                          const obras = getCashflowTotal(col.monthly_cashflow, "Obras");
                          const terreno = getCashflowTotal(col.monthly_cashflow, "Terreno");
                          const desp = getCashflowTotal(col.monthly_cashflow, "Despesas");
                          const funding = custoFinanceiro(col.monthly_cashflow);
                          
                          const ll = rec - imp - obras - terreno - desp - funding;
                          const liq = rec - (pis + cofins + outros);
                          const perc = liq > 0 ? (ll / liq) * 100 : 0;
                          return (
                           <td key={col.id} className={`py-2 px-4 border-b border-slate-200 text-right font-medium italic text-slate-800 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatPerc(perc)}
                          </td>
                      )})}
                  </tr>

                  </tbody>
                  <tbody className="print:break-inside-avoid">
                  {/* KPIs */}
                  <tr>
                      <th className="text-left py-3 px-4 mt-6 font-bold text-slate-700 bg-slate-50 border-y border-slate-200 uppercase" colSpan={2}>
                          INDICADORES DE RENTABILIDADE {viewMode !== "Global" ? `(${viewMode})` : ""}
                      </th>
                      {columns.map(col => (
                          <th key={col.id} className={`py-3 px-4 border-y border-slate-200 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/20 text-ml-dark' : 'bg-slate-50 text-slate-700'}`}></th>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">MTIR</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">% a.m.</td>
                      {columns.map(col => (
                           <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {formatPerc(col.ind?.mtir_am)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">MTIR ANUAL</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">% a.a.</td>
                      {columns.map(col => (
                           <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {formatPerc(col.ind?.mtir_aa)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">TIR MENSAL</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">% a.m.</td>
                      {columns.map(col => (
                           <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {formatPerc(col.ind?.tir_am)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">TIR ANUAL</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">% a.a.</td>
                      {columns.map(col => (
                           <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {formatPerc(col.ind?.tir_aa)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">EXPOSIÇÃO MÁXIMA CAIXA</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">R$</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold text-red-600 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              ({formatCurrency(Math.abs((col.ind?.exposicao_maxima || 0) * multiplier))})
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">EXPOSIÇÃO CAIXA / INVESTIMENTO</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">%</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {formatPerc(col.ind?.expo_inv)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">EXPOSIÇÃO CAIXA / VGV</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">%</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {formatPerc(col.ind?.expo_vgv)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <th className="text-left py-3 px-4 mt-6 font-bold text-slate-700 bg-slate-50 border-y border-slate-200 uppercase" colSpan={2}>
                          RENTABILIDADE
                      </th>
                      {columns.map(col => (
                          <th key={col.id} className={`py-3 px-4 border-y border-slate-200 ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/20 text-ml-dark' : 'bg-slate-50 text-slate-700'}`}></th>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">(INVESTIMENTO/RETORNO) SEM JUROS</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">%</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {formatPerc(col.ind?.retorno_sem_juros)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">(INVESTIMENTO/RETORNO) COM JUROS</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">%</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {formatPerc(col.ind?.retorno_com_juros)}
                          </td>
                      ))}
                  </tr>

                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">PERÍODO</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">Mês</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {col.ind?.periodo_exposicao || 0}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">Payback</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">Mês</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {col.ind?.payback != null ? Math.round(Number(col.ind.payback)) : 'N/A'}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">VIDA</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">Meses</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {col.ind?.vida || 0}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">ANOS</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">Anos</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${((col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10 text-ml-very-dark' : (col as any).isFamily ? 'bg-blue-50/50 text-ml-very-dark' : 'text-slate-900')}`}>
                              {col.ind?.vida ? Math.round(col.ind.vida / 12) : 0}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">VPL ({data.indicators?.tma_aa ? (data.indicators.tma_aa).toFixed(1) : 12}% a.a.)</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">R$</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-bold ${col.ind?.vpl >= 0 ? 'text-green-600' : 'text-red-600'} ${(col.isCurrent || (col as any).isFamily) ? 'bg-ml-green/10' : ''}`}>
                              {formatCurrency((col.ind?.vpl || 0) * multiplier)}
                          </td>
                      ))}
                  </tr>
              </tbody>
          </table>
      </div>

      <Modal isOpen={isSelectionModalOpen} onClose={() => setIsSelectionModalOpen(false)} title="Selecionar Cenários">
          <div className="space-y-4">
              <p className="text-sm text-slate-500">
                  Selecione quais cenários vocêê deseja visualizar na tabela de comparação:
              </p>
              <div className="flex flex-col gap-2 max-h-[60vh] overflow-y-auto pr-2">
                  {allColumns.map(col => (
                      <label 
                          key={col.id} 
                          className="flex items-center gap-3 cursor-pointer p-3 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
                      >
                          <input 
                              type="checkbox" 
                              checked={!hiddenColIds.includes(col.id)}
                              onChange={(e) => {
                                  if (e.target.checked) {
                                      setHiddenColIds(prev => prev.filter(id => id !== col.id));
                                  } else {
                                      setHiddenColIds(prev => [...prev, col.id]);
                                  }
                              }}
                              className="w-4 h-4 rounded text-ml-green focus:ring-ml-green"
                          />
                          <span className={`text-sm font-medium ${col.isCurrent ? 'text-ml-dark' : 'text-slate-700'}`}>
                              {col.title}
                          </span>
                      </label>
                  ))}
              </div>
              <div className="flex justify-end pt-4 border-t border-slate-100">
                  <Button onClick={() => setIsSelectionModalOpen(false)} className="bg-ml-dark text-white hover:bg-slate-800 px-6">
                      Concluir
                  </Button>
              </div>
          </div>
      </Modal>

      <ReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        project={project}
        physicalData={physicalData}
        datesData={datesData}
        allColumns={columns.map(c => ({...c, rawData: c.isFamily ? familyRawData.find(f => `family_${f.id}` === c.id)?.data : (c.isCurrent ? data : snapshots.find(s => `snap_${s.id}` === c.id)?.snapshot_data)}))}
        exchangesData={exchangesData}
      />
    </div>
  );
}
