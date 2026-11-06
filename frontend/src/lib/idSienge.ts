/** Espelha `id_sienge.py`: ID público = ID Sienge. */

export function mapaNomeSiengePrimeiro(
  rows: Array<{
    sienge?: string | number | null;
    interno?: string | number | null;
    nome: string;
  }>,
): Map<string, string> {
  const bySienge = new Map<string, string>();
  for (const r of rows) {
    const nome = (r.nome || "").trim();
    if (!nome) continue;
    if (r.sienge != null && r.sienge !== "") bySienge.set(String(r.sienge), nome);
  }
  return bySienge;
}

export function siengeOcupadosDe(
  rows: Array<{ id_sienge?: string | number | null }>,
): Set<string> {
  const ocupados = new Set<string>();
  for (const r of rows) {
    const v = r.id_sienge != null ? String(r.id_sienge).trim() : "";
    if (v) ocupados.add(v);
  }
  return ocupados;
}

/** ID público do centro/obra/empresa: só o Sienge. */
export function idPublicoSienge(
  row: { id?: string | number | null; id_sienge?: string | number | null },
  _ocupados?: Set<string>,
): string {
  return row.id_sienge != null ? String(row.id_sienge).trim() : "";
}

export function idsPublicosCentro(
  produtos: Array<{ id?: string | number | null; id_sienge?: string | number | null }>,
): string[] {
  return Array.from(
    new Set(produtos.map((p) => idPublicoSienge(p)).filter(Boolean)),
  );
}
