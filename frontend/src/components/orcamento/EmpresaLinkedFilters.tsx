"use client";

import { MultiSelect } from "@/components/ui/MultiSelect";
import type { GridFilterOptionsResult } from "@/lib/gridFilters";

export function EmpresaLinkedFilters({
  opcoes,
  value,
  onChange,
}: {
  opcoes: Pick<GridFilterOptionsResult, "empresasId" | "empresasNome">;
  value: string[];
  onChange: (ids: string[]) => void;
}) {
  return (
    <>
      <div className="w-32 z-10">
        <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
          ID Empresa
        </label>
        <MultiSelect
          options={opcoes.empresasId}
          value={value}
          onChange={onChange}
          placeholder="Todos"
          className="bg-white"
        />
      </div>
      <div className="w-48 z-10">
        <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
          Empresa
        </label>
        <MultiSelect
          options={opcoes.empresasNome}
          value={value}
          onChange={onChange}
          placeholder="Todas"
          className="bg-white"
        />
      </div>
    </>
  );
}
