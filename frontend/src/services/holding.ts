import { api } from "@/lib/api";

export interface OwnershipPeriod {
  id: number;
  percentage: number;
  valid_from: string | null;
  valid_until: string | null;
  notes?: string | null;
}

export interface OwnershipTreeNode {
  link_id?: number;
  company_id: number;
  id_sienge: string;
  nome_fantasia?: string;
  razao_social?: string;
  percentage?: number;
  consolidates?: boolean;
  notes?: string | null;
  historico?: OwnershipPeriod[];
  participacao_efetiva: number;
  participacao_calculada?: number | null;
  participacao_manual?: number | null;
  usa_participacao_manual?: boolean;
  fonte?: string;
  calculo_tooltip?: string;
  children?: OwnershipTreeNode[];
}

export interface EstruturaMlduResponse {
  root: OwnershipTreeNode | null;
  message?: string;
  empresas_sem_vinculo?: OwnershipTreeNode[];
  divergencias?: { nome: string; pai: string; apoio_pct: number; consolidacao_pct: number }[];
}

export interface OwnershipLinkPayload {
  parent_company_id: number;
  child_company_id: number;
  percentage: number;
  consolidates?: boolean;
  notes?: string;
}

export interface OrganogramaValidacaoEmpresa {
  id_sienge: string;
  company_id?: number;
  nome?: string;
  status: "ok" | "divergente" | "ausente";
  expected_pct: number;
  actual_pct?: number;
  calculated_pct?: number;
  fonte?: string;
  message?: string;
}

export interface OrganogramaValidacaoResponse {
  ok: boolean;
  divergencias: number;
  empresas: OrganogramaValidacaoEmpresa[];
  vinculos: Array<{
    parent_id_sienge: string;
    child_id_sienge: string;
    status: string;
    expected_pct: number;
    actual_pct?: number;
    message?: string;
  }>;
  avisos: string[];
  referencia: {
    fonte: string;
    tolerancia_pct: number;
    total_empresas_referencia: number;
    total_vinculos_referencia: number;
  };
}

export const holdingService = {
  getEstrutura: async (): Promise<EstruturaMlduResponse> => {
    const response = await api.get("/holding/estrutura-mldu");
    return response.data;
  },

  createLink: async (data: OwnershipLinkPayload): Promise<{ id: number }> => {
    const response = await api.post("/holding/ownership-links", data);
    return response.data;
  },

  updateLink: async (
    linkId: number,
    data: Partial<OwnershipLinkPayload & { parent_company_id: number; valid_from?: string }>,
  ): Promise<void> => {
    await api.put(`/holding/ownership-links/${linkId}`, data);
  },

  deleteLink: async (linkId: number): Promise<void> => {
    await api.delete(`/holding/ownership-links/${linkId}`);
  },

  setParticipacaoManual: async (
    companyId: number,
    data: { usa_participacao_manual: boolean; participacao_mldu_manual?: number | null },
  ): Promise<void> => {
    await api.put(`/holding/empresas/${companyId}/participacao-manual`, data);
  },

  recalcular: async (): Promise<void> => {
    await api.post("/holding/estrutura-mldu/recalcular");
  },

  seedReferencia: async (): Promise<{ created: number; skipped: string[] }> => {
    const response = await api.post("/holding/estrutura-mldu/seed");
    return response.data;
  },

  getValidacaoOrganograma: async (): Promise<OrganogramaValidacaoResponse> => {
    const response = await api.get("/holding/validacao-organograma");
    return response.data;
  },
};
