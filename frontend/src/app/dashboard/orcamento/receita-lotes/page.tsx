"use client";

import { Home } from "lucide-react";
import { BudgetAcompMatrixPage } from "@/components/orcamento/BudgetAcompMatrixPage";
import { matchReceitaLotes } from "@/lib/orcamentoPlanFilters";

export default function ReceitaLotesPage() {
  return (
    <BudgetAcompMatrixPage
      title="Receita de Lotes"
      subtitle="Receitas de loteamentos e venda de lotes por produto e plano financeiro"
      icon={Home}
      iconGradient="from-brand-green to-brand-dark-green"
      source="receitas"
      desvioTipo="RECEITAS"
      matchPlano={matchReceitaLotes}
      emptyMessage="Nenhuma receita de loteamento encontrada para o ano selecionado."
    />
  );
}
