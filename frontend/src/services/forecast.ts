import { api } from '@/lib/api';
import { buildBudgetQuery } from '@/lib/consolidacaoMldu';
import { OrcamentoItemData, OrcamentoVendaLinha, OrcamentoVendaLinhaBase } from './orcamento';

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
  db_id?: number;
}

export interface ForecastBaseOption {
  id: number;
  tipo: 'Orcamento' | 'Forecast';
  descricao: string;
}

export interface BaseForecastResponse {
  mapa_ids?: Record<number, number>;
  is_empty?: boolean;
  opcoes_base?: ForecastBaseOption[];
  forecast_id: number;
  ano: number;
  tipo: string;
  status: string;
  versao_numero: number;
  motivo_reabertura?: string;
  data_criacao?: string;
  is_locked_by_other: boolean;
  usuario_edicao_nome?: string;
  is_consolidado: boolean;
  meses_fechados: number[];
  holding_mldu?: boolean;
  holding_avisos?: string[];
}

export interface ForecastDespesasResponse extends BaseForecastResponse {
  itens: OrcamentoItemData[];
  itens_base: OrcamentoItemData[];
  versoes_disponiveis?: any[];
  opcoes_produtos: OpcaoProduto[];
  opcoes_planos: OpcaoPlano[];
}

export interface ForecastVendasResponse extends BaseForecastResponse {
  itens: OrcamentoVendaLinha[];
  itens_base: OrcamentoVendaLinhaBase[];
  versoes_disponiveis?: any[];
  opcoes_produtos: OpcaoProduto[];
  opcoes_planos: OpcaoPlano[];
}

const deptHeader = (deptId: number) => ({
  headers: { 'X-Department-Id': deptId.toString() }
});

export const forecastService = {
  delete: async (id: number) => {
    const response = await api.delete(`/forecasts/${id}`);
    return response.data;
  },
  getAnosDisponiveis: async (tipo: string, departamento_id: number, consolidado: boolean = false) => {
    const response = await api.get(`/forecasts/anos-disponiveis?tipo=${tipo}&consolidado=${consolidado}&departamento_id=${departamento_id}`, deptHeader(departamento_id));
    return response.data;
  },

  getDespesas: async (ano: number, departamento_id: number, consolidado: boolean = false, versao_id?: number, holdingMldu: boolean = false) => {
    const q = buildBudgetQuery(consolidado, holdingMldu);
    const url = versao_id
      ? `/forecasts/despesas/${ano}?${q}&versao_id=${versao_id}`
      : `/forecasts/despesas/${ano}?${q}`;
    const response = await api.get(url, deptHeader(departamento_id));
    return response.data;
  },

  salvarDespesas: async (ano: number, departamento_id: number, itens: OrcamentoItemData[]) => {
    const response = await api.post(`/forecasts/despesas/${ano}/salvar`, { itens }, deptHeader(departamento_id));
    return response.data;
  },

  getVendas: async (ano: number, departamento_id: number, consolidado: boolean = false, versao_id?: number, holdingMldu: boolean = false) => {
    const q = buildBudgetQuery(consolidado, holdingMldu);
    const url = versao_id
      ? `/forecasts/vendas/${ano}?${q}&versao_id=${versao_id}`
      : `/forecasts/vendas/${ano}?${q}`;
    const response = await api.get(url, deptHeader(departamento_id));
    return response.data;
  },

  salvarVendas: async (ano: number, departamento_id: number, itens: OrcamentoVendaLinha[]) => {
    const response = await api.post(`/forecasts/vendas/${ano}/salvar`, { itens }, deptHeader(departamento_id));
    return response.data;
  },
  
  criarDeBase: async (
    ano: number,
    tipo: string,
    departamento_id: number,
    orcamento_id?: number,
    forecast_id?: number,
    produto_id?: number,
    extra?: { plano_financeiro_id?: number; plano_venda_id?: number },
  ) => {
    const response = await api.post(`/forecasts/criar_de_base`, {
      ano,
      tipo,
      versao_base_orcamento_id: orcamento_id,
      versao_base_forecast_id: forecast_id,
      produto_id,
      ...(extra || {}),
    }, deptHeader(departamento_id));
    return response.data;
  },

  getCatalogo: async (tipo: string, ano: number, departamento_id: number) => {
    const response = await api.get(
      `/forecasts/catalogo?tipo=${tipo}&ano=${ano}`,
      deptHeader(departamento_id),
    );
    return response.data as {
      opcoes_produtos: OpcaoProduto[];
      opcoes_planos: OpcaoPlano[];
      opcoes_base: ForecastBaseOption[];
    };
  },

  travarForecast: async (id: number, departamento_id: number) => {
    const response = await api.post(`/forecasts/${id}/travar`);
    return response.data;
  },

  destravarForecast: async (id: number, departamento_id: number) => {
    const response = await api.post(`/forecasts/${id}/destravar`);
    return response.data;
  },

  changeStatus: async (id: number, departamento_id: number, novo_status: string, motivo?: string) => {
    const response = await api.post(`/forecasts/${id}/status`, { novo_status, motivo });
    return response.data;
  },

  solicitarReabertura: async (id: number, departamento_id: number, motivo: string) => {
    const { data } = await api.post(`/forecasts/${id}/solicitar-reabertura`, { novo_status: "Solicitação Reabertura", motivo }, deptHeader(departamento_id));
    return data;
  },

  aprovarReabertura: async (id: number, departamento_id: number) => {
    const { data } = await api.post(`/forecasts/${id}/aprovar-reabertura`, {}, deptHeader(departamento_id));
    return data;
  },

  gerarLote: async (ano: number, tipo: string, departamento_id: number) => {
    const response = await api.post(`/forecasts/gerar-lote`, { ano, tipo }, deptHeader(departamento_id));
    return response.data;
  },

  excluirForecast: async (forecastId: number, departamento_id: number) => {
    const response = await api.delete(`/forecasts/${forecastId}`, deptHeader(departamento_id));
    return response.data;
  }
};
