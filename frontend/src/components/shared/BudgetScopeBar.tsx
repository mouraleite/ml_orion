"use client";

import { GitBranch } from "lucide-react";
import { DepartmentFilter } from "@/components/shared/DepartmentFilter";
import { HoldingScope } from "@/lib/consolidacaoMldu";

interface BudgetScopeBarProps {
  scope: HoldingScope;
  holdingMldu: boolean;
  onHoldingMlduChange: (value: boolean) => void;
  canUseHoldingMldu: boolean;
  className?: string;
}

export function BudgetScopeBar({
  scope,
  holdingMldu,
  onHoldingMlduChange,
  canUseHoldingMldu,
  className = "",
}: BudgetScopeBarProps) {
  return (
    <div className={`flex flex-wrap items-end gap-3 ${className}`}>
      <DepartmentFilter />
      {canUseHoldingMldu && (
        <label className="flex items-center gap-2 text-sm text-slate-700 bg-orange-50 px-3 py-2 rounded-lg border border-orange-200 cursor-pointer select-none h-[38px] mt-auto">
          <input
            type="checkbox"
            checked={holdingMldu}
            onChange={(e) => onHoldingMlduChange(e.target.checked)}
            className="w-4 h-4 accent-[#F5883A]"
          />
          <GitBranch className="w-3.5 h-3.5 text-[#F5883A]" />
          <span className="font-medium whitespace-nowrap">Consolidação MLDU</span>
        </label>
      )}
    </div>
  );
}
