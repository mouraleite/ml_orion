"use client";

import { ReactNode, useEffect, useState } from "react";
import { ChevronDown, Eraser, Filter } from "lucide-react";
import { Card } from "@/components/ui/Card";

interface CollapsibleFilterPanelProps {
  children: ReactNode;
  activeFilterCount?: number;
  /** Aberto por padrão quando há filtros ativos */
  defaultOpen?: boolean;
  onClear?: () => void;
  clearTitle?: string;
}

export function countActiveGridFilters(
  busca: string,
  ...multiSelects: { length: number }[]
): number {
  let count = busca.trim() ? 1 : 0;
  for (const list of multiSelects) {
    if (list.length > 0) count += 1;
  }
  return count;
}

export function CollapsibleFilterPanel({
  children,
  activeFilterCount = 0,
  defaultOpen = false,
  onClear,
  clearTitle = "Limpar todos os filtros",
}: CollapsibleFilterPanelProps) {
  const [open, setOpen] = useState(defaultOpen || activeFilterCount > 0);

  useEffect(() => {
    if (activeFilterCount > 0) setOpen(true);
  }, [activeFilterCount]);

  return (
    <Card className="shrink-0 bg-white shadow-sm overflow-visible p-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500 shrink-0" />
          Filtros
          {activeFilterCount > 0 ? (
            <span className="bg-brand-green/10 text-brand-green text-xs font-semibold px-2 py-0.5 rounded-full">
              {activeFilterCount}
            </span>
          ) : null}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-slate-400 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open ? (
        <div className="px-3 pb-3 pt-2 flex flex-wrap gap-3 items-end border-t border-slate-100">
          {children}
          {onClear ? (
            <button
              type="button"
              onClick={onClear}
              className="flex items-center justify-center h-[34px] px-3 text-slate-500 bg-white border border-slate-300 rounded-md hover:bg-brand-orange/10 hover:text-brand-orange hover:border-brand-orange/30 transition-all shadow-sm group mb-[2px]"
              title={clearTitle}
            >
              <Eraser className="w-4 h-4 group-hover:scale-110 transition-transform" />
            </button>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
