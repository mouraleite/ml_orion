"use client";

import { TrendingUp } from "lucide-react";
import { BudgetAcompMatrixPage } from "@/components/orcamento/BudgetAcompMatrixPage";
import { matchInvestimentos } from "@/lib/orcamentoPlanFilters";

export default function InvestimentosPage() {
  return (
    <BudgetAcompMatrixPage
      title="Investimentos e Participações"
      subtitle="Planos de investimento, aportes e participações — orçado, forecast e realizado"
      icon={TrendingUp}
      iconGradient="from-brand-dark-green to-slate-800"
      source="despesas"
      desvioTipo="DESPESAS"
      matchPlano={matchInvestimentos}
      emptyMessage="Nenhum plano de investimento encontrado. Verifique os planos financeiros cadastrados."
    />
  );
}
