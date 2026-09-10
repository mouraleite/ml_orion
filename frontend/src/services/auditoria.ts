import { api } from '@/lib/api';

export interface AuditoriaLog {
  id: number;
  evento: string;
  tabela_afetada: string | null;
  registro_id: number | null;
  campo: string | null;
  valor_anterior: string | null;
  novo_valor: string | null;
  usuario_id: number | null;
  data_hora: string;
  usuario_nome: string | null;
}

export interface AuditoriaResponse {
  items: AuditoriaLog[];
  total: number;
}

export interface AuditoriaFilterParams {
  usuario_id?: number;
  data_inicio?: string;
  data_fim?: string;
  evento?: string;
  tabela_afetada?: string;
  skip?: number;
  limit?: number;
}

export const auditoriaService = {
  async getLogs(params: AuditoriaFilterParams): Promise<AuditoriaResponse> {
    const { data } = await api.get<AuditoriaResponse>('/auditoria/', { params });
    return data;
  },

  async exportLogs(params: AuditoriaFilterParams): Promise<Blob> {
    // We can use the same params, ignoring skip and limit
    const exportParams = { ...params };
    delete exportParams.skip;
    delete exportParams.limit;

    const response = await api.get('/auditoria/export', {
      params: exportParams,
      responseType: 'blob', // Important to get the file as Blob
    });
    return response.data;
  }
};
