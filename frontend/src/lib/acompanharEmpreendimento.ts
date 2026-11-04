/** Quem pode marcar “Acompanhar empreendimento” no cadastro de centro de custo. */

import { rotuloTipoSienge } from "./tipoCentroCusto.ts";

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
  if (typeof override === "string" && override.trim()) {
    return rotuloTipoSienge(override.trim());
  }
  return rotuloTipoSienge(cc.tipo_sienge);
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

/** Só cabeçalho de obra: Somente Obra ou Obra e Centro de Custo. */
export function ehCabecaDeObra(tipo: string): boolean {
  return (TIPOS_CABECA_OBRA as readonly string[]).includes((tipo || "").trim());
}

export function rotuloCentroIdNome(
  id: string | number | null | undefined,
  nome: string,
): string {
  const n = (nome || "").trim() || "—";
  if (id === null || id === undefined || String(id).trim() === "") return n;
  return `${String(id).trim()} - ${n}`;
}

export type CentroObraOpcao = {
  db_id: number;
  id?: string | number;
  nome: string;
  tipo_sienge?: string | null;
  custom_data?: Record<string, unknown> | null;
  track_in_dashboard?: boolean;
};

export function opcoesObraAcompanhamento(centros: CentroObraOpcao[]): CentroObraOpcao[] {
  return centros
    .filter((c) => ehCabecaDeObra(tipoEfetivoCentro(c)))
    .slice()
    .sort((a, b) => {
      const ia = Number(a.id);
      const ib = Number(b.id);
      if (Number.isFinite(ia) && Number.isFinite(ib) && ia !== ib) return ia - ib;
      return (a.nome || "").localeCompare(b.nome || "", "pt-BR");
    });
}
