/** Texto e fatos do painel “Como lemos estes números”. Não calcula KPI. */

export const TITULO_PAINEL = "Como lemos estes números";

export const TITULO_CRONOGRAMA_OBRA = "Cronograma de desembolso de obra";
export const TITULO_VENDAS_ESTOQUE = "Vendas de lotes em estoque";

export const TEXTO_CAMADAS = {
  pago: "Baixa no Sienge. Não se altera aqui.",
  comprometido: "Títulos em aberto. Não mexe no realizado.",
  obras: "Só o saldo, a partir do mês que vem.",
  estoque: "Média dos últimos 6 meses com venda, a partir do mês que vem.",
} as const;

export const TEXTO_VGV_ESTOQUE =
  "VGV vendido são os contratos. O estoque entra no card da lista; a curva mês a mês só no detalhe.";

export const TEXTO_DRE = "Lucro operacional é caixa (entrada menos saída), não VGV.";

export const TEXTO_FORA =
  "Orçamento e forecast ficam nas telas deles. Este painel não muda número.";

export const TEXTO_SEM_PRODUTO =
  "O mesmo método vale para todos os produtos. Abra um empreendimento para ver os números desta obra.";

export type FatosAcompanhamento = {
  nome: string;
  fase?: string;
  estoqueUnidades: number;
  vgvEstoque: number;
  terreno: number;
  obrasPagas: number;
  obrasPrevistas: number;
  tirAnual: number;
  mtirAnual: number;
  payback: number;
  exposicao: number;
};

export function formatarMi(valor: number): string {
  const n = Number(valor) || 0;
  if (Math.abs(n) >= 50_000) {
    return `R$ ${(n / 1_000_000).toLocaleString("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })} mi`;
  }
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(n);
}

export function estoqueDaDre(dre: Array<{ item?: string; valor?: number }> | null | undefined): {
  unidades: number;
  valor: number;
} {
  for (const row of dre || []) {
    const m = String(row.item || "").match(/VGV Estoque Potencial \((\d+) unidades\)/i);
    if (m) return { unidades: Number(m[1]) || 0, valor: Number(row.valor) || 0 };
  }
  return { unidades: 0, valor: 0 };
}

export function terrenoDaDre(dre: Array<{ item?: string; valor?: number }> | null | undefined): number {
  for (const row of dre || []) {
    const item = String(row.item || "").toLowerCase();
    if (item.includes("terreno") || item.includes("aquisição área") || item.includes("aquisicao area")) {
      return Math.abs(Number(row.valor) || 0);
    }
  }
  return 0;
}

export function somaFluxo(
  fc: Array<{ Obras?: number; Terreno?: number; is_forecast?: boolean }> | null | undefined,
): { obrasPagas: number; obrasPrevistas: number; terreno: number } {
  let obrasPagas = 0;
  let obrasPrevistas = 0;
  let terreno = 0;
  for (const row of fc || []) {
    const obras = Math.abs(Number(row.Obras) || 0);
    terreno += Math.abs(Number(row.Terreno) || 0);
    if (row.is_forecast) obrasPrevistas += obras;
    else obrasPagas += obras;
  }
  return { obrasPagas, obrasPrevistas, terreno };
}

export function tirClassicaAusente(tirAnual: number, mtirAnual: number): boolean {
  return (Number(tirAnual) || 0) === 0 && (Number(mtirAnual) || 0) > 0.5;
}

export function textoTir(fatos: FatosAcompanhamento): string {
  const mtir = (Number(fatos.mtirAnual) || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  const payback = Math.round(Number(fatos.payback) || 0);
  const exp = formatarMi(Math.abs(Number(fatos.exposicao) || 0));
  if (tirClassicaAusente(fatos.tirAnual, fatos.mtirAnual)) {
    return `TIR clássica só existe se o caixa começa com investimento. Neste produto o card pode mostrar 0% — a taxa da vida é a MTIR ${mtir}%. Payback ${payback} meses. Exposição máxima ${exp}.`;
  }
  const tir = (Number(fatos.tirAnual) || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  return `TIR clássica ${tir}%. MTIR ${mtir}% (TMA 12%). Payback ${payback} meses. Exposição máxima ${exp}.`;
}

export function fatosDoDetalhe(opts: {
  nome: string;
  fase?: string;
  kpis?: Record<string, number | null | undefined> | null;
  dre?: Array<{ item?: string; valor?: number }> | null;
  fluxoCaixa?: Array<{ Obras?: number; Terreno?: number; is_forecast?: boolean }> | null;
}): FatosAcompanhamento {
  const kpis = opts.kpis || {};
  const estoque = estoqueDaDre(opts.dre);
  const fluxo = somaFluxo(opts.fluxoCaixa);
  const terrenoDre = terrenoDaDre(opts.dre);
  return {
    nome: opts.nome,
    fase: opts.fase,
    estoqueUnidades: estoque.unidades,
    vgvEstoque: estoque.valor,
    terreno: terrenoDre || fluxo.terreno,
    obrasPagas: fluxo.obrasPagas,
    obrasPrevistas: fluxo.obrasPrevistas,
    tirAnual: Number(kpis.tir_anual) || 0,
    mtirAnual: Number(kpis.mtir_anual) || 0,
    payback: Number(kpis.payback) || 0,
    exposicao: Number(kpis.exposicao_max_caixa) || 0,
  };
}

export function fatosDaLista(row: {
  project_name?: string;
  status?: string;
  tir_anual?: number;
  mtir_anual?: number;
  payback_anos?: number;
  exposicao_max_caixa?: number;
} | null): FatosAcompanhamento | null {
  if (!row?.project_name) return null;
  return {
    nome: row.project_name,
    fase: row.status,
    estoqueUnidades: 0,
    vgvEstoque: 0,
    terreno: 0,
    obrasPagas: 0,
    obrasPrevistas: 0,
    tirAnual: Number(row.tir_anual) || 0,
    mtirAnual: Number(row.mtir_anual) || 0,
    payback: Number(row.payback_anos) || 0,
    exposicao: Number(row.exposicao_max_caixa) || 0,
  };
}
