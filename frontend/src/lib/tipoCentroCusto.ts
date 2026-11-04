/** Rótulo de tipo do centro de custo / obra Sienge. Nunca HTML, URL ou objeto. */

export const TIPO_POR_CODIGO: Record<string, string> = {
  "1": "Obra e Centro de Custo",
  "2": "Somente Obra",
  "3": "Somente Centro de Custo",
  "4": "Centro de Custo associado à Obra",
};

export const ROTULOS_TIPO = Object.values(TIPO_POR_CODIGO);

const HTML = /<[^>]*>/g;
const URL = /^(https?:\/\/|data:image|\/\/)/i;
const ARQUIVO_IMAGEM = /\.(png|jpe?g|gif|svg|webp)(\?|$)/i;

function texto(raw: unknown): string {
  if (raw == null || typeof raw === "boolean") return "";
  if (Array.isArray(raw)) return raw.length ? texto(raw[0]) : "";
  if (typeof raw === "object") {
    const obj = raw as Record<string, unknown>;
    for (const key of ["id", "value", "type", "codigo", "code"]) {
      const extraido = texto(obj[key]);
      if (extraido) return extraido;
    }
    for (const key of ["description", "nome", "name", "label"]) {
      const extraido = texto(obj[key]);
      if (extraido) return extraido;
    }
    return "";
  }
  if (typeof raw === "number" && Number.isInteger(raw)) {
    return String(raw);
  }
  return String(raw)
    .replace(HTML, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function rotuloTipoSienge(raw: unknown, vazio = ""): string {
  const t = texto(raw);
  if (!t) return vazio;
  if (URL.test(t) || ARQUIVO_IMAGEM.test(t)) return "Desconhecido";
  if (TIPO_POR_CODIGO[t]) return TIPO_POR_CODIGO[t];
  const conhecido = ROTULOS_TIPO.find((rotulo) => rotulo.toLowerCase() === t.toLowerCase());
  if (conhecido) return conhecido;
  return "Desconhecido";
}
