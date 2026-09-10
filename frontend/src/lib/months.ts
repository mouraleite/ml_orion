/** Constantes de meses compartilhadas pelas grades mensais e vendas. */

export const MESES_KEYS = [
  "jan", "fev", "mar", "abr", "mai", "jun",
  "jul", "ago", "set", "out", "nov", "dez",
] as const;

export type MesKey = (typeof MESES_KEYS)[number];

export const MESES_VENDAS = [
  { id: 1, label: "jan" }, { id: 2, label: "fev" }, { id: 3, label: "mar" },
  { id: 4, label: "abr" }, { id: 5, label: "mai" }, { id: 6, label: "jun" },
  { id: 7, label: "jul" }, { id: 8, label: "ago" }, { id: 9, label: "set" },
  { id: 10, label: "out" }, { id: 11, label: "nov" }, { id: 12, label: "dez" },
] as const;

export function recalcularTotalAnual<T extends Record<string, unknown>>(item: T): T {
  const total = MESES_KEYS.reduce(
    (acc, mes) => acc + (Number(item[mes]) || 0),
    0,
  );
  return { ...item, total_anual: total };
}
