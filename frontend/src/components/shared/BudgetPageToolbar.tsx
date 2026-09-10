"use client";

import { ReactNode } from "react";
import { BudgetScopeBar } from "@/components/shared/BudgetScopeBar";
import { HoldingScope } from "@/lib/consolidacaoMldu";

interface BudgetPageToolbarProps {
  scope: HoldingScope;
  holdingMldu: boolean;
  onHoldingMlduChange: (value: boolean) => void;
  canUseHoldingMldu: boolean;
  /** Ano, versão forecast, etc. */
  contextControls?: ReactNode;
  /** Criar, Excel, Salvar… */
  actions?: ReactNode;
}

export function BudgetPageToolbar({
  scope,
  holdingMldu,
  onHoldingMlduChange,
  canUseHoldingMldu,
  contextControls,
  actions,
}: BudgetPageToolbarProps) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex flex-wrap items-end gap-2">
        <BudgetScopeBar
          scope={scope}
          holdingMldu={holdingMldu}
          onHoldingMlduChange={onHoldingMlduChange}
          canUseHoldingMldu={canUseHoldingMldu}
        />
        {contextControls}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-1.5 sm:justify-end">{actions}</div>
      )}
    </div>
  );
}
