/** Consolidação MLDU — filtro de tela (sem liberação no perfil) e query string. */

export type HoldingScope = "orcamento" | "forecast";

interface UserLike {
  pode_consolidacao_mldu_orcamento?: boolean;
  pode_consolidacao_mldu_forecast?: boolean;
  capabilities?: { admin?: boolean; diretor?: boolean };
}

/** Filtro da tela: quem já entrou vê. Não passa pela matriz de perfil. */
export function canConsolidacaoMldu(user: UserLike | null | undefined, _scope: HoldingScope): boolean {
  return Boolean(user);
}

export function buildBudgetQuery(consolidado = false, holdingMldu = false): string {
  const params = new URLSearchParams({ consolidado: String(consolidado) });
  if (holdingMldu) params.set("holding_mldu", "true");
  return params.toString();
}

export const HOLDING_SCOPE_LABEL: Record<HoldingScope, string> = {
  orcamento: "Orçamento",
  forecast: "Forecast",
};
