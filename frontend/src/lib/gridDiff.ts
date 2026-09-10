/** Classes CSS de diff vs itens_base (grades mensais). */

export function getMonthlyDiffClass<T extends Record<string, unknown>>(
  linha: T,
  campo: keyof T,
  itensBase: T[] | undefined | null,
  matchKeys: (a: T, b: T) => boolean,
  classes: {
    nova: string;
    alterada: string;
  } = {
    nova: "bg-brand-green/5",
    alterada: "bg-brand-orange-light/30 border-brand-orange-light text-slate-900",
  },
): string {
  if (!itensBase || itensBase.length === 0) return "";
  const linhaBase = itensBase.find((b) => matchKeys(linha, b));
  if (!linhaBase) return classes.nova;
  if (linha[campo] !== linhaBase[campo]) return classes.alterada;
  return "";
}

export function matchProdutoPlano<T extends { produto_id: number; plano_financeiro_id: number }>(
  a: T,
  b: T,
): boolean {
  return a.produto_id === b.produto_id && a.plano_financeiro_id === b.plano_financeiro_id;
}
