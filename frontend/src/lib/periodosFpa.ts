/** Recortes de ano civil no produto. Não confundir com "cheio" (100% vs MLDU). */

export const SIGLAS_PERIODO = {
  ytd: "YTD",
  ytg: "YTG",
  fy: "FY",
  ly: "LY",
} as const;

export type ChavePeriodo = keyof typeof SIGLAS_PERIODO;

export const PERIODOS_KPI = ["ytd", "ytg", "fy"] as const;

export const GLOSSA_PERIODO: Record<ChavePeriodo, string> = {
  ytd: "realizado até o corte",
  ytg: "restante do ano",
  fy: "ano cheio (YTD + YTG)",
  ly: "ano anterior",
};

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"] as const;

export function tituloPeriodo(chave: ChavePeriodo): string {
  return SIGLAS_PERIODO[chave];
}

export function hintPeriodo(chave: ChavePeriodo): string {
  return `${SIGLAS_PERIODO[chave]} — ${GLOSSA_PERIODO[chave]}`;
}

export function corteNoAno(corte: number): number {
  const n = Number(corte);
  if (!Number.isFinite(n) || n < 1) return 1;
  if (n > 12) return 12;
  return Math.floor(n);
}

export function legendaPeriodo(chave: "ytd" | "ytg" | "fy", corte: number): string {
  const c = corteNoAno(corte);
  if (chave === "fy") return "YTD + YTG";
  if (chave === "ytd") return `jan–${MESES[c - 1]}`;
  if (c >= 12) return "sem meses";
  return `${MESES[c]}–dez`;
}
