import { api } from "@/lib/api";
import { cachedRead } from "@/lib/readCache";

const ACOMP_TIMEOUT_MS = 120000;

function deptHeader(deptId: number) {
  return { headers: { "X-Department-Id": String(deptId) } };
}

export type DfcGerencialAgrupamento = "visao" | "centro";

export async function getDfcGerencial(
  ano: number,
  deptId: number,
  meses?: string[],
  empresaIds?: string[],
  forecastId?: number,
  agrupamento: DfcGerencialAgrupamento = "visao",
) {
  let url = `/dashboard/dfc/${ano}/gerencial?agrupamento=${agrupamento}`;
  if (meses && meses.length > 0) url += `&meses=${meses.join(",")}`;
  if (empresaIds && empresaIds.length > 0) {
    url += `&empresa_ids=${empresaIds.map(encodeURIComponent).join(",")}`;
  }
  if (forecastId) url += `&forecast_id=${forecastId}`;
  return cachedRead(
    `dash:dfc-gerencial:${ano}:${deptId}:${agrupamento}:${(meses || []).join(",")}:${(empresaIds || []).join(",")}:${forecastId || ""}`,
    () => api.get(url, { ...deptHeader(deptId), timeout: ACOMP_TIMEOUT_MS }).then((r) => r.data),
  );
}
