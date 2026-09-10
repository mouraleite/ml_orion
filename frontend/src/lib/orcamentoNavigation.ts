import { useEffect, useMemo } from "react";
import { useSearchParams } from "next/navigation";

export const ORCAMENTO_ROUTES = {
  analitico1: "/dashboard/orcamento/analitico-gastos-1",
  analitico2: "/dashboard/orcamento/analitico-gastos-2",
  realizadoCp: "/dashboard/orcamento/realizado-despesas",
} as const;

export type OrcamentoRouteKey = keyof typeof ORCAMENTO_ROUTES;

export interface OrcamentoLinkParams {
  ano?: number;
  meses?: string[];
  produto?: number;
  plano?: number;
  modo?: "orcado" | "forecast";
  expand?: boolean;
  busca?: string;
}

export function mesesFiltroToStr(
  mesesSelecionados: string[] | undefined,
  filtroMesesAtivo?: boolean,
): string[] | undefined {
  if (!filtroMesesAtivo || !mesesSelecionados?.length) return undefined;
  return mesesSelecionados.map((m) => m.toLowerCase());
}

export function buildOrcamentoHref(
  route: OrcamentoRouteKey,
  params?: OrcamentoLinkParams,
): string {
  const base = ORCAMENTO_ROUTES[route];
  const sp = new URLSearchParams();
  if (params?.ano) sp.set("ano", String(params.ano));
  if (params?.meses?.length) sp.set("meses", params.meses.join(","));
  if (params?.produto) sp.set("produto", String(params.produto));
  if (params?.plano) sp.set("plano", String(params.plano));
  if (params?.modo) sp.set("modo", params.modo);
  if (params?.expand) sp.set("expand", "1");
  if (params?.busca?.trim()) sp.set("busca", params.busca.trim());
  const qs = sp.toString();
  return qs ? `${base}?${qs}` : base;
}

export function parseOrcamentoSearchParams(
  searchParams: Pick<URLSearchParams, "get" | "has">,
): OrcamentoLinkParams {
  const mesesRaw = searchParams.get("meses");
  const expand = searchParams.get("expand");
  const modoRaw = searchParams.get("modo");
  return {
    ano: searchParams.has("ano") ? Number(searchParams.get("ano")) : undefined,
    meses: mesesRaw ? mesesRaw.split(",").filter(Boolean) : undefined,
    produto: searchParams.has("produto") ? Number(searchParams.get("produto")) : undefined,
    plano: searchParams.has("plano") ? Number(searchParams.get("plano")) : undefined,
    modo: modoRaw === "forecast" ? "forecast" : modoRaw === "orcado" ? "orcado" : undefined,
    expand: expand === "1" || expand === "true",
    busca: searchParams.get("busca") || undefined,
  };
}

export function buildDespesasDeepLinks(params: OrcamentoLinkParams) {
  const base: OrcamentoLinkParams = {
    ano: params.ano,
    meses: params.meses,
    modo: params.modo,
    produto: params.produto,
    plano: params.plano,
  };
  return {
    analitico1: buildOrcamentoHref("analitico1", { ...base, expand: params.expand }),
    analitico2: buildOrcamentoHref("analitico2", { ...base, expand: params.expand }),
    realizadoCp: buildOrcamentoHref("realizadoCp", { ...base, busca: params.busca }),
  };
}

export function useOrcamentoDeepLinkParams(): OrcamentoLinkParams {
  const searchParams = useSearchParams();
  return useMemo(() => parseOrcamentoSearchParams(searchParams), [searchParams]);
}

export function useOrcamentoDeepLinkFilters(setters: {
  setAno?: (v: number) => void;
  setModo?: (v: "orcado" | "forecast") => void;
  setMeses?: (v: string[]) => void;
  setProdutoId?: (v: number | "") => void;
  setPlanoId?: (v: number | "") => void;
  setBusca?: (v: string) => void;
  setBuscaApplied?: (v: string) => void;
}) {
  const deepLink = useOrcamentoDeepLinkParams();

  useEffect(() => {
    if (deepLink.ano && setters.setAno) setters.setAno(deepLink.ano);
    if (deepLink.modo && setters.setModo) setters.setModo(deepLink.modo);
    if (deepLink.meses && setters.setMeses) setters.setMeses(deepLink.meses);
    if (deepLink.produto && setters.setProdutoId) setters.setProdutoId(deepLink.produto);
    if (deepLink.plano && setters.setPlanoId) setters.setPlanoId(deepLink.plano);
    if (deepLink.busca) {
      setters.setBusca?.(deepLink.busca);
      setters.setBuscaApplied?.(deepLink.busca);
    }
  }, [
    deepLink.ano,
    deepLink.modo,
    deepLink.meses,
    deepLink.produto,
    deepLink.plano,
    deepLink.busca,
    setters.setAno,
    setters.setModo,
    setters.setMeses,
    setters.setProdutoId,
    setters.setPlanoId,
    setters.setBusca,
    setters.setBuscaApplied,
  ]);

  return deepLink;
}
