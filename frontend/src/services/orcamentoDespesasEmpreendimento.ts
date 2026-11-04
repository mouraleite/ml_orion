import { api } from "@/lib/api";
import { cachedRead } from "@/lib/readCache";

const ACOMP_TIMEOUT_MS = 120000;

function deptHeader(deptId: number) {
  return { headers: { "X-Department-Id": String(deptId) } };
}

export async function getDespesasEmpreendimento(
  ano: number,
  deptId: number,
  corte: number,
  empresaIds?: string[],
  forecastId?: number,
) {
  let url = `/dashboard/despesas-empreendimento/${ano}?corte=${corte}`;
  if (empresaIds && empresaIds.length > 0) {
    url += `&empresa_ids=${empresaIds.map(encodeURIComponent).join(",")}`;
  }
  if (forecastId) url += `&forecast_id=${forecastId}`;
  return cachedRead(
    `dash:desp-emp:${ano}:${deptId}:${corte}:${(empresaIds || []).join(",")}:${forecastId || ""}`,
    () => api.get(url, { ...deptHeader(deptId), timeout: ACOMP_TIMEOUT_MS }).then((r) => r.data),
  );
}
