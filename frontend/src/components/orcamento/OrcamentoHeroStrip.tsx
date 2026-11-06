"use client";

import Link from "next/link";
import { SemaforoDesvio } from "@/components/orcamento/SemaforoDesvio";
import { formatMoedaK, formatPerc, type DesvioTipo } from "@/lib/orcamentoDesvioUi";
import { classesPainelSemaforo, estadoSemaforo } from "@/lib/semaforoDesvio";

export function OrcamentoHeroStrip({
  refLabel,
  refVal,
  realVal,
  varRs,
  varPerc,
  tipo = "RESULTADO",
  caption = "Comparação no período filtrado",
  refCaption,
  favoravel: _favoravel,
  material: _material,
}: {
  refLabel: string;
  refVal: number;
  realVal: number;
  varRs: number;
  varPerc: number;
  tipo?: DesvioTipo;
  caption?: string;
  refCaption?: string;
  favoravel?: boolean;
  material?: boolean;
}) {
  const estado = estadoSemaforo(realVal, refVal, tipo);
  const tone = classesPainelSemaforo(estado);

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] divide-y md:divide-y-0 md:divide-x divide-slate-100">
        <div className="px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5">{refLabel}</p>
          <p className="text-xl font-bold text-slate-900 tabular-nums">{formatMoedaK(refVal)}</p>
          {refCaption ? <p className="text-[11px] text-slate-500">{refCaption}</p> : null}
        </div>
        <div className={`px-5 py-3 flex flex-col items-center justify-center text-center min-w-[168px] ${tone.panel}`}>
          <p className="text-[10px] font-semibold uppercase tracking-wider opacity-70 mb-0.5">Variação</p>
          <p className="text-xl font-bold tabular-nums">
            {varRs > 0 ? "+" : ""}{formatMoedaK(varRs)}
          </p>
          <p className="text-[11px] font-semibold tabular-nums">{formatPerc(varPerc)}</p>
        </div>
        <div className="px-4 py-3 md:text-right">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5">Realizado</p>
          <p className="text-xl font-bold text-slate-900 tabular-nums">{formatMoedaK(realVal)}</p>
        </div>
      </div>
      <div className="px-4 py-1.5 border-t border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-2">
        <span className="text-[11px] text-slate-500">{caption}</span>
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${tone.badge}`}>
          <SemaforoDesvio n={realVal} ref={refVal} tipo={tipo} />
          {estado.titulo}
        </span>
      </div>
    </div>
  );
}

export function OrcamentoSecondaryMetric({
  title,
  realVal,
  refVal,
  desvio,
  n,
  ref,
  tipo,
  invert: _invert,
  href,
  linkLabel,
}: {
  title: string;
  realVal: string;
  refVal: string;
  desvio?: number;
  n?: number;
  ref?: number;
  tipo?: DesvioTipo;
  invert?: boolean;
  href?: string;
  linkLabel?: string;
}) {
  const temSemaforo = n != null && ref != null && tipo;
  const estado = temSemaforo ? estadoSemaforo(n, ref, tipo) : null;
  const deltaClass = estado
    ? estado.cor.includes("emerald")
      ? "text-emerald-700"
      : estado.cor.includes("red")
        ? "text-red-700"
        : estado.cor.includes("amber")
          ? "text-amber-800"
          : "text-slate-600"
    : "text-slate-600";
  return (
    <div className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex flex-col gap-1.5 min-w-0">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{title}</p>
        {temSemaforo ? <SemaforoDesvio n={n} ref={ref} tipo={tipo} /> : null}
      </div>
      <p className="text-lg font-bold text-slate-900 tabular-nums leading-tight">{realVal}</p>
      <p className="text-[11px] text-slate-500 tabular-nums">
        {refVal}
        {desvio != null && (
          <span className={`ml-2 font-semibold ${deltaClass}`}>{formatPerc(desvio)}</span>
        )}
      </p>
      {href && linkLabel ? (
        <Link href={href} className="text-[11px] font-semibold text-ml-green hover:underline w-fit">
          {linkLabel}
        </Link>
      ) : null}
    </div>
  );
}
