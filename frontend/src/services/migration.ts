import { api } from '@/lib/api';

export interface MigrationMapping {
  id: number;
  tipo: string;
  nome_origem: string;
  id_destino: number | null;
  status: string;
  data_criacao: string;
}

export interface MigrationMapRequest {
  id: number;
  id_destino: number;
}

export const getPendencias = async (): Promise<MigrationMapping[]> => {
  const response = await api.get('/migration/pendencias');
  return response.data;
};

export const mapearPendencias = async (req: MigrationMapRequest[]): Promise<any> => {
  const response = await api.post('/migration/map', req);
  return response.data;
};

export const runMigration = async (): Promise<any> => {
  const response = await api.post('/migration/run');
  return response.data;
};

export const runForecastMigration = async (): Promise<any> => {
  const response = await api.post('/migration/run-forecast');
  return response.data;
};
