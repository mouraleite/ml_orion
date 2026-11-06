import { mapaNomeSiengePrimeiro } from "./idSienge.ts";

/** Cadastro Apoio: `id` é o ID Sienge (público). `db_id` é só PK interno. */
export function empresasNomePorId(
  empresas: Array<{
    id?: string | number | null;
    db_id?: number | null;
    nomeFantasia?: string | null;
    razaoSocial?: string | null;
  }>,
): Map<string, string> {
  return mapaNomeSiengePrimeiro(
    empresas.map((e) => ({
      sienge: e.id,
      interno: e.db_id,
      nome: e.nomeFantasia || e.razaoSocial || "",
    })),
  );
}

export function centrosNomePorId(
  centros: Array<{
    id?: string | number | null;
    db_id?: number | null;
    nome?: string | null;
  }>,
): Map<string, string> {
  return mapaNomeSiengePrimeiro(
    centros.map((c) => ({
      sienge: c.id,
      interno: c.db_id,
      nome: c.nome || "",
    })),
  );
}
