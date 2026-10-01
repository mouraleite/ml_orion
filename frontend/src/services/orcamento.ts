import { api } from "@/lib/api";
import { buildBudgetQuery } from "@/lib/consolidacaoMldu";
import { cachedRead } from "@/lib/readCache";

// ── Helper ───────────────────────────────────────────────────────────────────

function deptHeader(deptId: number) {
  return { headers: { "X-Department-Id": String(deptId) } };
}

const ACOMP_TIMEOUT_MS = 120000;

function acompGet(url: string, deptId: number) {
  return api.get(url, { ...deptHeader(deptId), timeout: ACOMP_TIMEOUT_MS });
}

function acompCached(key: string, url: string, deptId: number) {
  return cachedRead(key, () => acompGet(url, deptId).then((r) => r.data));
}

// ── Tipos ────────────────────────────────────────────────────────────────────

export interface OrcamentoItemData {
  id?: number;
  produto_id: number;
  plano_financeiro_id: number;
  jan: number;
  fev: number;
  mar: number;
  abr: number;
  mai: number;
  jun: number;
  jul: number;
  ago: number;
  set: number;
  out: number;
  nov: number;
  dez: number;
  total_anual: number;
  observacao?: string;
  is_auto_generated?: boolean;
}

export const orcamentoService = {
  criar: async (
    ano: number,
    tipo: string,
    departamento_id: number,
    produto_id?: number,
    extra?: { plano_financeiro_id?: number; plano_venda_id?: number },
  ) => {
    const response = await api.post(
      `/orcamentos/criar`,
      { ano, tipo, produto_id, ...extra },
      { headers: { 'X-Department-Id': departamento_id } },
    );
    return response.data;
  },
  getCatalogo: async (tipo: string, deptId: number): Promise<{ opcoes_produtos: OpcaoProduto[]; opcoes_planos: OpcaoPlano[] }> => {
    const { data } = await api.get(`/orcamentos/catalogo?tipo=${tipo}`, deptHeader(deptId));
    return data;
  },
  delete: async (id: number) => {
    const response = await api.delete(`/orcamentos/${id}`);
    return response.data;
  },

  // ==================== GERENCIAMENTO ====================
  getAnosDisponiveis: async (tipo: string, deptId: number, consolidado: boolean = false): Promise<{ anos: number[] }> => {
    const { data } = await api.get(`/orcamentos/anos-disponiveis?tipo=${tipo}&consolidado=${consolidado}`, deptHeader(deptId));
    return data;
  },

  // ==================== RECEITAS ====================
  getReceitas: async (ano: number, deptId: number, consolidado: boolean = false, holdingMldu: boolean = false): Promise<OrcamentoDespesasResponse> => {
    const { data } = await api.get(`/orcamentos/receitas/${ano}?${buildBudgetQuery(consolidado, holdingMldu)}`, deptHeader(deptId));
    return data;
  },

  salvarReceitas: async (ano: number, deptId: number, itens: any[]): Promise<any> => {
    const { data } = await api.post(`/orcamentos/receitas/${ano}/salvar`, { itens }, deptHeader(deptId));
    return data;
  },

  getDespesas: async (ano: number, deptId: number, consolidado: boolean = false, holdingMldu: boolean = false): Promise<OrcamentoDespesasResponse> => {
    const { data } = await api.get(`/orcamentos/despesas/${ano}?${buildBudgetQuery(consolidado, holdingMldu)}`, deptHeader(deptId));
    return data;
  },

  salvarDespesas: async (ano: number, deptId: number, itens: OrcamentoItemData[]): Promise<any> => {
    const { data } = await api.post(`/orcamentos/despesas/${ano}/salvar`, { itens }, deptHeader(deptId));
    return data;
  },

  getVendas: async (ano: number, deptId: number, consolidado: boolean = false, holdingMldu: boolean = false): Promise<OrcamentoVendasResponse> => {
    const { data } = await api.get(`/orcamentos/vendas/${ano}?${buildBudgetQuery(consolidado, holdingMldu)}`, deptHeader(deptId));
    return data;
  },

  salvarVendas: async (ano: number, deptId: number, itens: OrcamentoVendaLinha[]): Promise<any> => {
    const { data } = await api.post(`/orcamentos/vendas/${ano}/salvar`, { itens }, deptHeader(deptId));
    return data;
  },

  changeStatus: async (orcamento_id: number, deptId: number, novo_status: string, motivo?: string) => {
    const { data } = await api.post(`/orcamentos/${orcamento_id}/status`, { novo_status, motivo }, deptHeader(deptId));
    return data;
  },

  solicitarReabertura: async (orcamento_id: number, deptId: number, motivo: string) => {
    const { data } = await api.post(`/orcamentos/${orcamento_id}/solicitar-reabertura`, { novo_status: "Solicitação Reabertura", motivo }, deptHeader(deptId));
    return data;
  },

  aprovarReabertura: async (orcamento_id: number, deptId: number) => {
    const { data } = await api.post(`/orcamentos/${orcamento_id}/aprovar-reabertura`, {}, deptHeader(deptId));
    return data;
  },

  destravarOrcamento: async (orcamento_id: number, deptId: number) => {
    const { data } = await api.post(`/orcamentos/${orcamento_id}/destravar`, {}, deptHeader(deptId));
    return data;
  },

  // ==================== ACOMPANHAMENTO ====================

  getAcompanhamentoConsolidado: async (ano: number, deptId: number, consolidado: boolean = false, forecastId?: number, holdingMldu: boolean = false) => {
    const q = buildBudgetQuery(consolidado, holdingMldu);
    const url = forecastId
      ? `/acompanhamento/consolidado/${ano}?${q}&forecast_id=${forecastId}`
      : `/acompanhamento/consolidado/${ano}?${q}`;
    return acompCached(`acomp:consolidado:${ano}:${deptId}:${consolidado}:${forecastId || ""}:${holdingMldu}`, url, deptId);
  },

  getAcompanhamentoDespesas: async (ano: number, deptId: number, consolidado: boolean = false, forecastId?: number, holdingMldu: boolean = false) => {
    const q = buildBudgetQuery(consolidado, holdingMldu);
    const url = forecastId
      ? `/acompanhamento/despesas/${ano}?${q}&forecast_id=${forecastId}`
      : `/acompanhamento/despesas/${ano}?${q}`;
    return acompCached(`acomp:despesas:${ano}:${deptId}:${consolidado}:${forecastId || ""}:${holdingMldu}`, url, deptId);
  },

  getAcompanhamentoReceitas: async (ano: number, deptId: number, consolidado: boolean = false, forecastId?: number, holdingMldu: boolean = false) => {
    const q = buildBudgetQuery(consolidado, holdingMldu);
    const url = forecastId
      ? `/acompanhamento/receitas/${ano}?${q}&forecast_id=${forecastId}`
      : `/acompanhamento/receitas/${ano}?${q}`;
    return acompCached(`acomp:receitas:${ano}:${deptId}:${consolidado}:${forecastId || ""}:${holdingMldu}`, url, deptId);
  },

  getAcompanhamentoVendas: async (ano: number, deptId: number, consolidado: boolean = false, forecastId?: number, holdingMldu: boolean = false) => {
    const q = buildBudgetQuery(consolidado, holdingMldu);
    const url = forecastId
      ? `/acompanhamento/vendas/${ano}?${q}&forecast_id=${forecastId}`
      : `/acompanhamento/vendas/${ano}?${q}`;
    return acompCached(`acomp:vendas:${ano}:${deptId}:${consolidado}:${forecastId || ""}:${holdingMldu}`, url, deptId);
  },

  getMatrizDetalhada: async (ano: number, deptId: number, consolidado: boolean = false, forecastId?: number, holdingMldu: boolean = false) => {
    let url = `/dashboard/matriz-detalhada/${ano}?${buildBudgetQuery(consolidado, holdingMldu)}`;
    if (forecastId) url += `&forecast_id=${forecastId}`;
    return acompCached(`acomp:matriz:${ano}:${deptId}:${consolidado}:${forecastId || ""}:${holdingMldu}`, url, deptId);
  },

  getRealizadoDespesas: async (
    ano: number,
    deptId: number,
    opts?: {
      consolidado?: boolean;
      holdingMldu?: boolean;
      produtoId?: number;
      planoId?: number;
      mes?: string;
      busca?: string;
    },
  ) => {
    const params = new URLSearchParams(buildBudgetQuery(opts?.consolidado ?? false, opts?.holdingMldu ?? false));
    if (opts?.produtoId != null) params.set("produto_id", String(opts.produtoId));
    if (opts?.planoId != null) params.set("plano_id", String(opts.planoId));
    if (opts?.mes) params.set("mes", opts.mes);
    if (opts?.busca?.trim()) params.set("busca", opts.busca.trim());
    const { data } = await api.get(`/dashboard/realizado-despesas/${ano}?${params.toString()}`, deptHeader(deptId));
    return data;
  },

  // ==================== COMPARATIVO DE VERSÕES ====================

  getComparativo: async (versao_a: string, versao_b: string, tipo: string, ano: number, deptId: number, consolidado: boolean = false) => {
    const { data } = await api.get(`/orcamentos/comparativo?versao_a=${encodeURIComponent(versao_a)}&versao_b=${encodeURIComponent(versao_b)}&tipo=${tipo}&ano=${ano}&consolidado=${consolidado}`, deptHeader(deptId));
    return data;
  },

  listarVersoes: async (ano: number, tipo: string, deptId: number) => {
    const { data } = await api.get(`/orcamentos/comparativo/versoes/${ano}?tipo=${tipo}`, deptHeader(deptId));
    return data || [];
  },

  // ==================== VISUALIZAÇÃO (Tela 4) ====================

  getVisualizacao: async (
    ano: number,
    departamento_id: number,
    tipo: string = "DESPESAS",
    consolidado: boolean = false,
    versao_id: string = "",
    holdingMldu: boolean = false,
  ) => {
    const params = new URLSearchParams({ tipo, consolidado: String(consolidado) });
    if (versao_id) params.append("versao_id", versao_id);
    if (holdingMldu) params.set("holding_mldu", "true");
    const { data } = await api.get(`/orcamentos/visualizacao/${ano}?${params.toString()}`, deptHeader(departamento_id));
    return data;
  },

  // ==================== DASHBOARD EXECUTIVO ====================

  getDashboardExecutivo: async (
    ano: number,
    deptId: number,
    consolidado: boolean = false,
    modo: string = "orcado",
    versaoForecastId?: number,
    meses?: string[],
    holdingMldu: boolean = false,
    empresaIds?: string[],
  ) => {
    let url = `/dashboard/executivo/${ano}?${buildBudgetQuery(consolidado, holdingMldu)}&modo=${modo}`;
    if (versaoForecastId) url += `&forecast_id=${versaoForecastId}`;
    if (meses && meses.length > 0) url += `&meses=${meses.join(",")}`;
    if (empresaIds && empresaIds.length > 0) url += `&empresa_ids=${empresaIds.map(encodeURIComponent).join(",")}`;
    return cachedRead(
      `dash:exec:${ano}:${deptId}:${consolidado}:${modo}:${versaoForecastId || ""}:${(meses || []).join(",")}:${holdingMldu}:${(empresaIds || []).join(",")}`,
      () => acompGet(url, deptId).then((r) => r.data),
    );
  },

  getDfc: async (
    ano: number,
    deptId: number,
    holdingMldu: boolean = false,
    meses?: string[],
    empresaIds?: string[],
    forecastId?: number,
  ) => {
    let url = `/dashboard/dfc/${ano}?${buildBudgetQuery(false, holdingMldu)}`;
    if (meses && meses.length > 0) url += `&meses=${meses.join(",")}`;
    if (empresaIds && empresaIds.length > 0) url += `&empresa_ids=${empresaIds.map(encodeURIComponent).join(",")}`;
    if (forecastId) url += `&forecast_id=${forecastId}`;
    return cachedRead(
      `dash:dfc:${ano}:${deptId}:${holdingMldu}:${(meses || []).join(",")}:${(empresaIds || []).join(",")}:${forecastId || ""}`,
      () => acompGet(url, deptId).then((r) => r.data),
    );
  },

  getDfcComparativo: async (
    ano: number,
    deptId: number,
    versaoA: string,
    versaoB: string,
    holdingMldu: boolean = false,
    meses?: string[],
    empresaIds?: string[],
  ) => {
    let url =
      `/dashboard/dfc/${ano}/comparativo?${buildBudgetQuery(false, holdingMldu)}` +
      `&versao_a=${encodeURIComponent(versaoA)}&versao_b=${encodeURIComponent(versaoB)}`;
    if (meses && meses.length > 0) url += `&meses=${meses.join(",")}`;
    if (empresaIds && empresaIds.length > 0) url += `&empresa_ids=${empresaIds.map(encodeURIComponent).join(",")}`;
    return acompGet(url, deptId).then((r) => r.data);
  },

  getForecastsDisponiveis: async (ano: number, deptId: number, consolidado: boolean = false) => {
    return cachedRead(
      `dash:forecasts:${ano}:${deptId}:${consolidado}`,
      () => api.get(`/dashboard/executivo/${ano}/forecasts?consolidado=${consolidado}`, deptHeader(deptId)).then((r) => r.data),
    );
  },
};

