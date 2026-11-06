"use client";

import { SemaforoDesvio } from "@/components/orcamento/SemaforoDesvio";
import { formatMoedaCompact, formatPerc, isDesvioFavoravel, type DesvioTipo } from "@/lib/orcamentoDesvioUi";
import { varPercDesvio } from "@/lib/semaforoDesvio";

function Num({ v }: { v: number }) {
  const cls = v < 0 ? "text-red-600" : v > 0 ? "text-slate-800" : "text-slate-400";
  return <span className={`tabular-nums ${cls}`}>{formatMoedaCompact(v)}</span>;
}

function Perc({ v }: { v: number | null }) {
  if (v == null) return <span className="text-slate-300">—</span>;
  return <span className={`tabular-nums ${v < 0 ? "text-red-600" : "text-slate-700"}`}>{formatPerc(v)}</span>;
}

function Coluna({
  n,
  ref,
  nLabel,
  refLabel,
  tipo,
  showSemaforo = true,
}: {
  n: number;
  ref: number;
  nLabel: string;
  refLabel: string;
  tipo: DesvioTipo;
  showSemaforo?: boolean;
}) {
  const v = n - ref;
  const p = varPercDesvio(n, ref);
  const fav = isDesvioFavoravel(v, tipo);
  const varClass = fav ? "text-emerald-700" : "text-red-600";
  return (
    <div className="min-w-0">
      {showSemaforo ? (
        <div className="flex justify-end mb-2">
          <SemaforoDesvio n={n} ref={ref} tipo={tipo} />
        </div>
      ) : null}
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 items-baseline m-0">
        <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{nLabel}</dt>
        <dd className="m-0 text-lg font-bold tabular-nums text-slate-900 text-right whitespace-nowrap">
          <Num v={n} />
        </dd>
        <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{refLabel}</dt>
        <dd className="m-0 text-sm font-semibold tabular-nums text-slate-700 text-right whitespace-nowrap">
          <Num v={ref} />
        </dd>
        <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Var</dt>
        <dd className={`m-0 text-sm font-semibold tabular-nums text-right whitespace-nowrap ${varClass}`}>
          <Num v={v} />
          <span className="ml-2"><Perc v={p} /></span>
        </dd>
      </dl>
    </div>
  );
}

export function PeriodoKpiCard({
  titulo,
  legenda,
  hint,
  n,
  ref,
  nLabel,
  refLabel,
  tipo,
  mldu,
}: {
  titulo: string;
  legenda?: string;
  hint?: string;
  n: number;
  ref: number;
  nLabel: string;
  refLabel: string;
  tipo: DesvioTipo;
  mldu?: { n: number; ref: number; nLabel?: string; refLabel?: string };
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 min-w-0 overflow-hidden h-full" title={hint}>
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{titulo}</p>
          {legenda ? (
            <p className="text-[10px] text-slate-400 mt-0.5 tracking-normal">{legenda}</p>
          ) : null}
        </div>
        {mldu ? null : <SemaforoDesvio n={n} ref={ref} tipo={tipo} />}
      </div>
      {mldu ? (
        <div className="mt-2 grid grid-cols-2 gap-4">
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Cheio</p>
            <Coluna n={n} ref={ref} nLabel={nLabel} refLabel={refLabel} tipo={tipo} />
          </div>
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 mb-1">MLDU</p>
            <Coluna
              n={mldu.n}
              ref={mldu.ref}
              nLabel={mldu.nLabel || nLabel}
              refLabel={mldu.refLabel || refLabel}
              tipo={tipo}
            />
          </div>
        </div>
      ) : (
        <Coluna n={n} ref={ref} nLabel={nLabel} refLabel={refLabel} tipo={tipo} showSemaforo={false} />
      )}
    </div>
  );
}
