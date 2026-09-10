/** Filtros client-side por nome de plano financeiro (sem alterar backend). */

export function matchInvestimentos(nome: string) {
  return /investimento|participaç|participac|aporte|divid/i.test(nome);
}

export function matchReceitaLotes(nome: string) {
  return /loteamento|venda de lote|receita de venda de lote/i.test(nome);
}

/** Agrupa planos de recebimento por padrão no nome (proxy para grupo de pagamento). */
export function recebimentoGrupoKey(nome: string): string {
  const n = nome.toUpperCase();
  if (/A VISTA|À VISTA|AVISTA/.test(n)) return "À vista";
  if (/SINAL|ENTRADA|ANTECIP/.test(n)) return "Sinal / antecipação";
  if (/PARCEL|FINANCI|BANCO|FGTS|CREDITO|CRÉDITO/.test(n)) return "Parcelado / financiamento";
  if (/MENSAL|ANUAL|RECORREN/.test(n)) return "Recorrente";
  return "Outros";
}

export function filterItensByPlanoNome(
  itens: any[],
  getPlanoNome: (id: number) => string,
  matcher: (nome: string) => boolean,
  planoField: "plano_financeiro_id" | "plano_venda_id" = "plano_financeiro_id",
) {
  return (itens || []).filter((item) => {
    const plId = item[planoField];
    if (!plId) return false;
    const nome = getPlanoNome(plId);
    return matcher(String(nome));
  });
}
