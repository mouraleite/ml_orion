"use client";

import {
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Line,
  ComposedChart,
} from "recharts";
import { formatMoedaK } from "@/lib/orcamentoDesvioUi";

type Row = { mes: string; referencia: number; real: number };

export default function GeracaoCaixaChart({
  data,
  modo,
}: {
  data: Row[];
  modo: "orcado" | "forecast";
}) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={(v) => formatMoedaK(v)} tick={{ fontSize: 10 }} width={72} />
        <Tooltip formatter={(v) => formatMoedaK(Number(v ?? 0))} />
        <Legend />
        <ReferenceLine y={0} stroke="#cbd5e1" />
        <Bar dataKey="referencia" name={modo === "orcado" ? "Orçado" : "Forecast"} fill="#64748b" radius={[4, 4, 0, 0]} />
        <Line type="monotone" dataKey="real" name="Realizado" stroke="#2E864D" strokeWidth={2.5} dot={{ r: 3 }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
