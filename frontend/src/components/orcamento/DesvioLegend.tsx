"use client";

export function DesvioLegend({ className = "" }: { className?: string }) {
  return (
    <div className={`flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500 ${className}`}>
      <span className="font-semibold uppercase tracking-wide text-slate-400">Desvios</span>
      <span className="inline-flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-brand-green" />
        Favorável
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-brand-orange" />
        Material (≥ 5%)
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-brand-red" />
        Atenção
      </span>
    </div>
  );
}