export interface OpcaoProduto {
  id: number;
  nome: string;
  id_sienge?: string;
  id_empresa?: string;
  nome_empresa?: string;
}

export interface OpcaoPlano {
  id: number;
  nome: string;
  db_id?: string;
}

export interface OrcamentoBaseResponse {
  orcamento_id: number;
  ano: number;
  tipo: string;
  status: string;
  versao_numero: number;
  versao_base_id?: number | null;
  motivo_reabertura?: string | null;
  data_criacao?: string | null;
  is_locked_by_other?: boolean;
  usuario_edicao_nome?: string | null;
  data_inicio_edicao?: string | null;
  is_consolidado?: boolean;
  holding_mldu?: boolean;
  holding_avisos?: string[];
}

export interface OrcamentoDespesasResponse extends OrcamentoBaseResponse {
  itens: OrcamentoItemData[];
  itens_base: OrcamentoItemData[];
  opcoes_produtos: OpcaoProduto[];
  opcoes_planos: OpcaoPlano[];
  mapa_ids?: Record<number, number>;
}

export interface MesVenda {
  mes: number;
  ticket_medio: number;
  numero_vendas: number;
  vgv: number;
  origem_venda?: string;
}

export interface OrcamentoVendaLinha {
  produto_id: number;
  plano_venda_id: number;
  observacao?: string;
  meses: MesVenda[];
}

export interface OrcamentoVendaLinhaBase {
  produto_id: number;
  plano_venda_id: number;
  mes: number;
  ticket_medio: number;
  numero_vendas: number;
  vgv: number;
  origem_venda?: string;
}

export interface OrcamentoVendasResponse extends OrcamentoBaseResponse {
  itens: OrcamentoVendaLinha[];
  itens_base: OrcamentoVendaLinhaBase[];
  opcoes_produtos: OpcaoProduto[];
  opcoes_planos: OpcaoPlano[];
  mapa_ids?: Record<number, number>;
}
