import { api } from "@/lib/api";

export interface DiaConsumoSienge {
  data: string;
  total: number | null;
  medido: boolean;
  acima_do_limite: boolean;
}

export interface FamiliaConsumoSienge {
  familia: "REST" | "BULK";
  limite_diario: number;
  limite_por_minuto: number;
  total: number | null;
  media_diaria: number | null;
  maior_dia: string | null;
  maior_dia_total: number | null;
  http_429: number;
  http_401: number;
  http_5xx: number;
  dias: DiaConsumoSienge[];
}

export interface ConsumoSiengeMes {
  ano: number;
  mes: number;
  fuso: string;
  pacote: string;
  historico_vazio: boolean;
  familias: FamiliaConsumoSienge[];
  endpoints: { caminho: string; familia: string; quantidade: number }[];
}

export const siengeConsumoService = {
  async getMes(ano: number, mes: number): Promise<ConsumoSiengeMes> {
    const response = await api.get("/apoio/consumo-sienge", { params: { ano, mes } });
    return response.data;
  },
};
