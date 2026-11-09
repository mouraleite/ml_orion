"use client";

import React, { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, ComposedChart, Line } from "recharts";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { calculateAISimilarity } from '@/lib/similarity';

interface ViabilityReportProps {
  project: any;
  physicalData: any;
  datesData: any;
  allColumns: any[]; // Cenários/Snapshots selecionados para comparativo
  viewsToPrint: string[]; // ["Global", "Empreendedor", "ParceiroX"]
  cashflowGranularity: "month" | "quarter" | "semester" | "year";
  includeCashflow: boolean;
  includeComparative: boolean;
  includeSchedule: boolean;
  exchangesData: any; // Para taxas de parceria se necessário
  orientation?: "portrait" | "landscape";
}

// Helper para formatar moeda
const formatCurrency = (val: any) => (Number(val) || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const formatNumber = (val: any) => (Number(val) || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const formatPerc = (val: any) => (Number(val) || 0).toFixed(2) + "%";
const formatDate = (val: string) => val ? new Date(val).toLocaleDateString('pt-BR', { timeZone: 'UTC' }) : "-";
const formatArea = (val: any) => (Number(val) || 0).toLocaleString('pt-BR', { maximumFractionDigits: 2 });

// Função para agrupar o cashflow
const groupCashflow = (data: any[], granularity: string) => {
  if (!data || data.length === 0) return [];

  // Simplificação para este exemplo: agregando por N meses
  let groupSize = 1;
  if (granularity === "quarter") groupSize = 3;
  if (granularity === "semester") groupSize = 6;
  if (granularity === "year") groupSize = 12;

  if (groupSize === 1) {
    return data.map(d => ({
      period: `Mês ${d.Mes}`,
      receitas: d.Receitas || 0,
      saidas: (d.Obras || 0) + (d.Despesas || 0) + (d.Terreno || 0) + (d.Impostos || 0) + (d.Funding_Despesas || 0),
      liquido: d.Caixa_Liquido || 0,
      acumulado: d.Caixa_Acumulado || 0,
      ...d
    }));
  }

  const grouped = [];
  for (let i = 0; i < data.length; i += groupSize) {
    const chunk = data.slice(i, i + groupSize);
    const receitas = chunk.reduce((sum, d) => sum + (d.Receitas || 0), 0);
    const saidas = chunk.reduce((sum, d) => sum + ((d.Obras || 0) + (d.Despesas || 0) + (d.Terreno || 0) + (d.Impostos || 0) + (d.Funding_Despesas || 0)), 0);
    const liquido = chunk.reduce((sum, d) => sum + (d.Caixa_Liquido || 0), 0);
    const acumulado = chunk[chunk.length - 1]?.Caixa_Acumulado || 0;

    let label = `Período ${Math.floor(i / groupSize) + 1}`;
    if (granularity === "year") label = `Ano ${Math.floor(i / 12) + 1}`;
    if (granularity === "quarter") label = `Tri ${Math.floor(i / 3) + 1}`;
    if (granularity === "semester") label = `Sem ${Math.floor(i / 6) + 1}`;

    const sumField = (field: string) => chunk.reduce((sum, d) => sum + (d[field] || 0), 0);

    grouped.push({
      period: label,
      receitas,
      saidas,
      liquido,
      acumulado,
      Receitas_Entrada: sumField("Receitas_Entrada"),
      Receitas_Parcelas: sumField("Receitas_Parcelas"),
      Receitas_Juros: sumField("Receitas_Juros"),
      Receitas: sumField("Receitas"),
      Impostos: sumField("Impostos"),
      Obras: sumField("Obras"),
      Obras_Proj: sumField("Obras_Proj"),
      Funding_Despesas: sumField("Funding_Despesas"),
      Despesas_Mkt: sumField("Despesas_Mkt"),
      Despesas_Com: sumField("Despesas_Com"),
      Despesas_Adm: sumField("Despesas_Adm"),
      Caixa_Liquido: sumField("Caixa_Liquido"),
      Caixa_Acumulado: acumulado
    });
  }
  return grouped;
};

const markdownComponents = {
  table: ({node, ...props}: any) => <div className="overflow-x-auto my-6"><table className="min-w-full divide-y divide-slate-200 border border-slate-200 shadow-sm rounded-lg" {...props} /></div>,
  thead: ({node, ...props}: any) => <thead className="bg-slate-50" {...props} />,
  th: ({node, ...props}: any) => <th className="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wider border-b border-slate-200" {...props} />,
  td: ({node, ...props}: any) => <td className="px-4 py-3 text-sm text-slate-700 border-b border-slate-100" {...props} />,
  h1: ({node, ...props}: any) => <h1 className="text-2xl font-bold text-slate-800 mt-6 mb-4" {...props} />,
  h2: ({node, ...props}: any) => <h2 className="text-xl font-bold text-slate-800 mt-6 mb-3" {...props} />,
  h3: ({node, ...props}: any) => <h3 className="text-lg font-bold text-slate-800 mt-5 mb-2" {...props} />,
  p: ({node, ...props}: any) => <p className="text-slate-600 mb-3 leading-relaxed" {...props} />,
  ul: ({node, ...props}: any) => <ul className="list-disc pl-5 mb-4 text-slate-600 space-y-1" {...props} />,
  ol: ({node, ...props}: any) => <ol className="list-decimal pl-5 mb-4 text-slate-600 space-y-1" {...props} />,
  li: ({node, ...props}: any) => <li className="" {...props} />,
  strong: ({node, ...props}: any) => <strong className="font-bold text-slate-800" {...props} />,
  blockquote: ({node, ...props}: any) => <blockquote className="border-l-4 border-emerald-500 pl-4 italic text-slate-500 my-4 bg-slate-50 py-2 rounded-r" {...props} />
};

export const ViabilityReport: React.FC<ViabilityReportProps> = ({
  project,
  physicalData,
  datesData,
  allColumns,
  viewsToPrint,
  cashflowGranularity,
  includeCashflow,
  includeComparative,
  includeSchedule,
  exchangesData,
  orientation = "portrait"
}) => {

  const dataAtual = new Date().toLocaleDateString('pt-BR');

  // Multiplier function is same as SummaryTab
  const getMultiplier = (viewMode: string, sourceData: any) => {
    if (viewMode === "Global") return 1;
    if (viewMode === "Empreendedor" && sourceData?.indicators_empreendedor) return 1;
    if (sourceData?.indicators_parceiros?.[viewMode]) return 1;
    const percEmpreendedor = exchangesData?.perc_parceria_empreendedor ?? 61.5;
    const percParceiro = exchangesData?.perc_parceria_terrenista ?? 38.5;
    if (viewMode === "Empreendedor") return percEmpreendedor / 100;
    if (viewMode === "Parceiro" || viewMode === "Terrenista") return percParceiro / 100;
    return 1;
  };

  const getCashflowTotal = (cashflow: any[], field: string, multiplier: number = 1) => {
    if (!cashflow) return 0;
    return cashflow.reduce((acc, month) => acc + (month[field] || 0), 0) * multiplier;
  };

  // Custo financeiro do funding na DRE: juros e taxas. Devolver o principal é caixa, não despesa.
  const custoFinanceiro = (cashflow: any[], multiplier: number = 1) =>
    getCashflowTotal(cashflow, "Funding_Despesas", multiplier) - getCashflowTotal(cashflow, "Funding_Amortizacao", multiplier);

  // Renomear dinamicamente os cenários para numeração romana (I, II, III) cronológica
  const renamedColumns = useMemo(() => {
    const currentCols = allColumns.filter(c => c.isCurrent);
    const snapshotCols = allColumns.filter(c => !c.isCurrent);
    snapshotCols.sort((a, b) => {
      const dateA = a.rawData?.created_at ? new Date(a.rawData.created_at).getTime() : 0;
      const dateB = b.rawData?.created_at ? new Date(b.rawData.created_at).getTime() : 0;
      return dateA - dateB;
    });
    const romanNumerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
    return [...currentCols, ...snapshotCols].map((col, idx) => {
      const numeral = romanNumerals[idx] || (idx + 1).toString();
      return {
        ...col,
        title: col.isCurrent ? `CENÁRIO I` : `CENÁRIO ${numeral}`
      };
    });
  }, [allColumns]);

  // Pré-calcular todos os totais de cashflow por coluna para evitar reduce() repetido no JSX
  const colTotals = useMemo(() => {
    return renamedColumns.map(col => {
      const cf = col.monthly_cashflow || [];
      const sum = (field: string) => cf.reduce((acc: number, m: any) => acc + (m[field] || 0), 0);
      return {
        colId: col.id,
        Receitas: sum('Receitas'),
        Receitas_Vendas: sum('Receitas_Vendas'),
        Receitas_Juros: sum('Receitas_Juros'),
        Receitas_Entrada: sum('Receitas_Entrada'),
        Receitas_Parcelas: sum('Receitas_Parcelas'),
        Impostos: sum('Impostos'),
        Impostos_PIS: sum('Impostos_PIS'),
        Impostos_COFINS: sum('Impostos_COFINS'),
        Impostos_IRPJ_CSLL: sum('Impostos_IRPJ_CSLL'),
        Impostos_Outros: sum('Impostos_Outros'),
        Obras: sum('Obras'),
        Obras_Proj: sum('Obras_Proj'),
        Terreno: sum('Terreno'),
        Despesas: sum('Despesas'),
        Despesas_Mkt: sum('Despesas_Mkt'),
        Despesas_Com: sum('Despesas_Com'),
        Despesas_Adm: sum('Despesas_Adm'),
        Funding_Despesas: sum('Funding_Despesas'),
      };
    });
  }, [renamedColumns]);

  // Pré-calcular cashflows agrupados para cada coluna (evita groupCashflow() a cada render)
  const allGroupedCashflows = useMemo(() => {
    return renamedColumns.map(col => groupCashflow(col.monthly_cashflow || [], cashflowGranularity));
  }, [renamedColumns, cashflowGranularity]);

  const maxPeriods = useMemo(() => {
    return Math.max(...allGroupedCashflows.map(gc => gc.length), 0);
  }, [allGroupedCashflows]);

  return (
    <div className={`bg-slate-100 py-10 min-h-screen text-slate-900 font-sans print:bg-white print:py-0 print:min-h-0 ${orientation === 'landscape' ? 'is-landscape' : 'is-portrait'}`}>

      {/* Estilos específicos para impressão */}
      <style dangerouslySetInnerHTML={{
        __html: `
        /* === SCREEN: TODAS as .page-break parecem folhas A4 físicas === */
        @media screen {
          div.page-break {
            display: block;
            width: ${orientation === 'landscape' ? '297mm' : '210mm'};
            min-height: ${orientation === 'landscape' ? '210mm' : '297mm'};
            margin: 0 auto 24px auto;
            background: white;
            box-shadow: 0 4px 24px rgba(0,0,0,0.18), 0 1px 4px rgba(0,0,0,0.10);
            box-sizing: border-box;
            position: relative;
          }
          table.page-break {
            display: table;
            width: ${orientation === 'landscape' ? '297mm' : '210mm'};
            margin: 0 auto 24px auto;
            background: white;
            box-shadow: 0 4px 24px rgba(0,0,0,0.18), 0 1px 4px rgba(0,0,0,0.10);
            box-sizing: border-box;
            position: relative;
          }
        }

        /* === PRINT: cada .page-break = exatamente uma página === */
        @media print {
          @page {
            margin: 0;
            size: A4 ${orientation};
          }
          body {
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
            background: white;
          }
          /* Divs de seção: cada uma ocupa uma página */
          div.page-break {
            display: block;
            width: 100%;
            min-height: auto;
            max-height: none;
            overflow: visible;
            box-shadow: none !important;
            margin: 0;
            position: relative;
            /* Força quebra de página ANTES de cada seção */
            break-before: page;
            page-break-before: always;
            break-after: auto;
            page-break-after: auto;
          }
          /* Tables de seção (Premissas etc.): break antes mas sem resetar padding */
          table.page-break {
            break-before: page;
            page-break-before: always;
            width: 100%;
            position: relative;
          }
          /* Primeira seção de cada view não precisa de break-before */
          .first-page-section {
            break-before: auto !important;
            page-break-before: auto !important;
          }
          .no-break { page-break-inside: avoid; break-inside: avoid; }
          .shadow-sm, .shadow, .shadow-md, .shadow-lg {
            box-shadow: none !important;
            border: 1px solid #e2e8f0 !important;
          }
        }

        /* === AJUSTES DE ESCALA PARA PAISAGEM (PRINT E SCREEN) === */
        .is-landscape table { font-size: 0.65rem !important; }
        .is-landscape th, .is-landscape td { padding-top: 0.15rem !important; padding-bottom: 0.15rem !important; }
        .is-landscape h1 { font-size: 1.5rem !important; margin-bottom: 0.5rem !important; }
        .is-landscape h2 { font-size: 1.1rem !important; margin-bottom: 0.5rem !important; }
        .is-landscape h3 { font-size: 0.85rem !important; margin-bottom: 0.25rem !important; }
        .is-landscape .page-break { padding-top: 1rem !important; padding-bottom: 0.5rem !important; }
        .is-landscape .mb-8 { margin-bottom: 0.75rem !important; }
        .is-landscape .mt-8 { margin-top: 0.5rem !important; }
        .is-landscape .pb-4 { padding-bottom: 0.25rem !important; }
        .is-landscape .pt-12 { padding-top: 1rem !important; }
        .is-landscape .pb-6 { padding-bottom: 0.5rem !important; }
      `}} />

      {viewsToPrint.map((viewMode, viewIndex) => {
        // Encontrar a coluna 'atual' para extrair os dados base
        const currentDataCol = renamedColumns.find(c => c.isCurrent) || renamedColumns[0];
        const multiplier = getMultiplier(viewMode, currentDataCol?.rawData);
        const ind = currentDataCol?.ind || {};
        // allGroupedCashflows, maxPeriods já computados via useMemo acima
        const groupedCashflow = allGroupedCashflows[renamedColumns.findIndex(c => c.id === currentDataCol?.id)] || [];

        return (
          <div key={`view-${viewMode}`}>

            {/* 1. CAPA */}
            <div
              className={`page-break ${viewIndex === 0 ? 'first-page-section' : ''} flex flex-col items-center justify-start text-center relative print:overflow-hidden`}
              style={{ height: orientation === 'landscape' ? '210mm' : '297mm' }}
            >
              {/* Background da Capa - Imagem de Paisagem em Tela Cheia */}
              <div className="absolute inset-0 z-0 bg-center bg-cover" style={{ backgroundImage: 'url(/Fundo.jpg)' }}></div>

              {/* Overlay gradiente suave para garantir leitura do texto e da nova descrição */}
              <div className="absolute inset-0 z-0 bg-white/40"></div>
              <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-white/90 via-white/50 to-white/90 z-0"></div>

              {/* Grafismos removidos a pedido */}

              {/* Conteúdo Centralizado */}
              <div className="relative z-10 pt-20 px-16 flex flex-col items-center w-full h-full pb-16">
                <img src="/logo-moura-leite.png" alt="Logo Moura Leite" className="h-28 w-auto mb-10" />

                <h1 className="text-5xl font-extrabold text-[#1a502e] tracking-tight mb-2 uppercase drop-shadow-md">ANÁLISE DE VIABILIDADE</h1>
                <h1 className="text-5xl font-extrabold text-[#1a502e] tracking-tight mb-12 uppercase drop-shadow-md">ECONÔMICO-FINANCEIRA</h1>

                <h3 className="text-2xl font-bold text-slate-900 mb-4 uppercase drop-shadow-md">
                  PROJETO: {project?.project_name || "[NOME DO EMPREENDIMENTO/LOTEAMENTO]"}
                </h3>
                <h3 className="text-xl font-bold text-slate-900 uppercase drop-shadow-md mb-2">
                  LOCALIZAÇÃO: {project?.city || "[CIDADE, ESTADO]"}
                </h3>
                <h3 className="text-xl font-bold text-slate-900 uppercase drop-shadow-md mb-2">
                  DATA: {dataAtual}
                </h3>
                <h3 className="text-xl font-bold text-slate-900 uppercase drop-shadow-md mb-auto">
                  VISÃO: {viewMode === 'Global' ? 'GLOBAL' : viewMode.toUpperCase()}
                </h3>

                {/* Texto descritivo final da capa */}
                <div className="mt-12 text-sm text-slate-800 font-medium text-justify max-w-4xl leading-relaxed drop-shadow-md bg-white/60 p-6 rounded-xl backdrop-blur-sm border border-white/50">
                  <p className="mb-4">
                    A análise a seguir tem o objetivo de apoiar a avaliação, pertinência e o potencial de sucesso.
                    No contexto atual, não consideramos nenhuma estrutura de financiamento do projeto em nenhuma etapa, utilizando, portanto, recursos próprios.
                  </p>
                  <p>
                    Entre os principais indicadores a serem analisados, destacam-se a Taxa Interna de Retorno (TIR) e o Payback, sinalizando rentabilidade e o tempo necessário para que o projeto gere retorno sobre o investimento e exposição máxima de caixa, a fim de mitigar risco quanto à otimização dos recursos.
                  </p>
                </div>
              </div>
            </div>

            {/* 1.5 PARECER EXECUTIVO (Opcional) */}
            {project?.parecer_executivo && (
              <div className={`page-break px-12 pt-12 pb-6 print:px-8 print:pt-6 print:pb-2 relative ${orientation === 'landscape' ? 'min-h-[180mm]' : 'min-h-[267mm]'}`}>
                {/* Header fixo das páginas internas */}
                <div className="flex justify-between items-center border-b-2 border-ml-green pb-4 mb-8">
                  <img src="/logo-moura-leite.png" alt="Logo" className="h-10 w-auto" />
                  <div className="text-right">
                    <p className="font-bold text-ml-dark">{project?.project_name}</p>
                    <p className="text-sm text-slate-500">Visão: {viewMode}</p>
                  </div>
                </div>

                <h1 className="text-3xl font-extrabold text-[#1a502e] tracking-tight mb-6 uppercase">ANÁLISE CRÍTICA E SUGESTÕES DE MELHORIA</h1>
                <h2 className="text-xl font-bold text-orange-500 mb-8">Estudo de Viabilidade de Novas Áreas — {project?.city || project?.project_name}</h2>

                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {project.parecer_executivo}
                </ReactMarkdown>

                {project.parecer_original_ia && (
                  <div className="mt-8 pt-4 border-t border-slate-200 text-sm italic text-slate-500">
                    <p>Nota: {calculateAISimilarity(project.parecer_original_ia, project.parecer_executivo)}% deste parecer foi gerado originalmente por Inteligência Artificial.</p>
                  </div>
                )}
              </div>
            )}

            {/* 2. DADOS FÍSICOS E KPIs */}
            <div className="page-break p-12 print:p-0 relative">
              <table className="w-full relative">
              <thead className="table-header-group">
                <tr>
                  <td className="px-12 pt-12 print:px-8 print:pt-6">
                    {/* Header fixo das páginas internas */}
                    <div className="flex justify-between items-center border-b-2 border-ml-green pb-4 mb-8">
                      <img src="/logo-moura-leite.png" alt="Logo" className="h-10 w-auto" />
                      <div className="text-right">
                        <p className="font-bold text-ml-dark">{project?.project_name}</p>
                        <p className="text-sm text-slate-500">Visão: {viewMode}</p>
                      </div>
                    </div>
                  </td>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="px-12 pb-6 print:px-8 print:pb-2">
                    {/* DADOS FÍSICOS E DATAS */}
                    <div className="grid grid-cols-2 gap-8 print:break-inside-avoid">
                      <div>
                        <h2 className="text-xl font-bold text-ml-dark mb-4 border-b pb-2">Ficha Técnica</h2>
                        <table className="w-full text-sm">
                          <tbody>
                            <tr className="border-b border-slate-100">
                              <td className="py-2 text-slate-600">Área Total</td>
                              <td className="py-2 text-right font-semibold">{formatArea(physicalData?.area_total)} m²</td>
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="py-2 text-slate-600">Total de Lotes</td>
                              <td className="py-2 text-right font-semibold">
                                {(physicalData?.qtde_lotes_residenciais || 0) + (physicalData?.qtde_lotes_comerciais || 0) + (physicalData?.qtde_lotes_mistos || 0)}
                              </td>
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="py-2 text-slate-600">Ticket Médio</td>
                              <td className="py-2 text-right font-semibold">
                                {(() => {
                                  const lotes = (physicalData?.qtde_lotes_residenciais || 0) + (physicalData?.qtde_lotes_comerciais || 0) + (physicalData?.qtde_lotes_mistos || 0);
                                  const vgvBase = ((physicalData?.area_lotes_residenciais || 0) * (physicalData?.valor_venda_residencial_m2 || 0)) +
                                    ((physicalData?.area_lotes_comerciais || 0) * (physicalData?.valor_venda_comercial_m2 || 0)) +
                                    ((physicalData?.area_lotes_mistos || 0) * (physicalData?.valor_venda_misto_m2 || 0));
                                  return lotes > 0 ? formatCurrency(vgvBase / lotes) : formatCurrency(0);
                                })()}
                              </td>
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="py-2 text-slate-600">VGV Total Projetado</td>
                              <td className="py-2 text-right font-semibold">
                                {(() => {
                                  const vgvBase = ((physicalData?.area_lotes_residenciais || 0) * (physicalData?.valor_venda_residencial_m2 || 0)) +
                                    ((physicalData?.area_lotes_comerciais || 0) * (physicalData?.valor_venda_comercial_m2 || 0)) +
                                    ((physicalData?.area_lotes_mistos || 0) * (physicalData?.valor_venda_misto_m2 || 0));
                                  return formatCurrency(vgvBase);
                                })()}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>

                      <div>
                        <h2 className="text-xl font-bold text-ml-dark mb-4 border-b pb-2">Marcos do Projeto</h2>
                        <table className="w-full text-sm">
                          <tbody>
                            <tr className="border-b border-slate-100">
                              <td className="py-2 text-slate-600">Registro (RI)</td>
                              <td className="py-2 text-right font-semibold">{formatDate(datesData?.data_registro)}</td>
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="py-2 text-slate-600">Lançamento</td>
                              <td className="py-2 text-right font-semibold">{formatDate(datesData?.data_lancamento)}</td>
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="py-2 text-slate-600">Início de Obras</td>
                              <td className="py-2 text-right font-semibold">{formatDate(datesData?.data_inicio_obras)}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* 3. DADOS GERAIS E QUADRO PARCERIA */}
                    <div className="print:break-inside-avoid mb-8 mt-8">
                      <h3 className="text-xl font-bold text-ml-dark mb-4 border-b pb-2">DADOS GERAIS</h3>

                      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                        <table className="w-full text-sm">
                          <thead>
                            <tr>
                              <th colSpan={2} className="p-3 bg-slate-50 text-left font-bold border-b border-slate-200">PROJETO URBANISTICO {physicalData?.tipo_projeto ? `- ${physicalData.tipo_projeto.toUpperCase()}` : ''}</th>
                              {renamedColumns.map(col => (
                                <th key={`geral-urb-${col.id}`} className="p-3 text-right bg-slate-50 border-b border-slate-200 font-bold uppercase text-xs">{col.title}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            <tr className="border-b border-slate-100 font-semibold">
                              <td colSpan={2} className="p-2 pl-4">Área Total</td>
                              {renamedColumns.map(col => (
                                <td key={`area-${col.id}`} className="p-2 text-right">{formatArea(col.phys?.area_total)}</td>
                              ))}
                            </tr>
                            {/* Sub-áreas */}
                            {[
                              { label: 'Lotes Residencial', field: 'area_lotes_residenciais' },
                              { label: 'Lotes Comerciais', field: 'area_lotes_comerciais' },
                              { label: 'Lotes Mistos', field: 'area_lotes_mistos' },
                              { label: 'Sistema Viário', field: 'area_sistema_viario' },
                              { label: 'Área Institucional', field: 'area_institucional' },
                              { label: 'Área Verde / APP', field: 'area_verde' },
                              { label: 'Sistema de Lazer', field: 'area_sistema_lazer' },
                              { label: 'Associação / Não Vendável', field: 'area_associacao' },
                            ].map((item, idx) => (
                              <tr key={idx} className="border-b border-slate-100 text-slate-600">
                                <td className="p-2 pl-8 w-1/3">{item.label}</td>
                                <td className="p-2 text-right text-xs"></td>
                                {renamedColumns.map(col => {
                                  const val = col.phys?.[item.field as keyof typeof col.phys] || 0;
                                  if (val === 0) return <td key={`sub-${col.id}-${idx}`} className="p-2 text-right text-slate-300">-</td>;
                                  return <td key={`sub-${col.id}-${idx}`} className="p-2 text-right bg-slate-50">{formatArea(val as number)}</td>
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div className="print:break-inside-avoid mb-8">
                      <h3 className="text-xl font-bold text-ml-dark mb-4 border-b pb-2">DADOS FÍSICOS</h3>
                      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                        <table className="w-full text-sm">
                          <thead>
                            <tr>
                              <th className="p-3 bg-slate-50 text-left font-bold border-b border-slate-200">Descrição</th>
                              <th className="p-3 bg-slate-50 text-center font-bold border-b border-slate-200">Unidade</th>
                              {renamedColumns.map(col => (
                                <th key={`fisico-${col.id}`} className="p-3 text-right bg-slate-50 border-b border-slate-200 font-bold uppercase text-xs">{col.title}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 font-semibold">Número Lotes</td>
                              <td className="p-2 text-center text-slate-500">UNIDADES</td>
                              {renamedColumns.map(col => (
                                <td key={`lotes-${col.id}`} className="p-2 text-right font-bold">
                                  {(col.phys?.qtde_lotes_residenciais || 0) + (col.phys?.qtde_lotes_comerciais || 0) + (col.phys?.qtde_lotes_mistos || 0)}
                                </td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 font-semibold">Area Total</td>
                              <td className="p-2 text-center text-slate-500">(m²)</td>
                              {renamedColumns.map(col => (
                                <td key={`atotal-${col.id}`} className="p-2 text-right font-semibold">{formatArea(col.phys?.area_total)}</td>
                              ))}
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            </div>

            {/* 3. QUADRO PARCERIA */}
            <div className="page-break p-12 print:p-0 relative">
              <table className="w-full relative">
              <thead className="table-header-group">
                <tr>
                  <td className="px-12 pt-12 print:px-8 print:pt-6">
                    {/* Header fixo das páginas internas */}
                    <div className="flex justify-between items-center border-b-2 border-ml-green pb-4 mb-8">
                      <img src="/logo-moura-leite.png" alt="Logo" className="h-10 w-auto" />
                      <div className="text-right">
                        <p className="font-bold text-ml-dark">{project?.project_name}</p>
                        <p className="text-sm text-slate-500">Visão: {viewMode}</p>
                      </div>
                    </div>
                  </td>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="px-12 pb-6 print:px-8 print:pb-2">
                    <div className="print:break-inside-avoid">
                      <h3 className="text-xl font-bold text-ml-dark mb-4 border-b pb-2 uppercase" style={{ pageBreakAfter: 'avoid', breakAfter: 'avoid' }}>Quadro Parceria</h3>
                      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                        <table className="w-full text-sm">
                          <thead>
                            <tr>
                              <th className="p-3 bg-slate-50 text-left font-bold border-b border-slate-200">Parceiro</th>
                              {renamedColumns.map(col => (
                                <th key={`parc-${col.id}`} className="p-3 text-right bg-slate-50 border-b border-slate-200 font-bold uppercase text-xs">{col.title}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {/* COMPOSIÇÃO NA ÁREA */}
                            <tr className="bg-slate-50 border-b border-slate-200">
                              <td colSpan={renamedColumns.length + 1} className="p-2 pl-4 font-bold text-slate-900 uppercase text-xs">Composição na Área</td>
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-8 font-semibold text-slate-700">Proprietários Originais</td>
                              {renamedColumns.map(col => (
                                <td key={`ca-prop-${col.id}`} className="p-2 text-right font-semibold">{formatPerc(exchangesData?.perc_area_terrenista || 0)}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-8 font-semibold text-slate-700">Investidor</td>
                              {renamedColumns.map(col => (
                                <td key={`ca-inv-${col.id}`} className="p-2 text-right font-semibold">{formatPerc(exchangesData?.perc_area_investidor || 0)}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-8 font-semibold text-slate-700">Loteador</td>
                              {renamedColumns.map(col => (
                                <td key={`ca-lot-${col.id}`} className="p-2 text-right font-semibold">{formatPerc(exchangesData?.perc_area_empreendedor || 0)}</td>
                              ))}
                            </tr>

                            {/* PERCENTUAL PARCERIA */}
                            <tr className="bg-slate-50 border-b border-slate-200">
                              <td colSpan={renamedColumns.length + 1} className="p-2 pl-4 font-bold text-slate-900 uppercase text-xs">Percentual Parceria (VGV Ponderada)</td>
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-8 font-semibold text-slate-700">Proprietário (Terrenista)</td>
                              {renamedColumns.map(col => (
                                <td key={`pp-prop-${col.id}`} className="p-2 text-right font-semibold">{formatPerc(exchangesData?.perc_parceria_terrenista || 0)}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-8 font-semibold text-slate-700">Investidor</td>
                              {renamedColumns.map(col => (
                                <td key={`pp-inv-${col.id}`} className="p-2 text-right font-semibold">{formatPerc(exchangesData?.perc_parceria_investidor || 0)}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-8 font-semibold text-slate-700">Empreendedor</td>
                              {renamedColumns.map(col => (
                                <td key={`pp-emp-${col.id}`} className="p-2 text-right font-semibold">{formatPerc(exchangesData?.perc_parceria_empreendedor || 0)}</td>
                              ))}
                            </tr>

                            {/* ABERTURA DE PARCEIROS */}
                            {exchangesData?.abertura_terrenistas_json && exchangesData.abertura_terrenistas_json.length > 0 && (
                              <>
                                <tr className="bg-slate-50 border-b border-slate-200">
                                  <td colSpan={renamedColumns.length + 1} className="p-2 pl-4 font-bold text-slate-900 uppercase text-xs">Abertura de Parceiros Detalhada</td>
                                </tr>
                                {exchangesData.abertura_terrenistas_json.map((terr: any, idx: number) => (
                                  <tr key={`terr-${idx}`} className="border-b border-slate-100">
                                    <td className="p-2 pl-8 font-semibold text-slate-700">{terr.nome || terr.tipo || "Parceiro"} <span className="text-xs font-normal text-slate-400">({terr.tipo || "Proprietário"})</span></td>
                                    {renamedColumns.map(col => (
                                      <td key={`terr-col-${col.id}-${idx}`} className="p-2 text-right font-semibold">
                                        {formatPerc(terr.percentual || 0)}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            </div>

            {/* 4. PREMISSAS */}
            <div className="page-break p-12 print:p-0 relative">
              <table className="w-full relative">
              <thead className="table-header-group">
                <tr>
                  <td className="px-8 pt-4 print:px-6 print:pt-3">
                    <div className="flex justify-between items-center border-b-2 border-ml-green pb-2 mb-3">
                      <img src="/logo-moura-leite.png" alt="Logo" className="h-8 w-auto" />
                      <div className="text-right">
                        <p className="font-bold text-ml-dark text-sm">PREMISSAS</p>
                        <p className="text-xs text-slate-500">Visão: {viewMode}</p>
                      </div>
                    </div>
                  </td>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="px-8 pb-2 print:px-6 print:pb-1">
                    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden print:break-inside-avoid mb-3">
                      <table className="w-full text-xs">
                        <thead>
                          <tr>
                            <th className="p-1.5 bg-slate-50 text-left font-bold border-b border-slate-200 text-slate-800 uppercase">PREÇOS</th>
                            <th className="p-1.5 bg-slate-50 text-center font-bold border-b border-slate-200"></th>
                            {renamedColumns.map(col => (
                              <th key={`prec-${col.id}`} className="p-1.5 text-right bg-slate-50 border-b border-slate-200 font-bold uppercase text-xs">{col.title}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          <tr className="border-b border-slate-100">
                            <td className="p-1 pl-4 text-slate-700">VGV BRUTO</td>
                            <td className="p-1 text-center text-slate-500">(R$)</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const vgvLiquidoFluxo = getCashflowTotal(col.monthly_cashflow, "Receitas", m);
                              const percComissao = col.rawData?.phase?.expenses?.comissao_corretagem_valor || 0;
                              const vgvBruto = percComissao < 100 ? vgvLiquidoFluxo / (1 - (percComissao / 100)) : 0;
                              return <td key={`vgvb-${col.id}`} className="p-1 text-right font-semibold">{formatCurrency(vgvBruto)}</td>;
                            })}
                          </tr>
                          <tr className="border-b border-slate-100">
                            <td className="p-1 pl-4 text-slate-700">VGV LÍQUIDO</td>
                            <td className="p-1 text-center text-slate-500">(R$)</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const vgvLiquidoFluxo = getCashflowTotal(col.monthly_cashflow, "Receitas", m);
                              const impostos = getCashflowTotal(col.monthly_cashflow, "Impostos_PIS", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS", m);
                              const vgvLiquido = vgvLiquidoFluxo - impostos;
                              return <td key={`vgvl-${col.id}`} className="p-1 text-right font-semibold">{formatCurrency(vgvLiquido)}</td>;
                            })}
                          </tr>
                          <tr className="border-b border-slate-100">
                            <td className="p-1 pl-4 text-slate-700">PREÇO MÉDIO DE VENDA</td>
                            <td className="p-1 text-center text-slate-500">(R$/m²)</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const vgvLiquidoFluxo = getCashflowTotal(col.monthly_cashflow, "Receitas", m);
                              const percComissao = col.rawData?.phase?.expenses?.comissao_corretagem_valor || 0;
                              const vgvBruto = percComissao < 100 ? vgvLiquidoFluxo / (1 - (percComissao / 100)) : 0;
                              const areaVendavel = (col.phys?.area_lotes_residenciais || 0) + (col.phys?.area_lotes_comerciais || 0) + (col.phys?.area_lotes_mistos || 0);
                              return <td key={`preco-medio-${col.id}`} className="p-1 text-right font-semibold">{formatCurrency(areaVendavel > 0 ? vgvBruto / areaVendavel : 0)}</td>;
                            })}
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden print:break-inside-avoid">
                      <table className="w-full text-[10px]">
                        <thead>
                          <tr>
                            <th className="p-1 bg-slate-50 text-left font-bold border-b border-slate-200 text-slate-800 uppercase w-1/4">DESPESAS</th>
                            <th className="p-1 bg-slate-50 text-left font-bold border-b border-slate-200 text-slate-800 uppercase w-1/6">BASE</th>
                            {renamedColumns.map(col => (
                              <th key={`desp-${col.id}`} colSpan={2} className="p-1 text-center bg-slate-50 border-b border-slate-200 font-bold uppercase text-[10px]">{col.title}</th>
                            ))}
                          </tr>
                          <tr>
                            <th colSpan={2} className="p-1 bg-slate-50 border-b border-slate-200"></th>
                            {renamedColumns.map(col => (
                              <React.Fragment key={`sub-${col.id}`}>
                                <th className="p-1 text-center text-slate-500 uppercase bg-slate-50 border-b border-slate-200">%</th>
                                <th className="p-1 text-right text-slate-500 uppercase bg-slate-50 border-b border-slate-200">R$</th>
                              </React.Fragment>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {[
                            { label: 'PROJETO E APROVAÇÃO', base: 'VGV', field: 'Obras_Proj' },
                            { label: 'IMPOSTOS', base: 'CARTEIRA', field: 'Impostos' },
                            { label: 'G&A - ESTRUTURA', base: 'CARTEIRA', field: 'Despesas_Adm' },
                            { label: 'COMISSÕES', base: 'VGV', field: 'COMISSOES' },
                            { label: 'MARKETING', base: 'VGV', field: 'Despesas_Mkt' },
                            { label: 'COMERCIAL', base: 'VGV', field: 'Despesas_Com' },
                          ].map((row, i) => (
                            <tr key={i} className="border-b border-slate-100">
                              <td className="p-1 pl-2 text-slate-700 uppercase">{row.label}</td>
                              <td className="p-1 text-slate-500 uppercase">{row.base}</td>
                              {renamedColumns.map(col => {
                                const m = getMultiplier(viewMode, col.rawData);
                                const expenses = col.rawData?.phase?.expenses || {};
                                const construction = col.rawData?.phase?.construction || {};
                                const taxes = col.rawData?.phase?.taxes || {};

                                let percConfig = 0;
                                let tipoConfig = "%";
                                let val = 0;

                                if (row.field === 'COMISSOES') {
                                  percConfig = expenses.comissao_corretagem_valor || 0;
                                  const vgvLiquido = getCashflowTotal(col.monthly_cashflow, "Receitas", m);
                                  const vgvBruto = percConfig < 100 ? vgvLiquido / (1 - (percConfig / 100)) : 0;
                                  val = vgvBruto * (percConfig / 100);
                                } else {
                                  val = getCashflowTotal(col.monthly_cashflow, row.field, m);
                                  if (row.label === 'PROJETO E APROVAÇÃO') {
                                    percConfig = construction.custo_projetos || 0;
                                    tipoConfig = construction.custo_projetos_tipo || "%";
                                  } else if (row.label === 'IMPOSTOS') {
                                    percConfig = taxes.aliquota_total || 0;
                                  } else if (row.label === 'G&A - ESTRUTURA') {
                                    percConfig = expenses.adm_valor || 0;
                                    tipoConfig = expenses.adm_tipo || "%";
                                  } else if (row.label === 'MARKETING') {
                                    percConfig = expenses.marketing_valor || 0;
                                    tipoConfig = expenses.marketing_tipo || "%";
                                  } else if (row.label === 'COMERCIAL') {
                                    percConfig = expenses.comercial_valor || 0;
                                    tipoConfig = expenses.comercial_tipo || "%";
                                  }
                                }

                                return (
                                  <React.Fragment key={`val-${col.id}-${i}`}>
                                    <td className="p-1 text-center bg-slate-50 font-semibold">{tipoConfig === '%' ? formatPerc(percConfig) : '-'}</td>
                                    <td className="p-1 text-right">{val > 0 ? formatCurrency(val) : '-'}</td>
                                  </React.Fragment>
                                )
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="print:break-inside-avoid mt-3">
                      <h3 className="text-[10px] font-bold text-ml-dark mb-1 border-b pb-1 uppercase">Vendas e Planos</h3>
                      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                        <table className="w-full text-[10px]">
                          <thead>
                            <tr>
                              <th className="p-1 bg-slate-50 text-left border-b border-slate-200"></th>
                              {renamedColumns.map(col => (
                                <th key={`vp-head-${col.id}`} className="p-1 text-center bg-slate-50 border-b border-slate-200 font-bold uppercase text-[10px]">{col.title}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            <tr className="bg-slate-50 font-bold border-b border-slate-200">
                              <td className="p-1 pl-2 text-slate-800">VENDAS</td>
                              {renamedColumns.map(col => <td key={`mix-${col.id}`}></td>)}
                            </tr>
                            {Array.from(new Set(renamedColumns.flatMap(col => {
                              let conds = col.rawData?.phase?.revenue?.condicoes_pagamento_json;
                              if (typeof conds === 'string') { try { conds = JSON.parse(conds); } catch (e) { conds = []; } }
                              if (!Array.isArray(conds)) conds = [];
                              let flatConds = [];
                              for (const item of conds) {
                                if (item.condicoes && Array.isArray(item.condicoes)) flatConds.push(...item.condicoes);
                                else flatConds.push(item);
                              }
                              return flatConds.map((c: any) => c.nome || '').filter(Boolean);
                            }))).sort().map((condName, i) => (
                              <tr key={`cond-${i}`} className="border-b border-slate-100">
                                <td className="p-1 pl-4 text-slate-600 uppercase">{condName}</td>
                                {renamedColumns.map(col => {
                                  let conds = col.rawData?.phase?.revenue?.condicoes_pagamento_json;
                                  if (typeof conds === 'string') { try { conds = JSON.parse(conds); } catch (e) { conds = []; } }
                                  if (!Array.isArray(conds)) conds = [];
                                  let flatConds = [];
                                  for (const item of conds) {
                                    if (item.condicoes && Array.isArray(item.condicoes)) flatConds.push(...item.condicoes);
                                    else flatConds.push(item);
                                  }
                                  const cond = flatConds.find((c: any) => c.nome === condName);
                                  return <td key={`cond-val-${col.id}`} className="p-1 text-center text-slate-600">{cond ? `${cond.perc}%` : '-'}</td>;
                                })}
                              </tr>
                            ))}
                            <tr className="bg-slate-100 font-bold border-b border-slate-200">
                              <td className="p-1 pl-2 text-slate-800">TAXA JUROS (a.m.)</td>
                              {renamedColumns.map(col => <td key={`jur-head-${col.id}`} className="bg-slate-100"></td>)}
                            </tr>
                            {Array.from(new Set(renamedColumns.flatMap(col => {
                              let conds = col.rawData?.phase?.revenue?.condicoes_pagamento_json;
                              if (typeof conds === 'string') { try { conds = JSON.parse(conds); } catch (e) { conds = []; } }
                              if (!Array.isArray(conds)) conds = [];
                              let flatConds = [];
                              for (const item of conds) {
                                if (item.condicoes && Array.isArray(item.condicoes)) flatConds.push(...item.condicoes);
                                else flatConds.push(item);
                              }
                              return flatConds.map((c: any) => c.nome || '').filter(Boolean);
                            }))).sort().map((condName, i) => (
                              <tr key={`juros-${i}`} className="border-b border-slate-100 bg-slate-50">
                                <td className="p-1 pl-4 text-slate-600 uppercase">{condName}</td>
                                {renamedColumns.map(col => {
                                  let conds = col.rawData?.phase?.revenue?.condicoes_pagamento_json;
                                  if (typeof conds === 'string') { try { conds = JSON.parse(conds); } catch (e) { conds = []; } }
                                  if (!Array.isArray(conds)) conds = [];
                                  let flatConds = [];
                                  for (const item of conds) {
                                    if (item.condicoes && Array.isArray(item.condicoes)) flatConds.push(...item.condicoes);
                                    else flatConds.push(item);
                                  }
                                  const cond = flatConds.find((c: any) => c.nome === condName);
                                  let val = '-';
                                  if (cond && cond.aplica_juros) {
                                      const jurosAnual = parseFloat(col.rawData?.phase?.revenue?.taxa_juros_vendas || '0');
                                      const jurosMensal = (Math.pow(1 + (jurosAnual / 100), 1 / 12) - 1) * 100;
                                      val = jurosMensal.toLocaleString('pt-BR', { minimumFractionDigits: 4, maximumFractionDigits: 4 }) + '%';
                                  } else if (cond) { val = '0,0000%'; }
                                  return <td key={`juros-val-${col.id}`} className="p-1 text-center font-bold text-slate-700">{val}</td>;
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            </div>

            {/* 5. DRE NEGÓCIO (COMPARATIVO) */}
            <div className="page-break p-12 print:px-8 print:py-6 relative">
                    <div className="flex justify-between items-center border-b-2 border-ml-green pb-4 mb-8">
                      <img src="/logo-moura-leite.png" alt="Logo" className="h-10 w-auto" />
                      <div className="text-right">
                        <p className="font-bold text-ml-dark">DRE NEGÓCIO</p>
                        <p className="text-sm text-slate-500">Visão: {viewMode}</p>
                      </div>
                    </div>

                    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden print:break-inside-avoid">
                      <table className="w-full text-sm">
                        <thead>
                          <tr>
                            <th className="p-4 bg-slate-50 text-left border-b border-slate-200 w-1/3"></th>
                            {renamedColumns.map(col => (
                              <th key={`dre-${col.id}`} className="p-4 text-right bg-slate-50 border-b border-slate-200 font-bold uppercase text-xs">{col.title}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {/* Receita Bruta */}
                          <tr className="bg-slate-50 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">RECEITA BRUTA</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              return <td key={`rb-${col.id}`} className="p-3 text-right">{formatCurrency(getCashflowTotal(col.monthly_cashflow, "Receitas", m))}</td>
                            })}
                          </tr>
                          <tr className="border-b border-slate-100">
                            <td className="p-2 pl-8 text-slate-600">Receita Vendas</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              return <td key={`rv-${col.id}`} className="p-2 text-right">{formatCurrency(getCashflowTotal(col.monthly_cashflow, "Receitas_Vendas", m))}</td>
                            })}
                          </tr>
                          <tr className="border-b border-slate-100">
                            <td className="p-2 pl-8 text-slate-600">Receita de Juros</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              return <td key={`rj-${col.id}`} className="p-2 text-right">{formatCurrency(getCashflowTotal(col.monthly_cashflow, "Receitas_Juros", m))}</td>
                            })}
                          </tr>

                          {/* Redutor */}
                          <tr className="bg-slate-50 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">REDUTOR RECEITA</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const imp = getCashflowTotal(col.monthly_cashflow, "Impostos_PIS", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS", m);
                              return <td key={`rr-${col.id}`} className="p-3 text-right text-red-600">({formatCurrency(imp)})</td>
                            })}
                          </tr>

                          {/* Receita Líquida */}
                          <tr className="bg-slate-100 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">RECEITA LÍQUIDA</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const liq = getCashflowTotal(col.monthly_cashflow, "Receitas", m) - (getCashflowTotal(col.monthly_cashflow, "Impostos_PIS", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS", m));
                              return <td key={`rl-${col.id}`} className="p-3 text-right text-ml-dark">{formatCurrency(liq)}</td>
                            })}
                          </tr>

                          {/* Custo */}
                          <tr className="bg-slate-50 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">CUSTO</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const cst = getCashflowTotal(col.monthly_cashflow, "Terreno", m) + getCashflowTotal(col.monthly_cashflow, "Obras", m);
                              return <td key={`cst-${col.id}`} className="p-3 text-right text-red-600">({formatCurrency(cst)})</td>
                            })}
                          </tr>
                          <tr className="border-b border-slate-100">
                            <td className="p-2 pl-8 text-slate-600">Obras</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              return <td key={`obras-${col.id}`} className="p-2 text-right text-red-600">({formatCurrency(getCashflowTotal(col.monthly_cashflow, "Obras", m))})</td>
                            })}
                          </tr>
                          <tr className="border-b border-slate-100">
                            <td className="p-2 pl-8 text-slate-600">Projetos</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              return <td key={`proj-${col.id}`} className="p-2 text-right text-red-600">({formatCurrency(getCashflowTotal(col.monthly_cashflow, "Obras_Proj", m))})</td>
                            })}
                          </tr>

                          {/* Margem Bruta */}
                          <tr className="bg-slate-100 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">MARGEM BRUTA</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const liq = getCashflowTotal(col.monthly_cashflow, "Receitas", m) - (getCashflowTotal(col.monthly_cashflow, "Impostos_PIS", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS", m));
                              const cst = getCashflowTotal(col.monthly_cashflow, "Terreno", m) + getCashflowTotal(col.monthly_cashflow, "Obras", m);
                              return <td key={`mb-${col.id}`} className="p-3 text-right text-ml-dark">{formatCurrency(liq - cst)}</td>
                            })}
                          </tr>
                          <tr className="bg-slate-100 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">MARGEM BRUTA (%)</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const liq = getCashflowTotal(col.monthly_cashflow, "Receitas", m) - (getCashflowTotal(col.monthly_cashflow, "Impostos_PIS", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS", m));
                              const cst = getCashflowTotal(col.monthly_cashflow, "Terreno", m) + getCashflowTotal(col.monthly_cashflow, "Obras", m);
                              const perc = liq > 0 ? ((liq - cst) / liq) * 100 : 0;
                              return <td key={`mbp-${col.id}`} className="p-3 text-right text-ml-dark">{formatPerc(perc)}</td>
                            })}
                          </tr>

                          {/* DV&A */}
                          <tr className="bg-slate-50 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">DV&A</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const dva = getCashflowTotal(col.monthly_cashflow, "Despesas", m) + custoFinanceiro(col.monthly_cashflow, m);
                              return <td key={`dva-${col.id}`} className="p-3 text-right text-red-600">({formatCurrency(dva)})</td>
                            })}
                          </tr>
                          <tr className="border-b border-slate-100">
                            <td className="p-2 pl-8 text-slate-600">Marketing</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              return <td key={`mkt-${col.id}`} className="p-2 text-right text-red-600">({formatCurrency(getCashflowTotal(col.monthly_cashflow, "Despesas_Mkt", m))})</td>
                            })}
                          </tr>
                          <tr className="border-b border-slate-100">
                            <td className="p-2 pl-8 text-slate-600">Comercial</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              return <td key={`com-${col.id}`} className="p-2 text-right text-red-600">({formatCurrency(getCashflowTotal(col.monthly_cashflow, "Despesas_Com", m))})</td>
                            })}
                          </tr>
                          <tr className="border-b border-slate-100">
                            <td className="p-2 pl-8 text-slate-600">G&A</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              return <td key={`ga-${col.id}`} className="p-2 text-right text-red-600">({formatCurrency(getCashflowTotal(col.monthly_cashflow, "Despesas_Adm", m))})</td>
                            })}
                          </tr>
                          <tr className="border-b border-slate-100">
                            <td className="p-2 pl-8 text-slate-600">Captação Externa</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              return <td key={`ce-${col.id}`} className="p-2 text-right text-red-600">({formatCurrency(custoFinanceiro(col.monthly_cashflow, m))})</td>
                            })}
                          </tr>

                          {/* Lucro Operacional */}
                          <tr className="bg-slate-100 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">LUCRO OPERACIONAL</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const liq = getCashflowTotal(col.monthly_cashflow, "Receitas", m) - (getCashflowTotal(col.monthly_cashflow, "Impostos_PIS", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS", m));
                              const cst = getCashflowTotal(col.monthly_cashflow, "Terreno", m) + getCashflowTotal(col.monthly_cashflow, "Obras", m);
                              const mb = liq - cst;
                              const dva = getCashflowTotal(col.monthly_cashflow, "Despesas", m) + custoFinanceiro(col.monthly_cashflow, m);
                              return <td key={`lo-${col.id}`} className="p-3 text-right text-ml-dark">{formatCurrency(mb - dva)}</td>
                            })}
                          </tr>
                          <tr className="bg-slate-100 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">LUCRO OPERACIONAL (%)</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const liq = getCashflowTotal(col.monthly_cashflow, "Receitas", m) - (getCashflowTotal(col.monthly_cashflow, "Impostos_PIS", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS", m));
                              const cst = getCashflowTotal(col.monthly_cashflow, "Terreno", m) + getCashflowTotal(col.monthly_cashflow, "Obras", m);
                              const mb = liq - cst;
                              const dva = getCashflowTotal(col.monthly_cashflow, "Despesas", m) + custoFinanceiro(col.monthly_cashflow, m);
                              const perc = liq > 0 ? ((mb - dva) / liq) * 100 : 0;
                              return <td key={`lop-${col.id}`} className="p-3 text-right text-ml-dark">{formatPerc(perc)}</td>
                            })}
                          </tr>

                          {/* IRPJ / CSLL */}
                          <tr className="bg-slate-50 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">IRPJ / CSLL</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const irpj = getCashflowTotal(col.monthly_cashflow, "Impostos_IRPJ_CSLL", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_Outros", m);
                              return <td key={`irpj-${col.id}`} className="p-3 text-right text-red-600">({formatCurrency(irpj)})</td>
                            })}
                          </tr>

                          {/* Lucro Líquido */}
                          <tr className="bg-slate-100 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">LUCRO LIQUIDO</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const liq = getCashflowTotal(col.monthly_cashflow, "Receitas", m) - (getCashflowTotal(col.monthly_cashflow, "Impostos_PIS", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS", m));
                              const cst = getCashflowTotal(col.monthly_cashflow, "Terreno", m) + getCashflowTotal(col.monthly_cashflow, "Obras", m);
                              const mb = liq - cst;
                              const dva = getCashflowTotal(col.monthly_cashflow, "Despesas", m) + custoFinanceiro(col.monthly_cashflow, m);
                              const irpj = getCashflowTotal(col.monthly_cashflow, "Impostos_IRPJ_CSLL", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_Outros", m);
                              const ll = mb - dva - irpj;
                              return <td key={`ll-${col.id}`} className="p-3 text-right text-ml-dark">{formatCurrency(ll)}</td>
                            })}
                          </tr>
                          <tr className="bg-slate-100 font-bold border-b border-slate-200">
                            <td className="p-3 pl-4 text-slate-800">LUCRO LIQUIDO (%)</td>
                            {renamedColumns.map(col => {
                              const m = getMultiplier(viewMode, col.rawData);
                              const liq = getCashflowTotal(col.monthly_cashflow, "Receitas", m) - (getCashflowTotal(col.monthly_cashflow, "Impostos_PIS", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS", m));
                              const cst = getCashflowTotal(col.monthly_cashflow, "Terreno", m) + getCashflowTotal(col.monthly_cashflow, "Obras", m);
                              const mb = liq - cst;
                              const dva = getCashflowTotal(col.monthly_cashflow, "Despesas", m) + custoFinanceiro(col.monthly_cashflow, m);
                              const irpj = getCashflowTotal(col.monthly_cashflow, "Impostos_IRPJ_CSLL", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_Outros", m);
                              const ll = mb - dva - irpj;
                              const perc = liq > 0 ? (ll / liq) * 100 : 0;
                              return <td key={`llp-${col.id}`} className="p-3 text-right text-ml-dark">{formatPerc(perc)}</td>
                            })}
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* 4. FLUXO DE CAIXA (RESUMO COMPARATIVO) */}
                  {includeCashflow && (
                    <div className="page-break p-12 print:px-8 print:py-6 relative">
                      <div className="flex justify-between items-center border-b-2 border-ml-green pb-4 mb-8">
                        <img src="/logo-moura-leite.png" alt="Logo" className="h-10 w-auto" />
                        <div className="text-right">
                          <p className="font-bold text-ml-dark">Resumo Financeiro ({cashflowGranularity})</p>
                          <p className="text-sm text-slate-500">Visão: {viewMode}</p>
                        </div>
                      </div>

                      {/* Tabela de Cashflow (Comparative) */}
                      <h3 className="text-lg font-bold text-slate-800 mb-4">Detalhamento Financeiro Comparativo <span className="text-sm font-normal text-slate-500 ml-2">(Valores em R$ mil)</span></h3>
                      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden print:break-inside-avoid">
                        <table className="w-full text-[10px] text-right" style={{ tableLayout: 'fixed' }}>
                          <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                            <tr>
                              <th className="p-2 text-left border-r border-slate-200 align-bottom w-16" rowSpan={2}>Período</th>
                              {renamedColumns.map((col) => (
                                <th key={`hdr-${col.id}`} colSpan={4} className={`p-2 text-center border-r border-slate-200 ${col.isCurrent ? 'bg-ml-green/10 text-ml-dark' : 'bg-slate-50'}`}>
                                  {col.title}
                                </th>
                              ))}
                            </tr>
                            <tr>
                              {renamedColumns.map((col) => (
                                <React.Fragment key={`sub-${col.id}`}>
                                  <th className={`p-1 text-center font-normal ${col.isCurrent ? 'bg-ml-green/5' : ''}`}>Entradas</th>
                                  <th className={`p-1 text-center font-normal ${col.isCurrent ? 'bg-ml-green/5' : ''}`}>Saídas</th>
                                  <th className={`p-1 text-center font-normal ${col.isCurrent ? 'bg-ml-green/5' : ''}`}>Líquido</th>
                                  <th className={`p-1 text-center font-normal border-r border-slate-200 ${col.isCurrent ? 'bg-ml-green/5' : ''}`}>Acumulado</th>
                                </React.Fragment>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {Array.from({ length: maxPeriods }).map((_, i) => (
                              <tr key={i} className={`border-b border-slate-100 ${i % 2 === 0 ? 'bg-white' : 'bg-slate-50'}`}>
                                <td className="p-1 pl-2 text-left font-medium text-slate-700 whitespace-nowrap border-r border-slate-200">
                                  {allGroupedCashflows[0][i]?.period || `Ano ${i + 1}`}
                                </td>
                                {renamedColumns.map((col, colIdx) => {
                                  const row = allGroupedCashflows[colIdx][i];
                                  if (!row) return (
                                    <React.Fragment key={`empty-${col.id}-${i}`}>
                                      <td className="p-1 text-right"></td>
                                      <td className="p-1 text-right"></td>
                                      <td className="p-1 text-right"></td>
                                      <td className="p-1 text-right border-r border-slate-200"></td>
                                    </React.Fragment>
                                  );
                                  return (
                                    <React.Fragment key={`data-${col.id}-${i}`}>
                                      <td className={`p-1 text-right ${row.receitas > 0 ? 'text-ml-green' : 'text-slate-400'}`}>{formatCurrency(row.receitas / 1000)}</td>
                                      <td className={`p-1 text-right ${row.saidas !== 0 ? 'text-ml-orange' : 'text-slate-400'}`}>({formatCurrency(Math.abs(row.saidas) / 1000)})</td>
                                      <td className={`p-1 text-right font-semibold ${row.liquido >= 0 ? 'text-ml-green' : 'text-red-600'}`}>
                                        {formatCurrency(row.liquido / 1000)}
                                      </td>
                                      <td className={`p-1 text-right font-bold border-r border-slate-200 ${row.acumulado >= 0 ? 'text-ml-dark' : 'text-red-700'}`}>
                                        {formatCurrency(row.acumulado / 1000)}
                                      </td>
                                    </React.Fragment>
                                  )
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* 5. COMPARATIVO (Opcional) */}
                  {includeComparative && renamedColumns.length > 1 && (
                    <div className="page-break p-12 print:py-6 relative">
                      <div className="flex justify-between items-center border-b-2 border-ml-green pb-4 mb-8">
                        <img src="/logo-moura-leite.png" alt="Logo" className="h-10 w-auto" />
                        <div className="text-right">
                          <p className="font-bold text-ml-dark">Comparativo de Cenários</p>
                          <p className="text-sm text-slate-500">Visão: {viewMode}</p>
                        </div>
                      </div>

                      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden print:break-inside-avoid mt-6">
                        <table className="w-full text-sm">
                          <thead>
                            <tr>
                              <th className="p-4 bg-slate-50 text-left border-b border-slate-200 w-1/4">Indicador</th>
                              {renamedColumns.map(col => (
                                <th key={`comp-${col.id}`} className={`p-4 text-right border-b border-slate-200 uppercase tracking-wider text-xs ${col.isCurrent ? 'bg-ml-green/10 text-ml-dark' : 'bg-slate-50 text-slate-700'}`}>
                                  {col.title}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {/* --- INDICADORES --- */}
                            <tr className="bg-slate-100 font-bold border-b border-slate-200">
                              <td colSpan={renamedColumns.length + 1} className="p-3 pl-4 text-slate-800 uppercase text-xs">INDICADORES</td>
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700">TIR MENSAL</td>
                              {renamedColumns.map(col => (
                                <td key={`tm-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{formatPerc(col.ind?.tir_am)}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700">TIR ANUAL</td>
                              {renamedColumns.map(col => (
                                <td key={`ta-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{formatPerc(col.ind?.tir_aa)}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase text-[11px] whitespace-nowrap tracking-tight">Exposição Máxima Caixa</td>
                              {renamedColumns.map(col => (
                                <td key={`emc-${col.id}`} className={`p-2 text-right font-bold text-red-600 ${col.isCurrent ? 'bg-ml-green/5' : ''}`}>{formatCurrency(col.ind?.exposicao_maxima)}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase text-[11px] whitespace-nowrap tracking-tight">Exposição Caixa / Investimento</td>
                              {renamedColumns.map(col => (
                                <td key={`eci-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{formatPerc(col.ind?.expo_inv)}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase text-[11px] whitespace-nowrap tracking-tight">Período Exposição (Meses)</td>
                              {renamedColumns.map(col => (
                                <td key={`per-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{col.ind?.periodo_exposicao || 0}</td>
                              ))}
                            </tr>

                            {/* --- RENTABILIDADE --- */}
                            <tr className="bg-slate-100 font-bold border-b border-slate-200">
                              <td colSpan={renamedColumns.length + 1} className="p-3 pl-4 text-slate-800 uppercase text-xs mt-4">RENTABILIDADE</td>
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase text-[11px] whitespace-nowrap tracking-tight">(Investimento/Retorno) Sem Juros</td>
                              {renamedColumns.map(col => (
                                <td key={`rsj-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{formatPerc(col.ind?.retorno_sem_juros)}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase text-[11px] whitespace-nowrap tracking-tight">(Investimento/Retorno) Com Juros</td>
                              {renamedColumns.map(col => (
                                <td key={`rcj-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{formatPerc(col.ind?.retorno_com_juros)}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase">Payback (Meses)</td>
                              {renamedColumns.map(col => (
                                <td key={`pay-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{Math.round(Number(col.ind?.payback || 0))}</td>
                              ))}
                            </tr>

                            {/* --- MARGEM BRUTA --- */}
                            <tr className="bg-slate-100 font-bold border-b border-slate-200">
                              <td colSpan={renamedColumns.length + 1} className="p-3 pl-4 text-slate-800 uppercase text-xs mt-4">MARGEM BRUTA E LÍQUIDA</td>
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase">Margem Bruta (R$)</td>
                              {renamedColumns.map(col => {
                                const m = getMultiplier(viewMode, col.rawData);
                                const liq = getCashflowTotal(col.monthly_cashflow, "Receitas", m) - (getCashflowTotal(col.monthly_cashflow, "Impostos_PIS", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS", m));
                                const cst = getCashflowTotal(col.monthly_cashflow, "Terreno", m) + getCashflowTotal(col.monthly_cashflow, "Obras", m);
                                const margemBruta = liq - cst;
                                return <td key={`mb-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{formatCurrency(margemBruta)}</td>
                              })}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase">Margem Bruta (%)</td>
                              {renamedColumns.map(col => {
                                const m = getMultiplier(viewMode, col.rawData);
                                const liq = getCashflowTotal(col.monthly_cashflow, "Receitas", m) - (getCashflowTotal(col.monthly_cashflow, "Impostos_PIS", m) + getCashflowTotal(col.monthly_cashflow, "Impostos_COFINS", m));
                                const cst = getCashflowTotal(col.monthly_cashflow, "Terreno", m) + getCashflowTotal(col.monthly_cashflow, "Obras", m);
                                const margemBruta = liq - cst;
                                const margemBrutaPerc = liq > 0 ? (margemBruta / liq) * 100 : 0;
                                return <td key={`mbp-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{formatPerc(margemBrutaPerc)}</td>
                              })}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase">Margem Líquida (R$)</td>
                              {renamedColumns.map(col => (
                                <td key={`ml-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{formatCurrency(col.ind?.lucro_liquido)}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase">Margem Líquida (%)</td>
                              {renamedColumns.map(col => (
                                <td key={`mlp-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{formatPerc(col.ind?.margem_perc)}</td>
                              ))}
                            </tr>

                            {/* --- DURAÇÃO EMPREENDIMENTO --- */}
                            <tr className="bg-slate-100 font-bold border-b border-slate-200">
                              <td colSpan={renamedColumns.length + 1} className="p-3 pl-4 text-slate-800 uppercase text-xs mt-4">DURAÇÃO EMPREENDIMENTO</td>
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase">Meses</td>
                              {renamedColumns.map(col => (
                                <td key={`meses-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{col.ind?.vida || 0}</td>
                              ))}
                            </tr>
                            <tr className="border-b border-slate-100">
                              <td className="p-2 pl-4 text-slate-700 uppercase">Anos</td>
                              {renamedColumns.map(col => (
                                <td key={`anos-${col.id}`} className={`p-2 text-right font-bold ${col.isCurrent ? 'bg-ml-green/5 text-ml-dark' : 'text-slate-800'}`}>{Math.round(Number(col.ind?.vida || 0) / 12)}</td>
                              ))}
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* 5. DEMONSTRATIVO DE FLUXO DE CAIXA DETALHADO POR CENÁRIO */}
                  {includeCashflow && renamedColumns.map((col, index) => {
                    // Usa cashflow já memoizado pelo useMemo acima
                    const colGrouped = allGroupedCashflows[index] || [];
                    const m = multiplier; // Inherit multiplier from viewMode

                    return (
                      <div key={`det-cf-${col.id}`} className="page-break p-12 print:px-8 print:py-6 relative">
                        {/* Cabeçalho: logo acima da linha, título abaixo */}
                        <div className="border-b-2 border-ml-green pb-2 mb-4 flex justify-between items-center">
                          <img src="/logo-moura-leite.png" alt="Logo" className="h-10 w-auto" />
                          <div className="text-right">
                            <p className="font-bold text-ml-dark">Fluxo de Caixa Detalhado</p>
                            <p className="text-sm text-slate-500">Visão: {viewMode}</p>
                          </div>
                        </div>
                        
                        <div className="text-center mb-6">
                          <p className="font-bold text-ml-dark uppercase text-lg">
                            DEMONSTRATIVO DE FLUXO DE CAIXA – VISÃO {viewMode === 'Global' ? 'TOTAL NEGÓCIO' : viewMode.toUpperCase()}
                            <span className="text-sm font-normal text-slate-500 normal-case ml-2">(Valores em R$ mil)</span>
                          </p>
                          <p className="text-red-600 font-bold text-base">{col.title}</p>
                        </div>

                        {/* Gráfico do Cenário - visível no print, sem animações para evitar ResizeObserver issues */}
                        <div className="h-[250px] w-full mb-8">
                          <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={colGrouped} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                              <XAxis dataKey="period" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={{ stroke: '#cbd5e1' }} tickLine={false} />
                              <YAxis yAxisId="left" tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`} tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
                              <YAxis yAxisId="right" orientation="right" tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`} tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
                              <RechartsTooltip formatter={(val: any) => formatCurrency(val)} />
                              <Legend wrapperStyle={{ fontSize: '12px' }} />

                              <Bar yAxisId="left" dataKey="receitas" name="Entradas" fill="#2E864D" radius={[2, 2, 0, 0]} maxBarSize={40} isAnimationActive={false} />
                              <Bar yAxisId="left" dataKey="saidas" name="Saídas" fill="#F5883A" radius={[2, 2, 0, 0]} maxBarSize={40} isAnimationActive={false} />
                              <Line yAxisId="right" type="monotone" dataKey="acumulado" name="Acumulado" stroke="#0B1C12" strokeWidth={3} dot={false} isAnimationActive={false} />
                            </ComposedChart>
                          </ResponsiveContainer>
                        </div>

                        {/* Tabela Detalhada do Cenário */}
                        <div className="bg-white overflow-hidden" style={{ margin: "0 -20px" }}>
                          <table className="w-full text-[7.5px] tracking-tighter text-right" style={{ tableLayout: 'auto' }}>
                            <thead className="text-white font-bold border-t border-b border-ml-dark text-center align-middle">
                              {/* LINHA 1 */}
                              <tr>
                                <th className="p-1 bg-black" rowSpan={3}>ANO</th>
                                <th className="p-1 bg-[#1a502e]" colSpan={4}>ENTRADAS</th>
                                <th className="p-1 bg-[#b34a1b]" colSpan={9}>SAÍDAS</th>
                                <th className="p-1 bg-slate-200 text-slate-800" rowSpan={3}>FCF</th>
                                <th className="p-1 bg-slate-200 text-slate-800" rowSpan={3}>SALDO INICIAL</th>
                                <th className="p-1 bg-slate-200 text-slate-800" rowSpan={3}>SALDO FINAL</th>
                              </tr>
                              {/* LINHA 2 */}
                              <tr>
                                <th className="p-1 bg-[#1a502e]" rowSpan={2}>ENTRADA</th>
                                <th className="p-1 bg-[#1a502e]" rowSpan={2}>PARCELA</th>
                                <th className="p-1 bg-[#1a502e]" rowSpan={2}>JUROS</th>
                                <th className="p-1 bg-[#1a502e]">TOTAL</th>

                                <th className="p-1 bg-[#b34a1b]" rowSpan={2}>TRIBUTOS</th>
                                <th className="p-1 bg-[#b34a1b]" rowSpan={2}>OBRAS</th>
                                <th className="p-1 bg-[#b34a1b]" rowSpan={2}>PROJETO</th>
                                <th className="p-1 bg-[#b34a1b]" colSpan={2}>CAPTAÇÃO</th>
                                <th className="p-1 bg-[#b34a1b]" rowSpan={2}>MKT</th>
                                <th className="p-1 bg-[#b34a1b]" rowSpan={2}>COMERCIAL</th>
                                <th className="p-1 bg-[#b34a1b]" rowSpan={2}>G&A</th>
                                <th className="p-1 bg-[#b34a1b]">TOTAL</th>
                              </tr>
                              {/* LINHA 3 */}
                              <tr>
                                <th className="p-1 bg-[#1a502e]">ENTRADA</th>
                                <th className="p-1 bg-[#b34a1b]">EXTERNA</th>
                                <th className="p-1 bg-[#b34a1b]">INTERNA</th>
                                <th className="p-1 bg-[#b34a1b]">SAÍDAS</th>
                              </tr>
                            </thead>
                            <tbody>
                              {colGrouped.map((row: any, i) => {
                                const rowReceitas = (row.Receitas || 0) * m;
                                const rowTributos = (row.Impostos || 0) * m;
                                const rowObras = (row.Obras || 0) * m;
                                const rowProj = (row.Obras_Proj || 0) * m;
                                const rowFundExt = (row.Funding_Despesas || 0) * m;
                                const rowFundInt = 0; // Se houver captação interna futuramente
                                const rowMkt = (row.Despesas_Mkt || 0) * m;
                                const rowCom = (row.Despesas_Com || 0) * m;
                                const rowGA = (row.Despesas_Adm || 0) * m;
                                const rowSaidas = rowTributos + rowObras + rowProj + rowFundExt + rowFundInt + rowMkt + rowCom + rowGA;
                                const rowFCF = rowReceitas - rowSaidas;
                                const rowSaldoFinal = (row.Caixa_Acumulado || 0) * m;
                                const rowSaldoInicial = rowSaldoFinal - rowFCF;

                                return (
                                  <tr key={`row-${col.id}-${i}`} className="border-b border-slate-100 hover:bg-slate-50">
                                    <td className="p-1 text-center font-bold text-slate-800">{row.period}</td>

                                    <td className="p-1 font-semibold text-slate-600">{formatNumber(((row.Receitas_Entrada || 0) * m) / 1000)}</td>
                                    <td className="p-1 font-semibold text-slate-600">{formatNumber(((row.Receitas_Parcelas || 0) * m) / 1000)}</td>
                                    <td className="p-1 font-semibold text-slate-600">{formatNumber(((row.Receitas_Juros || 0) * m) / 1000)}</td>
                                    <td className="p-1 font-bold text-[#1a502e]">{formatNumber(rowReceitas / 1000)}</td>

                                    <td className="p-1 font-semibold text-slate-600">({formatNumber(rowTributos / 1000)})</td>
                                    <td className="p-1 font-semibold text-slate-600">({formatNumber(rowObras / 1000)})</td>
                                    <td className="p-1 font-semibold text-slate-600">({formatNumber(rowProj / 1000)})</td>
                                    <td className="p-1 font-semibold text-slate-600">({formatNumber(rowFundExt / 1000)})</td>
                                    <td className="p-1 font-semibold text-slate-600">({formatNumber(rowFundInt / 1000)})</td>
                                    <td className="p-1 font-semibold text-slate-600">({formatNumber(rowMkt / 1000)})</td>
                                    <td className="p-1 font-semibold text-slate-600">({formatNumber(rowCom / 1000)})</td>
                                    <td className="p-1 font-semibold text-slate-600">({formatNumber(rowGA / 1000)})</td>
                                    <td className="p-1 font-bold text-[#b34a1b]">({formatNumber(rowSaidas / 1000)})</td>

                                    <td className="p-1 font-bold text-slate-800">{formatNumber(rowFCF / 1000)}</td>
                                    <td className="p-1 font-semibold text-slate-600">{formatNumber(rowSaldoInicial / 1000)}</td>
                                    <td className="p-1 font-bold text-ml-dark">{formatNumber(rowSaldoFinal / 1000)}</td>
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    );
                  })}

                </div>
                );
      })}
              </div>
              );
};
