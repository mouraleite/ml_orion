import { api } from "@/lib/api";

export interface AccessProfile {
  id: number;
  name: string;
  description?: string;
  is_active: boolean;
  permissions: Record<string, Record<string, boolean>>;
}

export const accessProfilesService = {
  getAll: async (): Promise<AccessProfile[]> => {
    const { data } = await api.get("/perfis-acesso/");
    return data;
  },

  create: async (payload: Partial<AccessProfile>): Promise<AccessProfile> => {
    const { data } = await api.post("/perfis-acesso/", payload);
    return data;
  },

  update: async (id: number, payload: Partial<AccessProfile>): Promise<AccessProfile> => {
    const { data } = await api.put(`/perfis-acesso/${id}`, payload);
    return data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/perfis-acesso/${id}`);
  }
};
