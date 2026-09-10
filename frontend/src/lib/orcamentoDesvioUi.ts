export const MESES_STR = [
  "jan", "fev", "mar", "abr", "mai", "jun",
  "jul", "ago", "set", "out", "nov", "dez",
] as const;

export const MATERIALITY_THRESHOLD = 0.05;

export type DesvioTipo = "DESPESAS" | "RECEITAS" | "VENDAS" | "RESULTADO";

export function formatMoedaCompact(v: number) {
  if (!v) return "R$ 0";
  return v.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

export function formatMoedaK(v: number) {
  if (Math.abs(v) >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `R$ ${(v / 1_000).toFixed(0)}K`;
  return formatMoedaCompact(v);
}

export function formatPerc(v: number) {
  if (v == null || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(1).replace(".", ",")}%`;
}

export function isDesvioFavoravel(varRs: number, tipo: DesvioTipo) {
  if (tipo === "DESPESAS") return varRs <= 0;
  return varRs >= 0;
}

export function computeItemDesvio(item: any, modo: "orcado" | "forecast") {
  const ref = item?.[modo]?.total ?? 0;
  const real = item?.realizado?.total ?? 0;
  const varRs = real - ref;
  const varPerc = ref !== 0 ? varRs / Math.abs(ref) : real !== 0 ? 1 : 0;
  return {
    ref,
    real,
    varRs,
    varPerc,
    absVarRs: Math.abs(varRs),
    material: Math.abs(varPerc) >= MATERIALITY_THRESHOLD,
  };
}

export function rowHighlightClass(
  varPerc: number,
  favoravel: boolean,
  material = Math.abs(varPerc) >= MATERIALITY_THRESHOLD,
) {
  if (varPerc === 0) return "";
  if (favoravel) return "ring-1 ring-inset ring-brand-green/20 bg-emerald-50/40";
  if (material) return "ring-1 ring-inset ring-brand-orange/30 bg-orange-50/50";
  return "ring-1 ring-inset ring-brand-red/15 bg-red-50/35";
}

export function buildExecInsights(
  itens: any[],
  modo: "orcado" | "forecast",
  tipo: DesvioTipo,
) {
  const lines = itens.map((item) => ({
    item,
    ...computeItemDesvio(item, modo),
    favoravel: isDesvioFavoravel(
      (item?.realizado?.total ?? 0) - (item?.[modo]?.total ?? 0),
      tipo,
    ),
  }));

  const comDesvio = lines.filter((l) => l.absVarRs > 0.01);
  const refTotal = lines.reduce((s, l) => s + l.ref, 0);
  const realTotal = lines.reduce((s, l) => s + l.real, 0);
  const varRs = realTotal - refTotal;
  const varPerc = refTotal !== 0 ? varRs / Math.abs(refTotal) : 0;
  const favoravel = isDesvioFavoravel(varRs, tipo);
  const material = comDesvio.filter((l) => l.material && !l.favoravel);
  const top = [...comDesvio].sort((a, b) => b.absVarRs - a.absVarRs)[0];

  const refLabel = modo === "orcado" ? "orçado" : "forecast";
  const narrative = comDesvio.length === 0
    ? `Sem desvios relevantes vs ${refLabel}.`
    : favoravel
      ? `${formatMoedaK(Math.abs(varRs))} ${varRs >= 0 ? "acima" : "abaixo"} da referência (${formatPerc(varPerc)}). ${comDesvio.length} linha(s) com movimento.`
      : `${formatMoedaK(Math.abs(varRs))} ${varRs >= 0 ? "acima" : "abaixo"} da referência (${formatPerc(varPerc)}). ${material.length} linha(s) com desvio material requer atenção.`;

  return {
    refTotal,
    realTotal,
    varRs,
    varPerc,
    favoravel,
    materialCount: material.length,
    comDesvioCount: comDesvio.length,
    topAbsVar: top?.absVarRs ?? 0,
    narrative,
  };
}
