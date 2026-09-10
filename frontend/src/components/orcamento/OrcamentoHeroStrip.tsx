"use client";

import Link from "next/link";
import { formatMoedaK, formatPerc } from "@/lib/orcamentoDesvioUi";

function vereditoLabel(favoravel: boolean, varRs: number) {
  if (varRs === 0) return "Neutro";
  return favoravel ? "Favorável" : "Requer atenção";
}

export function OrcamentoHeroStrip({
  refLabel,
  refVal,
  realVal,
  varRs,
  varPerc,
  favoravel,
  material,
  caption = "Comparação no período filtrado",
  refCaption,
}: {
  refLabel: string;
  refVal: number;
  realVal: number;
  varRs: number;
  varPerc: number;
  favoravel: boolean;
  material?: boolean;
  caption?: string;
  refCaption?: string;
}) {
  const tone = varRs === 0
    ? "bg-slate-50/80 text-slate-800"
    : favoravel
      ? "bg-emerald-50/80 text-emerald-800"
      : material
        ? "bg-orange-50/80 text-orange-950"
        : "bg-red-50/80 text-red-800";
  const label = vereditoLabel(favoravel, varRs);

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] divide-y md:divide-y-0 md:divide-x divide-slate-100">
        <div className="px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5">{refLabel}</p>
          <p className="text-xl font-bold text-slate-900 tabular-nums">{formatMoedaK(refVal)}</p>
          {refCaption ? <p className="text-[11px] text-slate-500">{refCaption}</p> : null}
        </div>
        <div className={`px-5 py-3 flex flex-col items-center justify-center text-center min-w-[168px] ${tone}`}>
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
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
          varRs === 0 ? "bg-slate-100 text-slate-600" : favoravel ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
        }`}>
          {label}
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
  invert = false,
  href,
  linkLabel,
}: {
  title: string;
  realVal: string;
  refVal: string;
  desvio?: number;
  invert?: boolean;
  href?: string;
  linkLabel?: string;
}) {
  const good = desvio == null ? null : invert ? desvio <= 0 : desvio >= 0;
  const deltaClass = good === null ? "text-slate-600" : good ? "text-emerald-700" : "text-red-700";
  return (
    <div className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex flex-col gap-1.5 min-w-0">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{title}</p>
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
