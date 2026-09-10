import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

export default function OrcamentoLoading() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white min-h-[40vh]">
      <AppLoadingState />
    </div>
  );
}
