/** Soma as entradas da árvore DFC já assinada. Não recalcula o realizado. */

import { MESES_STR } from "./orcamentoDesvioUi.ts";

export type NoDfcFluxo = {
  kind?: string;
  sentido?: string | null;
  total?: number;
  total_n1?: number;
  total_real?: number;
  total_real_mldu?: number;
  total_n1_mldu?: number;
  planos?: NoDfcFluxo[];
  filhos?: NoDfcFluxo[];
};

export type FluxoCartoes = {
  entradas: number;
  entradasN1: number;
  entradasMldu: number;
  entradasN1Mldu: number;
  saidas: number;
  saidasN1: number;
  saidasMldu: number;
  saidasN1Mldu: number;
};

function valorN(node: NoDfcFluxo): number {
  return Number(node.total_real ?? node.total ?? 0) || 0;
}

function isPlanoEntrada(node: NoDfcFluxo): boolean {
  if (node.sentido === "entrada") return true;
  if (node.sentido === "saida") return false;
  if (node.kind === "plano") return valorN(node) > 0;
  return false;
}

function somarEntradas(nodes: NoDfcFluxo[] | undefined, acc: { n: number; n1: number; nMldu: number; n1Mldu: number }) {
  for (const node of nodes || []) {
    if (isPlanoEntrada(node)) {
      acc.n += valorN(node);
      acc.n1 += Number(node.total_n1 ?? 0) || 0;
      acc.nMldu += Number(node.total_real_mldu ?? 0) || 0;
      acc.n1Mldu += Number(node.total_n1_mldu ?? 0) || 0;
    }
    somarEntradas(node.planos, acc);
    somarEntradas(node.filhos, acc);
  }
}

export function legendaMesesDfc(meses: string[]): string {
  if (!meses.length) return "ano completo";
  const idxs = meses
    .map((m) => (MESES_STR as readonly string[]).indexOf(m))
    .filter((i) => i >= 0)
    .sort((a, b) => a - b);
  if (!idxs.length) return "ano completo";
  if (idxs.length === 1) return MESES_STR[idxs[0]];
  const contig = idxs.every((v, i) => i === 0 || v === idxs[i - 1] + 1);
  if (contig) return `${MESES_STR[idxs[0]]}–${MESES_STR[idxs[idxs.length - 1]]}`;
  return idxs.map((i) => MESES_STR[i]).join(", ");
}

export function fluxoCartoesDfc(opts: {
  linhas: NoDfcFluxo[];
  liquido: number;
  liquidoN1: number;
  totalEntradas?: number;
  liquidoMldu?: number;
  liquidoN1Mldu?: number;
}): FluxoCartoes {
  const acc = { n: 0, n1: 0, nMldu: 0, n1Mldu: 0 };
  somarEntradas(opts.linhas, acc);
  const entradas = opts.totalEntradas != null ? Number(opts.totalEntradas) || 0 : acc.n;
  const entradasN1 = acc.n1;
  const entradasMldu = acc.nMldu;
  const entradasN1Mldu = acc.n1Mldu;
  return {
    entradas,
    entradasN1,
    entradasMldu,
    entradasN1Mldu,
    saidas: opts.liquido - entradas,
    saidasN1: opts.liquidoN1 - entradasN1,
    saidasMldu: (opts.liquidoMldu ?? 0) - entradasMldu,
    saidasN1Mldu: (opts.liquidoN1Mldu ?? 0) - entradasN1Mldu,
  };
}
