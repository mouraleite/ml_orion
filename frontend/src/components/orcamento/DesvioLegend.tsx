"use client";

export function DesvioLegend({ className = "" }: { className?: string }) {
  return (
    <div className={`flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500 ${className}`}>
      <span className="font-semibold uppercase tracking-wide text-slate-400">Semáforo</span>
      <span className="inline-flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-slate-300" />
        Imaterial (&lt; R$ 5 mil)
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-emerald-500" />
        Favorável ou ≤ 5%
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-amber-400" />
        Atenção (≤ 10%)
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-red-500" />
        Acima do limite
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-sky-500" />
        Novo
      </span>
    </div>
  );
}
