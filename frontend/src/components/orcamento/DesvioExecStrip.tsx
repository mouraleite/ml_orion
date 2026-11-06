"use client";

import { AlertTriangle, CheckCircle2, MinusCircle } from "lucide-react";
import { SemaforoDesvio } from "@/components/orcamento/SemaforoDesvio";
import { formatMoedaK, formatPerc, type DesvioTipo } from "@/lib/orcamentoDesvioUi";
import { classesPainelSemaforo, estadoSemaforo } from "@/lib/semaforoDesvio";

interface DesvioExecStripProps {
  narrative: string;
  favoravel: boolean;
  varRs: number;
  varPerc: number;
  materialCount?: number;
  comDesvioCount?: number;
  refLabel?: string;
  n?: number;
  ref?: number;
  tipo?: DesvioTipo;
}

export function DesvioExecStrip({
  narrative,
  favoravel,
  varRs,
  varPerc,
  materialCount = 0,
  comDesvioCount = 0,
  refLabel = "referência",
  n,
  ref,
  tipo,
}: DesvioExecStripProps) {
  const temSemaforo = n != null && ref != null && tipo;
  const estado = temSemaforo ? estadoSemaforo(n, ref, tipo) : null;
  const Icon = estado
    ? estado.cor.includes("emerald")
      ? CheckCircle2
      : estado.cor.includes("slate")
        ? MinusCircle
        : AlertTriangle
    : varRs === 0
      ? MinusCircle
      : favoravel
        ? CheckCircle2
        : AlertTriangle;
  const tone = estado
    ? `border-slate-200 ${classesPainelSemaforo(estado).panel}`
    : varRs === 0
      ? "border-slate-200 bg-slate-50 text-slate-700"
      : favoravel
        ? "border-brand-green/30 bg-emerald-50/80 text-emerald-900"
        : materialCount > 0
          ? "border-brand-orange/40 bg-orange-50/80 text-orange-950"
          : "border-brand-red/30 bg-red-50/80 text-red-900";

  return (
    <div className={`rounded-xl border px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-3 shrink-0 ${tone}`}>
      <div className="flex items-start gap-3 min-w-0 flex-1">
        <Icon className="w-5 h-5 shrink-0 mt-0.5 opacity-80" />
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-wider opacity-70 mb-0.5">Leitura executiva</p>
          <p className="text-sm leading-snug">{narrative}</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 sm:justify-end shrink-0 text-xs">
        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-white/70 border border-white font-semibold tabular-nums">
          {temSemaforo ? <SemaforoDesvio n={n} ref={ref} tipo={tipo} /> : null}
          Δ {formatMoedaK(varRs)} ({formatPerc(varPerc)} vs {refLabel})
        </span>
        {comDesvioCount > 0 && (
          <span className="px-2 py-1 rounded-md bg-white/60 tabular-nums">
            {comDesvioCount} linha(s)
            {materialCount > 0 && ` · ${materialCount} material`}
          </span>
        )}
      </div>
    </div>
  );
}
