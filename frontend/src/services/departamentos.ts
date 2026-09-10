import { api } from "@/lib/api";

export interface Departamento {
  id: number;
  nome: string;
  ativo: boolean;
  is_residual?: boolean;
  diretoria_id?: number | null;
}

export interface Diretoria {
  id: number;
  nome: string;
  ativo: boolean;
  departamento_ids: number[];
}

export interface DeptCostCenter {
  id: number;
  id_sienge: string;
  nome: string;
  status: string;
  id_empresa?: number | null;
  nome_empresa?: string | null;
  permitido: boolean;
}

export interface DeptPlano {
  id: number;
  nome: string;
  tipo: string;
  db_id: string;
  permitido: boolean;
}

export const departamentosService = {
  getAll: async (): Promise<Departamento[]> => {
    const { data } = await api.get("/matriz-permissoes/departamentos");
    return data;
  },

  getTodos: async (): Promise<Departamento[]> => {
    const { data } = await api.get("/matriz-permissoes/departamentos/todos");
    return data;
  },

  create: async (payload: Partial<Departamento>): Promise<Departamento> => {
    const { data } = await api.post("/matriz-permissoes/departamentos", payload);
    return data;
  },

  update: async (id: number, payload: Partial<Departamento>): Promise<Departamento> => {
    const { data } = await api.put(`/matriz-permissoes/departamentos/${id}`, payload);
    return data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/matriz-permissoes/departamentos/${id}`);
  },

  getCostCenters: async (deptId: number): Promise<DeptCostCenter[]> => {
    const { data } = await api.get(`/matriz-permissoes/departamentos/${deptId}/cost-centers`);
    return data;
  },

  getPlanos: async (deptId: number): Promise<DeptPlano[]> => {
    const { data } = await api.get(`/matriz-permissoes/departamentos/${deptId}/planos`);
    return data;
  },

  setCostCenter: async (departamento_id: number, cost_center_id: number, permitido: boolean) => {
    const { data } = await api.post("/matriz-permissoes/departamento-cost-center", {
      departamento_id, cost_center_id, permitido
    });
    return data;
  },

  setPlano: async (departamento_id: number, plano_financeiro_id: number, permitido: boolean) => {
    const { data } = await api.post("/matriz-permissoes/departamento-plano", {
      departamento_id, plano_financeiro_id, permitido
    });
    return data;
  },

  setCostCentersBulk: async (departamento_id: number, ids: number[], permitido: boolean) => {
    const { data } = await api.post("/matriz-permissoes/departamento-cost-center/bulk", {
      departamento_id, ids, permitido
    });
    return data;
  },

  setPlanosBulk: async (departamento_id: number, ids: number[], permitido: boolean) => {
    const { data } = await api.post("/matriz-permissoes/departamento-plano/bulk", {
      departamento_id, ids, permitido
    });
    return data;
  },

  copiarAutorizacoes: async (
    destId: number,
    payload: { origem_id: number; copiar_obras: boolean; copiar_planos: boolean },
  ) => {
    const { data } = await api.post(`/matriz-permissoes/departamentos/${destId}/copiar-autorizacoes`, payload);
    return data as { obras: number; planos: number; origem: string; destino: string };
  },

  listDepara: async (): Promise<DeparaAutorizacao[]> => {
    const { data } = await api.get("/matriz-permissoes/depara-autorizacao");
    return data;
  },

  residualCorporativo: async (): Promise<CorporativoResidual> => {
    const { data } = await api.get("/matriz-permissoes/corporativo-residual");
    return data;
  },

  syncDepara: async (): Promise<DeparaAutorizacao[]> => {
    const { data } = await api.post("/matriz-permissoes/depara-autorizacao/sync");
    return data;
  },

  updateDepara: async (id: number, departamento_id: number | null): Promise<DeparaAutorizacao> => {
    const { data } = await api.put(`/matriz-permissoes/depara-autorizacao/${id}`, { departamento_id });
    return data;
  },

  listDiretorias: async (): Promise<Diretoria[]> => {
    const { data } = await api.get("/matriz-permissoes/diretorias");
    return data;
  },

  createDiretoria: async (payload: {
    nome: string;
    ativo?: boolean;
    departamento_ids?: number[];
  }): Promise<Diretoria> => {
    const { data } = await api.post("/matriz-permissoes/diretorias", payload);
    return data;
  },

  updateDiretoria: async (
    id: number,
    payload: { nome?: string; ativo?: boolean; departamento_ids?: number[] },
  ): Promise<Diretoria> => {
    const { data } = await api.put(`/matriz-permissoes/diretorias/${id}`, payload);
    return data;
  },

  deleteDiretoria: async (id: number): Promise<void> => {
    await api.delete(`/matriz-permissoes/diretorias/${id}`);
  },
};

export interface CorporativoResidual {
  departamento_id: number;
  nome: string;
  planos_residuais: number;
  planos_comuns: number;
  planos_exclusivos: number;
  orcamentos_sem_departamento: number;
  forecasts_sem_departamento: number;
}

export interface DeparaAutorizacao {
  id: number;
  nome_sienge: string;
  sienge_department_id: number | null;
  departamento_id: number | null;
  departamento_nome: string | null;
  definido_manual: boolean;
  corporativo: boolean;
}
