"use client";

import { ReactNode } from "react";
import { Filter, RefreshCw } from "lucide-react";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { BudgetScopeBar } from "@/components/shared/BudgetScopeBar";
import { EmpresaLinkedFilters } from "@/components/orcamento/EmpresaLinkedFilters";
import { MESES_STR } from "@/lib/orcamentoDesvioUi";
import type { HoldingScope } from "@/lib/consolidacaoMldu";
import type { GridFilterOptionsResult } from "@/lib/gridFilters";

export type OrcamentoModo = "orcado" | "forecast";

export type FlyoutForecastOption = { id: number; descricao: string };

type Props = {
  scope?: HoldingScope;
  holdingMldu: boolean;
  onHoldingMlduChange: (value: boolean) => void;
  canUseHoldingMldu: boolean;
  empresaOpcoes: Pick<GridFilterOptionsResult, "empresasId" | "empresasNome">;
  filtroEmpresaIds: string[];
  onEmpresaChange: (ids: string[]) => void;
  meses: string[];
  onMesesChange: (meses: string[]) => void;
  mesesPlaceholder?: string;
  ano: number;
  onAnoChange: (ano: number) => void;
  modo?: OrcamentoModo;
  onModoChange?: (modo: OrcamentoModo) => void;
  showModo?: boolean;
  forecasts?: FlyoutForecastOption[];
  forecastId?: number | "";
  onForecastIdChange?: (id: number | "") => void;
  onRefresh?: () => void;
  loading?: boolean;
  children?: ReactNode;
};

const ANOS = [2024, 2025, 2026, 2027];

export function OrcamentoFlyoutFilterBar({
  scope = "orcamento",
  holdingMldu,
  onHoldingMlduChange,
  canUseHoldingMldu,
  empresaOpcoes,
  filtroEmpresaIds,
  onEmpresaChange,
  meses,
  onMesesChange,
  mesesPlaceholder = "Ano completo",
  ano,
  onAnoChange,
  modo,
  onModoChange,
  showModo = true,
  forecasts,
  forecastId,
  onForecastIdChange,
  onRefresh,
  loading,
  children,
}: Props) {
  const showForecastVersion = showModo && modo === "forecast" && onForecastIdChange;

  return (
    <div className="bg-white border border-slate-200 rounded-xl px-3 py-2.5 flex flex-wrap items-end gap-3 shrink-0">
      <BudgetScopeBar
        scope={scope}
        holdingMldu={holdingMldu}
        onHoldingMlduChange={onHoldingMlduChange}
        canUseHoldingMldu={canUseHoldingMldu}
      />
      <EmpresaLinkedFilters opcoes={empresaOpcoes} value={filtroEmpresaIds} onChange={onEmpresaChange} />
      <div className="w-44 z-10">
        <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Meses</label>
        <MultiSelect
          options={[...MESES_STR]}
          value={meses}
          onChange={onMesesChange}
          placeholder={mesesPlaceholder}
          className="bg-white"
        />
      </div>
      <div>
        <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Ano</label>
        <div className="flex items-center gap-2 border border-slate-200 rounded-lg px-3 py-2 text-sm">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={ano}
            onChange={(e) => onAnoChange(Number(e.target.value))}
            className="bg-transparent border-none outline-none font-semibold text-slate-700"
          >
            {ANOS.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>
      </div>
      {showModo && onModoChange && modo && (
        <div>
          <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Comparar com</label>
          <div className="flex rounded-lg overflow-hidden border border-slate-200">
            {(["orcado", "forecast"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => onModoChange(m)}
                className={`px-3 py-2 text-sm font-semibold transition-colors ${
                  modo === m ? "bg-ml-green text-white" : "bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {m === "orcado" ? "Orçado" : "Forecast"}
              </button>
            ))}
          </div>
        </div>
      )}
      {showForecastVersion && (
        <div>
          <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Versão</label>
          {forecasts && forecasts.length > 0 ? (
            <select
              value={forecastId || ""}
              onChange={(e) => onForecastIdChange(e.target.value ? Number(e.target.value) : "")}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 bg-white"
            >
              {forecasts.map((f) => (
                <option key={f.id} value={f.id}>{f.descricao}</option>
              ))}
            </select>
          ) : (
            <span className="text-slate-400 italic text-xs block py-2">Nenhum forecast cadastrado</span>
          )}
        </div>
      )}
      {children}
      {onRefresh && (
        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="p-2 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-700 hover:bg-slate-50 transition disabled:opacity-40 ml-auto"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      )}
    </div>
  );
}
