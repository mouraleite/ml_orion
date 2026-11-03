"use client";
import React, { useEffect, useState, Fragment } from "react";
import { useRouter, useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/Table";
import { ArrowLeft, Download, RefreshCcw, ChevronDown } from "lucide-react";
import { BotaoComoLemos, ComoLemosAcompanhamentoPanel } from "@/components/tracking/ComoLemosAcompanhamentoPanel";
import { fatosDoDetalhe } from "@/lib/comoLemosAcompanhamento";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend, LabelList } from 'recharts';
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

const formatCurrency = (val: number) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(val);
const formatPercent = (val: number | null | undefined) => {
  if (val === null || val === undefined) return "N/A";
  return new Intl.NumberFormat("pt-BR", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(val / 100);
};
const formatNumber = (val: number | null | undefined) => {
  if (val === null || val === undefined) return "N/A";
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(val);
};

export default function TrackingDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params?.id as string;
  const [viewMode, setViewMode] = useState<string>('consolidado');
  
  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [allProjects, setAllProjects] = useState<any[]>([]);

  const loadData = async () => {
    setIsLoading(true);
    let detalhe: any = null;
    try {
      const res = await api.get(`/tracking/${id}/details?view_mode=${viewMode}`);
      detalhe = res.data;
      setData(detalhe);
    } catch (e) {
      console.error(e);
      alert("Erro ao carregar detalhes.");
      setIsLoading(false);
      return;
    }
    const currentId = decodeURIComponent(id);
    const fallback = detalhe?.project_name
      ? [{ id: currentId, project_name: detalhe.project_name }]
      : [];
    try {
      const listRes = await api.get("/tracking/empreendimentos", { timeout: 60000 });
      const lista = Array.isArray(listRes.data) ? listRes.data : (listRes.data.items || []);
      if (currentId && !lista.some((p: any) => String(p.id) === currentId)) {
        lista.unshift({ id: currentId, project_name: detalhe?.project_name || currentId });
      }
      setAllProjects(lista);
    } catch (e) {
      console.error(e);
      setAllProjects(fallback);
    } finally {
      setIsLoading(false);
    }
  };

  const [isSyncing, setIsSyncing] = useState(false);
  const [expandedYears, setExpandedYears] = useState<Record<string, boolean>>({});
  const [painelMetodoAberto, setPainelMetodoAberto] = useState(false);

  const toggleYear = (year: string) => {
    setExpandedYears(prev => ({ ...prev, [year]: !prev[year] }));
  };

  const mockSalesVelocity = [
    { ano: "2021", vendas: 327, distratos: 0, saldo: 327, perc: 70.93, vel: 70.17, meses: [{ mes: "dez", vendas: 327, distratos: 0, saldo: 327, perc: 70.93, vel: 70.17 }] },
    { ano: "2022", vendas: 190, distratos: 153, saldo: 37, perc: 8.03, vel: 40.77, meses: [] },
    { ano: "2023", vendas: 174, distratos: 120, saldo: 54, perc: 11.71, vel: 37.34, meses: [] },
    { ano: "2024", vendas: 113, distratos: 72, saldo: 41, perc: 8.89, vel: 24.25, meses: [] },
    { ano: "2025", vendas: 69, distratos: 65, saldo: 4, perc: 0.87, vel: 14.81, meses: [] },
    { ano: "2026", vendas: 34, distratos: 36, saldo: -2, perc: -0.43, vel: 7.30, meses: [
        { mes: "jan", vendas: 7, distratos: 5, saldo: 2, perc: 0.43, vel: 1.50 },
        { mes: "fev", vendas: 2, distratos: 4, saldo: -2, perc: -0.43, vel: 0.43 },
        { mes: "mar", vendas: 5, distratos: 7, saldo: -2, perc: -0.43, vel: 1.07 },
        { mes: "abr", vendas: 8, distratos: 6, saldo: 2, perc: 0.43, vel: 1.72 },
        { mes: "mai", vendas: 6, distratos: 8, saldo: -2, perc: -0.43, vel: 1.29 },
        { mes: "jun", vendas: 4, distratos: 5, saldo: -1, perc: -0.22, vel: 0.86 },
        { mes: "jul", vendas: 2, distratos: 1, saldo: 1, perc: 0.22, vel: 0.43 }
    ]}
  ];

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await api.post('/sync/sienge', { full_load: false });
      alert("Sincronização iniciada! O ERP está sendo atualizado em segundo plano. Atualize a página em alguns minutos.");
    } catch (e) {
      alert("Erro ao iniciar a sincronização com o Sienge.");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleExport = () => {
    window.print();
  };

  useEffect(() => {
    if (id) loadData();
  }, [id, viewMode]);

  if (isLoading || !data) {
    return <AppLoadingState />;
  }

  const kpis = data.kpis || {};
  const dre = data.dre || [];
  const fc = data.fluxo_caixa || [];
  const defaultPlanos = {
    curto_longo: [
      { name: "Plano Curto", value: 12.3, color: "#0F766E" }, // Teal
      { name: "Plano Longo", value: 87.7, color: "#64748B" }  // Grey
    ],
    distribuicao: [
      { name: "Até 6x", curto: 0.8, longo: 0 },
      { name: "Até 12x", curto: 0.2, longo: 0 },
      { name: "Até 24x", curto: 7.6, longo: 0 },
      { name: "Até 36x", curto: 2.0, longo: 0 },
      { name: "Até 48x", curto: 1.8, longo: 0 },
      { name: "Até 60x", curto: 0, longo: 0.7 },
      { name: "Até 120x", curto: 0, longo: 4.0 },
      { name: "Até 156x", curto: 0, longo: 1.4 },
      { name: "Até 180x", curto: 0, longo: 81.6 }
    ]
  };
  const planos = (data?.planos_vendas && !Array.isArray(data.planos_vendas)) ? data.planos_vendas : defaultPlanos;

  const fcTotals = fc.reduce((acc: any, row: any) => {
    acc.Entradas += row.Entradas || 0;
    acc.Tributos += row.Tributos || 0;
    acc.Terreno += row.Terreno || 0;
    acc.Obras += row.Obras || 0;
    acc.Projetos += row.Projetos || 0;
    acc.Marketing += row.Marketing || 0;
    acc.Comercial += row.Comercial || 0;
    acc.Administrativas += Number(row.Administrativas || 0);
    acc.Devolucao_Distratos += Number(row.Devolucao_Distratos || 0);
    acc.Total_Saidas += Number(row.Total_Saidas || 0);
    return acc;
  }, {
    Entradas: 0, Tributos: 0, Terreno: 0, Obras: 0, Projetos: 0, Marketing: 0, Comercial: 0, Administrativas: 0, Devolucao_Distratos: 0, Total_Saidas: 0
  });

  const nomeProduto =
    allProjects.find((p) => String(p.id) === decodeURIComponent(id))?.project_name
    || data.project_name
    || decodeURIComponent(id);
  const fatosMetodo = fatosDoDetalhe({
    nome: nomeProduto,
    fase: data.status || allProjects.find((p) => String(p.id) === decodeURIComponent(id))?.status,
    kpis,
    dre,
    fluxoCaixa: fc,
  });

  const velVendas = data.velocidade_vendas || [];
  const velVendasTotal = velVendas.reduce((acc: any, curr: any) => {
    acc.vendas += curr.vendas;
    acc.distratos += curr.distratos;
    acc.saldo += curr.saldo;
    acc.perc += curr.perc;
    acc.vel += curr.vel;
    return acc;
  }, { vendas: 0, distratos: 0, saldo: 0, perc: 0, vel: 0 });
  
  // O % sobre total vendido deve ser a soma de todos os anos (fecha em 100%)
  // O acc.perc já acumulou isso na linha acima.

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">ACOMPANHAMENTO DE EMPREENDIMENTOS</h1>
      </div>

      {/* TABS */}
      <div className="flex overflow-x-auto border-b border-slate-200 hide-scrollbar mt-4">
        <button 
          onClick={() => router.push('/dashboard/tracking')}
          className="whitespace-nowrap px-6 py-3 font-medium text-sm text-slate-500 hover:text-slate-700 transition-colors"
        >
          Visão Geral
        </button>
        <button className="whitespace-nowrap px-6 py-3 font-medium text-sm border-b-2 border-brand-green text-brand-green transition-colors">
          Empreendimentos
        </button>
      </div>

      <div className="flex flex-col md:flex-row md:items-end justify-between mt-4 gap-4">
        <div className="flex flex-col md:flex-row items-end gap-6">
          <div>
            <span className="text-xs text-slate-500 font-medium mb-1.5 block">Selecione o Empreendimento</span>
            <div className="relative inline-block min-w-[320px]">
              <select 
                 key={id}
                 className="w-full py-2 pl-3 pr-10 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0F5B30]/40 focus:border-[#0F5B30] transition-colors cursor-pointer border-slate-200 text-slate-700 bg-white appearance-none font-medium"
                 value={decodeURIComponent(id)}
                 onChange={(e) => router.push('/dashboard/tracking/' + e.target.value)}
              >
                 {allProjects.map(p => (
                    <option key={p.id} value={String(p.id)}>{p.project_name}</option>
                 ))}
              </select>
              <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                 <ChevronDown className="w-4 h-4" />
              </div>
            </div>
          </div>
          
          <div>
            <span className="text-xs text-slate-500 font-medium mb-1.5 block">Visão de Parceria</span>
            <div className="flex items-center bg-slate-100 rounded-lg p-1 border border-slate-200">
              <button onClick={() => setViewMode('consolidado')} className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${viewMode === 'consolidado' ? 'bg-white shadow text-slate-900' : 'text-slate-500 hover:text-slate-700'}`}>Consolidada</button>
              <button onClick={() => setViewMode('empreendedor')} className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${viewMode === 'empreendedor' ? 'bg-white shadow text-slate-900' : 'text-slate-500 hover:text-slate-700'}`}>Empreendedor</button>
              <button onClick={() => setViewMode('parceiro')} className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${viewMode === 'parceiro' ? 'bg-white shadow text-slate-900' : 'text-slate-500 hover:text-slate-700'}`}>Parceiro</button>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <BotaoComoLemos onClick={() => setPainelMetodoAberto(true)} />
          <button 
            onClick={handleSync}
            disabled={isSyncing}
            className="flex items-center gap-2 px-4 py-2 border border-slate-200 text-slate-600 rounded-md hover:bg-slate-50 font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCcw className={`w-4 h-4 ${isSyncing ? 'animate-spin text-brand-green' : ''}`} /> 
            {isSyncing ? 'Sincronizando...' : 'Atualizar ERP'}
          </button>
          <button 
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 bg-brand-green text-white rounded-md hover:bg-emerald-700 font-medium text-sm"
          >
            <Download className="w-4 h-4" /> Exportar
          </button>
        </div>
      </div>

      {/* TOP KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">TIR Mensal</span>
          <span className="text-xl font-bold text-slate-900">{formatPercent(kpis.tir_mensal || 0)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">TIR Anual</span>
          <span className="text-xl font-bold text-slate-900">{formatPercent(kpis.tir_anual || 0)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">MTIR Mensal</span>
          <span className="text-xl font-bold text-slate-900">{formatPercent(kpis.mtir_mensal || 0)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">MTIR Anual</span>
          <span className="text-xl font-bold text-slate-900">{formatPercent(kpis.mtir_anual || 0)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">Rentabilidade do Investimento</span>
          <span className="text-xl font-bold text-slate-900">{formatPercent(kpis.rent_inv || 0)}</span>
        </Card>

        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">Exposição Máxima de Caixa</span>
          <span className="text-xl font-bold text-red-600">{formatCurrency(kpis.exposicao_max_caixa || 0)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">Período (Exposição)</span>
          <span className="text-xl font-bold text-slate-900">{formatNumber(kpis.periodo_exposicao || 0)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">Payback</span>
          <span className="text-xl font-bold text-slate-900">{formatNumber(kpis.payback || 0)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">Vida</span>
          <span className="text-xl font-bold text-slate-900">{formatNumber(kpis.vida || 0)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">Exposição de Caixa / VGV</span>
          <span className="text-xl font-bold text-slate-900">{formatPercent(kpis.exposicao_caixa_vgv || 0)}</span>
        </Card>
      </div>

      <div className="flex flex-col gap-6">
        {/* Top Section: 2 Columns */}
        <div className="grid lg:grid-cols-2 gap-6 items-start">
          
          {/* Left Column: DRE */}
          <Card className="p-0 border border-slate-200 shadow-sm overflow-hidden flex flex-col">
            <div className="bg-slate-100 border-b border-slate-200 px-4 py-3">
              <h2 className="text-base font-bold text-slate-700">DRE</h2>
            </div>
            <Table>
              <TableBody>
                {dre.map((row: any, idx: number) => (
                  <TableRow key={idx} className={`${row.bold ? 'bg-slate-50/50' : 'hover:bg-slate-50'}`}>
                    <TableCell className={`py-[0.6rem] ${row.bold ? 'font-bold text-slate-900' : 'text-slate-600'} ${row.indent ? 'pl-8' : ''}`}>
                      {row.item}
                    </TableCell>
                    <TableCell className={`py-[0.6rem] text-right ${row.bold ? 'font-bold text-slate-900' : 'text-slate-600'}`}>
                      {row.is_percentage ? row.valor : formatCurrency(row.valor)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>

          {/* Right Column: Planos e Velocidade */}
          <div className="flex flex-col space-y-6 sticky top-6 max-h-[calc(100vh-120px)]">
            {/* Módulo de Planos de Pagamento Sugerido */}
            {planos && (
              <Card className="p-0 border border-slate-200 shadow-sm overflow-hidden flex flex-col flex-initial shrink-0">
                <div className="bg-slate-100 border-b border-slate-200 px-4 py-3">
                  <h2 className="text-base font-bold text-slate-700">Planos Contratados</h2>
                </div>
                
                <div className="p-4 flex-1 flex flex-col lg:flex-row gap-8 items-stretch justify-center">
                  {/* Gráfico de Rosca */}
                  <div className="flex flex-col items-center justify-between w-full lg:w-1/3 self-stretch">
                    <div className="flex-1 flex items-center justify-center w-full">
                      <div className="h-[180px] w-full relative">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={planos.curto_longo}
                              cx="50%"
                              cy="50%"
                              innerRadius={50}
                              outerRadius={70}
                              paddingAngle={2}
                              dataKey="value"
                              stroke="none"
                              label={({ cx, cy, midAngle, innerRadius, outerRadius, value, name }) => {
                                const RADIAN = Math.PI / 180;
                                const radius = outerRadius * 1.3;
                                const x = cx + radius * Math.cos(-(midAngle || 0) * RADIAN);
                                const y = cy + radius * Math.sin(-(midAngle || 0) * RADIAN);
                                const textAnchor = x > cx ? 'start' : 'end';
                                return (
                                  <text x={x} y={y} fill="#64748b" textAnchor={textAnchor} dominantBaseline="central" fontSize={11} fontWeight={600}>
                                    {`${Number(value).toFixed(1).replace('.', ',')}%`}
                                  </text>
                                );
                              }}
                              labelLine={true}
                            >
                              {planos.curto_longo.map((entry: any, index: number) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                    <div className="text-[10px] text-slate-400 font-medium text-left w-full mt-auto">
                      **Plano Curto: Até 48x<br/>e Plano Longo: de 60x até 180x
                    </div>
                  </div>

                  {/* Gráfico de Barras */}
                  <div className="w-full lg:w-2/3 flex flex-col self-stretch">
                    <div className="flex-1 w-full min-h-[220px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={planos.distribuicao}
                          margin={{ top: 20, right: 0, left: -20, bottom: -5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                          <XAxis 
                            dataKey="name" 
                            axisLine={false} 
                            tickLine={false} 
                            tick={{ fontSize: 11, fill: '#64748b' }} 
                            dy={10}
                          />
                          <YAxis 
                            axisLine={false} 
                            tickLine={false} 
                            tick={{ fontSize: 11, fill: '#64748b' }}
                            tickFormatter={(value) => `${value}%`}
                          />
                          <Tooltip 
                            cursor={{ fill: '#f1f5f9' }}
                            formatter={(value: any) => [`${value}%`, 'Percentual']}
                            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                          />
                          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '15px' }} iconType="circle" />
                          <Bar dataKey="curto" name="Plano Curto" fill="#0F5B30" radius={[4, 4, 0, 0]} maxBarSize={40}>
                            <LabelList dataKey="curto" position="top" formatter={(val: any) => val > 0 ? `${val}%` : ''} style={{ fontSize: '9px', fill: '#64748b', fontWeight: 600 }} />
                          </Bar>
                          <Bar dataKey="longo" name="Plano Longo" fill="#94a3b8" radius={[4, 4, 0, 0]} maxBarSize={40}>
                            <LabelList dataKey="longo" position="top" formatter={(val: any) => val > 0 ? `${val}%` : ''} style={{ fontSize: '9px', fill: '#64748b', fontWeight: 600 }} />
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </Card>
            )}

          {/* Módulo de Tabela de Velocidade de Vendas Sugerido */}
            <Card className="p-0 border border-slate-200 shadow-sm overflow-hidden flex flex-col flex-initial min-h-0">
              <div className="bg-slate-100 border-b border-slate-200 px-4 py-3 flex justify-between items-center">
                <h2 className="text-base font-bold text-slate-700">Velocidade de Vendas</h2>
              </div>
              <div className="w-full flex-auto overflow-auto min-h-0">
                <Table className="w-full text-xs">
                  <TableHeader className="bg-slate-50 border-b border-slate-200 sticky top-0 z-10">
                    <TableRow>
                      <TableHead className="!text-center font-semibold text-slate-600 text-[10px] px-2">ANO / MÊS</TableHead>
                      <TableHead className="!text-center font-semibold text-slate-600 text-[10px] px-2">VENDAS</TableHead>
                      <TableHead className="!text-center font-semibold text-slate-600 text-[10px] px-2">DISTRATOS</TableHead>
                      <TableHead className="!text-center font-semibold text-slate-600 text-[10px] px-2">SALDO</TableHead>
                      <TableHead className="!text-center font-semibold text-slate-600 text-[10px] px-2">% SOBRE TOTAL VENDIDO</TableHead>
                      <TableHead className="!text-center font-semibold text-slate-600 text-[10px] px-2">VELOCIDADE</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {velVendas.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center p-8 text-slate-500">
                          Nenhum dado de velocidade de vendas disponível.
                        </TableCell>
                      </TableRow>
                    )}
                    {velVendas.map((row: any) => (
                      <Fragment key={row.ano}>
                        <TableRow 
                          className="hover:bg-slate-50 cursor-pointer border-b border-slate-100 transition-colors"
                          onClick={() => toggleYear(row.ano)}
                        >
                          <TableCell className="font-bold text-slate-700 flex items-center gap-1.5 py-2 px-2 whitespace-nowrap">
                            <span className="text-slate-400">
                              {expandedYears[row.ano] ? <ChevronDown className="w-3 h-3" /> : <ChevronDown className="w-3 h-3 -rotate-90" />}
                            </span>
                            {row.ano}
                          </TableCell>
                          <TableCell className="!text-center font-bold text-slate-700 py-2 px-2">{row.vendas}</TableCell>
                          <TableCell className="!text-center font-bold text-slate-700 py-2 px-2">{row.distratos > 0 ? row.distratos : '-'}</TableCell>
                          <TableCell className="!text-center font-bold text-slate-700 py-2 px-2">{row.saldo}</TableCell>
                          <TableCell className="!text-center font-bold text-slate-700 py-2 px-2">{row.perc.toFixed(2).replace('.', ',')}%</TableCell>
                          <TableCell className="!text-center font-bold text-slate-700 py-2 px-2">{row.vel.toFixed(2).replace('.', ',')}%</TableCell>
                        </TableRow>
                        
                        {expandedYears[row.ano] && row.meses && row.meses.map((mes: any, idx: number) => {
                          const [_, monthStr] = mes.mes.split('-');
                          const monthNames = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
                          const monthName = monthNames[parseInt(monthStr, 10) - 1];
                          
                          return (
                            <TableRow key={`${row.ano}-${idx}`} className="bg-slate-50/30 hover:bg-slate-50 border-0">
                              <TableCell className="text-slate-500 pl-7 py-1.5 text-[11px] px-2">{monthName}</TableCell>
                              <TableCell className="!text-center text-slate-600 py-1.5 text-[11px] px-2">{mes.vendas}</TableCell>
                              <TableCell className="!text-center text-slate-600 py-1.5 text-[11px] px-2">{mes.distratos > 0 ? mes.distratos : '-'}</TableCell>
                              <TableCell className="!text-center text-slate-600 py-1.5 text-[11px] px-2">{mes.saldo}</TableCell>
                              <TableCell className="!text-center text-slate-600 py-1.5 text-[11px] px-2">{mes.perc.toFixed(2).replace('.', ',')}%</TableCell>
                              <TableCell className="!text-center text-slate-600 py-1.5 text-[11px] px-2">{mes.vel.toFixed(2).replace('.', ',')}%</TableCell>
                            </TableRow>
                          );
                        })}
                      </Fragment>
                    ))}
                    {velVendas.length > 0 && (
                      <TableRow className="bg-slate-100 border-t border-slate-200">
                        <TableCell className="font-bold text-slate-900 py-2 px-2">Total</TableCell>
                        <TableCell className="!text-center font-bold text-slate-900 py-2 px-2">{velVendasTotal.vendas}</TableCell>
                        <TableCell className="!text-center font-bold text-slate-900 py-2 px-2">{velVendasTotal.distratos}</TableCell>
                        <TableCell className="!text-center font-bold text-slate-900 py-2 px-2">{velVendasTotal.saldo}</TableCell>
                        <TableCell className="!text-center font-bold text-slate-900 py-2 px-2">{velVendasTotal.perc.toFixed(2).replace('.', ',')}%</TableCell>
                        <TableCell className="!text-center font-bold text-slate-900 py-2 px-2">{velVendasTotal.vel > 0 || velVendasTotal.vel < 0 ? velVendasTotal.vel.toFixed(2).replace('.', ',') + '%' : '0,00%'}</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </Card>
        </div>
        </div>

        {/* Bottom Section: Fluxo de Caixa (Full Width) */}
        <div className="flex flex-col space-y-4">
          <Card className="p-0 border border-slate-200 shadow-sm overflow-hidden overflow-x-auto">
            <div className="bg-slate-100 border-b border-slate-200 px-4 py-3">
              <h2 className="text-base font-bold text-slate-700">Fluxo de Caixa</h2>
            </div>
            <Table>
              <TableHeader className="bg-slate-50/50">
                <TableRow>
                  <TableHead className="!text-center text-[11px] uppercase font-semibold text-slate-500 tracking-wider">Ano</TableHead>
                  <TableHead className="!text-center text-[11px] uppercase font-semibold text-slate-500 tracking-wider">Entradas</TableHead>
                  <TableHead className="!text-center text-[11px] uppercase font-semibold text-slate-500 tracking-wider">Dev. Distrato</TableHead>
                  <TableHead className="!text-center text-[11px] uppercase font-semibold text-slate-500 tracking-wider">Tributos</TableHead>
                  <TableHead className="!text-center text-[11px] uppercase font-semibold text-slate-500 tracking-wider">Terreno</TableHead>
                  <TableHead className="!text-center text-[11px] uppercase font-semibold text-slate-500 tracking-wider">Obras</TableHead>
                  <TableHead className="!text-center text-[11px] uppercase font-semibold text-slate-500 tracking-wider">Projetos</TableHead>
                  <TableHead className="!text-center text-[11px] uppercase font-semibold text-slate-500 tracking-wider">MKT</TableHead>
                  <TableHead className="!text-center text-[11px] uppercase font-semibold text-slate-500 tracking-wider">Comercial</TableHead>
                  <TableHead className="!text-center text-[11px] uppercase font-semibold text-slate-500 tracking-wider">Admin</TableHead>
                  <TableHead className="!text-center text-[11px] uppercase font-bold text-slate-600 tracking-wider">Total Saídas (T)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {fc.map((row: any, idx: number) => (
                  <TableRow 
                    key={idx} 
                    className={row.is_forecast ? "bg-blue-50 hover:bg-blue-100" : "hover:bg-slate-50"}
                  >
                    <TableCell className="font-medium text-slate-900">
                      {row.Ano}
                      {row.is_forecast && (
                        <span className="ml-2 text-xs font-semibold text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded">
                          Previsto
                        </span>
                      )}
                    </TableCell>
                    <TableCell className={`!text-center font-medium ${row.is_forecast ? 'text-blue-600' : 'text-brand-green'}`}>{formatCurrency(row.Entradas)}</TableCell>
                    <TableCell className="!text-center text-orange-500 font-medium">{formatCurrency(row.Devolucao_Distratos || 0)}</TableCell>
                    <TableCell className="!text-center text-slate-600">{formatCurrency(row.Tributos)}</TableCell>
                    <TableCell className="!text-center text-slate-600">{formatCurrency(row.Terreno || 0)}</TableCell>
                    <TableCell className="!text-center text-slate-600">{formatCurrency(row.Obras)}</TableCell>
                    <TableCell className="!text-center text-slate-600">{formatCurrency(row.Projetos)}</TableCell>
                    <TableCell className="!text-center text-slate-600">{formatCurrency(row.Marketing)}</TableCell>
                    <TableCell className="!text-center text-slate-600">{formatCurrency(row.Comercial)}</TableCell>
                    <TableCell className="!text-center text-slate-600">{formatCurrency(row.Administrativas)}</TableCell>
                    <TableCell className="!text-center font-bold text-red-600">{formatCurrency(row.Total_Saidas)}</TableCell>
                  </TableRow>
                ))}
                {fc.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center p-8 text-slate-500">
                      Nenhum fluxo de caixa projetado / realizado disponível.
                    </TableCell>
                  </TableRow>
                )}
                {fc.length > 0 && (
                  <TableRow className="bg-slate-100 hover:bg-slate-200 border-t-2 border-slate-300">
                    <TableCell className="font-bold text-slate-900 uppercase text-xs tracking-wider">Total</TableCell>
                    <TableCell className="!text-center font-bold text-brand-green">{formatCurrency(fcTotals.Entradas)}</TableCell>
                    <TableCell className="!text-center font-bold text-orange-500">{formatCurrency(fcTotals.Devolucao_Distratos)}</TableCell>
                    <TableCell className="!text-center font-bold text-slate-900">{formatCurrency(fcTotals.Tributos)}</TableCell>
                    <TableCell className="!text-center font-bold text-slate-900">{formatCurrency(fcTotals.Terreno || 0)}</TableCell>
                    <TableCell className="!text-center font-bold text-slate-900">{formatCurrency(fcTotals.Obras)}</TableCell>
                    <TableCell className="!text-center font-bold text-slate-900">{formatCurrency(fcTotals.Projetos)}</TableCell>
                    <TableCell className="!text-center font-bold text-slate-900">{formatCurrency(fcTotals.Marketing)}</TableCell>
                    <TableCell className="!text-center font-bold text-slate-900">{formatCurrency(fcTotals.Comercial)}</TableCell>
                    <TableCell className="!text-center font-bold text-slate-900">{formatCurrency(fcTotals.Administrativas)}</TableCell>
                    <TableCell className="!text-center font-bold text-red-600">{formatCurrency(fcTotals.Total_Saidas)}</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </div>
      </div>
      <ComoLemosAcompanhamentoPanel
        open={painelMetodoAberto}
        onClose={() => setPainelMetodoAberto(false)}
        fatos={fatosMetodo}
      />
    </div>
  );
}
