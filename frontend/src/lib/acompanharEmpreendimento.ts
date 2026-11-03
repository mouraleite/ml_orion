/** Quem pode marcar “Acompanhar empreendimento” no cadastro de centro de custo. */

export const TIPOS_CABECA_OBRA = [
  "Somente Obra",
  "Obra e Centro de Custo",
] as const;

const TIPO_SOMENTE_CC = "Somente Centro de Custo";
const TIPO_ASSOCIADO = "Centro de Custo associado à Obra";

const SUFIXO_SATELITE =
  / - (OBRAS|MARKETING|COMERCIAL|PROJETOS|NOVOS NEG|GEST|PARCERIA|MLDU)/i;

export function tipoEfetivoCentro(cc: {
  tipo_sienge?: string | null;
  custom_data?: Record<string, unknown> | null;
}): string {
  const override = cc.custom_data?.__tipo_override;
  if (typeof override === "string" && override.trim()) return override.trim();
  return (cc.tipo_sienge || "").trim();
}

export function centroEhSateliteDeProduto(nome: string): boolean {
  return SUFIXO_SATELITE.test(nome || "");
}

export function podeAcompanharEmpreendimento(tipo: string, nome: string): boolean {
  const t = (tipo || "").trim();
  if ((TIPOS_CABECA_OBRA as readonly string[]).includes(t)) return true;
  if (t === TIPO_SOMENTE_CC) return false;
  if (t === TIPO_ASSOCIADO) return !centroEhSateliteDeProduto(nome);
  return false;
}

export function mostraFlagAcompanharEmpreendimento(opts: {
  tipo: string;
  nome: string;
  jaAcompanhado?: boolean;
}): boolean {
  if (podeAcompanharEmpreendimento(opts.tipo, opts.nome)) return true;
  return Boolean(opts.jaAcompanhado);
}
