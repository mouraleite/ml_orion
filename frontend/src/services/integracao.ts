import { api } from '@/lib/api';

export interface ReprocessRequest {
  start_date: string;
  end_date: string;
}

export interface IntegracaoLog {
  id: number;
  processo: string;
  inicio: string;
  fim: string | null;
  status: string;
  volume_processado: number;
  erros: string | null;
}

export interface Pendencia {
  id: number;
  id_sienge: string;
  produto_id_sienge: string | null;
  plano_financeiro_id_sienge: string | null;
  tipo: string | null;
  mes: number;
  ano: number;
  valor: number;
  vgv: number;
  data_integracao: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export const integracaoService = {
  async reprocessar(data: ReprocessRequest): Promise<{ message: string }> {
    const response = await api.post('/integracao/reprocessar', data);
    return response.data;
  },

  async getLogs(skip: number = 0, limit: number = 20): Promise<PaginatedResponse<IntegracaoLog>> {
    const response = await api.get('/integracao/logs', { params: { skip, limit } });
    return response.data;
  },

  async getPendencias(skip: number = 0, limit: number = 50): Promise<PaginatedResponse<Pendencia>> {
    const response = await api.get('/integracao/pendencias', { params: { skip, limit } });
    return response.data;
  }
};
