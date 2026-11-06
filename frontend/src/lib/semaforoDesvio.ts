import { isDesvioFavoravel, type DesvioTipo } from "./orcamentoDesvioUi.ts";

/** Mesma régua da Análise de Orçamento. */
export const SEMAFORO_IMATERIAL_RS = 5000;
export const SEMAFORO_TOLERANCIA = 0.05;
export const SEMAFORO_LIMITE = 0.10;

export type SemaforoEstado = {
  cor: string;
  titulo: string;
};

export function varPercDesvio(n: number, ref: number): number | null {
  if (Math.abs(ref) < 1e-12) return Math.abs(n) > 1e-12 ? 1 : null;
  return (n - ref) / Math.abs(ref);
}

export function estadoSemaforo(n: number, ref: number, tipo: DesvioTipo): SemaforoEstado {
  const v = n - ref;
  if (Math.abs(ref) < 1e-12 && Math.abs(n) > 1e-12) {
    return { cor: "bg-sky-500", titulo: "Novo" };
  }
  if (Math.abs(v) < SEMAFORO_IMATERIAL_RS) return { cor: "bg-slate-300", titulo: "Imaterial" };
  const p = Math.abs(varPercDesvio(n, ref) || 0);
  const fav = isDesvioFavoravel(v, tipo);
  if (fav || p <= SEMAFORO_TOLERANCIA) {
    return { cor: "bg-emerald-500", titulo: fav ? "Favorável" : "Dentro da tolerância" };
  }
  if (p <= SEMAFORO_LIMITE) return { cor: "bg-amber-400", titulo: "Atenção" };
  return { cor: "bg-red-500", titulo: "Acima do limite" };
}

export function tipoSemaforo(tipo: string | null | undefined): DesvioTipo {
  if (tipo === "DESPESAS" || tipo === "RECEITAS" || tipo === "VENDAS" || tipo === "RESULTADO") {
    return tipo;
  }
  return "RESULTADO";
}

export function classesPainelSemaforo(s: SemaforoEstado): { panel: string; badge: string } {
  if (s.cor.includes("sky")) return { panel: "bg-sky-50/80 text-sky-900", badge: "bg-sky-100 text-sky-800" };
  if (s.cor.includes("slate")) return { panel: "bg-slate-50/80 text-slate-800", badge: "bg-slate-100 text-slate-600" };
  if (s.cor.includes("emerald")) return { panel: "bg-emerald-50/80 text-emerald-800", badge: "bg-emerald-100 text-emerald-800" };
  if (s.cor.includes("amber")) return { panel: "bg-amber-50/80 text-amber-950", badge: "bg-amber-100 text-amber-900" };
  return { panel: "bg-red-50/80 text-red-800", badge: "bg-red-100 text-red-800" };
}
