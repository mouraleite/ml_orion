"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

const fmtM = (v: number) =>
  v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 0, maximumFractionDigits: 0 });

const fmtK = (v: number) => {
  if (Math.abs(v) >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `R$ ${(v / 1_000).toFixed(0)}K`;
  return fmtM(v);
};

const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-xl p-3 text-xs min-w-[160px]">
      <div className="font-bold text-slate-700 mb-2">{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
            {p.name}
          </span>
          <span className="font-semibold tabular-nums">{fmtK(p.value)}</span>
        </div>
      ))}
    </div>
  );
};

type ChartView = "despesas" | "receitas" | "resultado" | "vgv";

type BarCfg = { key: string; name: string; color: string };

export default function ResumoGeralCharts({
  loading,
  hasData,
  wfChartData,
  chart,
  chartView,
  onChartViewChange,
  cfg,
  meses,
}: {
  loading: boolean;
  hasData: boolean;
  wfChartData: { name: string; transparent: number; value: number; actualValue: number; fill: string }[];
  chart: any[];
  chartView: ChartView;
  onChartViewChange: (v: ChartView) => void;
  cfg: { title: string; bars: BarCfg[] };
  meses: string[];
}) {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
        <h2 className="font-bold text-slate-700">Waterfall de Resultado</h2>
        {loading && !hasData ? (
          <AppLoadingState />
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={wfChartData} margin={{ top: 20, right: 16, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
              <YAxis tickFormatter={(v) => fmtK(v)} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} width={72} />
              <Tooltip
                cursor={{ fill: "transparent" }}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const row = payload[0].payload;
                  return (
                    <div className="bg-white border border-slate-200 rounded-xl shadow-xl p-3 text-xs min-w-[140px]">
                      <div className="font-bold text-slate-700 mb-2">{row.name}</div>
                      <div className="flex justify-between gap-4 font-semibold tabular-nums" style={{ color: row.fill }}>
                        <span>Valor:</span>
                        <span>{fmtM(row.actualValue)}</span>
                      </div>
                    </div>
                  );
                }}
              />
              <Bar dataKey="transparent" stackId="a" fill="transparent" />
              <Bar dataKey="value" stackId="a">
                {wfChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="xl:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h2 className="font-bold text-slate-700">{cfg.title}</h2>
          <div className="flex rounded-lg overflow-hidden border border-slate-200">
            {(["resultado", "despesas", "receitas", "vgv"] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => onChartViewChange(v)}
                className={`px-3 py-1.5 text-xs font-semibold capitalize transition-colors ${
                  chartView === v ? "bg-ml-green text-white" : "bg-white text-slate-500 hover:bg-slate-50"
                }`}
              >
                {v === "resultado" ? "Resultado" : v === "despesas" ? "Despesas" : v === "receitas" ? "Receitas" : "VGV"}
              </button>
            ))}
          </div>
        </div>

        {loading && !hasData ? (
          <AppLoadingState />
        ) : chart.length === 0 ? (
          <div className="h-72 flex items-center justify-center text-slate-400 text-sm">
            Sem dados para exibir no gráfico.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chart} margin={{ top: 8, right: 16, left: 8, bottom: 4 }} barCategoryGap="30%">
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="mes" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
              <YAxis tickFormatter={(v) => fmtK(v)} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} width={72} />
              <Tooltip content={<ChartTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {chartView === "resultado" && <ReferenceLine y={0} stroke="#cbd5e1" />}
              {cfg.bars.map((b) => (
                <Bar key={b.key} dataKey={b.key} name={b.name} fill={b.color} radius={[4, 4, 0, 0]}>
                  {chart.map((_entry: any, index: number) => {
                    const mStr = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"][index];
                    const isSelected = meses.length === 0 || meses.includes(mStr);
                    return <Cell key={`cell-${index}`} fill={b.color} fillOpacity={isSelected ? 1 : 0.25} />;
                  })}
                </Bar>
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
