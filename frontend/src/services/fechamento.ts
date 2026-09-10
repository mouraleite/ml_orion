import { api } from '@/lib/api';

export interface ClosedMonthResponse {
  id: number;
  ano: number;
  mes: number;
  fechado_por_id: number;
  data_fechamento: string;
}

export const fechamentoService = {
  getMesesFechados: async () => {
    const response = await api.get('/fechamento/meses');
    return response.data;
  },

  fecharMes: async (ano: number, mes: number) => {
    const response = await api.post('/fechamento/mes', { ano, mes });
    return response.data;
  },

  abrirMes: async (ano: number, mes: number) => {
    const response = await api.delete(`/fechamento/mes/${ano}/${mes}`);
    return response.data;
  }
};
