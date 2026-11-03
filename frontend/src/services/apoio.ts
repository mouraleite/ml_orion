export interface Empresa {
  id: string;
  db_id?: string;
  nome?: string;
  razaoSocial?: string;
  nomeFantasia?: string;
  cnpj: string;
  status: string;
  cidade?: string;
  estado?: string;
  custom_data?: Record<string, any>;
  socios?: any[];
}

export interface VisaoNode {
  id: number;
  codigo: string;
  descricao: string;
  planos_financeiros: {
    id: number;
    db_id: string;
    name: string;
    tp_conta: string;
  }[];
}

export interface CentroCusto {
  id: string;
  codigo: string;
  descricao: string;
  empresaId: string;
  status: string;
}

export interface PlanoFinanceiro {
  id: string;
  codigo: string;
  descricao: string;
  tipo: "RECEITA" | "CUSTO" | "DESPESA" | "IMPOSTO";
  nivel: number;
}

// MOCK DATA (Simulando o ERP)
const mockEmpresas: Empresa[] = [
  { id: "EMP-001", cnpj: "00.000.000/0001-01", razaoSocial: "Moura Leite Empreendimentos S/A", nomeFantasia: "ML Empreendimentos", status: "Ativa" },
  { id: "EMP-002", cnpj: "11.111.111/0001-11", razaoSocial: "SPE Residencial Botucatu LTDA", nomeFantasia: "SPE Botucatu", status: "Ativa" },
  { id: "EMP-003", cnpj: "22.222.222/0001-22", razaoSocial: "SPE Loteamento Bela Vista LTDA", nomeFantasia: "SPE Bela Vista", status: "Ativa" },
];

const mockCentrosCusto: CentroCusto[] = [
  { id: "CC-100", codigo: "1.0.0", descricao: "Holding (Administrativo)", empresaId: "EMP-001", status: "Ativo" },
  { id: "CC-201", codigo: "2.0.1", descricao: "Obras - Res. Botucatu", empresaId: "EMP-002", status: "Ativo" },
  { id: "CC-202", codigo: "2.0.2", descricao: "Vendas - Res. Botucatu", empresaId: "EMP-002", status: "Ativo" },
  { id: "CC-301", codigo: "3.0.1", descricao: "Obras - Bela Vista", empresaId: "EMP-003", status: "Inativo" },
];

const mockPlanos: PlanoFinanceiro[] = [
  { id: "PL-1", codigo: "1.0.0", descricao: "Receitas Brutas", tipo: "RECEITA", nivel: 1 },
  { id: "PL-11", codigo: "1.1.0", descricao: "Receitas de Vendas de Unidades", tipo: "RECEITA", nivel: 2 },
  { id: "PL-2", codigo: "2.0.0", descricao: "Impostos Incidentes", tipo: "IMPOSTO", nivel: 1 },
  { id: "PL-3", codigo: "3.0.0", descricao: "Custos de Obra", tipo: "CUSTO", nivel: 1 },
  { id: "PL-31", codigo: "3.1.0", descricao: "Terreno", tipo: "CUSTO", nivel: 2 },
  { id: "PL-32", codigo: "3.2.0", descricao: "Projetos e Aprovações", tipo: "CUSTO", nivel: 2 },
  { id: "PL-4", codigo: "4.0.0", descricao: "Despesas Comerciais", tipo: "DESPESA", nivel: 1 },
];

import { api } from '@/lib/api';
import { cachedRead, invalidateRead } from '@/lib/readCache';

