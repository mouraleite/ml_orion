/** Textos e regras do cadastro de terreno manual. Não calcula KPI. */

export const TEXTO_TERRENO_MANUAL =
  "Complemento de terreno que não veio no caixa do Sienge. Entra só no acompanhamento (lucro e fluxo), não no orçamento nem no forecast. Soma-se ao terreno já pago.";

export const TEXTO_INICIO_CURVA =
  "À vista: o valor inteiro no mês de início. Com curva: o desembolso começa nesse mês.";

const MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export function mostraInicioTerreno(valor: number): boolean {
  return Number(valor) > 0;
}

export function formatarMesPt(yyyyMm: string | null | undefined): string {
  if (!yyyyMm || !/^\d{4}-\d{2}$/.test(yyyyMm)) return "";
  const mes = Number(yyyyMm.slice(5, 7)) - 1;
  if (mes < 0 || mes > 11) return "";
  return `${MESES_PT[mes]}/${yyyyMm.slice(0, 4)}`;
}

export function mesSugeridoInicio(opts: {
  primeiroMesCaixa?: string | null;
  primeiroMesDesembolso?: string | null;
}): string | null {
  return opts.primeiroMesCaixa || opts.primeiroMesDesembolso || null;
}

export function linhasAlertaTerreno(opts: {
  primeiroMesCaixa?: string | null;
  primeiroMesDesembolso?: string | null;
}): string[] {
  const caixa = formatarMesPt(opts.primeiroMesCaixa);
  const saida = formatarMesPt(opts.primeiroMesDesembolso);
  if (!caixa && !saida) {
    return [
      "Ainda não há movimento de caixa desta obra no sistema. Escolha o mês de início; sem isso, o detalhe usa o mês de hoje.",
    ];
  }
  const linhas: string[] = [];
  if (caixa) linhas.push(`O caixa desta obra começa em ${caixa}.`);
  if (saida && saida !== caixa) linhas.push(`A primeira saída é ${saida}.`);
  linhas.push("Use este mês ou outro no início do pagamento.");
  return linhas;
}
