"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Plus, Target, CheckCircle2 } from "lucide-react";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

interface TrackingTabProps {
  phaseId: number;
}

export function TrackingTab({ phaseId }: TrackingTabProps) {
  const [actuals, setActuals] = useState<any[]>([]);
  const [baseline, setBaseline] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);

  // Form states
  const [categoria, setCategoria] = useState("Obras");
  const [mes, setMes] = useState(1);
  const [valor, setValor] = useState(0);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      // 1. Fetch Actuals
      const resActuals = await api.get(`/viabilities/phases/${phaseId}/actuals`);
      setActuals(resActuals.data);

      // 2. Fetch Baseline Snapshot (se existir)
      const resSnaps = await api.get(`/viabilities/phases/${phaseId}/snapshots`);
      const official = resSnaps.data.find((s: any) => s.is_baseline);
      if (official) {
        setBaseline(official.snapshot_data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [phaseId]);

  const handleAddActual = async () => {
    if (valor <= 0) return alert("O valor deve ser maior que zero.");
    try {
      await api.post(`/viabilities/phases/${phaseId}/actuals`, {
        categoria,
        mes_referencia: mes,
        valor_realizado: valor,
        observacao: "Lançamento Manual"
      });
      setValor(0);
      fetchData(); // recarrega
    } catch (error) {
      alert("Erro ao lançar valor real.");
    }
  };

  const handleSyncERP = async () => {
    setIsSyncing(true);
    try {
      const res = await api.post(`/viabilities/phases/${phaseId}/actuals/sync`, {});
      alert(res.data.message);
      fetchData(); // recarrega após sincronizar
    } catch (error) {
      alert("Erro ao sincronizar com ERP.");
    } finally {
      setIsSyncing(false);
    }
  };

  const formatCurrency = (val: number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);

  // PREPARAÇÃO DOS DADOS PARA O GRÁFICO
  // Vamos agrupar os custos de obra por mês (do baseline vs actuals)
  const chartData = [];
  
  if (baseline && baseline.monthly_cashflow) {
    const totalMeses = baseline.monthly_cashflow.length;
    for (let i = 0; i < totalMeses; i++) {
      const monthData = baseline.monthly_cashflow[i];
      // Valor orçado de Obra no mês i+1
      const orcadoObra = monthData["Custos de Obra"] || 0;
      
      // Valor realizado de Obra no mês i+1
      const actualObra = actuals.find(a => a.categoria === "Obras" && a.mes_referencia === (i + 1))?.valor_realizado || 0;

      // Só adiciona ao gráfico meses que tenham alguma das coisas para não ficar gigante
      if (orcadoObra > 0 || actualObra > 0 || i < 12) {
        chartData.push({
          name: `Mês ${i + 1}`,
          Orcado: orcadoObra,
          Realizado: actualObra,
        });
      }
    }
  }

  // Agrega totais da categoria "Obras"
  const totalOrcadoObra = baseline?.indicators?.custo_obras || 0;
  const totalRealizadoObra = actuals.filter(a => a.categoria === "Obras").reduce((sum, a) => sum + a.valor_realizado, 0);

  if (isLoading) return <AppLoadingState />;

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Acompanhamento (Real vs Orçado)</h2>
          <p className="text-sm text-slate-500">Compare a execução física/financeira contra o Baseline oficial do projeto.</p>
        </div>
        <div>
          <Button onClick={handleSyncERP} disabled={isSyncing || !baseline} className="bg-slate-800 hover:bg-slate-900 text-white shadow-sm flex items-center gap-2">
            {isSyncing ? "Sincronizando..." : "Sincronizar com ERP"}
          </Button>
        </div>
      </div>

      {!baseline ? (
        <div className="bg-amber-50 p-6 rounded-lg border border-amber-200 text-amber-800 text-center">
          <p className="font-bold">Nenhum Baseline Oficial Encontrado.</p>
          <p className="text-sm mt-1">Para acessar os gráficos comparativos, você precisa &quot;Congelar uma Versão Oficial&quot; na aba Resumo primeiro.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="p-5 border-l-4 border-l-ml-green flex flex-col justify-between">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-slate-500">Total Orçado (Obras)</span>
                <Target className="w-5 h-5 text-ml-green" />
              </div>
              <span className="text-2xl font-bold text-slate-900">{formatCurrency(totalOrcadoObra)}</span>
            </Card>

            <Card className="p-5 border-l-4 border-l-ml-orange flex flex-col justify-between">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-slate-500">Total Realizado (Obras)</span>
                <CheckCircle2 className="w-5 h-5 text-ml-orange" />
              </div>
              <div>
                <span className="text-2xl font-bold text-slate-900">{formatCurrency(totalRealizadoObra)}</span>
                {totalOrcadoObra > 0 && (
                  <span className="text-sm text-slate-500 ml-2">
                    ({((totalRealizadoObra / totalOrcadoObra) * 100).toFixed(1)}% consumido)
                  </span>
                )}
              </div>
            </Card>
          </div>

          <Card className="p-6">
            <h3 className="font-bold text-slate-900 mb-6">Comparativo Mensal (Obras)</h3>
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#64748B', fontSize: 12}} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748B', fontSize: 12}} tickFormatter={(val) => `R$ ${(val/1000).toFixed(0)}k`} />
                  <Tooltip 
                    formatter={(value: any) => formatCurrency(value as number)}
                    cursor={{fill: '#F1F5F9'}}
                    contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}
                  />
                  <Legend iconType="circle" />
                  <Bar dataKey="Orcado" fill="#154e38" radius={[4, 4, 0, 0]} name="Orçado" />
                  <Bar dataKey="Realizado" fill="#f5822a" radius={[4, 4, 0, 0]} name="Realizado" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Lançamento Manual */}
          <Card className="p-6 bg-slate-50 border-dashed border-2 border-slate-200">
            <h3 className="font-bold text-slate-800 mb-2 flex items-center gap-2">
              Lançamentos Extraordinários (Manual)
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              A alimentação principal ocorre via botão &quot;Sincronizar com ERP&quot; acima. Utilize este quadro 
              apenas para inserir &quot;Realizados&quot; não registrados no sistema de origem.
            </p>
            <div className="flex items-end gap-4">
              <div className="flex-1 space-y-1">
                <label className="text-xs font-semibold text-slate-600">Categoria</label>
                <select className="w-full flex h-10 rounded-md border border-slate-300 bg-white px-3" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
                  <option value="Obras">Obras</option>
                  <option value="Receitas">Receitas</option>
                  <option value="Despesas">Despesas Admin/Comercial</option>
                </select>
              </div>
              <div className="flex-1 space-y-1">
                <label className="text-xs font-semibold text-slate-600">Mês do Cronograma (Ex: 1)</label>
                <Input type="number" value={mes} onChange={(e) => setMes(parseInt(e.target.value) || 1)} />
              </div>
              <div className="flex-1 space-y-1">
                <label className="text-xs font-semibold text-slate-600">Valor Realizado (R$)</label>
                <Input type="number" value={valor} onChange={(e) => setValor(parseFloat(e.target.value) || 0)} />
              </div>
              <Button onClick={handleAddActual} className="bg-ml-green hover:bg-ml-dark text-white gap-2">
                <Plus className="w-4 h-4" /> Lançar
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
