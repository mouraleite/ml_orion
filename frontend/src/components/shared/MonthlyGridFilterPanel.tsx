"use client";

import { Search } from "lucide-react";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Input } from "@/components/ui/Input";
import {
  CollapsibleFilterPanel,
  countActiveGridFilters,
} from "@/components/shared/CollapsibleFilterPanel";
import type { SelectOption } from "@/lib/gridFilters";

export interface MonthlyGridFilterValues {
  busca: string;
  filtroIdCentro: string[];
  filtroProduto: string[];
  filtroPlano: string[];
  filtroEmpresaIds: string[];
}

interface MonthlyGridFilterPanelProps {
  values: MonthlyGridFilterValues;
  onChange: (patch: Partial<MonthlyGridFilterValues>) => void;
  opcoesIdCentro: SelectOption[];
  opcoesProduto: SelectOption[];
  opcoesPlano: SelectOption[];
  opcoesEmpresaId: SelectOption[];
  opcoesEmpresaNome: SelectOption[];
  /** "Plano Financeiro" (despesas/receitas) ou "Forma de Venda" (vendas) */
  planoLabel?: string;
  /** Usa Input compacto (vendas) em vez de input nativo */
  useCompactInput?: boolean;
}

export function countMonthlyGridFilters(values: MonthlyGridFilterValues): number {
  return countActiveGridFilters(
    values.busca,
    values.filtroIdCentro,
    values.filtroProduto,
    values.filtroPlano,
    values.filtroEmpresaIds,
  );
}

export function MonthlyGridFilterPanel({
  values,
  onChange,
  opcoesIdCentro,
  opcoesProduto,
  opcoesPlano,
  opcoesEmpresaId,
  opcoesEmpresaNome,
  planoLabel = "Plano Financeiro",
  useCompactInput = false,
}: MonthlyGridFilterPanelProps) {
  const activeFilterCount = countMonthlyGridFilters(values);

  const clearAll = () => {
    onChange({
      busca: "",
      filtroIdCentro: [],
      filtroProduto: [],
      filtroPlano: [],
      filtroEmpresaIds: [],
    });
  };

  return (
    <CollapsibleFilterPanel activeFilterCount={activeFilterCount} onClear={clearAll}>
      <div className="flex-1 min-w-[200px]">
        <label className="text-xs text-slate-500 font-medium mb-1 flex items-center">
          <Search className="w-3.5 h-3.5 mr-1" />
          Buscar
        </label>
        {useCompactInput ? (
          <Input
            placeholder="Nome do centro de custo..."
            value={values.busca}
            onChange={(e) => onChange({ busca: e.target.value })}
            className="h-9"
          />
        ) : (
          <input
            type="text"
            placeholder="Nome do centro de custo..."
            className="w-full px-2.5 py-1.5 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
            value={values.busca}
            onChange={(e) => onChange({ busca: e.target.value })}
          />
        )}
      </div>

      <div className="flex-1 min-w-[150px]">
        <label className="text-xs text-slate-500 font-medium mb-1 block">ID Centro de Custo</label>
        <MultiSelect
          options={opcoesIdCentro}
          value={values.filtroIdCentro}
          onChange={(v) => onChange({ filtroIdCentro: v })}
          placeholder="Todos"
        />
      </div>

      <div className="flex-1 min-w-[180px]">
        <label className="text-xs text-slate-500 font-medium mb-1 block">Produto</label>
        <MultiSelect
          options={opcoesProduto}
          value={values.filtroProduto}
          onChange={(v) => onChange({ filtroProduto: v })}
          placeholder="Todos"
        />
      </div>

      <div className="flex-1 min-w-[200px]">
        <label className="text-xs text-slate-500 font-medium mb-1 block">{planoLabel}</label>
        <MultiSelect
          options={opcoesPlano}
          value={values.filtroPlano}
          onChange={(v) => onChange({ filtroPlano: v })}
          placeholder="Todos"
        />
      </div>

      <div className="flex-1 min-w-[120px]">
        <label className="text-xs text-slate-500 font-medium mb-1 block">ID Empresa</label>
        <MultiSelect
          options={opcoesEmpresaId}
          value={values.filtroEmpresaIds}
          onChange={(v) => onChange({ filtroEmpresaIds: v })}
          placeholder="Todos"
        />
      </div>

      <div className="flex-1 min-w-[180px]">
        <label className="text-xs text-slate-500 font-medium mb-1 block">Empresa</label>
        <MultiSelect
          options={opcoesEmpresaNome}
          value={values.filtroEmpresaIds}
          onChange={(v) => onChange({ filtroEmpresaIds: v })}
          placeholder="Todas"
        />
      </div>
    </CollapsibleFilterPanel>
  );
}