// Funções do Serviço
export const apoioService = {
  getEmpresas: async (): Promise<any[]> => {
    try {
      return await cachedRead("apoio:empresas", async () => {
        const response = await api.get('/apoio/empresas');
        return response.data;
      }, 5 * 60_000);
    } catch (error) {
      console.error("Erro ao buscar empresas da API:", error);
      return [];
    }
  },

  syncEmpresas: async (): Promise<any> => {
    const response = await api.post('/apoio/empresas/sync');
    invalidateRead("apoio:empresas");
    return response.data;
  },

  getUsuariosParaSocios: async (): Promise<{ id: number; full_name: string; email: string }[]> => {
    const response = await api.get("/apoio/usuarios-para-socios");
    return response.data;
  },

  getCompanyPartners: async (dbId: number): Promise<any[]> => {
    try {
      const response = await api.get(`/apoio/empresas/${dbId}/socios`);
      return response.data;
    } catch (error) {
      console.error("Erro ao buscar sócios:", error);
      return [];
    }
  },

  addCompanyPartner: async (dbId: number, partner: any): Promise<any> => {
    const response = await api.post(`/apoio/empresas/${dbId}/socios`, partner);
    return response.data;
  },

  deleteCompanyPartner: async (dbId: number, partnerId: number): Promise<any> => {
    const response = await api.delete(`/apoio/empresas/${dbId}/socios/${partnerId}`);
    return response.data;
  },

  updateCompany: async (dbId: number, data: { nome_fantasia?: string; is_consolidated?: boolean; tipo_empresa?: string; status?: string }): Promise<any> => {
    const response = await api.put(`/apoio/empresas/${dbId}`, data);
    return response.data;
  },
  
  getCentrosCusto: async (): Promise<any[]> => {
    try {
      const response = await api.get('/apoio/centros-custo');
      return response.data;
    } catch (error) {
      console.error("Erro ao buscar centros de custo da API:", error);
      return [];
    }
  },

  syncCentrosCusto: async (): Promise<any> => {
    const response = await api.post('/apoio/centros-custo/sync');
    return response.data;
  },

  getFiltrosAtivos: async (ano: number): Promise<any> => {
    try {
      const response = await api.get(`/acompanhamento/filtros-ativos/${ano}`);
      return response.data;
    } catch (error) {
      console.error("Erro ao buscar filtros ativos da API:", error);
      return { centros_custo: [], planos_financeiros: [], planos_venda: [], empresas: [] };
    }
  },

  getCustomColumns: async (entityType: string = "centro_custo"): Promise<any[]> => {
    const response = await api.get(`/apoio/centros-custo/colunas?entity_type=${entityType}`);
    return response.data;
  },

  createCustomColumn: async (data: any): Promise<any> => {
    const response = await api.post('/apoio/centros-custo/colunas', data);
    return response.data;
  },

  deleteCustomColumn: async (id: number): Promise<any> => {
    const response = await api.delete(`/apoio/centros-custo/colunas/${id}`);
    return response.data;
  },

  updateCentroCusto: async (dbId: number, data: { custom_data?: any; status?: string; track_in_dashboard?: boolean; project_phase?: string; manual_land_cost?: number; land_payment_curve_id?: number | null; land_payment_start_date?: string | null; apportionment_rules?: any[] }): Promise<any> => {
    const response = await api.put(`/apoio/centros-custo/${dbId}`, data);
    return response.data;
  },

  getPrimeiroMesCaixa: async (dbId: number): Promise<{
    primeiro_mes_caixa: string | null;
    primeiro_mes_desembolso: string | null;
    mes_sugerido: string | null;
  }> => {
    const response = await api.get(`/apoio/centros-custo/${dbId}/primeiro-mes-caixa`);
    return response.data;
  },

  getPlanosFinanceiros: async (): Promise<any[]> => {
    try {
      const response = await api.get('/apoio/planos-financeiros');
      return response.data;
    } catch (error) {
      console.error("Erro ao buscar planos financeiros da API:", error);
      return []; 
    }
  },

  syncPlanosFinanceiros: async (): Promise<any> => {
    const response = await api.post('/apoio/planos-financeiros/sync');
    return response.data;
  },

  // ── Visões ──────────────────────────────────────────────────────────────────

  listVisoes: async (): Promise<any[]> => {
    try {
      const response = await api.get('/apoio/visoes');
      return response.data;
    } catch (error) {
      console.error("Erro ao listar visões:", error);
      return [];
    }
  },

  createVisao: async (data: { nome: string; descricao?: string; copiar_de_id?: number | null }): Promise<any> => {
    const response = await api.post('/apoio/visoes', data);
    return response.data;
  },

  updateVisao: async (id: number, data: { nome: string; descricao?: string }): Promise<any> => {
    const response = await api.put(`/apoio/visoes/${id}`, data);
    return response.data;
  },

  deleteVisao: async (id: number): Promise<any> => {
    const response = await api.delete(`/apoio/visoes/${id}`);
    return response.data;
  },

  getArvoreVisao: async (id: number): Promise<VisaoNode[]> => {
    try {
      const response = await api.get(`/apoio/visoes/${id}/arvore`);
      return response.data;
    } catch (error) {
      console.error("Erro ao buscar árvore da Visão:", error);
      return [];
    }
  },

  getNaoMapeadosVisao: async (id: number): Promise<any[]> => {
    try {
      const response = await api.get(`/apoio/visoes/${id}/nao-mapeados`);
      return response.data;
    } catch (error) {
      console.error("Erro ao buscar não mapeados:", error);
      return [];
    }
  },

  movePlanoInVisao: async (visaoId: number, planoId: number, visionNodeId: number | null): Promise<any> => {
    const response = await api.patch(`/apoio/visoes/${visaoId}/planos/${planoId}/move`, { vision_node_id: visionNodeId });
    return response.data;
  },

  createCategoria: async (visaoId: number, data: { codigo: string; descricao: string }): Promise<any> => {
    const response = await api.post(`/apoio/visoes/${visaoId}/categorias`, data);
    return response.data;
  },

  updateCategoria: async (visaoId: number, nodeId: number, data: { codigo: string; descricao: string }): Promise<any> => {
    const response = await api.put(`/apoio/visoes/${visaoId}/categorias/${nodeId}`, data);
    return response.data;
  },

  deleteCategoria: async (visaoId: number, nodeId: number): Promise<any> => {
    const response = await api.delete(`/apoio/visoes/${visaoId}/categorias/${nodeId}`);
    return response.data;
  },

  // ── Planos de Pagamento (Templates Globais) ─────────────────────────────────

  getPlanosPagamento: async (): Promise<any[]> => {
    try {
      const response = await api.get('/apoio/planos-pagamento');
      return response.data;
    } catch (error) {
      console.error("Erro ao buscar planos de pagamento da API:", error);
      return []; 
    }
  },

  createPlanoPagamento: async (data: { nome: string; condicoes_json: any[] }): Promise<any> => {
    const response = await api.post('/apoio/planos-pagamento', data);
    return response.data;
  },

  updatePlanoPagamento: async (id: number, data: { nome?: string; condicoes_json?: any[] }): Promise<any> => {
    const response = await api.put(`/apoio/planos-pagamento/${id}`, data);
    return response.data;
  },

  deletePlanoPagamento: async (id: number): Promise<any> => {
    const response = await api.delete(`/apoio/planos-pagamento/${id}`);
    return response.data;
  },

  seedPlanosPagamento: async (): Promise<any[]> => {
    const response = await api.post('/apoio/planos-pagamento/seed');
    return response.data;
  },

  // ── Cenários ─────────────────────────────────────────────────────────────────

  getCenarios: async (): Promise<any[]> => {
    try {
      const response = await api.get('/apoio/cenarios');
      return response.data;
    } catch (error) {
      console.error("Erro ao buscar cenários da API:", error);
      return []; 
    }
  },

  createCenario: async (data: { nome: string; vgv_multiplier?: number; construction_cost_multiplier?: number; sales_speed_multiplier?: number }): Promise<any> => {
    const response = await api.post('/apoio/cenarios', data);
    return response.data;
  },

  updateCenario: async (id: number, data: { nome?: string; vgv_multiplier?: number; construction_cost_multiplier?: number; sales_speed_multiplier?: number }): Promise<any> => {
    const response = await api.put(`/apoio/cenarios/${id}`, data);
    return response.data;
  },

  deleteCenario: async (id: number): Promise<any> => {
    const response = await api.delete(`/apoio/cenarios/${id}`);
    return response.data;
  },

  seedCenarios: async (): Promise<any[]> => {
    const response = await api.post('/apoio/cenarios/seed');
    return response.data;
  },

  // ── Indicadores Globais (Econômicos) ─────────────────────────────────────────

  getIndicadores: async (): Promise<any[]> => {
    try {
      const response = await api.get('/apoio/indicadores');
      return response.data;
    } catch (error) {
      console.error("Erro ao buscar indicadores da API:", error);
      return [];
    }
  },

  createIndicador: async (data: { nome: string; index_type: string; valor: number; tipo_unidade: string }): Promise<any> => {
    const response = await api.post('/apoio/indicadores', data);
    return response.data;
  },

  updateIndicador: async (id: number, data: { nome?: string; index_type?: string; valor?: number; tipo_unidade?: string }): Promise<any> => {
    const response = await api.put(`/apoio/indicadores/${id}`, data);
    return response.data;
  },

  deleteIndicador: async (id: number): Promise<any> => {
    const response = await api.delete(`/apoio/indicadores/${id}`);
    return response.data;
  },

  // --- Regimes Tributários ---
  getTaxRegimes: async (): Promise<any[]> => {
    try {
      const response = await api.get('/apoio/impostos/');
      return response.data;
    } catch (e) {
      console.error(e);
      return [];
    }
  },
  createTaxRegime: async (data: any): Promise<any> => {
    const response = await api.post('/apoio/impostos/', data);
    return response.data;
  },
  updateTaxRegime: async (id: number, data: any): Promise<any> => {
    const response = await api.put(`/apoio/impostos/${id}`, data);
    return response.data;
  },
  deleteTaxRegime: async (id: number): Promise<any> => {
    const response = await api.delete(`/apoio/impostos/${id}`);
    return response.data;
  },

  // ── Índices de Mercado (BCB Tempo Real) ─────────────────────────────────────

  getIpca: async (): Promise<any> => {
    const response = await api.get('/market-indices/ipca');
    return response.data;
  },

  getIncc: async (): Promise<any> => {
    const response = await api.get('/market-indices/incc');
    return response.data;
  },

  getFocus: async (): Promise<any> => {
    const response = await api.get('/market-indices/focus');
    return response.data;
  },
};

