"use client";

import { useEffect, useState } from"react";
import { api } from"@/lib/api";
import { Card } from"@/components/ui/Card";
import { Building2, TrendingUp, AlertTriangle, DollarSign, FolderOpen, Activity } from"lucide-react";
import { 
 BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Line
} from 'recharts';
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

export default function GlobalDashboardPage() {
 const [data, setData] = useState<any>(null);
 const [isLoading, setIsLoading] = useState(true);

 useEffect(() => {
 const fetchSummary = async () => {
 try {
 const res = await api.get('/dashboard/summary');
 setData(res.data);
 } catch (error) {
 console.error("Erro ao carregar o dashboard consolidado", error);
 } finally {
 setIsLoading(false);
 }
 };
 fetchSummary();
 }, []);

 const formatCurrency = (val: number) => 
 new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(val || 0);

 if (isLoading) {
 return <AppLoadingState />;
 }

 if (!data) {
 return <div className="p-8 text-center text-slate-500">Erro ao carregar dados.</div>;
 }

 const { kpis, chart_data, project_breakdown } = data;

 return (
 <div className="p-8 space-y-8 animate-in fade-in duration-300">
 <div>
 <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Visão Global</h1>
 <p className="text-slate-500 mt-2">
 Consolidação de Fluxo de Caixa e Exposição Máxima de todos os projetos que possuem um <strong className="text-slate-700">Baseline Oficial</strong> congelado.
 </p>
 </div>

 {/* KPIs Principais */}
 <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
 <Card className="p-6 bg-white border-slate-200">
 <div className="flex items-center gap-4 mb-2">
 <div className="p-3 bg-green-50 text-green-700 rounded-lg">
 <FolderOpen className="w-6 h-6" />
 </div>
 <p className="text-sm font-medium text-slate-500">Empreendimentos Ativos (Base Oficial)</p>
 </div>
 <h3 className="text-3xl font-bold text-slate-800 ml-[60px]">{kpis.total_projects}</h3>
 </Card>

 <Card className="p-6 bg-white border-slate-200">
 <div className="flex items-center gap-4 mb-2">
 <div className="p-3 bg-green-50 text-green-700 rounded-lg">
 <DollarSign className="w-6 h-6" />
 </div>
 <p className="text-sm font-medium text-slate-500">VGV Total Projetado</p>
 </div>
 <h3 className="text-3xl font-bold text-slate-800 ml-[60px]">{formatCurrency(kpis.total_vgv)}</h3>
 </Card>

 <Card className="p-6 bg-white border-slate-200">
 <div className="flex items-center gap-4 mb-2">
 <div className="p-3 bg-red-50 text-red-600 rounded-lg">
 <TrendingUp className="w-6 h-6" />
 </div>
 <p className="text-sm font-medium text-slate-500">Exposição Máxima de Caixa Global</p>
 </div>
 <h3 className="text-3xl font-bold text-red-600 ml-[60px]">{formatCurrency(kpis.max_exposicao_global)}</h3>
 </Card>

 <Card className="p-6 bg-white border-slate-200">
 <div className="flex justify-between items-start">
 <div>
 <p className="text-sm font-semibold text-slate-500 mb-1">Lucro Líquido Global</p>
 <h3 className="text-2xl font-bold text-ml-green">{formatCurrency(kpis.total_lucro_liquido)}</h3>
 </div>
 <div className="p-2 bg-green-50 rounded-lg">
 <DollarSign className="w-6 h-6 text-ml-green" />
 </div>
 </div>
 <p className="text-xs text-slate-400 mt-4">Margem Consolidada: {kpis.global_margem.toFixed(2)}%</p>
 </Card>
 </div>

 {/* Gráfico Consolidado */}
 <Card className="p-6 shadow-sm">
 <div className="bg-white p-6 rounded-xl border border-slate-200">
 <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
 <Activity className="w-5 h-5 text-green-700" />
 Fluxo de Caixa Acumulado
 </h3>
 <div className="h-96 w-full">
 {chart_data && chart_data.length > 0 ? (
 <ResponsiveContainer width="100%" height="100%">
 <ComposedChart data={chart_data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
 <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
 <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#64748B', fontSize: 12}} />
 <YAxis yAxisId="left" axisLine={false} tickLine={false} tickFormatter={(val) => `R$ ${(val/1000000).toFixed(1)}M`} tick={{fill: '#64748B', fontSize: 12}} />
 <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tickFormatter={(val) => `R$ ${(val/1000000).toFixed(1)}M`} tick={{fill: '#64748B', fontSize: 12}} />
 <Tooltip 
 formatter={(value: any) => formatCurrency(value as number)}
 cursor={{fill: '#F1F5F9'}}
 contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}
 />
 <Legend />
 <Bar yAxisId="left" dataKey="Obras" name="Custos/Obras" fill="#ef4444" radius={[4, 4, 0, 0]} />
 <Bar yAxisId="left" dataKey="Receitas" name="Receitas" fill="#227f3f" radius={[4, 4, 0, 0]} />
 <Line yAxisId="right" type="monotone" dataKey="Acumulado" name="Caixa Acumulado" stroke="#f5822a" strokeWidth={3} dot={false} />
 </ComposedChart>
 </ResponsiveContainer>
 ) : (
 <div className="flex h-full items-center justify-center bg-slate-50 rounded-lg border border-dashed border-slate-300">
 <p className="text-slate-500">Nenhum projeto com Baseline Congelado encontrado para formar o gráfico global.</p>
 </div>
 )}
 </div>
 </div>
 </Card>

 {/* Tabela de Projetos */}
 <Card className="shadow-sm overflow-hidden">
 <div className="p-6 border-b border-slate-100">
 <h2 className="text-xl font-bold text-slate-900">Detalhamento por Projeto</h2>
 <p className="text-sm text-slate-500">Apenas estudos oficiais são listados nesta composição.</p>
 </div>
 <div className="overflow-x-auto">
 <table className="w-full text-sm text-left text-slate-600">
 <thead className="text-xs text-slate-500 uppercase bg-slate-50 border-b border-slate-200">
 <tr>
 <th className="px-6 py-4 font-medium">Projeto</th>
 <th className="px-6 py-4 font-medium">Status</th>
 <th className="px-6 py-4 font-medium text-right">VGV Oficial</th>
 <th className="px-6 py-4 font-medium text-right">VPL</th>
 <th className="px-6 py-4 font-medium text-right">TIR (a.a)</th>
 <th className="px-6 py-4 font-medium text-right">Lucro Líquido</th>
 </tr>
 </thead>
 <tbody>
 {project_breakdown.map((p: any, idx: number) => (
 <tr key={p.id} className={`border-b border-slate-100 hover:bg-slate-50 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}`}>
 <td className="px-6 py-4 font-bold text-slate-800">{p.project_name}</td>
 <td className="px-6 py-4">
 <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
 {p.status}
 </span>
 </td>
 <td className="px-6 py-4 text-right">{formatCurrency(p.vgv)}</td>
 <td className="px-6 py-4 text-right font-medium text-blue-600">{formatCurrency(p.vpl)}</td>
 <td className="px-6 py-4 text-right font-medium">{p.tir.toFixed(2)}%</td>
 <td className="px-6 py-4 text-right font-medium text-ml-green">{formatCurrency(p.lucro_liquido)}</td>
 </tr>
 ))}
 {project_breakdown.length === 0 && (
 <tr>
 <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
 Nenhum Baseline encontrado. Vá até a aba &quot;Resumo&quot; de uma viabilidade e congele uma versão para que ela venha para o consolidado!
 </td>
 </tr>
 )}
 </tbody>
 </table>
 </div>
 </Card>
 </div>
 );
}
