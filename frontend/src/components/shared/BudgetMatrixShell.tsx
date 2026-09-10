"use client";

import { ReactNode } from "react";

interface BudgetMatrixShellProps {
  title: string;
  subtitle?: string;
  /** Toolbar (ano, ações, escopo holding…) */
  toolbar?: ReactNode;
  /** Banners, VersionHeader, MonthSelector, filtros, alertas */
  chrome?: ReactNode;
  /** Grade, empty state ou loading */
  children: ReactNode;
  /** Mais altura útil (ex.: comparativo de versões com tabela grande) */
  tall?: boolean;
}

/**
 * Shell para telas de matriz mensal (orçamento / forecast).
 * Preenche a área útil do dashboard; scroll fica só na grade (filho flex-1).
 */
export function BudgetMatrixShell({
  title,
  subtitle,
  toolbar,
  chrome,
  children,
  tall = false,
}: BudgetMatrixShellProps) {
  return (
    <div
      className={
        tall
          ? "w-full flex flex-col gap-2 h-[calc(100dvh-4rem-1rem)] md:h-[calc(100dvh-4rem-1.5rem)] min-h-[480px]"
          : "w-full flex flex-col gap-2 h-[calc(100dvh-4rem-3rem)] md:h-[calc(100dvh-4rem-4rem)] min-h-[320px]"
      }
    >
      <div className="shrink-0 space-y-2 overflow-visible">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-slate-800 leading-tight">{title}</h1>
            {subtitle ? (
              <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
            ) : null}
          </div>
          {toolbar ? <div className="shrink-0 min-w-0">{toolbar}</div> : null}
        </div>
        {chrome}
      </div>

      <div className="flex-1 min-h-0 flex flex-col min-w-0 overflow-hidden">{children}</div>
    </div>
  );
}

/** Área rolável da grade dentro de Card */
export function BudgetMatrixScrollArea({ children }: { children: ReactNode }) {
  return (
    <div className="flex-1 min-h-0 overflow-auto budget-matrix-scroll">{children}</div>
  );
}

export const BUDGET_MATRIX_TABLE_CLASS =
  "w-full text-xs text-left text-slate-600 border-collapse tabular-nums budget-matrix-table";
