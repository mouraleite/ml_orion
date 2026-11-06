import { parseCentroNome } from "@/lib/parseCentroNome";
import { idPublicoSienge, idsPublicosCentro } from "./idSienge";

export type SelectOption = { value: string; label: string };

export interface GridProdutoOption {
  id: number;
  nome: string;
  id_sienge?: string | null;
  id_empresa?: string | null;
  nome_empresa?: string | null;
}

export interface GridPlanoOption {
  id: number;
  nome: string;
}

export interface GridFilterSource {
  itens?: Array<{ produto_id: number; plano_financeiro_id: number }>;
  opcoes_produtos: GridProdutoOption[];
  opcoes_planos: GridPlanoOption[];
}

export interface GridFilterOptionsResult {
  centrosId: SelectOption[];
  produtos: SelectOption[];
  planos: SelectOption[];
  empresasId: SelectOption[];
  empresasNome: SelectOption[];
}

export interface GridFilterState {
  busca: string;
  filtroIdCentro: string[];
  filtroProduto: string[];
  filtroPlano: string[];
  /** IDs Sienge das empresas (filtro ID e Nome compartilham este valor) */
  filtroEmpresaIds: string[];
}

/** @deprecated use filtroEmpresaIds — mantido só para migração gradual */
export type LegacyGridFilterState = GridFilterState & {
  filtroIdEmpresa?: string[];
  filtroEmpresa?: string[];
};

const EMPTY: GridFilterOptionsResult = {
  centrosId: [],
  produtos: [],
  planos: [],
  empresasId: [],
  empresasNome: [],
};

export { empresasNomePorId as buildEmpresasMapFromCadastro } from "./empresasNomePorId";

/** Resolve nome_empresa pelo cadastro de Apoio (Company), como no orçamento de despesas. */
export function enrichProdutosComEmpresaCadastro<
  T extends { id_empresa?: string | null; nome_empresa?: string | null },
>(produtos: T[], empresasMap: Map<string, string>): T[] {
  return produtos.map((p) => {
    const id = p.id_empresa ? String(p.id_empresa) : "";
    const nome = id
      ? empresasMap.get(id) || p.nome_empresa || id
      : p.nome_empresa || "";
    return { ...p, id_empresa: id || p.id_empresa, nome_empresa: nome };
  });
}

/** Pares id ↔ nome únicos, ordenados por id. Ambos os selects usam value = id. */
export function buildEmpresaLinkedOptions(
  produtos: Array<{ id_empresa?: string | null; nome_empresa?: string | null }>,
): Pick<GridFilterOptionsResult, "empresasId" | "empresasNome"> {
  const byId = new Map<string, string>();
  for (const p of produtos) {
    if (p.id_empresa) {
      byId.set(p.id_empresa, p.nome_empresa || p.id_empresa);
    }
  }
  const sorted = Array.from(byId.entries()).sort(
    (a, b) => Number(a[0]) - Number(b[0]) || a[1].localeCompare(b[1], "pt-BR"),
  );
  return {
    empresasId: sorted.map(([id]) => ({ value: id, label: id })),
    empresasNome: sorted.map(([id, nome]) => ({ value: id, label: nome })),
  };
}

export function buildGridFilterOptions(
  data: GridFilterSource | null | undefined,
  smartFilter = false,
): GridFilterOptionsResult {
  if (!data) return EMPTY;

  let produtosList = data.opcoes_produtos;
  let planosList = data.opcoes_planos;

  if (smartFilter && data.itens?.length) {
    const produtosComData = new Set(data.itens.map((i) => i.produto_id));
    const planosComData = new Set(data.itens.map((i) => i.plano_financeiro_id));
    produtosList = data.opcoes_produtos.filter((p) => produtosComData.has(p.id));
    planosList = data.opcoes_planos.filter((p) => planosComData.has(p.id));
  }

  const centrosId = idsPublicosCentro(produtosList).sort(
    (a, b) => Number(a) - Number(b),
  );
  const produtos = Array.from(
    new Set(produtosList.map((p) => parseCentroNome(p.nome).produto)),
  );
  const plans = Array.from(new Set(planosList.map((p) => p.nome)));
  const { empresasId, empresasNome } = buildEmpresaLinkedOptions(produtosList);

  return {
    centrosId: centrosId.map((id) => ({ value: id, label: id })),
    produtos: produtos.map((p) => ({ value: p, label: p })),
    planos: plans.map((p) => ({ value: p, label: p })),
    empresasId,
    empresasNome,
  };
}

export function filterLinhasMensais<T extends { produto_id: number; plano_financeiro_id: number }>(
  linhas: T[],
  data: GridFilterSource | null | undefined,
  filters: GridFilterState,
): T[] {
  return linhas.filter((linha) => {
    const produtoInfo = data?.opcoes_produtos.find((p) => p.id === linha.produto_id);
    const planoInfo = data?.opcoes_planos.find((p) => p.id === linha.plano_financeiro_id);
    const nomeCompleto = produtoInfo
      ? `${produtoInfo.id_sienge || ""} - ${produtoInfo.nome}`
      : "";

    if (filters.busca && !nomeCompleto.toLowerCase().includes(filters.busca.toLowerCase())) {
      return false;
    }
    if (
      filters.filtroIdCentro.length > 0 &&
      produtoInfo &&
      !filters.filtroIdCentro.includes(idPublicoSienge(produtoInfo))
    ) {
      return false;
    }
    if (
      filters.filtroProduto.length > 0 &&
      produtoInfo &&
      !filters.filtroProduto.includes(parseCentroNome(produtoInfo.nome).produto)
    ) {
      return false;
    }
    if (
      filters.filtroPlano.length > 0 &&
      planoInfo &&
      !filters.filtroPlano.includes(planoInfo.nome)
    ) {
      return false;
    }
    if (
      filters.filtroEmpresaIds.length > 0 &&
      produtoInfo &&
      !filters.filtroEmpresaIds.includes(produtoInfo.id_empresa || "")
    ) {
      return false;
    }
    return true;
  });
}

/** Recorta linhas pelo id_empresa do produto — mesmo critério da matriz de orçamento. */
export function filterItensPorEmpresaIds<T extends { produto_id?: number | null }>(
  itens: T[],
  opcoes: Array<{ id: number; id_empresa?: string | null }>,
  empresaIds: string[] | null | undefined,
): T[] {
  if (!empresaIds?.length) return itens;
  const wanted = new Set(empresaIds.map((e) => String(e).trim()).filter(Boolean));
  if (!wanted.size) return itens;
  const allowed = new Set(
    opcoes.filter((p) => wanted.has(String(p.id_empresa || ""))).map((p) => p.id),
  );
  return itens.filter((i) => i.produto_id != null && allowed.has(i.produto_id));
}

export function groupByProductId<T extends { produto_id: number }>(
  linhas: T[],
): Record<number, T[]> {
  const groups: Record<number, T[]> = {};
  linhas.forEach((linha) => {
    if (!groups[linha.produto_id]) groups[linha.produto_id] = [];
    groups[linha.produto_id].push(linha);
  });
  return groups;
}
