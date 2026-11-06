import { tituloPeriodo } from "./periodosFpa.ts";

export type BlocoGeracaoCaixa = {
  ano: number;
  corte: number;
  ytd: number;
  ytg: number;
  geracao: number;
  abertura: number | null;
  abertura_origem?: string;
  abertura_ano_base?: number | null;
  posicao_fim: number | null;
  posicao_origem?: string;
  tem_abertura: boolean;
  legenda?: string;
  ytd_n1?: number;
  ytg_n1?: number;
  geracao_n1?: number;
  abertura_n1?: number | null;
  posicao_fim_n1?: number | null;
  tem_abertura_n1?: boolean;
  mldu?: BlocoGeracaoCaixa | null;
};

export function valoresCardGeracao(bloco: BlocoGeracaoCaixa): {
  n: number;
  ref: number;
  nLabel: string;
  refLabel: string;
  usaPosicao: boolean;
} {
  const nLabel = String(bloco.ano);
  const refLabel = tituloPeriodo("ly");
  if (bloco.tem_abertura && bloco.posicao_fim != null) {
    const ref =
      bloco.tem_abertura_n1 && bloco.posicao_fim_n1 != null ? bloco.posicao_fim_n1 : bloco.posicao_fim;
    return { n: bloco.posicao_fim, ref, nLabel, refLabel, usaPosicao: true };
  }
  return {
    n: bloco.geracao,
    ref: bloco.geracao_n1 ?? 0,
    nLabel,
    refLabel,
    usaPosicao: false,
  };
}
