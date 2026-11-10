"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Trophy, TrendingUp, AlertTriangle, Lightbulb, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

interface ScenarioResult {
  id: number;
  project_name: string;
  is_root: boolean;
  score: number;
  is_winner: boolean;
  explanation: string;
  suggestions: string[];
  indicators: {
    vgv_total: number;
    custo_obras: number;
    valor_terreno: number;
    lucro_liquido: number;
    margem_perc: number;
    tir_aa: number | null;
    vpl: number;
    exposicao_maxima: number;
  };
}

const formatCurrency = (val: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(val || 0);

const formatPercent = (val: number | null) =>
  val === null || val === undefined
    ? "n/d"
    : new Intl.NumberFormat("pt-BR", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 }).format((val || 0) / 100);

export function ComparisonTab({ viabilityId }: { viabilityId: number }) {
  const [data, setData] = useState<ScenarioResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadComparison = async () => {
      try {
        setLoading(true);
        const res = await api.get(`/viabilities/${viabilityId}/compare-analysis`);
        setData(res.data);
      } catch (error) {
        console.error("Failed to load comparison data", error);
      } finally {
        setLoading(false);
      }
    };
    if (viabilityId) loadComparison();
  }, [viabilityId]);

  if (loading) {
    return <AppLoadingState />;
  }

  if (!data || data.length === 0) {
    return <div className="p-8 text-center text-slate-500">Nenhum dado encontrado para comparação.</div>;
  }

  return (
    <div className="p-6 space-y-8 bg-slate-50/50 min-h-screen">
      {/* Header Panel */}
      <div className="bg-gradient-to-r from-ml-green to-teal-700 rounded-2xl p-8 text-white shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-10">
          <Trophy className="w-48 h-48" />
        </div>
        <h2 className="text-3xl font-bold mb-2 flex items-center gap-3 relative z-10">
          <Lightbulb className="w-8 h-8 text-yellow-300" /> Comparador Inteligente de Cenários
        </h2>
        <p className="text-ml-green-100 max-w-2xl text-lg relative z-10">
          Nosso motor algorítmico avaliou {data.length} cenário(s) para este projeto. Descubra qual apresenta o melhor equilíbrio entre Margem, TIR e Exposição de Caixa.
        </p>
      </div>

      {/* Cards - Scenarios */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {data.map((scenario) => (
          <div 
            key={scenario.id} 
            className={`relative flex flex-col bg-white rounded-xl shadow-lg border transition-all duration-300 hover:shadow-xl ${
              scenario.is_winner 
                ? "border-amber-400 ring-2 ring-amber-400 ring-offset-2 scale-[1.02]" 
                : "border-slate-200"
            }`}
          >
            {scenario.is_winner && (
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-amber-400 text-amber-950 font-bold px-4 py-1 rounded-full text-sm shadow-md flex items-center gap-2">
                <Trophy className="w-4 h-4" /> VENCEDOR
              </div>
            )}
            
            <div className="p-6 border-b border-slate-100 flex-1">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-bold text-xl text-slate-800 line-clamp-2">{scenario.project_name}</h3>
                  {scenario.is_root && (
                    <span className="inline-block mt-1 px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded-full font-medium">
                      Projeto Original
                    </span>
                  )}
                </div>
              </div>

              {/* Score Circle */}
              <div className="flex flex-col items-center justify-center py-6">
                <div className="relative flex items-center justify-center w-24 h-24 mb-2">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="48" cy="48" r="44" stroke="currentColor" strokeWidth="6" fill="none" className="text-slate-100" />
                    <circle 
                      cx="48" cy="48" r="44" stroke="currentColor" strokeWidth="6" fill="none" 
                      className={`${scenario.is_winner ? 'text-amber-400' : 'text-ml-green'} transition-all duration-1000 ease-out`}
                      strokeDasharray="276"
                      strokeDashoffset={276 - (276 * scenario.score) / 100}
                    />
                  </svg>
                  <div className="absolute flex flex-col items-center justify-center">
                    <span className="text-3xl font-black text-slate-800">{scenario.score}</span>
                    <span className="text-[10px] uppercase font-bold text-slate-400">Score</span>
                  </div>
                </div>
              </div>

              {/* Explicação */}
              <div className="bg-slate-50 p-4 rounded-lg text-sm text-slate-700 leading-relaxed min-h-[5rem] mb-6 border border-slate-100">
                {scenario.explanation}
              </div>

              {/* Tabela de Indicadores Resumida */}
              <div className="space-y-3">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-500 font-medium">VGV Total:</span>
                  <span className="font-bold text-slate-800">{formatCurrency(scenario.indicators.vgv_total)}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-500 font-medium">Margem Líquida:</span>
                  <span className={`font-bold ${scenario.indicators.margem_perc >= 15 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatPercent(scenario.indicators.margem_perc)}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-500 font-medium">TIR (a.a.):</span>
                  <span className={`font-bold ${(scenario.indicators.tir_aa ?? -Infinity) >= 15 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatPercent(scenario.indicators.tir_aa)}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-500 font-medium">Exposição:</span>
                  <span className={`font-bold ${Math.abs(scenario.indicators.exposicao_maxima) > (scenario.indicators.vgv_total * 0.1) ? 'text-red-600' : 'text-slate-800'}`}>
                    {formatCurrency(scenario.indicators.exposicao_maxima)}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-500 font-medium">Lucro Líquido:</span>
                  <span className="font-bold text-slate-800">{formatCurrency(scenario.indicators.lucro_liquido)}</span>
                </div>
              </div>
            </div>

            {/* Dicas / Sugestões */}
            <div className="p-6 bg-slate-50 rounded-b-xl border-t border-slate-100 mt-auto">
              <h4 className="text-xs font-bold uppercase text-slate-500 mb-3 flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-amber-500" /> Insights & Sugestões
              </h4>
              <ul className="space-y-3">
                {scenario.suggestions.map((sug, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-700">
                    <CheckCircle2 className="w-4 h-4 text-ml-green shrink-0 mt-0.5" />
                    <span className="leading-tight">{sug}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
