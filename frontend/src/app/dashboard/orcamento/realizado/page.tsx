"use client";
import React, { useState, useEffect, useCallback, Fragment, useMemo, useRef, startTransition } from "react";
import { FileSpreadsheet } from "lucide-react";
import { useRouter } from "next/navigation";
import { orcamentoService } from "@/services/orcamento";
import { apoioService } from "@/services/apoio";
import { useAuth } from "@/contexts/AuthContext";
import { BudgetScopeBar } from "@/components/shared/BudgetScopeBar";
import { YearSelect } from "@/components/shared/YearSelect";
import { BudgetMatrixShell } from "@/components/shared/BudgetMatrixShell";
import {
  MonthlyGridFilterPanel,
  type MonthlyGridFilterValues,
} from "@/components/shared/MonthlyGridFilterPanel";
import {
  buildEmpresaLinkedOptions,
  buildEmpresasMapFromCadastro,
  enrichProdutosComEmpresaCadastro,
} from "@/lib/gridFilters";
import { idsPublicosCentro } from "@/lib/idSienge";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId } from "@/lib/useActiveDepartmentId";
import {
  buildOrcamentoHref,
  mesesFiltroToStr,
  type OrcamentoLinkParams,
} from "@/lib/orcamentoNavigation";
import { OrcamentoDeepLinks } from "@/components/orcamento/OrcamentoDeepLinks";
import {
  BarChart2, TrendingUp, TrendingDown, DollarSign, GitCompare,
  Eye, RefreshCw, Download, ChevronDown, ChevronRight, AlertCircle, CheckCircle2,
  ArrowRightLeft, Search, LayoutDashboard, Table2, Target, Layers,
  ArrowUp, ArrowDown, ArrowUpDown, Calendar, LineChart
} from "lucide-react";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/Table";
import { parseCentroNome } from "@/lib/parseCentroNome";
import { MATERIALITY_THRESHOLD } from "@/lib/orcamentoDesvioUi";
import { SemaforoDesvio } from "@/components/orcamento/SemaforoDesvio";
import { tipoSemaforo } from "@/lib/semaforoDesvio";
import {
  BudgetLoadError,
  BudgetLoadingState,
  AppLoadingState,
  BudgetRefreshingBanner,
  acompRequestError,
} from "@/components/shared/BudgetLoadingState";

const MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const MESES_STR = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

async function exportDataToExcel(headers: string[], rows: any[][], filename: string) {
  const { baixarXlsx } = await import("@/lib/planilha");
  await baixarXlsx([headers, ...rows], "Dados", filename);
}

const formatMoeda = (v: number) => {
  if (v === null || v === undefined) return "R$ 0";
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 0, maximumFractionDigits: 0 });
};
const formatPerc = (v: number) => {
  if (v === null || v === undefined) return "0%";
  return `${(v * 100).toFixed(1)}%`;
};

/** Cor só no Δ / veredito: verde favorável, laranja material, vermelho desfavorável. */
function variationTone(favoravel: boolean, varRs: number, varPerc: number) {
  if (varRs === 0) {
    return {
      panel: "bg-slate-50/80",
      value: "text-slate-800",
      muted: "text-slate-600",
      badge: "bg-slate-100 text-slate-600",
    };
  }
  if (favoravel) {
    return {
      panel: "bg-emerald-50/80",
      value: "text-emerald-800",
      muted: "text-emerald-700",
      badge: "bg-emerald-100 text-emerald-800",
    };
  }
  if (Math.abs(varPerc) >= MATERIALITY_THRESHOLD) {
    return {
      panel: "bg-orange-50/80",
      value: "text-orange-950",
      muted: "text-orange-800",
      badge: "bg-orange-100 text-orange-900",
    };
  }
  return {
    panel: "bg-red-50/80",
    value: "text-red-800",
    muted: "text-red-700",
    badge: "bg-red-100 text-red-800",
  };
}

type VendasComparativoMetric = "vgv" | "unidades";

function formatComparativoValor(v: number, metric: VendasComparativoMetric, tipo: string) {
  if (tipo === "VENDAS" && metric === "unidades") {
    return Number(v || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  }
  return formatMoeda(v);
}

function getComparativoVersaoTotal(versaoData: any, metric: VendasComparativoMetric, tipo: string) {
  if (!versaoData) return 0;
  if (tipo === "VENDAS" && metric === "unidades") {
    return Number(versaoData.numero_vendas?.total ?? 0);
  }
  return Number(versaoData.total ?? versaoData.vgv ?? 0);
}

function getComparativoVersaoMes(
  versaoData: any,
  mes: string,
  metric: VendasComparativoMetric,
  tipo: string,
) {
  if (!versaoData) return 0;
  if (tipo === "VENDAS" && metric === "unidades") {
    return Number(versaoData.numero_vendas?.[mes] ?? 0);
  }
  return Number(versaoData[mes] ?? 0);
}

function getComparativoVisibleMeses(filtros: any) {
  return MESES.filter(
    (m) => !filtros?.filtroMesesAtivo || filtros.mesesSelecionados.includes(m),
  ).map((m) => m.toLowerCase());
}

function getComparativoItemMultiplier(item: any, result: any, tipo: string) {
  if (tipo !== "CONSOLIDADO") return 1;
  const planoId = item.versao_a?.plano_financeiro_id ?? item.plano_financeiro_id;
  return result?.planos_redutora?.[planoId] ? -1 : 1;
}

function processComparativoItemMes(
  item: any,
  mes: string,
  tipo: string,
  result: any,
  vendasMetric: VendasComparativoMetric,
) {
  const mult = getComparativoItemMultiplier(item, result, tipo);
  const valA = getComparativoVersaoMes(item.versao_a, mes, vendasMetric, tipo) * mult;
  const valB = getComparativoVersaoMes(item.versao_b, mes, vendasMetric, tipo) * mult;
  const varRs = valB - valA;
  return { valA, valB, varRs, favoravel: isVariacaoFavoravel(varRs, tipo) };
}

function buildComparativoDesvioPorMes(
  filteredResult: any,
  tipo: string,
  vendasMetric: VendasComparativoMetric,
  mesesStr: string[],
) {
  return mesesStr.map((mes) => {
    let totalA = 0;
    let totalB = 0;
    for (const list of [filteredResult.inclusoes, filteredResult.alteracoes, filteredResult.exclusoes]) {
      for (const item of list || []) {
        const mult = getComparativoItemMultiplier(item, filteredResult, tipo);
        totalA += getComparativoVersaoMes(item.versao_a, mes, vendasMetric, tipo) * mult;
        totalB += getComparativoVersaoMes(item.versao_b, mes, vendasMetric, tipo) * mult;
      }
    }
    const idx = MESES_STR.indexOf(mes);
    return {
      mes,
      label: MESES[idx] ?? mes,
      varRs: totalB - totalA,
      totalA,
      totalB,
      favoravel: isVariacaoFavoravel(totalB - totalA, tipo),
    };
  });
}

function comparativoMinVariacao(tipo: string, metric: VendasComparativoMetric) {
  return tipo === "VENDAS" && metric === "unidades" ? 0 : 0.01;
}

function isVariacaoFavoravel(varRs: number, tipo: string) {
  const positivoBom = tipo === "VENDAS" || tipo === "RECEITAS" || tipo === "CONSOLIDADO";
  if (varRs === 0) return true;
  return (varRs > 0 && positivoBom) || (varRs < 0 && !positivoBom);
}

function processComparativoItem(
  item: any,
  tipo: string,
  result: any,
  vendasMetric: VendasComparativoMetric = "vgv",
) {
  const planoId = item.versao_a?.plano_financeiro_id ?? item.plano_financeiro_id;
  let multiplier = 1;
  if (tipo === "CONSOLIDADO") {
    const isRedutora = result.planos_redutora?.[planoId];
    multiplier = isRedutora ? -1 : 1;
  }
  const valA = getComparativoVersaoTotal(item.versao_a, vendasMetric, tipo) * multiplier;
  const valB = getComparativoVersaoTotal(item.versao_b, vendasMetric, tipo) * multiplier;
  const varRs = valB - valA;
  const varPerc = valA !== 0 ? varRs / Math.abs(valA) : valB !== 0 ? 1 : 0;
  return {
    ...item,
    valA,
    valB,
    varRs,
    varPerc,
    absVarRs: Math.abs(varRs),
    multiplier,
    favoravel: isVariacaoFavoravel(varRs, tipo),
  };
}

function aggregateComparativoByKey(
  items: any[],
  getKey: (item: any) => string | number,
  getLabel: (key: string | number) => string,
) {
  const map = new Map<string | number, { key: string | number; label: string; varRs: number; absVarRs: number; count: number }>();
  for (const item of items) {
    const key = getKey(item);
    const existing = map.get(key) || { key, label: getLabel(key), varRs: 0, absVarRs: 0, count: 0 };
    existing.varRs += item.varRs;
    existing.absVarRs += item.absVarRs;
    existing.count += 1;
    map.set(key, existing);
  }
  return Array.from(map.values()).sort((a, b) => b.absVarRs - a.absVarRs);
}

function buildComparativoInsights(
  result: any,
  tipo: string,
  vendasMetric: VendasComparativoMetric = "vgv",
) {
  const fmt = (v: number) => formatComparativoValor(v, vendasMetric, tipo);
  const minVar = comparativoMinVariacao(tipo, vendasMetric);

  const rawInc = (result.inclusoes || []).map((i: any) => processComparativoItem(i, tipo, result, vendasMetric));
  const rawExc = (result.exclusoes || []).map((i: any) => processComparativoItem(i, tipo, result, vendasMetric));
  const rawAlt = (result.alteracoes || []).map((i: any) => processComparativoItem(i, tipo, result, vendasMetric));

  let globalTotalA = 0;
  let globalTotalB = 0;
  for (const item of [...rawInc, ...rawExc, ...rawAlt]) {
    globalTotalA += item.valA;
    globalTotalB += item.valB;
  }

  const processedInc = rawInc.filter((i) => i.absVarRs > minVar);
  const processedExc = rawExc.filter((i) => i.absVarRs > minVar);
  const processedAltChanged = rawAlt.filter((i) => i.absVarRs > minVar);
  const processedAltUnchanged = rawAlt.filter((i) => i.absVarRs <= minVar);

  const allItems = [...processedInc, ...processedExc, ...processedAltChanged].sort(
    (a, b) => b.absVarRs - a.absVarRs,
  );

  const todasLinhasRaw = [
    ...rawInc.map((i) => ({ ...i, categoriaComparativo: "Inclusão" as const })),
    ...rawExc.map((i) => ({ ...i, categoriaComparativo: "Exclusão" as const })),
    ...rawAlt.map((i) => ({
      ...i,
      categoriaComparativo: (i.absVarRs > minVar ? "Alteração" : "Sem variação") as const,
    })),
  ].sort((a, b) => b.absVarRs - a.absVarRs);

  const globalVarRs = globalTotalB - globalTotalA;
  const globalVarPerc = globalTotalA !== 0 ? globalVarRs / Math.abs(globalTotalA) : 0;

  const favorableItems = allItems.filter((i) => i.favoravel && i.varRs !== 0);
  const unfavorableItems = allItems.filter((i) => !i.favoravel && i.varRs !== 0);

  const sumVar = (items: any[]) => items.reduce((s, i) => s + i.varRs, 0);
  const sumAbsVar = (items: any[]) => items.reduce((s, i) => s + i.absVarRs, 0);

  const impactInc = sumVar(processedInc);
  const impactExc = sumVar(processedExc);
  const impactAlt = sumVar(processedAltChanged);
  const totalAbsVar = sumAbsVar(allItems) || 1;

  const top5Abs = sumAbsVar(allItems.slice(0, 5));
  const concentracaoTop5 = allItems.length > 0 ? top5Abs / totalAbsVar : 0;
  const concentracaoTop10 = allItems.length > 0 ? sumAbsVar(allItems.slice(0, 10)) / totalAbsVar : 0;

  const absImpactTotal = Math.abs(impactAlt) + Math.abs(impactInc) + Math.abs(impactExc) || 1;
  const pctImpactAlt = Math.abs(impactAlt) / absImpactTotal;
  const pctImpactInc = Math.abs(impactInc) / absImpactTotal;
  const pctImpactExc = Math.abs(impactExc) / absImpactTotal;

  const saldoFavoravel = sumVar(favorableItems);
  const saldoDesfavoravel = sumVar(unfavorableItems);

  const getProdId = (item: any) => item.versao_a?.produto_id ?? item.produto_id;
  const getPlanoId = (item: any) => item.versao_a?.plano_financeiro_id ?? item.plano_financeiro_id;

  const topProdutos = aggregateComparativoByKey(
    allItems,
    getProdId,
    (id) => result.produtos_map?.[id] || String(id),
  ).slice(0, 5);

  const topPlanos = aggregateComparativoByKey(
    allItems,
    getPlanoId,
    (id) => result.planos_map?.[id] || String(id),
  ).slice(0, 5);

  const topProdutosWithShare = topProdutos.map((p) => ({ ...p, shareAbs: p.absVarRs / totalAbsVar }));
  const topPlanosWithShare = topPlanos.map((p) => ({ ...p, shareAbs: p.absVarRs / totalAbsVar }));

  const tipoLabel =
    tipo === "DESPESAS" ? "despesas" : tipo === "RECEITAS" ? "receitas" : tipo === "VENDAS" ? "vendas" : "resultado consolidado";

  const alertas: { tone: "red" | "amber"; title: string; detail: string }[] = [];
  if (!isVariacaoFavoravel(globalVarRs, tipo) && allItems.length > 0) {
    alertas.push({
      tone: "red",
      title: "Variação total desfavorável",
      detail: `${fmt(globalVarRs)} (${formatPerc(globalVarPerc)}) em ${tipoLabel}. Priorize revisão dos itens em vermelho.`,
    });
  }
  if (concentracaoTop5 >= 0.6) {
    alertas.push({
      tone: "amber",
      title: "Alta concentração do desvio",
      detail: `Os 5 maiores itens explicam ${(concentracaoTop5 * 100).toFixed(0)}% do desvio absoluto.`,
    });
  }
  if (processedInc.length > 0 && Math.abs(impactInc) > totalAbsVar * 0.15) {
    alertas.push({
      tone: "amber",
      title: "Inclusões relevantes",
      detail: `${processedInc.length} linha(s) nova(s) somam ${fmt(impactInc)} na versão comparada.`,
    });
  }
  unfavorableItems.slice(0, 3).forEach((item, idx) => {
    const prod = result.produtos_map?.[getProdId(item)] || getProdId(item);
    const plano = result.planos_map?.[getPlanoId(item)] || getPlanoId(item);
    alertas.push({
      tone: "red",
      title: `Atenção #${idx + 1}`,
      detail: `${prod} · ${plano}: ${fmt(item.varRs)} (${((item.absVarRs / totalAbsVar) * 100).toFixed(0)}% do desvio).`,
    });
  });

  const veredito = allItems.length === 0
    ? "neutro"
    : isVariacaoFavoravel(globalVarRs, tipo)
      ? "favoravel"
      : "desfavoravel";

  const itemsWithShare = allItems.map((item) => ({
    ...item,
    shareAbs: item.absVarRs / totalAbsVar,
  }));

  const todasLinhas = todasLinhasRaw.map((item) => ({
    ...item,
    shareAbs: totalAbsVar > 0 ? item.absVarRs / totalAbsVar : 0,
  }));

  let narrative = "";
  if (allItems.length === 0) {
    narrative = "As duas versões são equivalentes no total — não há desvios materiais por produto/plano.";
  } else if (isVariacaoFavoravel(globalVarRs, tipo)) {
    narrative = `A versão comparada é ${globalVarRs >= 0 ? "superior" : "inferior"} em ${fmt(Math.abs(globalVarRs))} (${formatPerc(globalVarPerc)}), movimento favorável para ${tipoLabel}. ${favorableItems.length} linha(s) contribuem positivamente; ${concentracaoTop5 >= 0.5 ? `mais de metade do desvio vem dos 5 maiores itens (${(concentracaoTop5 * 100).toFixed(0)}%).` : "O desvio está distribuído entre vários itens."}`;
  } else {
    narrative = `Atenção: variação de ${fmt(globalVarRs)} (${formatPerc(globalVarPerc)}) em desfavor de ${tipoLabel}. ${unfavorableItems.length} linha(s) puxam o resultado; revise os destaques abaixo.`;
  }

  return {
    globalTotalA,
    globalTotalB,
    globalVarRs,
    globalVarPerc,
    processedInc,
    processedExc,
    processedAlt: processedAltChanged,
    processedAltUnchanged,
    allItems: itemsWithShare,
    todasLinhas,
    favorableItems,
    unfavorableItems,
    impactInc,
    impactExc,
    impactAlt,
    totalAbsVar,
    concentracaoTop5,
    concentracaoTop10,
    pctImpactAlt,
    pctImpactInc,
    pctImpactExc,
    saldoFavoravel,
    saldoDesfavoravel,
    topProdutos: topProdutosWithShare,
    topPlanos: topPlanosWithShare,
    alertas,
    veredito,
    narrative,
    counts: {
      comDesvio: allItems.length,
      favoravel: favorableItems.length,
      desfavoravel: unfavorableItems.length,
      inclusoes: processedInc.length,
      exclusoes: processedExc.length,
      alteracoes: processedAltChanged.length,
      semMudanca: processedAltUnchanged.length,
      totalLinhas: rawInc.length + rawExc.length + rawAlt.length,
    },
  };
}

function applyMesesToVersaoData(data: any, filtros: any) {
  if (!data || !filtros?.filtroMesesAtivo) return data;
  const meses = (filtros.mesesSelecionados || []).map((m: string) => m.toLowerCase());
  const next: Record<string, number> = { total: 0 };
  for (const m of meses) {
    next[m] = Number(data[m] || 0);
    next.total += next[m];
  }
  if (data.numero_vendas) {
    const nq: Record<string, number> = { total: 0 };
    for (const m of meses) {
      nq[m] = Number(data.numero_vendas[m] || 0);
      nq.total += nq[m];
    }
    return { ...next, numero_vendas: nq };
  }
  return next;
}

function comparativoItemMatchesFilters(item: any, result: any, filtros: any) {
  const prodId = item.produto_id ?? item.versao_a?.produto_id;
  const planoRaw = item.plano_financeiro_id ?? item.versao_a?.plano_financeiro_id;
  const prodNome = String(result.produtos_map?.[prodId] || "");
  const planoNome = String(result.planos_map?.[planoRaw] || planoRaw || "");

  const baseInfo = (filtros?.centrosCustoBase || []).find((cc: any) => cc.db_id === prodId) || {};
  const idSienge = baseInfo.id ? String(baseInfo.id) : String(prodId);
  const produtoNome = parseCentroNome(prodNome).produto || "";
  const empresaId = String(baseInfo.id_empresa || "");

  if (filtros?.busca) {
    const q = filtros.busca.toLowerCase();
    if (!prodNome.toLowerCase().includes(q) && !planoNome.toLowerCase().includes(q)) return false;
  }
  if (filtros?.idCentroCusto?.length > 0 && !filtros.idCentroCusto.includes(idSienge)) return false;
  if (filtros?.produtoFiltro?.length > 0 && !filtros.produtoFiltro.includes(produtoNome)) return false;
  if (filtros?.planoFinanceiro?.length > 0 && !filtros.planoFinanceiro.includes(planoNome)) return false;
  if (filtros?.idEmpresa?.length > 0 && !filtros.idEmpresa.includes(empresaId)) return false;
  return true;
}

function normalizeComparativoItemForFiltros(item: any, filtros: any) {
  if (!filtros?.filtroMesesAtivo) return item;
  return {
    ...item,
    versao_a: applyMesesToVersaoData(item.versao_a, filtros),
    versao_b: applyMesesToVersaoData(item.versao_b, filtros),
  };
}

function filterComparativoResult(result: any, filtros: any) {
  const filterList = (list: any[]) =>
    (list || [])
      .filter((item) => comparativoItemMatchesFilters(item, result, filtros))
      .map((item) => normalizeComparativoItemForFiltros(item, filtros));

  return {
    ...result,
    inclusoes: filterList(result.inclusoes),
    exclusoes: filterList(result.exclusoes),
    alteracoes: filterList(result.alteracoes),
  };
}

type VendasComparativoCategoria = "todos" | "vendas" | "distratos" | "liquido";

function zeroComparativoVersaoVendas() {
  const z: Record<string, any> = { total: 0 };
  for (const m of MESES_STR) z[m] = 0;
  z.numero_vendas = { total: 0 };
  for (const m of MESES_STR) z.numero_vendas[m] = 0;
  return z;
}

function addComparativoVersaoSigned(target: any, source: any, sign: number) {
  if (!source) return target;
  for (const m of MESES_STR) {
    target[m] = (target[m] || 0) + Number(source[m] || 0) * sign;
  }
  target.total = (target.total || 0) + Number(source.total || 0) * sign;
  if (source.numero_vendas) {
    if (!target.numero_vendas) target.numero_vendas = { total: 0 };
    for (const m of [...MESES_STR, "total"]) {
      target.numero_vendas[m] = (target.numero_vendas[m] || 0) + Number(source.numero_vendas[m] || 0) * sign;
    }
  }
  return target;
}

function versaoVendasTemValor(versao: any) {
  if (!versao) return false;
  if (Math.abs(Number(versao.total || 0)) > 0) return true;
  if (versao.numero_vendas && Math.abs(Number(versao.numero_vendas.total || 0)) > 0) return true;
  return false;
}

function buildComparativoLiquidoResult(result: any) {
  const map = new Map<string, any>();
  for (const list of [result.inclusoes, result.alteracoes, result.exclusoes]) {
    for (const item of list || []) {
      const key = `${item.produto_id}-${item.plano_financeiro_id}`;
      if (!map.has(key)) {
        map.set(key, {
          produto_id: item.produto_id,
          plano_financeiro_id: item.plano_financeiro_id,
          is_distrato: false,
          versao_a: zeroComparativoVersaoVendas(),
          versao_b: zeroComparativoVersaoVendas(),
        });
      }
      const sign = item.is_distrato ? -1 : 1;
      const entry = map.get(key)!;
      addComparativoVersaoSigned(entry.versao_a, item.versao_a, sign);
      addComparativoVersaoSigned(entry.versao_b, item.versao_b, sign);
    }
  }
  const inclusoes: any[] = [];
  const exclusoes: any[] = [];
  const alteracoes: any[] = [];
  for (const item of map.values()) {
    const hasA = versaoVendasTemValor(item.versao_a);
    const hasB = versaoVendasTemValor(item.versao_b);
    if (hasA && !hasB) exclusoes.push(item);
    else if (hasB && !hasA) inclusoes.push(item);
    else alteracoes.push(item);
  }
  return { ...result, inclusoes, exclusoes, alteracoes };
}

function filterComparativoVendasCategoria(result: any, categoria: VendasComparativoCategoria) {
  if (!result || categoria === "todos") return result;
  if (categoria === "liquido") return buildComparativoLiquidoResult(result);
  const match = (item: any) => (categoria === "distratos" ? Boolean(item.is_distrato) : !item.is_distrato);
  const filterList = (list: any[]) => (list || []).filter(match);
  return {
    ...result,
    inclusoes: filterList(result.inclusoes),
    exclusoes: filterList(result.exclusoes),
    alteracoes: filterList(result.alteracoes),
  };
}

const COMPARATIVO_VENDAS_CATEGORIA_LABEL: Record<VendasComparativoCategoria, string> = {
  todos: "Todos",
  vendas: "Vendas",
  distratos: "Distratos",
  liquido: "VGV líquido",
};

function comparativoResultToFilterPayload(result: any) {
  const itens: any[] = [];
  const produtoIds = new Set<number>();
  const planoKeys = new Set<string | number>();

  for (const list of [result.inclusoes, result.exclusoes, result.alteracoes]) {
    for (const item of list || []) {
      const prodId = item.produto_id;
      const planoId = item.plano_financeiro_id;
      produtoIds.add(prodId);
      planoKeys.add(planoId);
      itens.push({ produto_id: prodId, plano_financeiro_id: planoId, plano_venda_id: planoId });
    }
  }

  return {
    itens,
    opcoes_produtos: Array.from(produtoIds).map((id) => ({
      id,
      nome: result.produtos_map?.[id] || String(id),
      id_sienge: id,
    })),
    opcoes_planos: Array.from(planoKeys).map((id) => ({
      id,
      nome: result.planos_map?.[id] || String(id),
    })),
  };
}

// ================================
// Badge de desvio
// ================================
function DesvBadge({ value, inverted = false }: { value: number, inverted?: boolean }) {
  if (value === 0) return <span className="text-slate-400 font-medium">-</span>;
  const isPositive = inverted ? value <= 0 : value > 0;
  return (
    <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold ${
      isPositive ? "text-emerald-700 bg-emerald-50" : "text-red-700 bg-red-50"
    }`}>
      {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {Math.abs(value * 100).toFixed(1)}%
    </div>
  );
}

// ================================
// Skeleton de carregamento
// ================================
function pickDefaultForecastId(res: any, current: number | ""): number | "" {
  const versoes = res?.versoes_disponiveis || [];
  if (current !== "" && versoes.some((v: any) => v.id === current)) return current;
  if (res?.active_forecast_id && versoes.some((v: any) => v.id === res.active_forecast_id)) {
    return res.active_forecast_id;
  }
  return versoes[0]?.id ?? "";
}

// ================================
// ABA: CONSOLIDADO — insights (orçado × realizado)
// ================================

type ConsolidadoInsightBloco = "resultado" | "receitas" | "despesas" | "vendas";
type ConsolidadoVendasCat = "liquido" | "vendas" | "distratos";

function getConsolidadoVisibleMeses(filtros: any) {
  return MESES.filter(
    (m) => !filtros?.filtroMesesAtivo || filtros.mesesSelecionados.includes(m),
  ).map((m) => m.toLowerCase());
}

function sumMesesVal(obj: Record<string, number> | undefined, meses: string[]) {
  if (!obj) return 0;
  return meses.reduce((s, m) => s + Number(obj[m] || 0), 0);
}

function isAcompFavoravel(varRs: number, inverted: boolean) {
  if (varRs === 0) return true;
  return inverted ? varRs < 0 : varRs > 0;
}

function summarizeAcompItens(itens: any[], ref: "orcado" | "forecast", meses: string[]) {
  const totais: Record<string, number> = { total: 0 };
  for (const m of meses) totais[m] = 0;
  for (const item of itens || []) {
    for (const m of meses) {
      totais[m] += Number(item[ref]?.[m] || 0);
    }
  }
  totais.total = meses.reduce((s, m) => s + totais[m], 0);
  return totais;
}

function summarizeAcompRealizado(itens: any[], meses: string[]) {
  const totais: Record<string, number> = { total: 0 };
  for (const m of meses) totais[m] = 0;
  for (const item of itens || []) {
    for (const m of meses) {
      totais[m] += Number(item.realizado?.[m] || 0);
    }
  }
  totais.total = meses.reduce((s, m) => s + totais[m], 0);
  return totais;
}

function buildAcompLinhaInsights(
  itens: any[],
  ref: "orcado" | "forecast",
  meses: string[],
  inverted: boolean,
  getLabel: (item: any) => string,
  getSublabel?: (item: any) => string,
) {
  return (itens || [])
    .map((item, i) => {
      const valRef = sumMesesVal(item[ref], meses);
      const valReal = sumMesesVal(item.realizado, meses);
      const varRs = valReal - valRef;
      const varPerc = valRef !== 0 ? varRs / Math.abs(valRef) : valReal !== 0 ? 1 : 0;
      return {
        key: `${i}-${item.produto_id}`,
        label: getLabel(item),
        sublabel: getSublabel?.(item),
        valRef,
        valReal,
        varRs,
        varPerc,
        absVarRs: Math.abs(varRs),
        favoravel: isAcompFavoravel(varRs, inverted),
        produto_id: item.produto_id,
        item,
      };
    })
    .filter((l) => l.absVarRs > 0.01)
    .sort((a, b) => b.absVarRs - a.absVarRs);
}

function getVendasSubcatVal(
  item: any,
  subcat: "vendas" | "distratos",
  tipo: "orcado" | "forecast" | "realizado",
  meses: string[],
  metric: VendasComparativoMetric,
) {
  let total = 0;
  for (const m of meses) {
    const cell = item[subcat]?.[tipo]?.[m];
    if (!cell) continue;
    total += metric === "unidades" ? Number(cell.unidades || 0) : Number(cell.vgv || 0);
  }
  return subcat === "distratos" && metric === "unidades" ? Math.abs(total) : total;
}

function getVendasCatVal(
  item: any,
  cat: ConsolidadoVendasCat,
  ref: "orcado" | "forecast",
  meses: string[],
  metric: VendasComparativoMetric,
) {
  if (cat === "vendas") return getVendasSubcatVal(item, "vendas", ref, meses, metric);
  if (cat === "distratos") return getVendasSubcatVal(item, "distratos", ref, meses, metric);
  return (
    getVendasSubcatVal(item, "vendas", ref, meses, metric) -
    getVendasSubcatVal(item, "distratos", ref, meses, metric)
  );
}

function getVendasCatReal(
  item: any,
  cat: ConsolidadoVendasCat,
  meses: string[],
  metric: VendasComparativoMetric,
) {
  if (cat === "vendas") return getVendasSubcatVal(item, "vendas", "realizado", meses, metric);
  if (cat === "distratos") return getVendasSubcatVal(item, "distratos", "realizado", meses, metric);
  return (
    getVendasSubcatVal(item, "vendas", "realizado", meses, metric) -
    getVendasSubcatVal(item, "distratos", "realizado", meses, metric)
  );
}

function buildVendasLinhaInsights(
  itens: any[],
  ref: "orcado" | "forecast",
  meses: string[],
  cat: ConsolidadoVendasCat,
  metric: VendasComparativoMetric,
  getLabel: (item: any) => string,
) {
  return (itens || [])
    .map((item, i) => {
      const valRef = getVendasCatVal(item, cat, ref, meses, metric);
      const valReal = getVendasCatReal(item, cat, meses, metric);
      const varRs = valReal - valRef;
      const varPerc = valRef !== 0 ? varRs / Math.abs(valRef) : valReal !== 0 ? 1 : 0;
      return {
        key: `v-${i}-${item.produto_id}`,
        label: getLabel(item),
        valRef,
        valReal,
        varRs,
        varPerc,
        absVarRs: Math.abs(varRs),
        favoravel: isVariacaoFavoravel(varRs, "VENDAS"),
        produto_id: item.produto_id,
        item,
      };
    })
    .filter((l) => l.absVarRs > (metric === "unidades" ? 0 : 0.01))
    .sort((a, b) => b.absVarRs - a.absVarRs);
}

function finalizeAcompBlockInsights(opts: {
  blockLabel: string;
  refTotal: number;
  realTotal: number;
  inverted: boolean;
  meses: string[];
  monthlyFn: (mes: string) => { ref: number; real: number };
  lines: ReturnType<typeof buildAcompLinhaInsights>;
  getProdLabel?: (id: number) => string;
}) {
  const { blockLabel, refTotal, realTotal, inverted, meses, monthlyFn, lines, getProdLabel } = opts;
  const globalVarRs = realTotal - refTotal;
  const globalVarPerc = refTotal !== 0 ? globalVarRs / Math.abs(refTotal) : 0;
  const favoravel = isAcompFavoravel(globalVarRs, inverted);
  const totalAbs = lines.reduce((s, l) => s + l.absVarRs, 0) || 1;
  const allItems = lines.map((l) => ({ ...l, shareAbs: l.absVarRs / totalAbs }));
  const topProdutos = aggregateComparativoByKey(
    allItems,
    (l) => l.produto_id,
    (id) => (getProdLabel ? getProdLabel(Number(id)) : String(id)),
  ).slice(0, 5);

  const desvioPorMes = meses.map((mes) => {
    const { ref, real } = monthlyFn(mes);
    const varRs = real - ref;
    const idx = MESES_STR.indexOf(mes);
    return {
      mes,
      label: MESES[idx] ?? mes,
      ref,
      real,
      varRs,
      favoravel: isAcompFavoravel(varRs, inverted),
    };
  });

  const alertas: { tone: "red" | "amber"; title: string; detail: string }[] = [];
  if (!favoravel && Math.abs(globalVarPerc) >= 0.05) {
    alertas.push({
      tone: "red",
      title: "Desvio material",
      detail: `${blockLabel}: referência ${formatMoeda(refTotal)} · realizado ${formatMoeda(realTotal)} (${(globalVarPerc * 100).toFixed(1)}%).`,
    });
  }
  if (allItems[0]?.shareAbs >= 0.25) {
    alertas.push({
      tone: "amber",
      title: "Concentração de desvio",
      detail: `${allItems[0].label} concentra ${(allItems[0].shareAbs * 100).toFixed(0)}% do desvio absoluto.`,
    });
  }

  const sinal = globalVarRs >= 0 ? "acima" : "abaixo";
  const narrative = favoravel
    ? `${blockLabel} ${sinal} da referência em ${formatMoeda(Math.abs(globalVarRs))} (${(Math.abs(globalVarPerc) * 100).toFixed(1)}%). ${allItems.length} linha(s) com desvio relevante.`
    : `${blockLabel} ${sinal} da referência em ${formatMoeda(Math.abs(globalVarRs))} (${(Math.abs(globalVarPerc) * 100).toFixed(1)}%). Revise os ${Math.min(5, allItems.length)} principais drivers.`;

  return {
    globalRef: refTotal,
    globalReal: realTotal,
    globalVarRs,
    globalVarPerc,
    favoravel,
    veredito: favoravel ? "favoravel" as const : globalVarRs === 0 ? "neutro" as const : "desfavoravel" as const,
    allItems,
    desvioPorMes,
    alertas,
    narrative,
    topProdutos,
    counts: {
      comDesvio: allItems.length,
      favoravel: allItems.filter((l) => l.favoravel && l.varRs !== 0).length,
      desfavoravel: allItems.filter((l) => !l.favoravel && l.varRs !== 0).length,
    },
  };
}

function buildConsolidadoInsightsBundle(opts: {
  ref: "orcado" | "forecast";
  meses: string[];
  receitas: any[];
  despesas: any[];
  vendas: any[];
  vendasCat: ConsolidadoVendasCat;
  vendasMetric: VendasComparativoMetric;
  getProdNome: (id: number) => string;
  getPlanoNome: (id: number) => string;
}) {
  const { ref, meses, receitas, despesas, vendas, vendasCat, vendasMetric, getProdNome, getPlanoNome } = opts;

  const totRecRef = summarizeAcompItens(receitas, ref, meses);
  const totRecReal = summarizeAcompRealizado(receitas, meses);
  const totDespRef = summarizeAcompItens(despesas, ref, meses);
  const totDespReal = summarizeAcompRealizado(despesas, meses);

  const refResultado = totRecRef.total - totDespRef.total;
  const realResultado = totRecReal.total - totDespReal.total;

  const recLines = buildAcompLinhaInsights(
    receitas,
    ref,
    meses,
    false,
    (i) => getProdNome(i.produto_id),
    (i) => getPlanoNome(i.plano_financeiro_id),
  );
  const despLines = buildAcompLinhaInsights(
    despesas,
    ref,
    meses,
    true,
    (i) => getProdNome(i.produto_id),
    (i) => getPlanoNome(i.plano_financeiro_id),
  );
  const vendasLines = buildVendasLinhaInsights(
    vendas,
    ref,
    meses,
    vendasCat,
    vendasMetric,
    (i) => getProdNome(i.produto_id),
  );

  const vendasRefTotal = vendas.reduce((s, i) => s + getVendasCatVal(i, vendasCat, ref, meses, vendasMetric), 0);
  const vendasRealTotal = vendas.reduce((s, i) => s + getVendasCatReal(i, vendasCat, meses, vendasMetric), 0);

  const resultado = finalizeAcompBlockInsights({
    blockLabel: "Resultado",
    refTotal: refResultado,
    realTotal: realResultado,
    inverted: false,
    meses,
    monthlyFn: (m) => ({
      ref: (totRecRef[m] || 0) - (totDespRef[m] || 0),
      real: (totRecReal[m] || 0) - (totDespReal[m] || 0),
    }),
    lines: [
      ...recLines.map((l) => ({ ...l, key: `r-${l.key}` })),
      ...despLines.map((l) => ({
        ...l,
        key: `d-${l.key}`,
        varRs: -l.varRs,
        favoravel: l.varRs <= 0,
      })),
    ].sort((a, b) => b.absVarRs - a.absVarRs),
    getProdLabel: getProdNome,
  });

  const receitasBlock = finalizeAcompBlockInsights({
    blockLabel: "Receitas",
    refTotal: totRecRef.total,
    realTotal: totRecReal.total,
    inverted: false,
    meses,
    monthlyFn: (m) => ({ ref: totRecRef[m] || 0, real: totRecReal[m] || 0 }),
    lines: recLines,
    getProdLabel: getProdNome,
  });

  const despesasBlock = finalizeAcompBlockInsights({
    blockLabel: "Despesas",
    refTotal: totDespRef.total,
    realTotal: totDespReal.total,
    inverted: true,
    meses,
    monthlyFn: (m) => ({ ref: totDespRef[m] || 0, real: totDespReal[m] || 0 }),
    lines: despLines,
    getProdLabel: getProdNome,
  });

  const vendasBlock = finalizeAcompBlockInsights({
    blockLabel: vendasCat === "liquido" ? "VGV líquido" : vendasCat === "distratos" ? "Distratos" : "Vendas",
    refTotal: vendasRefTotal,
    realTotal: vendasRealTotal,
    inverted: false,
    meses,
    monthlyFn: (m) => ({
      ref: vendas.reduce((s, i) => s + getVendasCatVal(i, vendasCat, ref, [m], vendasMetric), 0),
      real: vendas.reduce((s, i) => s + getVendasCatReal(i, vendasCat, [m], vendasMetric), 0),
    }),
    lines: vendasLines,
    getProdLabel: getProdNome,
  });

  const impactRec = totRecReal.total - totRecRef.total;
  const impactDesp = totDespReal.total - totDespRef.total;
  const absSum = Math.abs(impactRec) + Math.abs(impactDesp) || 1;

  return {
    resultado,
    receitas: receitasBlock,
    despesas: despesasBlock,
    vendas: vendasBlock,
    compositionResultado: {
      impactRec,
      impactDesp,
      pctRec: Math.abs(impactRec) / absSum,
      pctDesp: Math.abs(impactDesp) / absSum,
    },
  };
}

const CONSOLIDADO_BLOCO_LABEL: Record<ConsolidadoInsightBloco, string> = {
  resultado: "Resultado",
  receitas: "Receitas",
  despesas: "Despesas",
  vendas: "Vendas",
};

type ConsolidadoAnaliticaSecao = "receitas" | "despesas" | "vendas";

function calcConsolidadoDesvioPerc(realVal: number, refVal: number) {
  return (realVal - refVal) / (Math.abs(refVal) || 1);
}

function ConsolidadoAnaliticaCells({
  m,
  refVal,
  realVal,
  inverted = false,
  tone = "neutral",
  emphasis = "normal",
}: {
  m: string;
  refVal: number;
  realVal: number;
  inverted?: boolean;
  tone?: "emerald" | "red" | "amber" | "slate" | "neutral";
  emphasis?: "section" | "resultado" | "child" | "sub";
}) {
  const perc = calcConsolidadoDesvioPerc(realVal, refVal);
  const isTotal = m === "total";
  const refCls =
    tone === "emerald" ? "text-emerald-700/80" :
    tone === "red" ? "text-red-700/80" :
    tone === "amber" ? "text-amber-800/80" :
    emphasis === "child" || emphasis === "sub" ? "text-slate-500" : "text-slate-500";
  const realCls =
    emphasis === "resultado"
      ? `${realVal >= 0 ? "text-emerald-600" : "text-red-600"} font-bold text-base`
      : emphasis === "section"
        ? tone === "emerald" ? "font-semibold text-emerald-800 bg-emerald-100/20" :
          tone === "red" ? "font-semibold text-red-800 bg-red-100/20" :
          tone === "amber" ? "font-semibold text-amber-900 bg-amber-100/20" :
          "font-semibold text-slate-800"
        : emphasis === "sub"
          ? "text-slate-600 font-medium"
          : "text-slate-700 font-medium bg-slate-50/50 group-hover:bg-slate-100/50";
  const borderCls =
    tone === "emerald" ? "border-emerald-100/50" :
    tone === "red" ? "border-red-100/50" :
    tone === "amber" ? "border-amber-100/50" :
    emphasis === "resultado" ? "border-slate-300" : "border-slate-100";
  const py = emphasis === "resultado" ? "py-3" : emphasis === "sub" ? "py-1.5" : "py-2";
  return (
    <Fragment>
      <td className={`px-2.5 ${py} text-right tabular-nums text-xs ${refCls} ${isTotal ? "bg-slate-50/80" : ""}`}>
        {formatMoeda(refVal)}
      </td>
      <td className={`px-2.5 ${py} text-right tabular-nums text-xs ${realCls} ${isTotal ? "border-l border-slate-200 bg-slate-50/60" : ""}`}>
        {formatMoeda(realVal)}
      </td>
      <td className={`px-2.5 ${py} text-right border-r ${borderCls} ${isTotal ? "bg-slate-50/80" : ""}`}>
        <DesvBadge value={perc} inverted={inverted} />
      </td>
    </Fragment>
  );
}

// ================================
// ABA: CONSOLIDADO (DRE Style)
// ================================
function TabConsolidado({ ano, consolidado, deptId, filtros, holdingMldu, onDataLoaded }: { ano: number; consolidado: boolean; deptId: number; filtros: any; holdingMldu: boolean; onDataLoaded?: (data: any) => void }) {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [vendasData, setVendasData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [modo, setModo] = useState<"orcado" | "forecast">("orcado");
  const [visao, setVisao] = useState<"executiva" | "analitica">("executiva");
  const [insightBloco, setInsightBloco] = useState<ConsolidadoInsightBloco>("resultado");
  const [vendasCat, setVendasCat] = useState<ConsolidadoVendasCat>("liquido");
  const [vendasMetric, setVendasMetric] = useState<VendasComparativoMetric>("vgv");
  const [expandedSecs, setExpandedSecs] = useState<Record<ConsolidadoAnaliticaSecao, boolean>>({
    receitas: false,
    despesas: false,
    vendas: false,
  });
  const [expandCtrl, setExpandCtrl] = useState<"all" | "none" | null>(null);
  const [expandedVendasProd, setExpandedVendasProd] = useState<Record<number, boolean>>({});
  const analiticaAutoExpandRef = useRef(false);
  const [forecastId, setForecastId] = useState<number | "">("");
  const [buscaAnalitica, setBuscaAnalitica] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const onDataLoadedRef = useRef(onDataLoaded);
  onDataLoadedRef.current = onDataLoaded;
  const loadSeq = useRef(0);

  const load = useCallback(async (fid: number | "" = "") => {
    const seq = ++loadSeq.current;
    setLoading(true);
    setLoadError(null);
    try {
      const [cons, vendas] = await Promise.all([
        orcamentoService.getAcompanhamentoConsolidado(ano, deptId, consolidado, fid || undefined, holdingMldu),
        orcamentoService.getAcompanhamentoVendas(ano, deptId, consolidado, fid || undefined, holdingMldu),
      ]);
      if (seq !== loadSeq.current) return;
      setData(cons);
      setVendasData(vendas);
      onDataLoadedRef.current?.({
        ...cons,
        vendas_itens: vendas?.itens || [],
        opcoes_planos: [
          ...(cons.opcoes_planos || []),
          ...(vendas.opcoes_planos || []),
        ],
      });
      const nextForecastId = pickDefaultForecastId(cons, fid);
      if (nextForecastId !== fid) setForecastId(nextForecastId);
      else if (fid) setForecastId(fid);
    } catch (e) {
      if (seq !== loadSeq.current) return;
      console.error(e);
      setLoadError(acompRequestError(e));
    } finally {
      if (seq === loadSeq.current) setLoading(false);
    }
  }, [ano, consolidado, deptId, holdingMldu]);

  useEffect(() => {
    setForecastId("");
    load("");
  }, [load]);

  useEffect(() => {
    if (visao !== "analitica") {
      analiticaAutoExpandRef.current = false;
      return;
    }
    if (analiticaAutoExpandRef.current) return;
    analiticaAutoExpandRef.current = true;
    setExpandCtrl(null);
    if (insightBloco === "receitas") {
      setExpandedSecs((s) => ({ ...s, receitas: true }));
    } else if (insightBloco === "despesas") {
      setExpandedSecs((s) => ({ ...s, despesas: true }));
    } else if (insightBloco === "vendas") {
      setExpandedSecs((s) => ({ ...s, vendas: true }));
    } else if (insightBloco === "resultado") {
      setExpandedSecs((s) => ({ ...s, receitas: true, despesas: true }));
    }
  }, [visao, insightBloco]);

  const visibleMesesStr = useMemo(() => getConsolidadoVisibleMeses(filtros), [filtros]);
  const visibleMeses = useMemo(
    () => visibleMesesStr.map((m) => MESES[MESES_STR.indexOf(m)] ?? m),
    [visibleMesesStr],
  );
  const ref = modo === "orcado" ? "orcado" : "forecast";

  const { filteredReceitas, filteredDespesas, filteredVendas, getProdNome, getPlanoNome } = useMemo(() => {
    if (!data) {
      return {
        filteredReceitas: [] as any[],
        filteredDespesas: [] as any[],
        filteredVendas: [] as any[],
        getProdNome: (id: number) => String(id),
        getPlanoNome: (id: number) => String(id),
      };
    }
    const baseCC: any[] = filtros?.centrosCustoBase || [];
    const produtosMap = data.opcoes_produtos || [];
    const planosMap = data.opcoes_planos || [];
    const vendasProdutos = vendasData?.opcoes_produtos || produtosMap;

    const getProdNomeInner = (id: number) =>
      produtosMap.find((p: any) => p.id === id)?.nome ||
      vendasProdutos.find((p: any) => p.id === id)?.nome ||
      `Produto ${id}`;
    const getPlanoNomeInner = (id: number) =>
      planosMap.find((p: any) => p.id === id)?.nome || String(id);

    const matchItem = (item: any, planoField?: number) => {
      const prodInfo = produtosMap.find((p: any) => p.id === item.produto_id) || {};
      const planoInfo = planosMap.find((p: any) => p.id === (planoField ?? item.plano_financeiro_id)) || {};
      const baseInfo = baseCC.find((cc: any) => cc.db_id === item.produto_id) || {};
      const idSienge = baseInfo.id ? String(baseInfo.id) : String(prodInfo.id_sienge || prodInfo.id || "");
      const prodName = prodInfo.nome || baseInfo.nome || getProdNomeInner(item.produto_id);
      if (filtros?.busca && !prodName.toLowerCase().includes(filtros.busca.toLowerCase())) return false;
      if (filtros?.idCentroCusto?.length > 0 && !filtros.idCentroCusto.includes(idSienge)) return false;
      if (filtros?.produtoFiltro?.length > 0 && !filtros.produtoFiltro.includes(parseCentroNome(prodInfo.nome || "").produto)) return false;
      if (filtros?.planoFinanceiro?.length > 0 && !filtros.planoFinanceiro.includes(planoInfo.nome || "")) return false;
      if (filtros?.idEmpresa?.length > 0 && !filtros.idEmpresa.includes(String(baseInfo.id_empresa || prodInfo.id_empresa || ""))) return false;
      return true;
    };

    return {
      filteredReceitas: (data.receitas || []).filter((i: any) => matchItem(i)),
      filteredDespesas: (data.despesas || []).filter((i: any) => matchItem(i)),
      filteredVendas: (vendasData?.itens || []).filter((i: any) => matchItem(i)),
      getProdNome: getProdNomeInner,
      getPlanoNome: getPlanoNomeInner,
    };
  }, [data, vendasData, filtros]);

  const insightsBundle = useMemo(() => {
    if (!data) return null;
    return buildConsolidadoInsightsBundle({
      ref,
      meses: visibleMesesStr,
      receitas: filteredReceitas,
      despesas: filteredDespesas,
      vendas: filteredVendas,
      vendasCat,
      vendasMetric,
      getProdNome,
      getPlanoNome,
    });
  }, [data, ref, visibleMesesStr, filteredReceitas, filteredDespesas, filteredVendas, vendasCat, vendasMetric, getProdNome, getPlanoNome]);

  const isSectionOpen = useCallback(
    (sec: ConsolidadoAnaliticaSecao) => {
      if (expandCtrl === "all") return true;
      if (expandCtrl === "none") return false;
      return expandedSecs[sec];
    },
    [expandCtrl, expandedSecs],
  );

  const toggleSecao = (sec: ConsolidadoAnaliticaSecao) => {
    setExpandCtrl(null);
    setExpandedSecs((s) => {
      const currentlyOpen =
        expandCtrl === "all" ? true : expandCtrl === "none" ? false : s[sec];
      return { ...s, [sec]: !currentlyOpen };
    });
  };

  const expandAllSecoes = () => {
    setExpandCtrl("all");
    setExpandedSecs({ receitas: true, despesas: true, vendas: true });
    startTransition(() => {
      const prodMap: Record<number, boolean> = {};
      filteredVendas.forEach((item: any) => {
        prodMap[item.produto_id] = true;
      });
      setExpandedVendasProd(prodMap);
    });
  };

  const collapseAllSecoes = () => {
    setExpandCtrl("none");
    setExpandedSecs({ receitas: false, despesas: false, vendas: false });
    setExpandedVendasProd({});
  };

  const scrollToSecao = (sec: ConsolidadoAnaliticaSecao | "resultado") => {
    if (sec !== "resultado") {
      setExpandCtrl(null);
      setExpandedSecs((s) => ({ ...s, [sec]: true }));
    }
    document.getElementById(`consolidado-sec-${sec}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };

  const activeInsights = insightsBundle
    ? insightBloco === "resultado"
      ? insightsBundle.resultado
      : insightBloco === "receitas"
        ? insightsBundle.receitas
        : insightBloco === "despesas"
          ? insightsBundle.despesas
          : insightsBundle.vendas
    : null;

  const summarize = (itens: any[], tipo: "orcado" | "forecast" | "realizado") => {
    const totais: Record<string, number> = {};
    MESES_STR.forEach((m) => { totais[m] = 0; });
    totais.total = 0;
    for (const item of itens || []) {
      MESES_STR.forEach((m) => { totais[m] += item[tipo]?.[m] || 0; });
      totais.total += item[tipo]?.total || 0;
    }
    return totais;
  };

  if (loading && !data) return <BudgetLoadingState />;
  if (loadError && !data) return <BudgetLoadError message={loadError} onRetry={() => load(forecastId)} />;
  if (!data || !insightsBundle || !activeInsights) return null;

  const totRecOrc = summarize(filteredReceitas, "orcado");
  const totRecFc = summarize(filteredReceitas, "forecast");
  const totRecReal = summarize(filteredReceitas, "realizado");
  const totDespOrc = summarize(filteredDespesas, "orcado");
  const totDespFc = summarize(filteredDespesas, "forecast");
  const totDespReal = summarize(filteredDespesas, "realizado");
  const totRecRef = modo === "orcado" ? totRecOrc : totRecFc;
  const totDespRef = modo === "orcado" ? totDespOrc : totDespFc;

  const resultado: any = {
    orcado: { total: totRecOrc.total - totDespOrc.total },
    forecast: { total: totRecFc.total - totDespFc.total },
    realizado: { total: totRecReal.total - totDespReal.total },
  };
  MESES_STR.forEach((m) => {
    resultado.orcado[m] = (totRecOrc[m] || 0) - (totDespOrc[m] || 0);
    resultado.forecast[m] = (totRecFc[m] || 0) - (totDespFc[m] || 0);
    resultado.realizado[m] = (totRecReal[m] || 0) - (totDespReal[m] || 0);
  });

  const visibleMonthsIdx = MESES_STR.map((m, i) => i).filter((i) => !filtros?.filtroMesesAtivo || filtros?.mesesSelecionados?.includes(MESES[i]));
  const months = [...visibleMesesStr, "total"];

  const matchBuscaAnalitica = (produtoId: number) =>
    !buscaAnalitica.trim() || getProdNome(produtoId).toLowerCase().includes(buscaAnalitica.toLowerCase());
  const receitasVisiveis = filteredReceitas.filter((i: any) => matchBuscaAnalitica(i.produto_id));
  const despesasVisiveis = filteredDespesas.filter((i: any) => matchBuscaAnalitica(i.produto_id));
  const vendasVisiveis = filteredVendas.filter((i: any) => matchBuscaAnalitica(i.produto_id));

  const refLabel = modo === "orcado" ? "Orçado" : "Forecast";
  const invertedBlock = insightBloco === "despesas";
  const linkMeses = mesesFiltroToStr(filtros?.mesesSelecionados, filtros?.filtroMesesAtivo);
  const despesasLinkBase: OrcamentoLinkParams = {
    ano,
    modo,
    meses: linkMeses,
  };
  const irParaAnaliticoDespesa = (opts?: { produto?: number; plano?: number; expand?: boolean }) => {
    router.push(buildOrcamentoHref("analitico1", {
      ...despesasLinkBase,
      produto: opts?.produto,
      plano: opts?.plano,
      expand: opts?.expand,
    }));
  };
  const fmtInsight = (v: number) => {
    if (insightBloco === "vendas") {
      const val = vendasCat === "distratos" ? Math.abs(v) : v;
      return formatComparativoValor(val, vendasMetric, "VENDAS");
    }
    return formatMoeda(v);
  };
  const rowVarClass = (varRs: number) => {
    if (varRs === 0) return "text-slate-600";
    const fav = invertedBlock ? varRs < 0 : varRs > 0;
    return fav ? "text-emerald-700" : "text-red-700";
  };
  const variacaoFavoravel = activeInsights.favoravel;
  const tone = variationTone(variacaoFavoravel, activeInsights.globalVarRs, activeInsights.globalVarPerc);

  const filteredDrivers = activeInsights.allItems.filter((item) => {
    if (!buscaAnalitica.trim()) return true;
    const q = buscaAnalitica.trim().toLowerCase();
    return item.label.toLowerCase().includes(q) || (item.sublabel || "").toLowerCase().includes(q);
  });

  const exportConsolidado = () => {
    const headers = ["Bloco", "Produto", "Plano", `${refLabel}`, "Realizado", "Variação", "Var. %"];
    const rows: (string | number)[][] = [];
    const pushBlock = (label: string, items: any[]) => {
      for (const item of items) {
        rows.push([
          label,
          item.label,
          item.sublabel || "",
          item.valRef,
          item.valReal,
          item.varRs,
          item.varPerc,
        ]);
      }
    };
    pushBlock("Receitas", insightsBundle.receitas.allItems);
    pushBlock("Despesas", insightsBundle.despesas.allItems);
    pushBlock("Vendas", insightsBundle.vendas.allItems);
    exportDataToExcel(headers, rows, `consolidado_${ano}_${modo}.xlsx`);
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden gap-2">
      {loading ? <BudgetRefreshingBanner /> : null}
      <div className="flex items-center gap-2 shrink-0 flex-wrap">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Comparar com</span>
        <div className="flex rounded-lg overflow-hidden border border-slate-200">
          {(["orcado", "forecast"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setModo(m)}
              className={`px-3 py-1 text-xs font-semibold transition-colors ${modo === m ? "bg-ml-green text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
            >
              {m === "orcado" ? "Orçado" : "Forecast"}
            </button>
          ))}
        </div>
        {modo === "forecast" && data?.versoes_disponiveis?.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Versão</span>
            <select
              value={forecastId}
              onChange={(e) => {
                const next = e.target.value ? Number(e.target.value) : "";
                setForecastId(next);
                load(next);
              }}
              className="text-xs border border-slate-200 rounded-lg px-2 py-1 bg-white text-slate-700"
            >
              {data.versoes_disponiveis.map((v: any) => (
                <option key={v.id} value={v.id}>{v.descricao}</option>
              ))}
            </select>
          </div>
        )}
        <div className="flex items-center gap-1 ml-auto">
          <button
            type="button"
            onClick={() => setVisao("executiva")}
            className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold transition-colors ${
              visao === "executiva" ? "bg-white text-slate-800 shadow-sm border border-slate-200" : "text-slate-500 hover:bg-white border border-transparent"
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            Executiva
          </button>
          <button
            type="button"
            onClick={() => setVisao("analitica")}
            className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold transition-colors ${
              visao === "analitica" ? "bg-white text-slate-800 shadow-sm border border-slate-200" : "text-slate-500 hover:bg-white border border-transparent"
            }`}
          >
            <Table2 className="w-3.5 h-3.5" />
            Analítica
          </button>
          <button type="button" onClick={() => load(forecastId)} className="p-1.5 text-slate-500 hover:text-ml-green transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {visao === "executiva" ? (
        <div className="flex-1 min-h-0 flex flex-col gap-2 overflow-hidden">
          <div className="shrink-0 rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] divide-y md:divide-y-0 md:divide-x divide-slate-100">
              <div className="px-3 py-2.5">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5">{refLabel}</p>
                <p className="text-lg font-bold text-slate-900 tabular-nums">{fmtInsight(activeInsights.globalRef)}</p>
                <p className="text-[11px] text-slate-500">{CONSOLIDADO_BLOCO_LABEL[insightBloco]}</p>
              </div>
              <div className={`px-4 py-2.5 flex flex-col items-center justify-center text-center min-w-[160px] ${tone.panel}`}>
                <p className="text-[10px] font-semibold uppercase tracking-wider opacity-70 mb-0.5">Variação</p>
                <p className={`text-lg font-bold tabular-nums ${tone.value}`}>
                  {activeInsights.globalVarRs > 0 ? "+" : ""}{fmtInsight(activeInsights.globalVarRs)}
                </p>
                <p className={`text-[11px] font-semibold tabular-nums ${tone.muted}`}>
                  {(activeInsights.globalVarPerc * 100).toFixed(1)}%
                </p>
              </div>
              <div className="px-3 py-2.5 md:text-right">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5">Realizado</p>
                <p className="text-lg font-bold text-slate-900 tabular-nums">{fmtInsight(activeInsights.globalReal)}</p>
                {filtros?.filtroMesesAtivo && visibleMeses.length > 0 && (
                  <p className="text-[11px] text-slate-400">Período: {visibleMeses.join(", ")}</p>
                )}
              </div>
            </div>
            <div className="px-3 py-1.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 bg-slate-50/50">
              <div className="flex flex-wrap gap-1">
                {(["resultado", "receitas", "despesas", "vendas"] as const).map((b) => (
                  <button
                    key={b}
                    type="button"
                    onClick={() => setInsightBloco(b)}
                    className={`px-2 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                      insightBloco === b ? "bg-white text-slate-800 shadow-sm border border-slate-200" : "text-slate-500 hover:bg-white"
                    }`}
                  >
                    {CONSOLIDADO_BLOCO_LABEL[b]}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap items-center gap-1">
                {insightBloco === "vendas" && (
                  <>
                    <div className="flex items-center gap-1 border-r border-slate-200 pr-2 mr-1">
                      {(["liquido", "vendas", "distratos"] as const).map((c) => (
                        <button
                          key={c}
                          type="button"
                          onClick={() => setVendasCat(c)}
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${vendasCat === c ? "bg-white border border-slate-200 text-slate-800" : "text-slate-500"}`}
                        >
                          {c === "liquido" ? "Líquido" : c === "vendas" ? "Vendas" : "Distratos"}
                        </button>
                      ))}
                    </div>
                    <div className="flex items-center gap-1">
                      <button type="button" onClick={() => setVendasMetric("vgv")} className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${vendasMetric === "vgv" ? "bg-white border border-slate-200" : "text-slate-500"}`}>VGV</button>
                      <button type="button" onClick={() => setVendasMetric("unidades")} className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${vendasMetric === "unidades" ? "bg-white border border-slate-200" : "text-slate-500"}`}>Nº lotes</button>
                    </div>
                  </>
                )}
                <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${tone.badge}`}>
                  <SemaforoDesvio
                    n={activeInsights.globalTotalB}
                    ref={activeInsights.globalTotalA}
                    tipo={tipoSemaforo(
                      insightBloco === "despesas"
                        ? "DESPESAS"
                        : insightBloco === "receitas"
                          ? "RECEITAS"
                          : insightBloco === "vendas"
                            ? "VENDAS"
                            : "RESULTADO",
                    )}
                  />
                  {activeInsights.veredito === "favoravel" ? "Favorável" : activeInsights.veredito === "desfavoravel" ? "Requer atenção" : "Neutro"}
                </span>
              </div>
            </div>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto budget-matrix-scroll flex flex-col gap-1.5 pb-1">
            <div className="grid grid-cols-1 xl:grid-cols-[1.3fr_0.9fr] gap-1.5 shrink-0">
              <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Leitura executiva</p>
                <p className="text-xs text-slate-700 leading-relaxed">{activeInsights.narrative}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  {insightBloco === "resultado" ? "Composição do desvio (resultado)" : "Referência × realizado"}
                </p>
                {insightBloco === "resultado" ? (
                  <div className="space-y-1.5">
                    {[
                      { label: "Receitas", value: insightsBundle.compositionResultado.impactRec, pct: insightsBundle.compositionResultado.pctRec, color: "bg-emerald-500" },
                      { label: "Despesas", value: -insightsBundle.compositionResultado.impactDesp, pct: insightsBundle.compositionResultado.pctDesp, color: "bg-red-500" },
                    ].map((row) => (
                      <div key={row.label}>
                        <div className="flex justify-between text-[11px] mb-0.5">
                          <span className="text-slate-600">{row.label} · {(row.pct * 100).toFixed(0)}%</span>
                          <span className={`font-semibold tabular-nums ${rowVarClass(row.value)}`}>{row.value > 0 ? "+" : ""}{formatMoeda(row.value)}</span>
                        </div>
                        <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${row.color}`} style={{ width: `${Math.min(100, row.pct * 100)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-slate-600 space-y-1">
                    <p>{refLabel}: <span className="font-semibold tabular-nums">{fmtInsight(activeInsights.globalRef)}</span></p>
                    <p>Realizado: <span className="font-semibold tabular-nums">{fmtInsight(activeInsights.globalReal)}</span></p>
                    <p>{activeInsights.counts.comDesvio} linha(s) com desvio · {activeInsights.counts.favoravel} favoráveis · {activeInsights.counts.desfavoravel} desfavoráveis</p>
                  </div>
                )}
              </div>
            </div>

            {activeInsights.desvioPorMes.length > 0 && (
              <ComparativoDesvioMensalStrip
                meses={activeInsights.desvioPorMes}
                formatVal={fmtInsight}
                refLabel={refLabel}
                realLabel="Realizado"
                onMesClick={() => setVisao("analitica")}
              />
            )}

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-1.5 shrink-0">
              <div className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 shadow-sm">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Target className="w-3.5 h-3.5 text-slate-500" />
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Pontos de atenção</p>
                </div>
                {activeInsights.alertas.length > 0 ? (
                  <div className="space-y-1">
                    {activeInsights.alertas.slice(0, 3).map((a, i) => (
                      <div key={i} className={`rounded-md border px-2 py-1 text-[11px] ${a.tone === "red" ? "border-red-200 bg-red-50/60 text-red-900" : "border-amber-200 bg-amber-50/60 text-amber-900"}`}>
                        <p className="font-semibold text-[10px] uppercase">{a.title}</p>
                        <p className="mt-0.5 opacity-90 line-clamp-2">{a.detail}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">Nenhum alerta crítico.</p>
                )}
              </div>
              <div className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 shadow-sm xl:col-span-2">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5">
                    <TrendingUp className="w-3.5 h-3.5 text-slate-500" />
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Top drivers</p>
                  </div>
                  <button type="button" onClick={() => insightBloco === "despesas" ? irParaAnaliticoDespesa() : setVisao("analitica")} className="text-[10px] font-semibold text-ml-green hover:underline">Ver analítica →</button>
                </div>
                <div className="space-y-1">
                  {activeInsights.allItems.slice(0, 5).map((item) => (
                    <ComparativoDriverBar
                      key={item.key}
                      compact
                      label={item.sublabel ? `${item.label} · ${item.sublabel}` : item.label}
                      varRs={item.varRs}
                      shareAbs={item.shareAbs || 0}
                      favoravel={item.favoravel}
                      formatVal={fmtInsight}
                      onClick={() => {
                        if (insightBloco === "despesas") {
                          const planoId = item.item?.plano_financeiro_id;
                          irParaAnaliticoDespesa({
                            produto: item.produto_id,
                            plano: planoId,
                            expand: Boolean(planoId),
                          });
                        } else {
                          setVisao("analitica");
                          setBuscaAnalitica(item.label.slice(0, 24));
                        }
                      }}
                    />
                  ))}
                </div>
                {insightBloco === "despesas" && (
                  <div className="mt-1 pt-1.5 border-t border-slate-100">
                    <OrcamentoDeepLinks params={despesasLinkBase} variant="menu" />
                  </div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 xl:grid-cols-4 gap-1.5 shrink-0">
              {[
                { label: "Resultado", block: insightsBundle.resultado, key: "resultado" as const },
                { label: "Receitas", block: insightsBundle.receitas, key: "receitas" as const },
                { label: "Despesas", block: insightsBundle.despesas, key: "despesas" as const },
                { label: "VGV líq.", block: insightsBundle.vendas, key: "vendas" as const },
              ].map((card) => (
                <button
                  key={card.key}
                  type="button"
                  onClick={() => setInsightBloco(card.key)}
                  className={`text-left rounded-lg border px-2.5 py-2 transition-colors ${insightBloco === card.key ? "border-ml-green bg-brand-green/5" : "border-slate-200 bg-white hover:border-slate-300"}`}
                >
                  <p className="text-[10px] font-semibold uppercase text-slate-500">{card.label}</p>
                  <p className={`text-sm font-bold tabular-nums mt-0.5 ${card.block.favoravel ? "text-emerald-700" : "text-red-700"}`}>
                    {card.block.globalVarRs > 0 ? "+" : ""}{card.key === "vendas" ? formatComparativoValor(card.block.globalVarRs, vendasMetric, "VENDAS") : formatMoeda(card.block.globalVarRs)}
                  </p>
                  <p className="text-[10px] text-slate-400">{(card.block.globalVarPerc * 100).toFixed(1)}% vs {refLabel.toLowerCase()}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 min-h-0 flex flex-col gap-2 overflow-hidden">
          <div className="shrink-0 flex flex-wrap items-center gap-2 px-1">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="search"
                value={buscaAnalitica}
                onChange={(e) => setBuscaAnalitica(e.target.value)}
                placeholder="Buscar produto…"
                className="pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg bg-white w-[200px]"
              />
            </div>
            <div className="flex flex-wrap items-center gap-1">
              {([
                { id: "receitas" as const, label: "Receitas", cls: "text-emerald-700 border-emerald-200 hover:bg-emerald-50" },
                { id: "despesas" as const, label: "Despesas", cls: "text-red-700 border-red-200 hover:bg-red-50" },
                { id: "resultado" as const, label: "Resultado", cls: "text-slate-700 border-slate-200 hover:bg-slate-50" },
                { id: "vendas" as const, label: "Vendas", cls: "text-amber-800 border-amber-200 hover:bg-amber-50" },
              ]).map((chip) => (
                <button
                  key={chip.id}
                  type="button"
                  onClick={() => scrollToSecao(chip.id)}
                  className={`px-2 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wide border transition-colors ${chip.cls}`}
                >
                  {chip.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1 border-l border-slate-200 pl-2">
              <button type="button" onClick={expandAllSecoes} className="px-2 py-1 text-[10px] font-semibold text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50">
                Expandir tudo
              </button>
              <button type="button" onClick={collapseAllSecoes} className="px-2 py-1 text-[10px] font-semibold text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50">
                Recolher
              </button>
            </div>
            <button type="button" onClick={exportConsolidado} className="ml-auto flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold border border-slate-200 rounded-lg hover:bg-slate-50">
              <Download className="w-3.5 h-3.5" /> Excel
            </button>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto overflow-x-auto border border-slate-200 rounded-xl budget-matrix-scroll bg-white shadow-sm">
            <table className="w-full text-left border-collapse min-w-max">
              <thead className="text-[10px] text-slate-600 uppercase bg-slate-100/95 sticky top-0 z-30 backdrop-blur-sm shadow-[0_1px_0_0_#e2e8f0]">
                <tr>
                  <th rowSpan={2} className="px-3 py-2.5 min-w-[220px] max-w-[280px] bg-slate-100 z-20 sticky left-0 shadow-[1px_0_0_0_#e2e8f0] align-bottom border-r border-slate-200 font-semibold">
                    Categoria / Produto
                  </th>
                  {visibleMeses.map((m) => (
                    <th key={m} colSpan={3} className="px-2 py-2 text-center border-r border-slate-200 bg-slate-100 min-w-[168px] font-semibold tracking-wide">
                      {m}
                    </th>
                  ))}
                  <th colSpan={3} className="px-2 py-2 text-center bg-slate-200/80 min-w-[168px] font-bold tracking-wide">
                    Total
                  </th>
                </tr>
                <tr>
                  {months.map((m) => (
                    <Fragment key={`sub-${m}`}>
                      <th className="px-2 py-1.5 text-right bg-slate-50/90 font-medium text-slate-500">{modo === "orcado" ? "Orç." : "Fcst."}</th>
                      <th className="px-2 py-1.5 text-right bg-slate-100 font-medium text-slate-600">Real</th>
                      <th className={`px-2 py-1.5 text-right font-medium text-slate-500 border-r border-slate-200 ${m === "total" ? "bg-slate-200/60" : "bg-slate-50/90"}`}>%</th>
                    </Fragment>
                  ))}
                </tr>
              </thead>
              <tbody>
                {/* Receitas */}
                <tr id="consolidado-sec-receitas" className="border-b border-emerald-200/80 bg-emerald-50/40">
                  <td className="px-3 py-2.5 font-bold text-emerald-900 sticky left-0 bg-emerald-50/95 shadow-[1px_0_0_0_#d1fae5] z-10 border-r border-emerald-100">
                    <button type="button" className="flex items-center gap-2 w-full text-left group/sec" onClick={() => toggleSecao("receitas")}>
                      <span className="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-100 text-emerald-700 group-hover/sec:bg-emerald-200/80 transition-colors">
                        {isSectionOpen("receitas") ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </span>
                      <TrendingUp className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span className="tracking-wide">Receitas</span>
                      <span className="ml-auto text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                        {receitasVisiveis.length} prod.
                      </span>
                    </button>
                  </td>
                  {months.map((m) => (
                    <ConsolidadoAnaliticaCells
                      key={`rec-sec-${m}`}
                      m={m}
                      refVal={totRecRef[m] || 0}
                      realVal={totRecReal[m] || 0}
                      tone="emerald"
                      emphasis="section"
                    />
                  ))}
                </tr>
                {isSectionOpen("receitas") && receitasVisiveis.map((item: any, idx: number) => (
                  <tr key={`rec-item-${item.produto_id}-${idx}`} className={`group border-b border-slate-100 ${idx % 2 === 0 ? "bg-white" : "bg-slate-50/40"}`}>
                    <td className="px-3 py-2 sticky left-0 bg-inherit shadow-[1px_0_0_0_#e2e8f0] z-10 border-r border-slate-100 group-hover:bg-slate-50/80">
                      <div className="flex items-center gap-2 pl-8">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0" />
                        <span className="text-xs font-medium text-slate-700 truncate max-w-[240px]" title={getProdNome(item.produto_id)}>
                          {getProdNome(item.produto_id)}
                        </span>
                      </div>
                    </td>
                    {months.map((m) => (
                      <ConsolidadoAnaliticaCells
                        key={`rec-item-${item.produto_id}-${m}`}
                        m={m}
                        refVal={item[ref]?.[m] || 0}
                        realVal={item.realizado?.[m] || 0}
                        emphasis="child"
                      />
                    ))}
                  </tr>
                ))}
                {isSectionOpen("receitas") && receitasVisiveis.length === 0 && (
                  <tr className="border-b border-slate-100 bg-white">
                    <td colSpan={1 + months.length * 3} className="px-3 py-3 text-xs text-slate-400 italic pl-12">
                      Nenhum produto encontrado para receitas.
                    </td>
                  </tr>
                )}

                {/* Despesas */}
                <tr id="consolidado-sec-despesas" className="border-b border-red-200/80 bg-red-50/40">
                  <td className="px-3 py-2.5 font-bold text-red-900 sticky left-0 bg-red-50/95 shadow-[1px_0_0_0_#fee2e2] z-10 border-r border-red-100">
                    <button type="button" className="flex items-center gap-2 w-full text-left group/sec" onClick={() => toggleSecao("despesas")}>
                      <span className="flex h-6 w-6 items-center justify-center rounded-md bg-red-100 text-red-700 group-hover/sec:bg-red-200/80 transition-colors">
                        {isSectionOpen("despesas") ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </span>
                      <TrendingDown className="w-4 h-4 text-red-600 shrink-0" />
                      <span className="tracking-wide">Despesas</span>
                      <span className="ml-auto text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-full bg-red-100 text-red-800">
                        {despesasVisiveis.length} prod.
                      </span>
                    </button>
                  </td>
                  {months.map((m) => (
                    <ConsolidadoAnaliticaCells
                      key={`desp-sec-${m}`}
                      m={m}
                      refVal={totDespRef[m] || 0}
                      realVal={totDespReal[m] || 0}
                      inverted
                      tone="red"
                      emphasis="section"
                    />
                  ))}
                </tr>
                {isSectionOpen("despesas") && despesasVisiveis.map((item: any, idx: number) => (
                  <tr key={`desp-item-${item.produto_id}-${idx}`} className={`group border-b border-slate-100 ${idx % 2 === 0 ? "bg-white" : "bg-slate-50/40"}`}>
                    <td className="px-3 py-2 sticky left-0 bg-inherit shadow-[1px_0_0_0_#e2e8f0] z-10 border-r border-slate-100 group-hover:bg-slate-50/80">
                      <div className="flex items-center gap-2 pl-8">
                        <span className="h-1.5 w-1.5 rounded-full bg-red-400 shrink-0" />
                        <span className="text-xs font-medium text-slate-700 truncate max-w-[240px]" title={getProdNome(item.produto_id)}>
                          {getProdNome(item.produto_id)}
                        </span>
                      </div>
                    </td>
                    {months.map((m) => (
                      <ConsolidadoAnaliticaCells
                        key={`desp-item-${item.produto_id}-${m}`}
                        m={m}
                        refVal={item[ref]?.[m] || 0}
                        realVal={item.realizado?.[m] || 0}
                        inverted
                        emphasis="child"
                      />
                    ))}
                  </tr>
                ))}
                {isSectionOpen("despesas") && despesasVisiveis.length === 0 && (
                  <tr className="border-b border-slate-100 bg-white">
                    <td colSpan={1 + months.length * 3} className="px-3 py-3 text-xs text-slate-400 italic pl-12">
                      Nenhum produto encontrado para despesas.
                    </td>
                  </tr>
                )}

                {/* Resultado */}
                <tr id="consolidado-sec-resultado" className="border-y-2 border-slate-300 bg-gradient-to-r from-slate-100/90 to-slate-50">
                  <td className="px-3 py-3 font-bold text-slate-800 sticky left-0 bg-slate-100 shadow-[1px_0_0_0_#cbd5e1] z-10 border-r border-slate-300">
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-4 h-4 text-brand-green shrink-0" />
                      <span className="tracking-wide">Resultado</span>
                      <span className="text-[10px] font-normal text-slate-500 normal-case">(Receitas − Despesas)</span>
                    </div>
                  </td>
                  {months.map((m) => (
                    <ConsolidadoAnaliticaCells
                      key={`res-${m}`}
                      m={m}
                      refVal={resultado?.[ref]?.[m] || 0}
                      realVal={resultado?.realizado?.[m] || 0}
                      tone="slate"
                      emphasis="resultado"
                    />
                  ))}
                </tr>

                {/* Vendas */}
                <tr id="consolidado-sec-vendas" className="border-b border-amber-200/80 bg-amber-50/40">
                  <td className="px-3 py-2.5 font-bold text-amber-950 sticky left-0 bg-amber-50/95 shadow-[1px_0_0_0_#fef3c7] z-10 border-r border-amber-100">
                    <button type="button" className="flex items-center gap-2 w-full text-left group/sec" onClick={() => toggleSecao("vendas")}>
                      <span className="flex h-6 w-6 items-center justify-center rounded-md bg-amber-100 text-amber-800 group-hover/sec:bg-amber-200/80 transition-colors">
                        {isSectionOpen("vendas") ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </span>
                      <LineChart className="w-4 h-4 text-amber-700 shrink-0" />
                      <span className="tracking-wide">Vendas</span>
                      <span className="text-[10px] font-normal normal-case text-amber-800/80">(VGV líq.)</span>
                      <span className="ml-auto text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-900">
                        {vendasVisiveis.length} prod.
                      </span>
                    </button>
                  </td>
                  {months.map((m) => {
                    const mesesCalc = m === "total" ? visibleMesesStr : [m];
                    const sumCat = (cat: "vendas" | "distratos", tipo: "orcado" | "forecast" | "realizado") =>
                      filteredVendas.reduce((s, i) => s + getVendasSubcatVal(i, cat, tipo, mesesCalc, "vgv"), 0);
                    const refVal = sumCat("vendas", ref) - sumCat("distratos", ref);
                    const realVal = sumCat("vendas", "realizado") - sumCat("distratos", "realizado");
                    return (
                      <ConsolidadoAnaliticaCells
                        key={`vend-sec-${m}`}
                        m={m}
                        refVal={refVal}
                        realVal={realVal}
                        tone="amber"
                        emphasis="section"
                      />
                    );
                  })}
                </tr>
                {isSectionOpen("vendas") && vendasVisiveis.map((item: any, idx: number) => {
                  const pid = item.produto_id;
                  const prodExpanded = expandedVendasProd[pid] === true;
                  const hasDistrato = visibleMesesStr.some((mes) =>
                    getVendasSubcatVal(item, "distratos", ref, [mes], "vgv") !== 0 ||
                    getVendasSubcatVal(item, "distratos", "realizado", [mes], "vgv") !== 0,
                  );
                  return (
                    <Fragment key={`vend-item-${pid}-${idx}`}>
                      <tr className={`group border-b border-slate-100 ${idx % 2 === 0 ? "bg-white" : "bg-slate-50/40"}`}>
                        <td className="px-3 py-2 sticky left-0 bg-inherit shadow-[1px_0_0_0_#e2e8f0] z-10 border-r border-slate-100 group-hover:bg-slate-50/80">
                          <div className="flex items-center gap-1.5 pl-6">
                            {hasDistrato ? (
                              <button
                                type="button"
                                onClick={() => setExpandedVendasProd((s) => ({ ...s, [pid]: !prodExpanded }))}
                                className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-amber-700 hover:bg-amber-100/80"
                              >
                                {prodExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                              </button>
                            ) : (
                              <span className="w-5 shrink-0" />
                            )}
                            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shrink-0" />
                            <span className="text-xs font-medium text-slate-700 truncate max-w-[220px]" title={getProdNome(pid)}>
                              {getProdNome(pid)}
                            </span>
                          </div>
                        </td>
                        {months.map((m) => {
                          const mesesCalc = m === "total" ? visibleMesesStr : [m];
                          return (
                            <ConsolidadoAnaliticaCells
                              key={`vend-item-${pid}-${m}`}
                              m={m}
                              refVal={getVendasCatVal(item, "liquido", ref, mesesCalc, "vgv")}
                              realVal={getVendasCatReal(item, "liquido", mesesCalc, "vgv")}
                              emphasis="child"
                            />
                          );
                        })}
                      </tr>
                      {prodExpanded && (
                        <>
                          {(["vendas", "distratos"] as const).map((subCat) => (
                            <tr key={`vend-sub-${pid}-${subCat}`} className="border-b border-slate-100 bg-amber-50/20">
                              <td className="px-3 py-1.5 sticky left-0 bg-inherit shadow-[1px_0_0_0_#e2e8f0] z-10 border-r border-slate-100">
                                <div className="flex items-center gap-2 pl-14 text-[11px] text-slate-600">
                                  <span className={`h-1 w-1 rounded-full ${subCat === "vendas" ? "bg-emerald-400" : "bg-red-400"}`} />
                                  {subCat === "vendas" ? "Vendas" : "Distratos"}
                                </div>
                              </td>
                              {months.map((m) => {
                                const mesesCalc = m === "total" ? visibleMesesStr : [m];
                                const refVal = getVendasSubcatVal(item, subCat, ref, mesesCalc, "vgv");
                                const realVal = getVendasSubcatVal(item, subCat, "realizado", mesesCalc, "vgv");
                                return (
                                  <ConsolidadoAnaliticaCells
                                    key={`vend-sub-${pid}-${subCat}-${m}`}
                                    m={m}
                                    refVal={refVal}
                                    realVal={realVal}
                                    inverted={subCat === "distratos"}
                                    emphasis="sub"
                                  />
                                );
                              })}
                            </tr>
                          ))}
                        </>
                      )}
                    </Fragment>
                  );
                })}
                {isSectionOpen("vendas") && vendasVisiveis.length === 0 && (
                  <tr className="border-b border-slate-100 bg-white">
                    <td colSpan={1 + months.length * 3} className="px-3 py-3 text-xs text-slate-400 italic pl-12">
                      Nenhum produto encontrado para vendas.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function TabDespesasReceitas({ tipo, ano, consolidado, deptId, filtros, holdingMldu, onDataLoaded }: { tipo: "despesas" | "receitas"; ano: number; consolidado: boolean; deptId: number; filtros: any; holdingMldu: boolean; onDataLoaded?: (data: any) => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [modo, setModo] = useState<"orcado" | "forecast">("orcado");
  const [forecastId, setForecastId] = useState<number | "">("");
  const [sortConfig, setSortConfig] = useState<{ key: 'produto_nome' | 'plano_financeiro_nome', direction: 'asc' | 'desc' } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const onDataLoadedRef = useRef(onDataLoaded);
  onDataLoadedRef.current = onDataLoaded;
  const loadSeq = useRef(0);

  const load = useCallback(async (fid: number | "" = "") => {
    const seq = ++loadSeq.current;
    setLoading(true);
    setLoadError(null);
    try {
      const fn = tipo === "despesas" ? orcamentoService.getAcompanhamentoDespesas : orcamentoService.getAcompanhamentoReceitas;
      const res = await fn(ano, deptId, consolidado, fid || undefined, holdingMldu);
      if (seq !== loadSeq.current) return;
      setData(res);
      onDataLoadedRef.current?.(res);
      const nextForecastId = pickDefaultForecastId(res, fid);
      if (nextForecastId !== fid) setForecastId(nextForecastId);
      else if (fid) setForecastId(fid);
    } catch (e) {
      if (seq !== loadSeq.current) return;
      console.error(e);
      setLoadError(acompRequestError(e));
    } finally {
      if (seq === loadSeq.current) setLoading(false);
    }
  }, [tipo, ano, consolidado, deptId, holdingMldu]);

  useEffect(() => {
    setForecastId("");
    load("");
  }, [load]);

  if (loading && !data) return <BudgetLoadingState />;
  if (loadError && !data) return <BudgetLoadError message={loadError} onRetry={() => load(forecastId)} />;
  if (!data) return null;

  const ref = modo === "orcado" ? "orcado" : "forecast";
  const linkMeses = mesesFiltroToStr(filtros?.mesesSelecionados, filtros?.filtroMesesAtivo);

  const visibleMonthsIdx = MESES_STR.map((m, i) => i).filter(i => !filtros?.filtroMesesAtivo || filtros?.mesesSelecionados?.includes(MESES[i]));
  const visibleMeses = visibleMonthsIdx.map(i => MESES[i]);
  const visibleMesesStr = visibleMonthsIdx.map(i => MESES_STR[i]);
  const months = [...visibleMesesStr, "total"];

  const getProdNome = (id: number) => data.opcoes_produtos?.find((p: any) => p.id === id)?.nome || id;
  const getPlanoNome = (id: number) => data.opcoes_planos?.find((p: any) => p.id === id)?.nome || id;

  const itens = (data.itens || []).filter((item: any) => {
    const prodInfo = data.opcoes_produtos?.find((p: any) => p.id === item.produto_id) || {};
    const planoIdField = item.plano_financeiro_id;
    const planoInfo = data.opcoes_planos?.find((p: any) => p.id === planoIdField) || {};
    const baseInfo = (filtros?.centrosCustoBase || []).find((cc: any) => cc.db_id === item.produto_id) || {};
    const idSienge = baseInfo.id ? String(baseInfo.id) : String(prodInfo.id_sienge || prodInfo.id || "");
    const produtoNome = parseCentroNome(prodInfo.nome || "").produto;
    const planoNome = planoInfo.nome || "";
    const empresaId = String(baseInfo.id_empresa || prodInfo.id_empresa || "");
    const nomeEmpresa = prodInfo.nome_empresa || "";
    
    if (filtros?.busca) {
      if (!(prodInfo.nome || "").toLowerCase().includes(filtros.busca.toLowerCase()) && 
          !(item.descricao || "").toLowerCase().includes(filtros.busca.toLowerCase())) {
        return false;
      }
    }
    
    if (filtros?.idCentroCusto?.length > 0 && !filtros.idCentroCusto.includes(idSienge)) return false;
    if (filtros?.produtoFiltro?.length > 0 && !filtros.produtoFiltro.includes(produtoNome)) return false;
    if (filtros?.planoFinanceiro?.length > 0 && !filtros.planoFinanceiro.includes(planoNome)) return false;
    if (filtros?.idEmpresa?.length > 0 && !filtros.idEmpresa.includes(empresaId)) return false;
    
    return true;
  }).sort((a: any, b: any) => {
    const pA = (getProdNome(a.produto_id) || "").toString();
    const pB = (getProdNome(b.produto_id) || "").toString();
    const plA = (getPlanoNome(a.plano_financeiro_id) || "").toString();
    const plB = (getPlanoNome(b.plano_financeiro_id) || "").toString();
    
    if (!sortConfig) {
      const compProd = pA.localeCompare(pB);
      if (compProd !== 0) return compProd;
      return plA.localeCompare(plB);
    }
    
    const valA = sortConfig.key === 'produto_nome' ? pA : plA;
    const valB = sortConfig.key === 'produto_nome' ? pB : plB;
    
    if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
    if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

  const handleSort = (key: 'produto_nome' | 'plano_financeiro_nome') => {
    setSortConfig(current => {
      if (current?.key === key) {
        if (current.direction === 'asc') return { key, direction: 'desc' };
        return null;
      }
      return { key, direction: 'asc' };
    });
  };

  const renderSortIcon = (key: 'produto_nome' | 'plano_financeiro_nome') => {
    if (sortConfig?.key !== key) return <ArrowUpDown className="w-3 h-3 ml-1 inline opacity-30 group-hover:opacity-100" />;
    return sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3 ml-1 inline text-ml-green" /> : <ArrowDown className="w-3 h-3 ml-1 inline text-ml-green" />;
  };

  const exportarExcel = () => {
    const headers = ["Produto", "Plano Financeiro", ...visibleMeses, "Total"];
    const rows = itens.map((item: any) => [
      getProdNome(item.produto_id),
      getPlanoNome(item.plano_financeiro_id),
      ...visibleMesesStr.map(m => item[ref]?.[m] || 0),
      item[ref]?.total || 0,
    ]);
    const csvContent = [headers, ...rows].map(r => r.join(";")).join("\n");
    exportDataToExcel(headers, rows, `${tipo}_${ano}.xlsx`);
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden gap-3">
      {loading ? <BudgetRefreshingBanner /> : null}
      <div className="flex items-center gap-2 flex-wrap shrink-0">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Comparar com</span>
        <div className="flex rounded-lg overflow-hidden border border-slate-200">
          {(["orcado", "forecast"] as const).map(m => (
            <button key={m} onClick={() => setModo(m)}
              className={`px-3 py-1 text-xs font-semibold transition-colors ${modo === m ? "bg-ml-green text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}>
              {m === "orcado" ? "Orçado" : "Forecast"}
            </button>
          ))}
        </div>

        {modo === "forecast" && data?.versoes_disponiveis && data.versoes_disponiveis.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Versão</span>
            <select
              value={forecastId}
              onChange={e => {
                const next = e.target.value ? Number(e.target.value) : "";
                setForecastId(next);
                load(next);
              }}
              className="text-xs border border-slate-200 rounded-lg px-2 py-1 bg-white text-slate-700"
            >
              {data.versoes_disponiveis.map((v: any) => (
                <option key={v.id} value={v.id}>{v.descricao}</option>
              ))}
            </select>
          </div>
        )}

        <div className="ml-auto flex items-center gap-2">
          <button onClick={exportarExcel} className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"><FileSpreadsheet className="w-4 h-4 text-brand-green" /> Excel</button>
          <button onClick={() => load(forecastId)} className="p-1.5 text-slate-500 hover:text-ml-green transition-colors bg-white border border-slate-200 rounded-lg shadow-sm">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {itens.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-slate-400 min-h-0">
          <div className="text-center py-16">
            <BarChart2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">Nenhum dado de {tipo} para {ano}.</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 min-h-0 overflow-y-auto overflow-x-auto border border-slate-200 rounded-lg budget-matrix-scroll">
          <table className="w-full text-left border-collapse min-w-max">
            <thead className="text-xs text-slate-700 uppercase bg-slate-100 sticky top-0 z-30 shadow-[0_1px_0_0_#e2e8f0]">
              <tr>
                <th className="px-3 py-3 min-w-[200px] bg-slate-100 z-30 cursor-pointer group hover:bg-slate-200 transition-colors sticky left-0 shadow-[1px_0_0_0_#e2e8f0]" onClick={() => handleSort('produto_nome')}>
                  Produto {renderSortIcon('produto_nome')}
                </th>
                <th className="px-3 py-3 min-w-[150px] bg-slate-100 z-30 cursor-pointer group hover:bg-slate-200 transition-colors sticky left-[200px] shadow-[1px_0_0_0_#e2e8f0]" onClick={() => handleSort('plano_financeiro_nome')}>
                  Plano Financeiro {renderSortIcon('plano_financeiro_nome')}
                </th>
                <th className="px-3 py-3 min-w-[100px] bg-slate-100 sticky left-[350px] z-30 shadow-[1px_0_0_0_#e2e8f0]">Métrica</th>
                {visibleMeses.map(m => <th key={m} className="px-3 py-3 text-right min-w-[80px] bg-slate-100">{m}</th>)}
                <th className="px-3 py-3 text-right min-w-[100px] border-l border-slate-200 bg-slate-100">Total</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((item: any, idx: number) => {
                const rows: {label: string, fn: (m: string) => any, raw?: boolean, isPerc?: boolean, inverted?: boolean, cls?: string}[] = [
                  { label: `${ref === "orcado" ? "ORC." : "FCST."}`, fn: (m: string) => formatMoeda(item[ref]?.[m] || 0), raw: true },
                  { label: "Real.", fn: (m: string) => formatMoeda(item.realizado?.[m] || 0), raw: true },
                  { label: "Desvio %", fn: (m: string) => item[`desvio_${modo}`]?.[m] || 0, isPerc: true, inverted: tipo === 'despesas', cls: "bg-slate-100 font-medium" },
                ];
                return rows.map((row, ri) => (
                  <tr key={`${idx}-${ri}`} className={`group hover:bg-slate-50 transition-colors border-b border-slate-200 ${ri % 2 === 0 ? "bg-white" : "bg-slate-50/50"}`}>
                    {ri === 0 && (
                      <td rowSpan={3} className="px-3 py-2 font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-20 group-hover:bg-slate-50 transition-colors align-top min-w-[200px]">
                        <div>{getProdNome(item.produto_id)}</div>
                        {tipo === "despesas" && (
                          <div className="mt-1">
                            <OrcamentoDeepLinks
                              variant="compact"
                              params={{
                                ano,
                                modo,
                                meses: linkMeses,
                                produto: item.produto_id,
                                plano: item.plano_financeiro_id,
                                expand: true,
                              }}
                            />
                          </div>
                        )}
                      </td>
                    )}
                    {ri === 0 && <td rowSpan={3} className="px-3 py-2 text-slate-600 sticky left-[200px] bg-white shadow-[1px_0_0_0_#e2e8f0] z-20 group-hover:bg-slate-50 transition-colors align-top min-w-[150px]">{getPlanoNome(item.plano_financeiro_id)}</td>}
                    <td className={`px-3 py-2 text-slate-500 whitespace-nowrap text-xs sticky left-[350px] shadow-[1px_0_0_0_#e2e8f0] z-20 transition-colors min-w-[100px] bg-inherit ${row.cls || ""}`}>{row.label}</td>
                    {months.map(m => (
                      <td key={m} className={`px-3 py-2 text-right tabular-nums ${m === "total" ? "font-bold border-l border-slate-200" : ""}`}>
                        {row.isPerc
                          ? <DesvBadge value={row.fn(m)} inverted={row.inverted} />
                          : row.raw
                            ? row.fn(m)
                            : <span className="text-slate-600">{row.fn(m)}</span>
                        }
                      </td>
                    ))}
                  </tr>
                ));
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function TabVendas({ ano, consolidado, deptId, filtros, holdingMldu, onDataLoaded }: { ano: number; consolidado: boolean; deptId: number; filtros: any; holdingMldu: boolean; onDataLoaded?: (data: any) => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [modo, setModo] = useState<"orcado" | "forecast">("orcado");
  const [forecastId, setForecastId] = useState<number | "">("");
  const [expandedSecs, setExpandedSecs] = useState<Record<string, boolean>>({});
  const [sortConfig, setSortConfig] = useState<{ key: 'produto_nome', direction: 'asc' | 'desc' } | null>(null);

  const VENDAS_BLOCO_STYLE = {
    vendas: {
      label: "Vendas brutas",
      accent: "border-l-emerald-500",
      dot: "bg-emerald-500",
    },
    distratos: {
      label: "Distratos",
      accent: "border-l-red-400",
      dot: "bg-red-400",
    },
    liquido: {
      label: "VGV líquido",
      accent: "border-l-amber-500",
      dot: "bg-amber-500",
    },
  } as const;

  const [loadError, setLoadError] = useState<string | null>(null);
  const onDataLoadedRef = useRef(onDataLoaded);
  onDataLoadedRef.current = onDataLoaded;
  const loadSeq = useRef(0);

  const load = useCallback(async (fid: number | "" = "") => {
    const seq = ++loadSeq.current;
    setLoading(true);
    setLoadError(null);
    try {
      const res = await orcamentoService.getAcompanhamentoVendas(ano, deptId, consolidado, fid || undefined, holdingMldu);
      if (seq !== loadSeq.current) return;
      setData(res);
      onDataLoadedRef.current?.(res);
      const nextForecastId = pickDefaultForecastId(res, fid);
      if (nextForecastId !== fid) setForecastId(nextForecastId);
      else if (fid) setForecastId(fid);
    } catch (e) {
      if (seq !== loadSeq.current) return;
      console.error(e);
      setLoadError(acompRequestError(e));
    } finally {
      if (seq === loadSeq.current) setLoading(false);
    }
  }, [ano, consolidado, deptId, holdingMldu]);

  useEffect(() => {
    setForecastId("");
    load("");
  }, [load]);

  const handleSort = (key: 'produto_nome') => {
    setSortConfig(current => {
      if (current?.key === key) {
        if (current.direction === 'asc') return { key, direction: 'desc' };
        return null;
      }
      return { key, direction: 'asc' };
    });
  };

  if (loading && !data) return <BudgetLoadingState />;
  if (loadError && !data) return <BudgetLoadError message={loadError} onRetry={() => load(forecastId)} />;
  if (!data) return null;

  const ref = modo === "orcado" ? "orcado" : "forecast";

  const visibleMonthsIdx = MESES_STR.map((m, i) => i).filter(i => !filtros?.filtroMesesAtivo || filtros?.mesesSelecionados?.includes(MESES[i]));
  const visibleMeses = visibleMonthsIdx.map(i => MESES[i]);
  const visibleMesesStr = visibleMonthsIdx.map(i => MESES_STR[i]);
  const months = [...visibleMesesStr, "total"];

  const getProdNome = (id: number) => data.opcoes_produtos?.find((p: any) => p.id === id)?.nome || id;

  const itens = (data.itens || []).filter((item: any) => {
    const prodInfo = data.opcoes_produtos?.find((p: any) => p.id === item.produto_id) || {};
    const planoIdField = item.plano_venda_id;
    const planoInfo = data.opcoes_planos?.find((p: any) => p.id === planoIdField) || {};
    const baseInfo = (filtros?.centrosCustoBase || []).find((cc: any) => cc.db_id === item.produto_id) || {};
    const idSienge = baseInfo.id ? String(baseInfo.id) : String(prodInfo.id_sienge || prodInfo.id || "");
    const produtoNome = parseCentroNome(prodInfo.nome || "").produto;
    const planoNome = planoInfo.nome || "";
    const empresaId = String(baseInfo.id_empresa || prodInfo.id_empresa || "");
    const nomeEmpresa = prodInfo.nome_empresa || "";
    
    if (filtros?.busca) {
      if (!(prodInfo.nome || "").toLowerCase().includes(filtros.busca.toLowerCase()) && 
          !(item.descricao || "").toLowerCase().includes(filtros.busca.toLowerCase())) {
        return false;
      }
    }
    
    if (filtros?.idCentroCusto?.length > 0 && !filtros.idCentroCusto.includes(idSienge)) return false;
    if (filtros?.produtoFiltro?.length > 0 && !filtros.produtoFiltro.includes(produtoNome)) return false;
    if (filtros?.planoFinanceiro?.length > 0 && !filtros.planoFinanceiro.includes(planoNome)) return false;
    if (filtros?.idEmpresa?.length > 0 && !filtros.idEmpresa.includes(empresaId)) return false;
    
    return true;
  }).sort((a: any, b: any) => {
    const pA = (getProdNome(a.produto_id) || "").toString();
    const pB = (getProdNome(b.produto_id) || "").toString();
    if (!sortConfig) return pA.localeCompare(pB);
    if (pA < pB) return sortConfig.direction === 'asc' ? -1 : 1;
    if (pA > pB) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

  const exportarExcel = () => {
    const headers = ["Produto", ...visibleMeses, "Total"];
    const rows = itens.map((item: any) => [
      getProdNome(item.produto_id),
      ...visibleMesesStr.map(m => (item.vendas?.[ref]?.[m]?.vgv ?? 0)),
      item.vendas?.[ref]?.total?.vgv ?? 0,
    ]);
    const csvContent = [headers, ...rows].map(r => r.join(";")).join("\n");
    exportDataToExcel(headers, rows, `Realizado_${ano}.xlsx`);
  };

  const renderSortIcon = (key: 'produto_nome') => {
    if (sortConfig?.key !== key) return <ArrowUpDown className="w-3 h-3 ml-1 inline opacity-30 group-hover:opacity-100" />;
    return sortConfig.direction === 'asc' ? <ArrowUp className="w-3 h-3 ml-1 inline text-ml-green" /> : <ArrowDown className="w-3 h-3 ml-1 inline text-ml-green" />;
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden gap-3">
      <div className="flex items-center gap-2 flex-wrap shrink-0">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Comparar com</span>
        <div className="flex rounded-lg overflow-hidden border border-slate-200">
          {(["orcado", "forecast"] as const).map(m => (
            <button key={m} onClick={() => setModo(m)}
              className={`px-3 py-1 text-xs font-semibold transition-colors ${modo === m ? "bg-ml-green text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}>
              {m === "orcado" ? "Orçado" : "Forecast"}
            </button>
          ))}
        </div>

        {modo === "forecast" && data?.versoes_disponiveis && data.versoes_disponiveis.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Versão</span>
            <select
              value={forecastId}
              onChange={e => {
                const next = e.target.value ? Number(e.target.value) : "";
                setForecastId(next);
                load(next);
              }}
              className="text-xs border border-slate-200 rounded-lg px-2 py-1 bg-white text-slate-700"
            >
              {data.versoes_disponiveis.map((v: any) => (
                <option key={v.id} value={v.id}>{v.descricao}</option>
              ))}
            </select>
          </div>
        )}

        <div className="ml-auto flex items-center gap-2">
          <button onClick={exportarExcel} className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"><FileSpreadsheet className="w-4 h-4 text-brand-green" /> Excel</button>
          <button onClick={() => load(forecastId)} className="p-1.5 text-slate-500 hover:text-ml-green transition-colors bg-white border border-slate-200 rounded-lg shadow-sm">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {loading ? <BudgetRefreshingBanner /> : null}
      {itens.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 shrink-0 text-xs text-slate-500 px-0.5">
          <span className="font-semibold text-slate-600 uppercase tracking-wide">Blocos</span>
          {Object.values(VENDAS_BLOCO_STYLE).map((bloco) => (
            <span key={bloco.label} className="inline-flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${bloco.dot}`} />
              {bloco.label}
            </span>
          ))}
          <span className="text-slate-400 hidden sm:inline">· Expanda um bloco para unidades e desvios</span>
        </div>
      )}
      
      {itens.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-slate-400 min-h-0">
          <div className="text-center py-16">
            <BarChart2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">Nenhum dado de vendas para {ano}.</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 min-h-0 overflow-y-auto overflow-x-auto border border-slate-200 rounded-lg budget-matrix-scroll">
          <table className="w-full text-left border-collapse min-w-max">
            <thead className="text-xs text-slate-700 uppercase bg-slate-100 sticky top-0 z-30 shadow-[0_1px_0_0_#e2e8f0]">
              <tr>
                <th className="px-3 py-3 min-w-[200px] bg-slate-100 z-30 cursor-pointer group hover:bg-slate-200 transition-colors sticky left-0 shadow-[1px_0_0_0_#e2e8f0]" onClick={() => handleSort('produto_nome')}>
                  Produto {renderSortIcon('produto_nome')}
                </th>
                <th className="px-3 py-3 min-w-[130px] bg-slate-100 sticky left-[200px] z-30 shadow-[1px_0_0_0_#e2e8f0]">Métrica</th>
                {visibleMeses.map(m => <th key={m} className="px-3 py-3 text-right min-w-[80px] bg-slate-100">{m}</th>)}
                <th className="px-3 py-3 text-right min-w-[100px] border-l border-slate-200 bg-slate-100">Total</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((item: any, idx: number) => {
                type RowDef = { label: string; fn: (m: string) => any; raw?: boolean; isPerc?: boolean; inverted?: boolean; cls?: string; group?: "unid" | "vgv" | "desvio" };
                const secoes: { key: keyof typeof VENDAS_BLOCO_STYLE; headerMetrica: string; headerFn?: (m: string) => any; rows: RowDef[] }[] = [
                  {
                    key: "vendas",
                    headerMetrica: "Real. VGV",
                    headerFn: (m: string) => formatMoeda(item.vendas?.realizado?.[m]?.vgv ?? 0),
                    rows: [
                      { label: ref === "orcado" ? "Orç. unidades" : "Fcst. unidades", fn: (m: string) => (item.vendas?.[ref]?.[m]?.unidades ?? 0), group: "unid" },
                      { label: "Real. unidades", fn: (m: string) => (item.vendas?.realizado?.[m]?.unidades ?? 0), group: "unid" },
                      { label: "Desvio % unid.", fn: (m: string) => item["desvio_" + modo + "_vendas_unid"]?.[m] ?? 0, isPerc: true, inverted: false, group: "desvio" },
                      { label: ref === "orcado" ? "Orç. VGV" : "Fcst. VGV", fn: (m: string) => formatMoeda(item.vendas?.[ref]?.[m]?.vgv ?? 0), raw: true, group: "vgv" },
                      { label: "Real. VGV", fn: (m: string) => formatMoeda(item.vendas?.realizado?.[m]?.vgv ?? 0), raw: true, group: "vgv" },
                      { label: "Desvio % VGV", fn: (m: string) => item["desvio_" + modo + "_vendas"]?.[m] ?? 0, isPerc: true, inverted: false, group: "desvio" },
                    ],
                  },
                  {
                    key: "distratos",
                    headerMetrica: "Real. VGV",
                    headerFn: (m: string) => formatMoeda(item.distratos?.realizado?.[m]?.vgv ?? 0),
                    rows: [
                      { label: ref === "orcado" ? "Orç. unidades" : "Fcst. unidades", fn: (m: string) => (item.distratos?.[ref]?.[m]?.unidades ?? 0), group: "unid" },
                      { label: "Real. unidades", fn: (m: string) => (item.distratos?.realizado?.[m]?.unidades ?? 0), group: "unid" },
                      { label: "Desvio % unid.", fn: (m: string) => item["desvio_" + modo + "_distratos_unid"]?.[m] ?? 0, isPerc: true, inverted: true, group: "desvio" },
                      { label: ref === "orcado" ? "Orç. VGV" : "Fcst. VGV", fn: (m: string) => formatMoeda(item.distratos?.[ref]?.[m]?.vgv ?? 0), raw: true, group: "vgv" },
                      { label: "Real. VGV", fn: (m: string) => formatMoeda(item.distratos?.realizado?.[m]?.vgv ?? 0), raw: true, group: "vgv" },
                      { label: "Desvio % VGV", fn: (m: string) => item["desvio_" + modo + "_distratos"]?.[m] ?? 0, isPerc: true, inverted: true, group: "desvio" },
                    ],
                  },
                  {
                    key: "liquido",
                    headerMetrica: "Real. VGV líq.",
                    headerFn: (m: string) => formatMoeda((item.vendas?.realizado?.[m]?.vgv ?? 0) - (item.distratos?.realizado?.[m]?.vgv ?? 0)),
                    rows: [
                      { label: ref === "orcado" ? "Orç. VGV líq." : "Fcst. VGV líq.", fn: (m: string) => formatMoeda((item.vendas?.[ref]?.[m]?.vgv ?? 0) - (item.distratos?.[ref]?.[m]?.vgv ?? 0)), raw: true, group: "vgv" },
                      { label: "Real. VGV líq.", fn: (m: string) => formatMoeda((item.vendas?.realizado?.[m]?.vgv ?? 0) - (item.distratos?.realizado?.[m]?.vgv ?? 0)), raw: true, group: "vgv" },
                      {
                        label: "Desvio % líq.",
                        fn: (m: string) => {
                          const refLiq = (item.vendas?.[ref]?.[m]?.vgv ?? 0) - (item.distratos?.[ref]?.[m]?.vgv ?? 0);
                          const realLiq = (item.vendas?.realizado?.[m]?.vgv ?? 0) - (item.distratos?.realizado?.[m]?.vgv ?? 0);
                          return refLiq !== 0 ? (realLiq - refLiq) / Math.abs(refLiq) : 0;
                        },
                        isPerc: true,
                        inverted: false,
                        group: "desvio",
                      },
                    ],
                  },
                ];

                const colCount = 2 + months.length;

                return (
                  <Fragment key={idx}>
                    <tr className="bg-brand-50/40 border-t-2 border-brand-200/60">
                      <td className="px-4 py-3 font-semibold text-brand-900 sticky left-0 shadow-[1px_0_0_0_#dbeafe] bg-brand-50/40 z-20 min-w-[200px] text-sm leading-snug">
                        {getProdNome(item.produto_id)}
                      </td>
                      <td className="px-3 py-3 text-[11px] font-semibold uppercase tracking-wider text-brand-700/70 sticky left-[200px] shadow-[1px_0_0_0_#dbeafe] bg-brand-50/40 z-10 min-w-[130px]">
                        VGV líquido
                      </td>
                      {months.map((m: string) => {
                        const val = (item.vendas?.realizado?.[m]?.vgv ?? 0) - (item.distratos?.realizado?.[m]?.vgv ?? 0);
                        return (
                          <td
                            key={m}
                            className={`px-3 py-3 text-right font-semibold text-sm tabular-nums ${
                              m === "total" ? "border-l border-brand-200/60 text-brand-900" : val < 0 ? "text-red-700" : "text-brand-900"
                            }`}
                          >
                            {formatMoeda(val)}
                          </td>
                        );
                      })}
                    </tr>
                    {secoes.map((secao) => {
                      const secKey = `${idx}-${secao.key}`;
                      const isSecExpanded = expandedSecs[secKey];
                      const bloco = VENDAS_BLOCO_STYLE[secao.key];
                      return (
                      <Fragment key={secao.key}>
                        <tr
                          className={`cursor-pointer border-b border-slate-100 bg-white hover:bg-slate-50/80 transition-colors border-l-[3px] ${bloco.accent}`}
                          onClick={() => setExpandedSecs(prev => ({ ...prev, [secKey]: !prev[secKey] }))}
                        >
                          <td className="px-3 py-2 sticky left-0 z-20 shadow-[1px_0_0_0_#e2e8f0] bg-inherit min-w-[200px] pl-4">
                            <div className="flex items-center gap-2">
                              {isSecExpanded
                                ? <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                : <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
                              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${bloco.dot}`} />
                              <span className="text-xs font-semibold text-slate-700">{bloco.label}</span>
                            </div>
                          </td>
                          <td className="px-3 py-2 text-[11px] font-medium text-slate-500 sticky left-[200px] z-10 shadow-[1px_0_0_0_#e2e8f0] bg-inherit min-w-[130px]">
                            {secao.headerMetrica}
                          </td>
                          {months.map(m => {
                            const raw = secao.headerFn ? secao.headerFn(m) : "-";
                            const isNegative = typeof raw === "string" && raw.includes("-");
                            return (
                              <td
                                key={m}
                                className={`px-3 py-2 font-semibold text-[13px] text-right tabular-nums whitespace-nowrap ${
                                  m === "total" ? "border-l border-slate-200" : ""
                                } ${isNegative ? "text-red-700" : "text-slate-800"}`}
                              >
                                {raw}
                              </td>
                            );
                          })}
                        </tr>
                        {isSecExpanded && secao.rows.map((row, ri) => (
                          <tr
                            key={`${secao.key}-${ri}`}
                            className={`group border-b border-slate-100 transition-colors ${
                              row.group === "unid"
                                ? "bg-slate-50/60 hover:bg-slate-100/50"
                                : row.group === "desvio"
                                  ? "bg-white hover:bg-slate-50/80"
                                  : "bg-white hover:bg-slate-50/80"
                            }`}
                          >
                            <td className="px-3 py-1.5 sticky left-0 shadow-[1px_0_0_0_#e2e8f0] bg-inherit z-20 min-w-[200px]" />
                            <td className={`px-3 py-1.5 whitespace-nowrap text-xs sticky left-[200px] shadow-[1px_0_0_0_#e2e8f0] bg-inherit z-10 min-w-[130px] pl-8 ${
                              row.group === "vgv" ? "font-medium text-slate-600" : "text-slate-500"
                            }`}>
                              {row.label}
                            </td>
                            {months.map((m: string) => (
                              <td key={m} className={`px-3 py-1.5 text-right tabular-nums text-sm ${m === "total" ? "font-semibold border-l border-slate-200" : ""}`}>
                                {row.isPerc
                                  ? <DesvBadge value={row.fn(m)} inverted={row.inverted || false} />
                                  : row.raw
                                    ? row.fn(m)
                                    : <span className="text-slate-600">{row.fn(m)}</span>
                                }
                              </td>
                            ))}
                          </tr>
                        ))}
                      </Fragment>
                    );
                  })}
                    <tr aria-hidden="true">
                      <td colSpan={colCount} className="h-2 bg-slate-100/80 p-0 border-none" />
                    </tr>
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const COMPARATIVO_TIPOS = [
  { id: "CONSOLIDADO", label: "Consolidado" },
  { id: "DESPESAS", label: "Despesas" },
  { id: "RECEITAS", label: "Receitas" },
  { id: "VENDAS", label: "Vendas" },
] as const;

function ComparativoDriverBar({
  label,
  varRs,
  shareAbs,
  favoravel,
  onClick,
  compact = false,
  formatVal = formatMoeda,
}: {
  label: string;
  varRs: number;
  shareAbs: number;
  favoravel: boolean;
  onClick?: () => void;
  compact?: boolean;
  formatVal?: (v: number) => string;
}) {
  const content = (
    <>
      <div className={`flex items-center justify-between gap-2 ${compact ? "mb-0.5" : "mb-1"}`}>
        <span className={`text-slate-700 line-clamp-1 leading-snug ${compact ? "text-[11px]" : "text-xs"}`} title={label}>{label}</span>
        <span className={`font-semibold tabular-nums shrink-0 ${compact ? "text-[11px]" : "text-xs"} ${favoravel ? "text-emerald-700" : "text-red-700"}`}>
          {varRs > 0 ? "+" : ""}{formatVal(varRs)}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="flex-1 h-1 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${favoravel ? "bg-emerald-500" : "bg-red-500"}`}
            style={{ width: `${Math.min(100, shareAbs * 100)}%` }}
          />
        </div>
        <span className="text-[10px] font-semibold text-slate-500 tabular-nums w-7 text-right">
          {(shareAbs * 100).toFixed(0)}%
        </span>
      </div>
    </>
  );

  const boxClass = compact
    ? "w-full text-left rounded-md border border-slate-100 bg-slate-50/50 px-2 py-1.5 hover:border-ml-green/40 hover:bg-brand-green/5 transition-colors"
    : "w-full text-left rounded-lg border border-slate-200 bg-white p-2.5 hover:border-ml-green/40 hover:bg-brand-green/5 transition-colors";

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={boxClass}>
        {content}
      </button>
    );
  }

  return <div className={compact ? "rounded-md border border-slate-100 bg-slate-50/50 px-2 py-1.5" : "rounded-lg border border-slate-200 bg-white p-2.5"}>{content}</div>;
}

function ComparativoDesvioMensalStrip({
  meses,
  formatVal,
  onMesClick,
  refLabel = "Referência",
  realLabel = "Realizado",
}: {
  meses: {
    mes: string;
    label: string;
    varRs: number;
    favoravel: boolean;
    ref?: number;
    real?: number;
    totalA?: number;
    totalB?: number;
  }[];
  formatVal: (v: number) => string;
  onMesClick?: (mes: string) => void;
  refLabel?: string;
  realLabel?: string;
}) {
  const pontos = meses.map((m) => ({
    ...m,
    refVal: m.ref ?? m.totalA ?? 0,
    realVal: m.real ?? m.totalB ?? 0,
  }));
  const maxAbs = Math.max(...pontos.flatMap((m) => [Math.abs(m.refVal), Math.abs(m.realVal), Math.abs(m.varRs)]), 1);
  const fmtCompact = (v: number) => {
    const abs = Math.abs(v);
    if (abs >= 1_000_000) return `${v < 0 ? "−" : ""}${(abs / 1_000_000).toFixed(1)}M`;
    if (abs >= 1_000) return `${v < 0 ? "−" : ""}${(abs / 1_000).toFixed(0)}k`;
    return formatVal(v);
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5">
          <LineChart className="w-3.5 h-3.5 text-slate-500" />
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Referência × Realizado por mês</p>
        </div>
        <div className="flex items-center gap-3 text-[9px] font-semibold text-slate-500">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-sm bg-slate-400" />
            {refLabel}
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-sm bg-emerald-500" />
            {realLabel}
          </span>
        </div>
      </div>
      <div className="flex gap-1 overflow-x-auto pb-0.5">
        {pontos.map((m) => {
          const refPct = (Math.abs(m.refVal) / maxAbs) * 100;
          const realPct = (Math.abs(m.realVal) / maxAbs) * 100;
          const inner = (
            <>
              <div className="h-12 w-full flex items-end justify-center gap-0.5 px-0.5">
                <div
                  className={`w-2.5 rounded-t ${m.refVal < 0 ? "bg-slate-300" : "bg-slate-400"}`}
                  style={{ height: `${Math.max(m.refVal === 0 ? 3 : 10, refPct)}%` }}
                  title={`${refLabel}: ${formatVal(m.refVal)}`}
                />
                <div
                  className={`w-2.5 rounded-t ${m.realVal < 0 ? "bg-red-400" : "bg-emerald-500"}`}
                  style={{ height: `${Math.max(m.realVal === 0 ? 3 : 10, realPct)}%` }}
                  title={`${realLabel}: ${formatVal(m.realVal)}`}
                />
              </div>
              <span className="text-[10px] font-semibold text-slate-600 mt-1">{m.label}</span>
              <span className="text-[8px] text-slate-400 tabular-nums leading-tight">{fmtCompact(m.refVal)}</span>
              <span className="text-[8px] text-slate-600 tabular-nums leading-tight font-medium">{fmtCompact(m.realVal)}</span>
              <span className={`text-[9px] font-semibold tabular-nums leading-tight ${m.favoravel ? "text-emerald-700" : "text-red-700"}`}>
                Δ {m.varRs > 0 ? "+" : ""}{fmtCompact(m.varRs)}
              </span>
            </>
          );
          const boxClass = "flex flex-col items-center min-w-[58px] shrink-0 rounded-md px-1 py-1 hover:bg-slate-50 transition-colors";
          if (onMesClick) {
            return (
              <button key={m.mes} type="button" onClick={() => onMesClick(m.mes)} className={boxClass} title={`Ver analítico · ${m.label}`}>
                {inner}
              </button>
            );
          }
          return <div key={m.mes} className={boxClass}>{inner}</div>;
        })}
      </div>
    </div>
  );
}

function TabComparativo({
  ano,
  deptId,
  filtros,
  onDataLoaded,
}: {
  ano: number;
  deptId: number;
  filtros: any;
  onDataLoaded?: (data: any) => void;
}) {
  const router = useRouter();
  const [versoesDespesas, setVersoesDespesas] = useState<any[]>([]);
  const [versoesReceitas, setVersoesReceitas] = useState<any[]>([]);
  const [versoesVendas, setVersoesVendas] = useState<any[]>([]);
  const [versoesConsolidadas, setVersoesConsolidadas] = useState<any[]>([]);
  const [tipo, setTipo] = useState("DESPESAS");
  const [idA, setIdA] = useState<string>("");
  const [idB, setIdB] = useState<string>("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [resultView, setResultView] = useState<"todas" | "destaques" | "alteracoes" | "inclusoes" | "exclusoes">("destaques");
  const [desvioFilter, setDesvioFilter] = useState<"todos" | "favoravel" | "desfavoravel">("todos");
  const [visao, setVisao] = useState<"executiva" | "analitica">("executiva");
  const [buscaAnalitica, setBuscaAnalitica] = useState("");
  const [materialidade, setMaterialidade] = useState<"todos" | "relevante" | "alto">("todos");
  const [vendasMetric, setVendasMetric] = useState<VendasComparativoMetric>("vgv");
  const [vendasCategoria, setVendasCategoria] = useState<VendasComparativoCategoria>("todos");
  const [analiticoModo, setAnaliticoModo] = useState<"total" | "mes">("total");

  const visibleMesesStr = useMemo(() => getComparativoVisibleMeses(filtros), [filtros]);
  const visibleMesesLabels = useMemo(
    () => visibleMesesStr.map((m) => MESES[MESES_STR.indexOf(m)] ?? m),
    [visibleMesesStr],
  );

  useEffect(() => {
    if (tipo !== "VENDAS") {
      setVendasMetric("vgv");
      setVendasCategoria("todos");
    }
  }, [tipo]);

  useEffect(() => {
    orcamentoService.listarVersoes(ano, "DESPESAS", deptId).then(setVersoesDespesas).catch(() => { });
    orcamentoService.listarVersoes(ano, "RECEITAS", deptId).then(setVersoesReceitas).catch(() => { });
    orcamentoService.listarVersoes(ano, "VENDAS", deptId).then(setVersoesVendas).catch(() => { });
    orcamentoService.listarVersoes(ano, "CONSOLIDADO", deptId).then(setVersoesConsolidadas).catch(() => { });
  }, [ano, deptId]);

  const versoes = tipo === "CONSOLIDADO"
    ? versoesConsolidadas
    : tipo === "DESPESAS"
      ? versoesDespesas
      : tipo === "RECEITAS"
        ? versoesReceitas
        : versoesVendas;

  const filteredResult = useMemo(() => {
    if (!result) return null;
    let payload = result;
    if (tipo === "VENDAS") {
      payload = filterComparativoVendasCategoria(payload, vendasCategoria);
    }
    return filterComparativoResult(payload, filtros);
  }, [result, filtros, tipo, vendasCategoria]);

  const insights = useMemo(
    () => (filteredResult ? buildComparativoInsights(filteredResult, tipo, vendasMetric) : null),
    [filteredResult, tipo, vendasMetric],
  );

  const desvioPorMes = useMemo(
    () => (filteredResult ? buildComparativoDesvioPorMes(filteredResult, tipo, vendasMetric, visibleMesesStr) : []),
    [filteredResult, tipo, vendasMetric, visibleMesesStr],
  );

  const fmtValor = useCallback(
    (v: number) => formatComparativoValor(v, vendasMetric, tipo),
    [vendasMetric, tipo],
  );
  const fmtValorExib = useCallback(
    (v: number) => {
      if (tipo === "VENDAS" && vendasCategoria === "distratos") {
        return formatComparativoValor(Math.abs(v), vendasMetric, tipo);
      }
      return fmtValor(v);
    },
    [fmtValor, tipo, vendasCategoria, vendasMetric],
  );
  const varColLabel = tipo === "VENDAS" && vendasMetric === "unidades" ? "Variação (un.)" : "Variação R$";

  useEffect(() => {
    if (result && onDataLoaded) {
      onDataLoaded(comparativoResultToFilterPayload(result));
    }
  }, [result, onDataLoaded]);

  const getProdNome = (id: number) => result?.produtos_map?.[id] || id;
  const getPlanoNome = (id: number) => result?.planos_map?.[id] || id;

  const getNomeVersao = (id: string) => versoes.find((v: any) => v.id === id)?.descricao || id;

  const comparar = async () => {
    if (!idA || !idB) return;
    setLoading(true);
    try {
      const res = await orcamentoService.getComparativo(idA, idB, tipo, ano, deptId, false);
      setResult(res);
      setResultView("destaques");
      setDesvioFilter("todos");
      setVisao("executiva");
      setBuscaAnalitica("");
      setMaterialidade("todos");
      setVendasMetric("vgv");
      setVendasCategoria("todos");
      setAnaliticoModo("total");
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const isPositivoBom = tipo === "VENDAS" || tipo === "RECEITAS" || tipo === "CONSOLIDADO";
  const variacaoFavoravel = insights ? isVariacaoFavoravel(insights.globalVarRs, tipo) : true;
  const tone = insights
    ? variationTone(variacaoFavoravel, insights.globalVarRs, insights.globalVarPerc)
    : variationTone(true, 0, 0);

  const rowVarClass = (varRs: number) => {
    if (varRs === 0) return "text-slate-600";
    return isVariacaoFavoravel(varRs, tipo) ? "text-emerald-700" : "text-red-700";
  };

  const tipoLabel = COMPARATIVO_TIPOS.find((t) => t.id === tipo)?.label ?? tipo;

  const materialidadeMinShare = materialidade === "alto" ? 0.05 : materialidade === "relevante" ? 0.01 : 0;

  const matchesAnalitico = useCallback((item: any) => {
    if (materialidadeMinShare > 0 && (item.shareAbs || 0) < materialidadeMinShare) return false;
    if (!buscaAnalitica.trim()) return true;
    const q = buscaAnalitica.trim().toLowerCase();
    const prodId = item.versao_a?.produto_id ?? item.produto_id;
    const planoId = item.versao_a?.plano_financeiro_id ?? item.plano_financeiro_id;
    const prod = String(result?.produtos_map?.[prodId] || prodId).toLowerCase();
    const plano = String(result?.planos_map?.[planoId] || planoId).toLowerCase();
    return prod.includes(q) || plano.includes(q);
  }, [buscaAnalitica, materialidadeMinShare, result]);

  const filteredAlteracoes = useMemo(() => {
    if (!insights) return [];
    let items = insights.processedAlt;
    if (desvioFilter === "favoravel") items = items.filter((i) => i.favoravel && i.varRs !== 0);
    if (desvioFilter === "desfavoravel") items = items.filter((i) => !i.favoravel && i.varRs !== 0);
    return items.filter(matchesAnalitico);
  }, [insights, desvioFilter, matchesAnalitico]);

  const filteredDestaques = useMemo(() => {
    if (!insights) return [];
    let items = insights.allItems;
    if (desvioFilter === "favoravel") items = items.filter((i) => i.favoravel && i.varRs !== 0);
    if (desvioFilter === "desfavoravel") items = items.filter((i) => !i.favoravel && i.varRs !== 0);
    const filtered = items.filter(matchesAnalitico);
    return visao === "executiva" ? filtered.slice(0, 5) : filtered.slice(0, 10);
  }, [insights, desvioFilter, matchesAnalitico, visao]);

  const filteredTodas = useMemo(() => {
    if (!insights) return [];
    let items = insights.todasLinhas || [];
    if (desvioFilter === "favoravel") items = items.filter((i) => i.favoravel && i.varRs !== 0);
    if (desvioFilter === "desfavoravel") items = items.filter((i) => !i.favoravel && i.varRs !== 0);
    return items.filter(matchesAnalitico);
  }, [insights, desvioFilter, matchesAnalitico]);

  const filteredInclusoes = useMemo(() => {
    if (!insights) return [];
    return insights.processedInc.filter(matchesAnalitico);
  }, [insights, matchesAnalitico]);

  const filteredExclusoes = useMemo(() => {
    if (!insights) return [];
    return insights.processedExc.filter(matchesAnalitico);
  }, [insights, matchesAnalitico]);

  const abrirAnalitico = (opts?: { view?: typeof resultView; filter?: typeof desvioFilter; busca?: string; modo?: typeof analiticoModo }) => {
    setVisao("analitica");
    if (opts?.view) setResultView(opts.view);
    if (opts?.filter) setDesvioFilter(opts.filter);
    if (opts?.busca) setBuscaAnalitica(opts.busca);
    if (opts?.modo) setAnaliticoModo(opts.modo);
  };

  const linkMeses = mesesFiltroToStr(filtros?.mesesSelecionados, filtros?.filtroMesesAtivo);
  const irParaDespesasExterno = (opts?: { produto?: number; plano?: number; expand?: boolean }) => {
    router.push(buildOrcamentoHref("analitico1", {
      ano,
      modo: "orcado",
      meses: linkMeses,
      produto: opts?.produto,
      plano: opts?.plano,
      expand: opts?.expand,
    }));
  };

  const exportarComparativo = () => {
    if (!insights) return;
    const linhas = insights.todasLinhas || [];
    if (analiticoModo === "mes") {
      const headers = [
        "Tipo",
        "Produto",
        "Plano",
        ...visibleMesesLabels.map((l) => `Var ${l}`),
        varColLabel,
        "Var. %",
        "Peso %",
        "Favorável",
      ];
      const rows = linhas.map((item) => {
        const prodId = item.versao_a?.produto_id ?? item.produto_id;
        const planoId = item.versao_a?.plano_financeiro_id ?? item.plano_financeiro_id;
        const varsMes = visibleMesesStr.map((mes) => processComparativoItemMes(item, mes, tipo, result, vendasMetric).varRs);
        return [
          item.categoriaComparativo || "",
          getProdNome(prodId),
          getPlanoNome(planoId),
          ...varsMes,
          item.varRs,
          item.varPerc,
          item.shareAbs,
          item.favoravel ? "Sim" : "Não",
        ];
      });
      exportDataToExcel(headers, rows, `comparativo_${tipo}_${ano}_completo_por_mes.xlsx`);
      return;
    }
    const headers = [
      "Tipo",
      "Produto",
      "Plano",
      getNomeVersao(idA),
      getNomeVersao(idB),
      varColLabel,
      "Var. %",
      "Peso %",
      "Favorável",
    ];
    const rows = linhas.map((item) => {
      const prodId = item.versao_a?.produto_id ?? item.produto_id;
      const planoId = item.versao_a?.plano_financeiro_id ?? item.plano_financeiro_id;
      return [
        item.categoriaComparativo || "",
        getProdNome(prodId),
        getPlanoNome(planoId),
        item.valA,
        item.valB,
        item.varRs,
        item.varPerc,
        item.shareAbs,
        item.favoravel ? "Sim" : "Não",
      ];
    });
    exportDataToExcel(headers, rows, `comparativo_${tipo}_${ano}_completo.xlsx`);
  };

  const resultTabs = insights ? [
    { id: "todas" as const, label: "Todas as linhas", count: insights.counts.totalLinhas },
    { id: "destaques" as const, label: "Destaques", count: Math.min(insights.allItems.length, 10) },
    { id: "alteracoes" as const, label: "Alterações", count: insights.processedAlt.length },
    { id: "inclusoes" as const, label: "Inclusões", count: insights.processedInc.length },
    { id: "exclusoes" as const, label: "Exclusões", count: insights.processedExc.length },
  ].filter((t) => t.id === "todas" || t.id === "destaques" || t.count > 0) : [];

  const renderComparisonRow = (alt: any, i: number, opts?: { rank?: number; compact?: boolean; showShare?: boolean; porMes?: boolean; showTipo?: boolean }) => {
    const prodId = alt.versao_a?.produto_id ?? alt.produto_id;
    const planoId = alt.versao_a?.plano_financeiro_id ?? alt.plano_financeiro_id;
    const py = opts?.compact ? "py-2.5" : "py-3.5";
    const stickyBg = "bg-white group-hover:bg-slate-50/80";
    const porMes = opts?.porMes && visibleMesesStr.length > 0;
    return (
      <tr key={i} className="group hover:bg-slate-50/80 border-b border-slate-100 transition-colors">
        {opts?.rank != null && (
          <td className={`px-3 ${py} text-xs font-semibold text-slate-400 tabular-nums w-10`}>{opts.rank}</td>
        )}
        {opts?.showTipo && (
          <td className={`px-3 ${py} whitespace-nowrap`}>
            <span className="inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide bg-slate-100 text-slate-600">
              {alt.categoriaComparativo || "—"}
            </span>
          </td>
        )}
        <td className={`px-4 ${py} font-medium text-slate-800 text-sm min-w-[200px] max-w-[260px] sticky left-0 z-10 ${stickyBg}`}>
          <span className="line-clamp-3">{getProdNome(prodId)}</span>
        </td>
        <td className={`px-4 ${py} text-slate-500 text-sm min-w-[160px] max-w-[220px] sticky left-[200px] z-10 ${stickyBg} shadow-[2px_0_5px_-2px_rgba(0,0,0,0.06)]`}>
          <span className="line-clamp-2">{getPlanoNome(planoId)}</span>
          {tipo === "VENDAS" && alt.is_distrato && vendasCategoria === "todos" && (
            <span className="ml-1.5 text-[10px] bg-red-50 text-red-700 px-1.5 py-0.5 rounded font-semibold uppercase tracking-wide">Distrato</span>
          )}
          {alt.multiplier === -1 && (
            <span className="ml-1.5 text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-semibold uppercase tracking-wide">Saída</span>
          )}
        </td>
        {!porMes && (
          <>
            <td className={`px-4 ${py} text-right tabular-nums text-sm text-slate-600 whitespace-nowrap`}>{fmtValorExib(alt.valA)}</td>
            <td className={`px-4 ${py} text-right tabular-nums text-sm font-medium text-slate-800 whitespace-nowrap`}>{fmtValorExib(alt.valB)}</td>
          </>
        )}
        {porMes && visibleMesesStr.map((mes) => {
          const { varRs } = processComparativoItemMes(alt, mes, tipo, result, vendasMetric);
          return (
            <td key={mes} className={`px-3 ${py} text-right tabular-nums text-xs whitespace-nowrap ${rowVarClass(varRs)}`}>
              {varRs > 0 ? "+" : ""}{fmtValorExib(varRs)}
            </td>
          );
        })}
        <td className={`px-4 ${py} text-right tabular-nums font-semibold text-sm whitespace-nowrap ${rowVarClass(alt.varRs)}`}>
          {alt.varRs > 0 ? "+" : ""}{fmtValorExib(alt.varRs)}
        </td>
        <td className={`px-4 ${py} text-right whitespace-nowrap`}>
          <DesvBadge value={alt.varPerc} inverted={!isPositivoBom} />
        </td>
        {opts?.showShare && (
          <td className={`px-4 ${py} w-[120px]`}>
            <div className="flex items-center gap-2 justify-end">
              <div className="flex-1 max-w-[72px] h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${alt.favoravel ? "bg-emerald-500" : "bg-red-500"}`}
                  style={{ width: `${Math.min(100, (alt.shareAbs || 0) * 100)}%` }}
                />
              </div>
              <span className="text-[10px] font-semibold text-slate-500 tabular-nums w-8 text-right">
                {((alt.shareAbs || 0) * 100).toFixed(0)}%
              </span>
            </div>
          </td>
        )}
      </tr>
    );
  };

  const tableHead = (opts?: { rank?: boolean; share?: boolean; porMes?: boolean; showTipo?: boolean }) => {
    const porMes = opts?.porMes && visibleMesesStr.length > 0;
    return (
    <thead className="text-[11px] text-slate-500 uppercase tracking-wide bg-slate-50/95 sticky top-0 z-20 shadow-[0_1px_0_0_#e2e8f0]">
      <tr>
        {opts?.rank && <th className="px-3 py-3 font-semibold border-b border-slate-200 w-10 bg-slate-50/95">#</th>}
        {opts?.showTipo && <th className="px-3 py-3 font-semibold border-b border-slate-200 whitespace-nowrap">Tipo</th>}
        <th className="px-4 py-3 font-semibold border-b border-slate-200 min-w-[200px] sticky left-0 z-20 bg-slate-50/95">Produto</th>
        <th className="px-4 py-3 font-semibold border-b border-slate-200 min-w-[160px] sticky left-[200px] z-20 bg-slate-50/95 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.06)]">Plano</th>
        {!porMes && (
          <>
            <th className="px-4 py-3 text-right font-semibold border-b border-slate-200 min-w-[110px]">{getNomeVersao(idA)}</th>
            <th className="px-4 py-3 text-right font-semibold border-b border-slate-200 min-w-[110px]">{getNomeVersao(idB)}</th>
          </>
        )}
        {porMes && visibleMesesLabels.map((label) => (
          <th key={label} className="px-3 py-3 text-right font-semibold border-b border-slate-200 min-w-[72px] whitespace-nowrap">
            Δ {label}
          </th>
        ))}
        <th className="px-4 py-3 text-right font-semibold border-b border-slate-200 min-w-[110px]">{porMes ? "Δ Total" : varColLabel}</th>
        <th className="px-4 py-3 text-right font-semibold border-b border-slate-200 min-w-[80px]">Var. %</th>
        {opts?.share && (
          <th className="px-4 py-3 text-right font-semibold border-b border-slate-200 min-w-[100px]">Peso</th>
        )}
      </tr>
    </thead>
  );};

  return (
    <div className="flex-1 flex flex-col min-h-0 gap-2">
      {/* Barra de configuração — compacta quando já há resultado */}
      <div className={`shrink-0 rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white shadow-sm ${result ? "p-2.5" : "p-4"}`}>
        <div className={`flex flex-col ${result ? "gap-2 lg:flex-row lg:items-center lg:justify-between" : "gap-4 lg:flex-row lg:items-end lg:justify-between"}`}>
          <div className={`min-w-0 flex-1 ${result ? "space-y-2" : "space-y-3"}`}>
            {!result && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Comparativo de versões</p>
                <p className="text-sm text-slate-600 mt-0.5">
                  Compare orçamento e forecast · {tipoLabel} · {ano}
                </p>
              </div>
            )}
            {result && (
              <p className="text-xs font-semibold text-slate-700 truncate">
                {tipoLabel} · {getNomeVersao(idA)} vs {getNomeVersao(idB)}
              </p>
            )}
            <div className="flex flex-wrap gap-1.5">
              {COMPARATIVO_TIPOS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => { setTipo(t.id); setIdA(""); setIdB(""); setResult(null); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors border ${
                    tipo === t.id
                      ? "bg-slate-800 text-white border-slate-800"
                      : "bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-2 lg:gap-3 lg:max-w-3xl w-full lg:w-auto">
            <div className="flex-1 min-w-[140px]">
              <label className="block text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-1">Versão base</label>
              <select
                value={idA}
                onChange={(e) => setIdA(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-ml-green/30 focus:border-ml-green"
              >
                <option value="">Selecione…</option>
                {versoes.map((v: any) => <option key={v.id} value={v.id}>{v.descricao}</option>)}
              </select>
            </div>
            <div className="hidden sm:flex items-center justify-center pb-2 text-slate-300 shrink-0">
              <ArrowRightLeft className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-[140px]">
              <label className="block text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-1">Versão comparada</label>
              <select
                value={idB}
                onChange={(e) => setIdB(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-ml-green/30 focus:border-ml-green"
              >
                <option value="">Selecione…</option>
                {versoes.map((v: any) => <option key={v.id} value={v.id}>{v.descricao}</option>)}
              </select>
            </div>
            <button
              type="button"
              onClick={comparar}
              disabled={!idA || !idB || loading}
              className="flex items-center justify-center gap-2 px-5 py-2.5 bg-ml-green text-white rounded-lg font-semibold text-sm hover:bg-ml-green/90 disabled:opacity-50 transition-all shrink-0 sm:mb-0"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <GitCompare className="w-4 h-4" />}
              Comparar
            </button>
            {tipo !== "VENDAS" && (
              <button
                type="button"
                disabled={!idA || !idB}
                title="Abre as mesmas duas versões na árvore da Visão DFC (entradas e saídas)"
                onClick={() =>
                  router.push(
                    `/dashboard/orcamento/dfc?modo=comparar&ano=${ano}&versao_a=${encodeURIComponent(idA)}&versao_b=${encodeURIComponent(idB)}`,
                  )
                }
                className="flex items-center justify-center gap-2 px-4 py-2.5 bg-white text-slate-700 border border-slate-200 rounded-lg font-semibold text-sm hover:bg-slate-50 disabled:opacity-50 transition-all shrink-0"
              >
                <Layers className="w-4 h-4" />
                Visão DFC
              </button>
            )}
          </div>
        </div>
      </div>

      {!result && !loading && (
        <div className="flex-1 flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/50 px-6 py-16 text-center">
          <GitCompare className="w-10 h-10 text-slate-300 mb-3" />
          <p className="text-sm font-semibold text-slate-700">Selecione duas versões para comparar</p>
          <p className="text-xs text-slate-500 mt-1 max-w-md">
            Escolha o tipo, a versão base (orçamento) e a versão comparada (forecast ou outra versão) para ver variações consolidadas e por produto.
          </p>
        </div>
      )}

      {loading && !result && (
        <div className="flex-1 flex items-center justify-center rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <RefreshCw className="w-5 h-5 animate-spin text-ml-green" />
            Gerando comparativo…
          </div>
        </div>
      )}

      {result && insights && (
        <div className="flex-1 min-h-0 flex flex-col gap-2 overflow-hidden animate-in fade-in duration-300">
          {/* KPI compacto + toggle análise — fixo no topo */}
          <div className="shrink-0 rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] divide-y md:divide-y-0 md:divide-x divide-slate-100">
              <div className="px-3 py-2.5">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5">Versão base</p>
                <p className="text-lg xl:text-xl font-bold text-slate-900 tabular-nums tracking-tight">{fmtValorExib(insights.globalTotalA)}</p>
                <p className="text-[11px] text-slate-500 mt-0.5 truncate" title={getNomeVersao(idA)}>{getNomeVersao(idA)}</p>
              </div>

              <div className={`px-4 py-2.5 flex flex-col items-center justify-center text-center min-w-[160px] ${tone.panel}`}>
                <p className="text-[10px] font-semibold uppercase tracking-wider opacity-70 mb-0.5">Variação total</p>
                <p className={`text-lg xl:text-xl font-bold tabular-nums tracking-tight ${tone.value}`}>
                  {insights.globalVarRs > 0 ? "+" : ""}{fmtValorExib(insights.globalVarRs)}
                </p>
                <p className={`text-[11px] font-semibold mt-0.5 tabular-nums ${tone.muted}`}>
                  {insights.globalVarPerc > 0 ? "+" : ""}{(insights.globalVarPerc * 100).toFixed(2)}%
                </p>
              </div>

              <div className="px-3 py-2.5 md:text-right">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5">Versão comparada</p>
                <p className="text-lg xl:text-xl font-bold text-slate-900 tabular-nums tracking-tight">{fmtValorExib(insights.globalTotalB)}</p>
                <p className="text-[11px] text-slate-500 mt-0.5 truncate" title={getNomeVersao(idB)}>{getNomeVersao(idB)}</p>
              </div>
            </div>
            <div className="px-3 py-1.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 bg-slate-50/50">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs text-slate-600">
                  {insights.counts.comDesvio} desvios · {insights.counts.inclusoes} inclusões · {insights.counts.exclusoes} exclusões
                  {filtros?.filtroMesesAtivo && visibleMesesLabels.length > 0 && (
                    <span className="text-slate-400"> · Período: {visibleMesesLabels.join(", ")}</span>
                  )}
                  {tipo === "VENDAS" && vendasCategoria !== "todos" && (
                    <span className="text-slate-400"> · {COMPARATIVO_VENDAS_CATEGORIA_LABEL[vendasCategoria]}</span>
                  )}
                  {tipo === "VENDAS" && (
                    <span className="text-slate-400"> · {vendasMetric === "vgv" ? "VGV" : "Nº vendas"}</span>
                  )}
                </p>
                <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${tone.badge}`}>
                  <SemaforoDesvio n={insights.globalTotalB} ref={insights.globalTotalA} tipo={tipoSemaforo(tipo)} />
                  {insights.veredito === "favoravel" ? <CheckCircle2 className="w-3 h-3" /> :
                   insights.veredito === "desfavoravel" ? <AlertCircle className="w-3 h-3" /> : null}
                  {insights.veredito === "favoravel" ? "Favorável" :
                   insights.veredito === "desfavoravel" ? "Requer atenção" : "Neutro"}
                </span>
              </div>
              <div className="flex items-center gap-1 flex-wrap justify-end">
                {tipo === "VENDAS" && (
                  <>
                    <div className="flex items-center gap-1 mr-2 border-r border-slate-200 pr-2">
                      {(["todos", "vendas", "distratos", "liquido"] as const).map((cat) => (
                        <button
                          key={cat}
                          type="button"
                          onClick={() => setVendasCategoria(cat)}
                          className={`px-2 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                            vendasCategoria === cat ? "bg-white text-slate-800 shadow-sm border border-slate-200" : "text-slate-500 hover:bg-white"
                          }`}
                        >
                          {COMPARATIVO_VENDAS_CATEGORIA_LABEL[cat]}
                        </button>
                      ))}
                    </div>
                    <div className="flex items-center gap-1 mr-2 border-r border-slate-200 pr-2">
                      <button
                        type="button"
                        onClick={() => setVendasMetric("vgv")}
                        className={`px-2 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                          vendasMetric === "vgv" ? "bg-white text-slate-800 shadow-sm border border-slate-200" : "text-slate-500 hover:bg-white"
                        }`}
                      >
                        VGV
                      </button>
                      <button
                        type="button"
                        onClick={() => setVendasMetric("unidades")}
                        className={`px-2 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                          vendasMetric === "unidades" ? "bg-white text-slate-800 shadow-sm border border-slate-200" : "text-slate-500 hover:bg-white"
                        }`}
                      >
                        Nº vendas
                      </button>
                    </div>
                  </>
                )}
                <button
                  type="button"
                  onClick={() => setVisao("executiva")}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
                    visao === "executiva" ? "bg-white text-slate-800 shadow-sm border border-slate-200" : "text-slate-500 hover:bg-white"
                  }`}
                >
                  <LayoutDashboard className="w-3.5 h-3.5" />
                  Executiva
                </button>
                <button
                  type="button"
                  onClick={() => setVisao("analitica")}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
                    visao === "analitica" ? "bg-white text-slate-800 shadow-sm border border-slate-200" : "text-slate-500 hover:bg-white"
                  }`}
                >
                  <Table2 className="w-3.5 h-3.5" />
                  Analítica
                </button>
              </div>
            </div>
          </div>

          {visao === "executiva" ? (
            <div className="flex-1 min-h-0 overflow-y-auto budget-matrix-scroll flex flex-col gap-1.5 pb-1 pr-0.5">
              <div className="grid grid-cols-1 xl:grid-cols-[1.3fr_0.9fr] gap-1.5 shrink-0">
                <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
                  <div className="flex items-start gap-2">
                    {variacaoFavoravel ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-3.5 h-3.5 text-red-600 shrink-0 mt-0.5" />
                    )}
                    <div className="min-w-0">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5">Leitura executiva</p>
                      <p className="text-xs text-slate-700 leading-relaxed line-clamp-3" title={insights.narrative}>{insights.narrative}</p>
                    </div>
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">Composição do desvio</p>
                  <div className="space-y-1.5">
                    {[
                      { label: "Alterações", value: insights.impactAlt, pct: insights.pctImpactAlt, color: "bg-slate-500" },
                      { label: "Inclusões", value: insights.impactInc, pct: insights.pctImpactInc, color: "bg-sky-500" },
                      { label: "Exclusões", value: insights.impactExc, pct: insights.pctImpactExc, color: "bg-amber-500" },
                    ].map((row) => (
                      <div key={row.label}>
                        <div className="flex justify-between text-[11px] mb-0.5">
                          <span className="text-slate-600">{row.label} · {(row.pct * 100).toFixed(0)}%</span>
                          <span className={`font-semibold tabular-nums ${rowVarClass(row.value)}`}>
                            {row.value > 0 ? "+" : ""}{fmtValorExib(row.value)}
                          </span>
                        </div>
                        <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${row.color}`} style={{ width: `${Math.min(100, row.pct * 100)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="shrink-0 flex flex-wrap gap-1">
                {[
                  { label: "Linhas", value: String(insights.counts.totalLinhas), hint: `${insights.counts.comDesvio} c/ desvio` },
                  { label: "Favoráveis", value: String(insights.counts.favoravel), hint: fmtValorExib(insights.saldoFavoravel), tone: "emerald" },
                  { label: "Desfavoráveis", value: String(insights.counts.desfavoravel), hint: fmtValorExib(insights.saldoDesfavoravel), tone: "red" },
                  { label: "Inclusões", value: String(insights.counts.inclusoes), hint: fmtValorExib(insights.impactInc) },
                  { label: "Exclusões", value: String(insights.counts.exclusoes), hint: fmtValorExib(insights.impactExc) },
                  { label: "Alterações", value: String(insights.counts.alteracoes), hint: fmtValorExib(insights.impactAlt) },
                  { label: "Top 5", value: `${(insights.concentracaoTop5 * 100).toFixed(0)}%`, hint: "desvio abs." },
                  { label: "Top 10", value: `${(insights.concentracaoTop10 * 100).toFixed(0)}%`, hint: "desvio abs." },
                ].map((chip) => (
                  <div
                    key={chip.label}
                    title={chip.hint}
                    className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] ${
                      chip.tone === "emerald" ? "border-emerald-200 bg-emerald-50/60" :
                      chip.tone === "red" ? "border-red-200 bg-red-50/60" :
                      "border-slate-200 bg-slate-50/80"
                    }`}
                  >
                    <span className="font-semibold text-slate-500 uppercase tracking-wide text-[10px]">{chip.label}</span>
                    <span className="font-bold text-slate-800 tabular-nums">{chip.value}</span>
                  </div>
                ))}
              </div>

              {desvioPorMes.length > 0 && (
                <div className="shrink-0">
                  <ComparativoDesvioMensalStrip
                    meses={desvioPorMes}
                    formatVal={fmtValorExib}
                    onMesClick={() => abrirAnalitico({ view: "destaques", modo: "mes" })}
                  />
                </div>
              )}

              <div className="grid grid-cols-1 xl:grid-cols-3 gap-1.5 shrink-0">
                <div className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 shadow-sm flex flex-col">
                  <div className="flex items-center gap-1.5 mb-1.5 shrink-0">
                    <Target className="w-3.5 h-3.5 text-slate-500" />
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Pontos de atenção</p>
                  </div>
                  {insights.alertas.length > 0 ? (
                    <div className="space-y-1">
                      {insights.alertas.slice(0, 3).map((a, i) => (
                        <div
                          key={i}
                          className={`rounded-md border px-2 py-1 text-[11px] leading-snug ${
                            a.tone === "red" ? "border-red-200 bg-red-50/60 text-red-900" : "border-amber-200 bg-amber-50/60 text-amber-900"
                          }`}
                        >
                          <p className="font-semibold text-[10px] uppercase tracking-wide">{a.title}</p>
                          <p className="mt-0.5 opacity-90 line-clamp-2" title={a.detail}>{a.detail}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">Nenhum alerta crítico.</p>
                  )}
                </div>

                <div className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 shadow-sm flex flex-col">
                  <div className="flex items-center justify-between gap-2 mb-1.5 shrink-0">
                    <div className="flex items-center gap-1.5">
                      <TrendingUp className="w-3.5 h-3.5 text-slate-500" />
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Top drivers (linha)</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => tipo === "DESPESAS" ? irParaDespesasExterno() : abrirAnalitico({ view: "destaques" })}
                      className="text-[10px] font-semibold text-ml-green hover:underline"
                    >
                      Ver todos →
                    </button>
                  </div>
                  <div className="space-y-1">
                    {insights.allItems.slice(0, 5).map((item, i) => {
                      const prodId = item.versao_a?.produto_id ?? item.produto_id;
                      const planoId = item.versao_a?.plano_financeiro_id ?? item.plano_financeiro_id;
                      const label = `${getProdNome(prodId)} · ${getPlanoNome(planoId)}`;
                      return (
                        <ComparativoDriverBar
                          key={i}
                          compact
                          label={label}
                          varRs={item.varRs}
                          shareAbs={item.shareAbs || 0}
                          favoravel={item.favoravel}
                          formatVal={fmtValorExib}
                          onClick={() => {
                            if (tipo === "DESPESAS") {
                              irParaDespesasExterno({
                                produto: prodId,
                                plano: planoId,
                                expand: Boolean(planoId),
                              });
                            } else {
                              abrirAnalitico({ view: "destaques", busca: String(getProdNome(prodId)).slice(0, 20) });
                            }
                          }}
                        />
                      );
                    })}
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 shadow-sm grid grid-cols-2 gap-2">
                  <div>
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Layers className="w-3.5 h-3.5 text-slate-500" />
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Por produto</p>
                    </div>
                    <div className="space-y-1">
                      {insights.topProdutos.slice(0, 3).map((p) => (
                        <ComparativoDriverBar
                          key={String(p.key)}
                          compact
                          label={p.label}
                          varRs={p.varRs}
                          shareAbs={p.shareAbs}
                          favoravel={isVariacaoFavoravel(p.varRs, tipo)}
                          formatVal={fmtValorExib}
                          onClick={() => {
                            if (tipo === "DESPESAS") {
                              irParaDespesasExterno({ produto: Number(p.key) });
                            } else {
                              abrirAnalitico({ busca: p.label.slice(0, 24) });
                            }
                          }}
                        />
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">Por plano</p>
                    <div className="space-y-1">
                      {insights.topPlanos.slice(0, 3).map((p) => (
                        <ComparativoDriverBar
                          key={String(p.key)}
                          compact
                          label={p.label}
                          varRs={p.varRs}
                          shareAbs={p.shareAbs}
                          favoravel={isVariacaoFavoravel(p.varRs, tipo)}
                          formatVal={fmtValorExib}
                          onClick={() => {
                            if (tipo === "DESPESAS") {
                              irParaDespesasExterno({ plano: Number(p.key), expand: true });
                            } else {
                              abrirAnalitico({ busca: p.label.slice(0, 24) });
                            }
                          }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="shrink-0 rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-3 py-2 flex flex-wrap items-center justify-between gap-2">
                <p className="text-[11px] text-slate-600">
                  {tipo === "DESPESAS"
                    ? "Detalhe transacional de Contas a Pagar nos analíticos e ledger CP."
                    : "Precisa do detalhe linha a linha? Use a visão analítica com busca, filtros e exportação."}
                </p>
                {tipo === "DESPESAS" ? (
                  <OrcamentoDeepLinks
                    variant="menu"
                    params={{ ano, modo: "orcado", meses: linkMeses }}
                  />
                ) : (
                  <button
                    type="button"
                    onClick={() => abrirAnalitico({ view: "destaques" })}
                    className="text-xs font-semibold text-ml-green hover:underline flex items-center gap-1 shrink-0"
                  >
                    Abrir analítica
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          ) : (
          <div className="flex-1 min-h-0 flex flex-col rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
            <div className="shrink-0 flex flex-wrap items-center gap-2 px-2 py-2 border-b border-slate-200 bg-slate-50/80">
              <div className="flex items-center gap-1 overflow-x-auto">
                {resultTabs.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setResultView(t.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                      resultView === t.id
                        ? "bg-white text-slate-800 shadow-sm border border-slate-200"
                        : "text-slate-500 hover:text-slate-700 hover:bg-white/60"
                    }`}
                  >
                    {t.label}
                    {t.count > 0 && (
                      <span className={`ml-1.5 tabular-nums ${resultView === t.id ? "text-slate-500" : "text-slate-400"}`}>
                        ({t.count})
                      </span>
                    )}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap items-center gap-2 ml-auto">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="search"
                    value={buscaAnalitica}
                    onChange={(e) => setBuscaAnalitica(e.target.value)}
                    placeholder="Buscar produto ou plano…"
                    className="pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg bg-white w-[180px] sm:w-[220px] focus:outline-none focus:ring-2 focus:ring-ml-green/30"
                  />
                </div>
                <select
                  value={materialidade}
                  onChange={(e) => setMaterialidade(e.target.value as typeof materialidade)}
                  className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white text-slate-700"
                >
                  <option value="todos">Toda materialidade</option>
                  <option value="relevante">Peso ≥ 1%</option>
                  <option value="alto">Peso ≥ 5%</option>
                </select>
                <div className="flex items-center gap-1 border border-slate-200 rounded-lg p-0.5 bg-white">
                  <button
                    type="button"
                    onClick={() => setAnaliticoModo("total")}
                    className={`px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                      analiticoModo === "total" ? "bg-slate-100 text-slate-800" : "text-slate-500 hover:bg-slate-50"
                    }`}
                  >
                    Total
                  </button>
                  <button
                    type="button"
                    onClick={() => setAnaliticoModo("mes")}
                    className={`px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                      analiticoModo === "mes" ? "bg-slate-100 text-slate-800" : "text-slate-500 hover:bg-slate-50"
                    }`}
                  >
                    Por mês
                  </button>
                </div>
                {(resultView === "todas" || resultView === "destaques" || resultView === "alteracoes") && insights.counts.comDesvio > 0 && (
                  <div className="flex items-center gap-1">
                    {(["todos", "favoravel", "desfavoravel"] as const).map((f) => (
                      <button
                        key={f}
                        type="button"
                        onClick={() => setDesvioFilter(f)}
                        className={`px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                          desvioFilter === f
                            ? f === "favoravel" ? "bg-emerald-100 text-emerald-800" :
                              f === "desfavoravel" ? "bg-red-100 text-red-800" :
                              "bg-slate-200 text-slate-800"
                            : "text-slate-500 hover:bg-white"
                        }`}
                      >
                        {f === "todos" ? "Todos" : f === "favoravel" ? "Favorável" : "Desfavorável"}
                      </button>
                    ))}
                  </div>
                )}
                <div className="flex flex-col items-end gap-0.5">
                  <button
                    type="button"
                    onClick={exportarComparativo}
                    title={`Exporta as ${insights.counts.totalLinhas} linhas do comparativo (completo), não só a aba atual`}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-700 border border-slate-200 bg-white hover:bg-slate-50"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Excel completo
                  </button>
                  <span className="text-[10px] text-slate-500 max-w-[230px] text-right leading-tight">
                    Exporta todas as {insights.counts.totalLinhas} linhas — não só o que está na aba
                  </span>
                </div>
              </div>
            </div>

            <div className="flex-1 min-h-0 overflow-auto budget-matrix-scroll">
              {resultView === "todas" && (
                filteredTodas.length > 0 ? (
                  <table className="w-full text-left border-collapse min-w-[880px]">
                    {tableHead({ showTipo: true, porMes: analiticoModo === "mes" })}
                    <tbody>
                      {filteredTodas.map((alt, i) =>
                        renderComparisonRow(alt, i, { showTipo: true, compact: true, porMes: analiticoModo === "mes" })
                      )}
                    </tbody>
                  </table>
                ) : (
                  <p className="p-8 text-center text-sm text-slate-500">Nenhuma linha neste filtro.</p>
                )
              )}

              {resultView === "destaques" && (
                filteredDestaques.length > 0 ? (
                  <table className="w-full text-left border-collapse min-w-[800px]">
                    {tableHead({ rank: true, share: true, porMes: analiticoModo === "mes" })}
                    <tbody>
                      {filteredDestaques.map((alt, i) => renderComparisonRow(alt, i, { rank: i + 1, showShare: true, porMes: analiticoModo === "mes" }))}
                    </tbody>
                  </table>
                ) : (
                  <p className="p-8 text-center text-sm text-slate-500">Nenhum desvio neste filtro.</p>
                )
              )}

              {resultView === "alteracoes" && (
                filteredAlteracoes.length > 0 ? (
                  <table className="w-full text-left border-collapse min-w-[720px]">
                    {tableHead({ porMes: analiticoModo === "mes" })}
                    <tbody>
                      {filteredAlteracoes.map((alt, i) => renderComparisonRow(alt, i, { compact: true, porMes: analiticoModo === "mes" }))}
                    </tbody>
                  </table>
                ) : (
                  <p className="p-8 text-center text-sm text-slate-500">
                    {insights.counts.semMudanca > 0
                      ? `${insights.counts.semMudanca} linha(s) idênticas entre as versões (sem variação).`
                      : "Nenhuma alteração com desvio."}
                  </p>
                )
              )}

              {resultView === "inclusoes" && (
                filteredInclusoes.length > 0 ? (
                  <SectionComparativo
                    title="Itens incluídos na versão comparada"
                    items={filteredInclusoes}
                    getProdNome={getProdNome}
                    getPlanoNome={getPlanoNome}
                    valKey="versao_b"
                    versaoLabel={getNomeVersao(idB)}
                    tipo={tipo}
                    vendasMetric={vendasMetric}
                    formatVal={fmtValorExib}
                  />
                ) : null
              )}

              {resultView === "exclusoes" && (
                filteredExclusoes.length > 0 ? (
                  <SectionComparativo
                    title="Itens presentes só na versão base"
                    items={filteredExclusoes}
                    getProdNome={getProdNome}
                    getPlanoNome={getPlanoNome}
                    valKey="versao_a"
                    versaoLabel={getNomeVersao(idA)}
                    tipo={tipo}
                    vendasMetric={vendasMetric}
                    formatVal={fmtValorExib}
                  />
                ) : null
              )}
            </div>
          </div>
          )}
        </div>
      )}
    </div>
  );
}

function SectionComparativo({
  title,
  items,
  getProdNome,
  getPlanoNome,
  valKey,
  versaoLabel,
  tipo,
  vendasMetric = "vgv",
  formatVal = formatMoeda,
}: {
  title: string;
  items: any[];
  tone?: "neutral";
  getProdNome: (id: number) => any;
  getPlanoNome: (id: number) => any;
  valKey: "versao_a" | "versao_b";
  versaoLabel: string;
  tipo?: string;
  vendasMetric?: VendasComparativoMetric;
  formatVal?: (v: number) => string;
}) {
  return (
    <div className="min-w-[480px]">
      <div className="px-4 py-3 border-b border-slate-100 bg-white sticky top-0 z-10">
        <p className="text-xs font-semibold text-slate-700">{title}</p>
        <p className="text-[10px] text-slate-500 mt-0.5">{items.length} {items.length === 1 ? "linha" : "linhas"} · {versaoLabel}</p>
      </div>
      <table className="w-full text-left border-collapse">
        <thead className="text-[10px] text-slate-500 uppercase tracking-wide bg-slate-50/80">
          <tr>
            <th className="px-4 py-2.5 font-semibold border-b border-slate-200">Produto</th>
            <th className="px-4 py-2.5 font-semibold border-b border-slate-200">Plano</th>
            <th className="px-4 py-2.5 text-right font-semibold border-b border-slate-200 min-w-[120px]">Valor</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item: any, i: number) => {
            const val = getComparativoVersaoTotal(item[valKey], vendasMetric, tipo || "DESPESAS");
            const prodId = item.versao_a?.produto_id ?? item.produto_id;
            const planoId = item.versao_a?.plano_financeiro_id ?? item.plano_financeiro_id;
            return (
              <tr key={i} className="hover:bg-slate-50/80 border-b border-slate-100 transition-colors">
                <td className="px-4 py-2.5 font-medium text-slate-800 text-sm">{getProdNome(prodId)}</td>
                <td className="px-4 py-2.5 text-slate-500 text-sm">{getPlanoNome(planoId)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums font-semibold text-slate-800 text-sm">{formatVal(val)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}


// ============================================================================
// TABS E VISUALIZAÇÃO
// ============================================================================

type VendasVisMetric = "vgv" | "unidades";
type VendasVisCategoria = "vendas" | "distratos";

const VIS_VENDAS_BLOCO = {
  vendas: { label: "Vendas", accent: "border-emerald-200/60 bg-emerald-50", head: "bg-emerald-50", dot: "bg-emerald-500" },
  distratos: { label: "Distratos", accent: "border-red-200/60 bg-red-50", head: "bg-red-50", dot: "bg-red-400" },
  liquido: { label: "VGV líquido", accent: "border-amber-200/60 bg-amber-50", head: "bg-amber-50", dot: "bg-amber-500" },
} as const;

function mergeVendasLiquidoPivot(vendasItems: any[], distratosItems: any[], mesesStr: string[]) {
  const map = new Map<string, any>();
  const ensure = (item: any) => {
    const key = `${item.produto_id}-${item.plano_venda_id}`;
    if (!map.has(key)) {
      map.set(key, {
        produto_id: item.produto_id,
        produto_nome: item.produto_nome,
        plano_venda_id: item.plano_venda_id,
        plano_venda_nome: item.plano_venda_nome,
        total: 0,
      });
    }
    return map.get(key)!;
  };
  const apply = (item: any, sign: 1 | -1) => {
    const entry = ensure(item);
    for (const m of mesesStr) {
      entry[m] = (entry[m] || 0) + sign * Number(item[m] || 0);
    }
    entry.total += sign * Number(item.total || 0);
  };
  for (const item of vendasItems) apply(item, 1);
  for (const item of distratosItems) apply(item, -1);
  return Array.from(map.values());
}

function pivotVendasVisualizacao(
  itens: any[],
  categoria: VendasVisCategoria,
  metric: VendasVisMetric,
) {
  const map = new Map<string, any>();
  for (const item of itens) {
    const isDistrato = Boolean(item.is_distrato);
    if (categoria === "distratos" ? !isDistrato : isDistrato) continue;
    const key = `${item.produto_id}-${item.plano_venda_id}`;
    if (!map.has(key)) {
      map.set(key, {
        produto_id: item.produto_id,
        produto_nome: item.produto_nome,
        plano_venda_id: item.plano_venda_id,
        plano_venda_nome: item.plano_venda_nome,
        total: 0,
      });
    }
    const entry = map.get(key)!;
    const mStr = typeof item.mes === "number" ? MESES_STR[item.mes - 1] : String(item.mes).toLowerCase();
    const raw = metric === "vgv" ? Number(item.vgv || 0) : Number(item.numero_vendas || 0);
    const val = categoria === "distratos" ? Math.abs(raw) : raw;
    entry[mStr] = (entry[mStr] || 0) + val;
    entry.total += val;
  }
  return Array.from(map.values());
}

function groupVisualizacaoByProduto(items: any[], opcoesProdutos: any[]) {
  const groups = new Map<number, { produto_id: number; produto_nome: string; items: any[] }>();
  for (const item of items) {
    const pid = item.produto_id;
    const prodInfo = opcoesProdutos?.find((p: any) => p.id === pid);
    const nome = item.produto_nome || prodInfo?.nome || String(pid);
    if (!groups.has(pid)) {
      groups.set(pid, { produto_id: pid, produto_nome: nome, items: [] });
    }
    groups.get(pid)!.items.push(item);
  }
  for (const g of groups.values()) {
    g.items.sort((a, b) => {
      const plA = a.plano_financeiro_nome || a.plano_venda_nome || "";
      const plB = b.plano_financeiro_nome || b.plano_venda_nome || "";
      return plA.localeCompare(plB, "pt-BR");
    });
  }
  return Array.from(groups.values()).sort((a, b) =>
    a.produto_nome.localeCompare(b.produto_nome, "pt-BR"),
  );
}

function TabVisualizacao({ ano, consolidado, deptId, filtros, holdingMldu, onDataLoaded }: { ano: number; consolidado: boolean; deptId: number; filtros: any; holdingMldu: boolean; onDataLoaded?: (data: any) => void }) {
  const [tipo, setTipo] = useState("DESPESAS");
  const [data, setData] = useState<any>({ itens: [], versoes: [] });
  const [loading, setLoading] = useState(false);
  const [versaoSelecionada, setVersaoSelecionada] = useState("");
  const [vendasVisMetric, setVendasVisMetric] = useState<VendasVisMetric>("vgv");

  useEffect(() => {
    setLoading(true);
    orcamentoService.getVisualizacao(ano, deptId, tipo, consolidado, versaoSelecionada, holdingMldu)
      .then((res) => {
        const payload = res || { itens: [], versoes: [] };
        setData(payload);
        if (onDataLoaded && res) onDataLoaded(res);
        const versoes = payload.versoes || [];
        const stillValid = versaoSelecionada && versoes.some((v: any) => v.id === versaoSelecionada);
        if (!stillValid) {
          const fromApi = payload.versao_selecionada;
          const fallback = versoes.find((v: any) => v.id === fromApi)?.id ?? versoes[0]?.id ?? "";
          setVersaoSelecionada(fallback);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [ano, tipo, consolidado, deptId, versaoSelecionada, holdingMldu]);

  const itensFiltrados = useMemo(() => {
    return (data.itens || []).filter((item: any) => {
      const prodInfo = data.opcoes_produtos?.find((p: any) => p.id === item.produto_id) || {};
      const planoIdField = item.plano_financeiro_id || item.plano_venda_id;
      const planoInfo = data.opcoes_planos?.find((p: any) => p.id === planoIdField) || {};
      const baseInfo = (filtros?.centrosCustoBase || []).find((cc: any) => cc.db_id === item.produto_id) || {};
      const idSienge = baseInfo.id ? String(baseInfo.id) : String(prodInfo.id_sienge || prodInfo.id || "");
      const produtoNome = parseCentroNome(prodInfo.nome || "").produto || "";
      const planoNome = planoInfo.nome || item.plano_financeiro_nome || item.plano_venda_nome || "";
      const empresaId = String(baseInfo.id_empresa || prodInfo.id_empresa || "");
      const nomeEmpresa = prodInfo.nome_empresa || "";
      
      if (filtros?.busca) {
        if (!(prodInfo.nome || "").toLowerCase().includes(filtros.busca.toLowerCase()) && 
            !(item.descricao || "").toLowerCase().includes(filtros.busca.toLowerCase())) {
          return false;
        }
      }
      
      if (filtros?.idCentroCusto?.length > 0 && !filtros.idCentroCusto.includes(idSienge)) return false;
      if (filtros?.produtoFiltro?.length > 0 && !filtros.produtoFiltro.includes(produtoNome)) return false;
      if (filtros?.planoFinanceiro?.length > 0 && !filtros.planoFinanceiro.includes(planoNome)) return false;
      if (filtros?.idEmpresa?.length > 0 && !filtros.idEmpresa.includes(empresaId)) return false;
      return true;
    });
  }, [data.itens, data.opcoes_produtos, data.opcoes_planos, filtros]);

  const visibleMeses = MESES.filter(
    (m) => !filtros?.filtroMesesAtivo || filtros.mesesSelecionados.includes(m),
  );
  const visibleMesesStr = visibleMeses.map((m) => m.toLowerCase());

  const vendasPivot = useMemo(() => {
    if (tipo !== "VENDAS") return null;
    const vendas = pivotVendasVisualizacao(itensFiltrados, "vendas", vendasVisMetric);
    const distratos = pivotVendasVisualizacao(itensFiltrados, "distratos", vendasVisMetric);
    return {
      vendas,
      distratos,
      liquido: mergeVendasLiquidoPivot(vendas, distratos, visibleMesesStr),
    };
  }, [itensFiltrados, tipo, vendasVisMetric, visibleMesesStr]);

  const finalItems = useMemo(() => {
    if (tipo === "VENDAS") {
      return [
        ...(vendasPivot?.vendas ?? []),
        ...(vendasPivot?.distratos ?? []),
        ...(vendasPivot?.liquido ?? []),
      ];
    }
    return itensFiltrados;
  }, [tipo, vendasPivot, itensFiltrados]);

  const [expandedProducts, setExpandedProducts] = useState<Record<string, boolean>>({});

  const groupedByProduto = useMemo(() => {
    if (tipo === "VENDAS") return [];
    return groupVisualizacaoByProduto(finalItems, data.opcoes_produtos || []);
  }, [finalItems, data.opcoes_produtos, tipo]);

  const groupedVendas = useMemo(() => {
    if (tipo !== "VENDAS") return [];
    return groupVisualizacaoByProduto(vendasPivot?.vendas ?? [], data.opcoes_produtos || []);
  }, [tipo, vendasPivot, data.opcoes_produtos]);

  const groupedDistratos = useMemo(() => {
    if (tipo !== "VENDAS") return [];
    return groupVisualizacaoByProduto(vendasPivot?.distratos ?? [], data.opcoes_produtos || []);
  }, [tipo, vendasPivot, data.opcoes_produtos]);

  const groupedLiquido = useMemo(() => {
    if (tipo !== "VENDAS") return [];
    return groupVisualizacaoByProduto(vendasPivot?.liquido ?? [], data.opcoes_produtos || []);
  }, [tipo, vendasPivot, data.opcoes_produtos]);

  const sumGroupMonth = (items: any[], mes: string) =>
    items.reduce((s, it) => s + (Number(it[mes]) || 0), 0);
  const sumGroupTotal = (items: any[]) =>
    items.reduce((s, it) => s + (Number(it.total) || 0), 0);

  const getPlanoLabel = (item: any) =>
    item.plano_financeiro_nome || item.plano_venda_nome || item.plano_financeiro_id || item.plano_venda_id || "—";

  const formatVisValor = (val: number) => {
    if (tipo === "VENDAS" && vendasVisMetric === "unidades") {
      return Number(val).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
    }
    return formatMoeda(val);
  };

  const toggleProduct = (expandKey: string) => {
    setExpandedProducts((prev) => ({
      ...prev,
      [expandKey]: prev[expandKey] === false,
    }));
  };

  const isProductExpanded = (expandKey: string) => expandedProducts[expandKey] !== false;

  const colCount = 2 + visibleMeses.length + 1;

  const buildGrandTotals = (groups: { items: any[] }[]) => {
    const byMonth: Record<string, number> = {};
    for (const m of visibleMesesStr) {
      byMonth[m] = groups.reduce((s, g) => s + sumGroupMonth(g.items, m), 0);
    }
    const total = groups.reduce((s, g) => s + sumGroupTotal(g.items), 0);
    return { byMonth, total };
  };

  const grandTotals = useMemo(
    () => buildGrandTotals(groupedByProduto),
    [groupedByProduto, visibleMesesStr],
  );

  const grandTotalsVendas = useMemo(
    () => buildGrandTotals(groupedVendas),
    [groupedVendas, visibleMesesStr],
  );

  const grandTotalsDistratos = useMemo(
    () => buildGrandTotals(groupedDistratos),
    [groupedDistratos, visibleMesesStr],
  );

  const grandTotalsLiquido = useMemo(
    () => buildGrandTotals(groupedLiquido),
    [groupedLiquido, visibleMesesStr],
  );

  const exportarExcel = () => {
    const headers = ["Produto", "Plano", ...visibleMeses, "Total"];
    if (tipo === "VENDAS") {
      const metricLabel = vendasVisMetric === "vgv" ? "VGV" : "N_lotes";
      const rows: (string | number)[][] = [];
      const appendBloco = (label: string, items: any[]) => {
        if (items.length === 0) return;
        rows.push([label, "", ...visibleMeses.map(() => ""), ""]);
        for (const item of items) {
          rows.push([
            item.produto_nome || item.produto_id,
            getPlanoLabel(item),
            ...visibleMesesStr.map((m) => item[m] || 0),
            item.total || 0,
          ]);
        }
      };
      appendBloco("VENDAS", vendasPivot?.vendas ?? []);
      appendBloco("DISTRATOS", vendasPivot?.distratos ?? []);
      appendBloco("VGV LIQUIDO", vendasPivot?.liquido ?? []);
      exportDataToExcel(headers, rows, `visualizacao_VENDAS_${metricLabel}_${ano}.xlsx`);
      return;
    }
    const rows = finalItems.map((item: any) => [
      item.produto_nome || item.produto_id,
      getPlanoLabel(item),
      ...visibleMesesStr.map((m) => item[m] || 0),
      item.total || 0,
    ]);
    exportDataToExcel(headers, rows, `visualizacao_${tipo}_${ano}.xlsx`);
  };

  const tipoAccent =
    tipo === "DESPESAS"
      ? "border-brand-200/60 bg-brand-50"
      : tipo === "RECEITAS"
        ? "border-emerald-200/60 bg-emerald-50"
        : "border-amber-200/60 bg-amber-50";

  const stickyGroupBg =
    tipo === "DESPESAS" ? "bg-brand-50" : tipo === "RECEITAS" ? "bg-emerald-50" : "bg-amber-50";

  const stickyHeadTop = "bg-slate-100 sticky top-0 z-30 shadow-[0_1px_0_0_#e2e8f0]";
  const stickyCol1Head = "px-4 py-3 font-semibold sticky left-0 top-0 z-40 bg-slate-100 min-w-[220px] shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]";
  const stickyCol2Head = "px-4 py-3 font-semibold sticky left-[220px] top-0 z-40 bg-slate-100 min-w-[180px] shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]";
  const stickyCol1Detail = "sticky left-0 z-10 bg-white group-hover:bg-slate-50 min-w-[220px] shadow-[2px_0_5px_-2px_rgba(0,0,0,0.08)]";
  const stickyCol2Detail =
    "px-4 py-2 text-xs text-slate-600 sticky left-[220px] z-10 bg-white group-hover:bg-slate-50 min-w-[180px] pl-6 border-l-2 border-l-slate-200 group-hover:border-l-brand-400 transition-colors shadow-[2px_0_5px_-2px_rgba(0,0,0,0.08)]";

  const renderProdutoGroupsBody = (opts: {
    groups: { produto_id: number; produto_nome: string; items: any[] }[];
    expandPrefix: string;
    accentClass: string;
    rowBgClass: string;
    totals: { byMonth: Record<string, number>; total: number };
    valueTone?: "default" | "distrato" | "liquido";
  }) => {
    const { groups, expandPrefix, accentClass, rowBgClass, totals, valueTone = "default" } = opts;
    const col1Group = `px-4 py-2.5 font-semibold text-sm text-slate-800 sticky left-0 z-20 ${rowBgClass} min-w-[220px] shadow-[2px_0_5px_-2px_rgba(0,0,0,0.08)]`;
    const col2Group = `px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500 sticky left-[220px] z-20 ${rowBgClass} min-w-[180px] shadow-[2px_0_5px_-2px_rgba(0,0,0,0.08)]`;
    const cellToneClass = (val: number, strong = false) => {
      if (valueTone === "distrato") return "text-red-700";
      if (valueTone === "liquido" && val < 0) return "text-red-700";
      return strong ? "text-slate-800" : "text-slate-600";
    };

    if (groups.length === 0) {
      return (
        <tr>
          <td colSpan={colCount} className="px-4 py-8 text-center text-slate-400 text-sm">
            Nenhum registro neste bloco.
          </td>
        </tr>
      );
    }

    return (
      <>
        {groups.map((group) => {
          const expandKey = `${expandPrefix}${group.produto_id}`;
          const expanded = isProductExpanded(expandKey);
          const subtotal = sumGroupTotal(group.items);
          return (
            <Fragment key={expandKey}>
              <tr
                className={`cursor-pointer border-t-2 ${accentClass} hover:brightness-[0.98] transition-colors`}
                onClick={() => toggleProduct(expandKey)}
              >
                <td className={col1Group}>
                  <div className="flex items-start gap-2">
                    {expanded
                      ? <ChevronDown className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                      : <ChevronRight className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />}
                    <span className="leading-snug">{group.produto_nome}</span>
                  </div>
                </td>
                <td className={col2Group}>
                  Subtotal · {group.items.length} {group.items.length === 1 ? "plano" : "planos"}
                </td>
                {visibleMesesStr.map((m) => {
                  const val = sumGroupMonth(group.items, m);
                  return (
                    <td key={m} className={`px-3 py-2.5 text-right tabular-nums text-sm font-semibold ${rowBgClass} ${cellToneClass(val, true)}`}>
                      {formatVisValor(val)}
                    </td>
                  );
                })}
                <td className={`px-3 py-2.5 text-right tabular-nums font-bold text-sm border-l border-slate-200 ${rowBgClass} ${cellToneClass(subtotal, true)}`}>
                  {formatVisValor(subtotal)}
                </td>
              </tr>
              {expanded && group.items.map((item, ri) => (
                <tr
                  key={`${expandKey}-${ri}`}
                  className="group border-b border-slate-100 bg-white hover:bg-slate-50/80 transition-colors"
                >
                  <td className={stickyCol1Detail} />
                  <td className={stickyCol2Detail}>
                    {getPlanoLabel(item)}
                  </td>
                  {visibleMesesStr.map((m) => {
                    const val = Number(item[m]) || 0;
                    return (
                      <td key={m} className={`px-3 py-2 text-right tabular-nums text-sm ${cellToneClass(val)}`}>
                        {formatVisValor(val)}
                      </td>
                    );
                  })}
                  <td className={`px-3 py-2 text-right tabular-nums text-sm font-semibold border-l border-slate-200 ${cellToneClass(item.total || 0, true)}`}>
                    {formatVisValor(item.total || 0)}
                  </td>
                </tr>
              ))}
              <tr aria-hidden="true">
                <td colSpan={colCount} className="h-1.5 bg-slate-100/80 p-0 border-none" />
              </tr>
            </Fragment>
          );
        })}
        {groups.length > 1 && (
          <tr className="bg-slate-100 border-t-2 border-slate-300">
            <td className="px-4 py-3 font-bold text-sm text-slate-800 sticky left-0 z-20 bg-slate-100 min-w-[220px] shadow-[2px_0_5px_-2px_rgba(0,0,0,0.08)]">
              Total do bloco
            </td>
            <td className="px-4 py-3 text-xs font-medium text-slate-500 sticky left-[220px] z-20 bg-slate-100 min-w-[180px] shadow-[2px_0_5px_-2px_rgba(0,0,0,0.08)]">
              {groups.length} produtos
            </td>
            {visibleMesesStr.map((m) => {
              const val = totals.byMonth[m] || 0;
              return (
              <td key={m} className={`px-3 py-3 text-right tabular-nums font-bold text-sm ${cellToneClass(val, true)}`}>
                {formatVisValor(val)}
              </td>
            );})}
            <td className={`px-3 py-3 text-right tabular-nums font-bold text-sm border-l border-slate-300 ${cellToneClass(totals.total, true)}`}>
              {formatVisValor(totals.total)}
            </td>
          </tr>
        )}
      </>
    );
  };

  const produtoCount = tipo === "VENDAS"
    ? new Set([...groupedVendas, ...groupedDistratos, ...groupedLiquido].map((g) => g.produto_id)).size
    : groupedByProduto.length;
  const linhaCount = tipo === "VENDAS" ? finalItems.length : finalItems.length;
  const hasData = tipo === "VENDAS"
    ? groupedVendas.length > 0 || groupedDistratos.length > 0
    : groupedByProduto.length > 0;

  const tableHead = (
    <thead className="text-xs text-slate-700 uppercase">
      <tr>
        <th className={stickyCol1Head}>Produto</th>
        <th className={stickyCol2Head}>Plano</th>
        {visibleMeses.map((m) => (
          <th key={m} className={`px-3 py-3 text-right font-semibold min-w-[88px] ${stickyHeadTop}`}>{m}</th>
        ))}
        <th className={`px-3 py-3 text-right font-semibold min-w-[100px] border-l border-slate-200 ${stickyHeadTop}`}>
          Total
        </th>
      </tr>
    </thead>
  );

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden gap-3">
      <div className="flex items-center gap-3 flex-wrap shrink-0">
        <select
          value={tipo}
          onChange={(e) => { setTipo(e.target.value); setVersaoSelecionada(""); }}
          className="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700"
        >
          <option value="DESPESAS">Despesas</option>
          <option value="RECEITAS">Receitas</option>
          <option value="VENDAS">Vendas</option>
        </select>
        {data.versoes && data.versoes.length > 0 && (
          <select
            value={versaoSelecionada}
            onChange={(e) => setVersaoSelecionada(e.target.value)}
            className="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700 min-w-[200px]"
          >
            {data.versoes.map((v: any) => (
              <option key={v.id} value={v.id}>{v.descricao}</option>
            ))}
          </select>
        )}
        {tipo === "VENDAS" && (
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5">
            <button
              type="button"
              onClick={() => setVendasVisMetric("vgv")}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                vendasVisMetric === "vgv" ? "bg-white text-slate-800 shadow-sm border border-slate-200" : "text-slate-500 hover:bg-white"
              }`}
            >
              VGV
            </button>
            <button
              type="button"
              onClick={() => setVendasVisMetric("unidades")}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                vendasVisMetric === "unidades" ? "bg-white text-slate-800 shadow-sm border border-slate-200" : "text-slate-500 hover:bg-white"
              }`}
            >
              Nº lotes
            </button>
          </div>
        )}
        {hasData && (
          <span className="text-xs text-slate-500">
            {produtoCount} produto{produtoCount !== 1 ? "s" : ""} · {linhaCount} linha{linhaCount !== 1 ? "s" : ""}
            {tipo === "VENDAS" && " · Vendas, distratos e líquido"}
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={exportarExcel}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"
          >
            <FileSpreadsheet className="w-4 h-4 text-brand-green" /> Excel
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-auto border border-slate-200 rounded-lg budget-matrix-scroll">
        {loading ? (
          <AppLoadingState />
        ) : tipo === "VENDAS" ? (
          !hasData ? (
            <div className="px-4 py-12 text-center text-slate-500">
              Nenhum dado encontrado para os filtros selecionados.
            </div>
          ) : (
          <div className="flex flex-col gap-5 p-1 min-w-max">
            {(["vendas", "distratos", "liquido"] as const).map((cat) => {
              const bloco = VIS_VENDAS_BLOCO[cat];
              const groups = cat === "vendas" ? groupedVendas : cat === "distratos" ? groupedDistratos : groupedLiquido;
              const totals = cat === "vendas" ? grandTotalsVendas : cat === "distratos" ? grandTotalsDistratos : grandTotalsLiquido;
              return (
                <div key={cat} className="border border-slate-200 rounded-lg overflow-hidden">
                  <div className={`flex items-center gap-2 px-4 py-2 border-b ${bloco.accent}`}>
                    <span className={`w-2 h-2 rounded-full ${bloco.dot}`} />
                    <span className="text-sm font-semibold text-slate-800">{bloco.label}</span>
                    <span className="text-xs text-slate-500">
                      {vendasVisMetric === "vgv" ? "VGV" : "Nº de lotes"}
                      {cat === "liquido" ? " (vendas − distratos)" : ""}
                    </span>
                  </div>
                  <table className="w-full text-left border-collapse min-w-max">
                    {tableHead}
                    <tbody>
                      {renderProdutoGroupsBody({
                        groups,
                        expandPrefix: `${cat}-`,
                        accentClass: bloco.accent,
                        rowBgClass: bloco.head,
                        totals,
                        valueTone: cat === "distratos" ? "distrato" : cat === "liquido" ? "liquido" : "default",
                      })}
                    </tbody>
                  </table>
                </div>
              );
            })}
          </div>
          )
        ) : (
          <table className="w-full text-left border-collapse min-w-max">
            {tableHead}
            <tbody>
              {groupedByProduto.length === 0 ? (
                <tr>
                  <td colSpan={colCount} className="px-4 py-12 text-center text-slate-500">
                    Nenhum dado encontrado para os filtros selecionados.
                  </td>
                </tr>
              ) : (
                renderProdutoGroupsBody({
                  groups: groupedByProduto,
                  expandPrefix: "",
                  accentClass: tipoAccent,
                  rowBgClass: stickyGroupBg,
                  totals: grandTotals,
                })
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default function RealizadoPage() {
  const { user } = useAuth();
  const deptId = useActiveDepartmentId();
  const { holdingMldu, setHoldingMldu, canUseHoldingMldu } = useHoldingMldu("orcamento");
  const currentYear = new Date().getFullYear();
  const [ano, setAno] = useState<number>(currentYear);
  const [anosDisponiveis, setAnosDisponiveis] = useState<number[]>([]);
  const [loadingAnos, setLoadingAnos] = useState(true);
  const [holdingAvisos, setHoldingAvisos] = useState<any>(undefined);

  // Tabs
  const [tab, setTab] = useState<"consolidado" | "despesas" | "receitas" | "vendas" | "comparativo" | "visualizacao">("consolidado");
  const [visitedTabs, setVisitedTabs] = useState<Set<typeof tab>>(() => new Set(["consolidado"]));
  const selectTab = (id: typeof tab) => {
    setVisitedTabs((prev) => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      return next;
    });
    setTab(id);
  };

  // Filtros Globais
  const [filtroMesesAtivo, setFiltroMesesAtivo] = useState(false);
  const [mesesSelecionados, setMesesSelecionados] = useState<string[]>(MESES);
  
  const [busca, setBusca] = useState("");
  const [idCentroCusto, setIdCentroCusto] = useState<string[]>([]);
  const [produtoFiltro, setProdutoFiltro] = useState<string[]>([]);
  const [planoFinanceiro, setPlanoFinanceiro] = useState<string[]>([]);
  const [filtroEmpresaIds, setFiltroEmpresaIds] = useState<string[]>([]);

  const patchGridFilters = (patch: Partial<MonthlyGridFilterValues>) => {
    if (patch.busca !== undefined) setBusca(patch.busca);
    if (patch.filtroIdCentro !== undefined) setIdCentroCusto(patch.filtroIdCentro);
    if (patch.filtroProduto !== undefined) setProdutoFiltro(patch.filtroProduto);
    if (patch.filtroPlano !== undefined) setPlanoFinanceiro(patch.filtroPlano);
    if (patch.filtroEmpresaIds !== undefined) setFiltroEmpresaIds(patch.filtroEmpresaIds);
  };

  const [activeOptions, setActiveOptions] = useState<{centrosId: any[], produtos: any[], planos: any[], empresasId: any[], empresasNome: any[]}>({ centrosId: [], produtos: [], planos: [], empresasId: [], empresasNome: [] });

  const carregarAnos = async () => {
    try {
      setLoadingAnos(true);
      const response = await orcamentoService.getAnosDisponiveis("DESPESAS", deptId, false);
      const anos = response.anos || [];
      setAnosDisponiveis(anos);
      if (anos.length > 0) setAno(anos[anos.length - 1]);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAnos(false);
    }
  };

  useEffect(() => {
    if (!user) return;
    carregarAnos();
  }, [deptId, user]);

  const [baseCC, setBaseCC] = useState<any[]>([]);
  const [empresasMap, setEmpresasMap] = useState<Map<string, string>>(new Map());

  useEffect(() => {
    apoioService.getCentrosCusto().then(setBaseCC).catch(console.error);
    apoioService
      .getEmpresas()
      .then((list) => setEmpresasMap(buildEmpresasMapFromCadastro(list)))
      .catch(console.error);
  }, []);

  const handleDataLoaded = useCallback((data: any) => {
    if (data?.holding_avisos) setHoldingAvisos(data.holding_avisos);
    const itens = data.itens || [...(data.receitas || []), ...(data.despesas || [])];
    if (!itens || itens.length === 0) return;
    const produtosComData = new Set(itens.map((i: any) => i.produto_id));
    const planosComData = new Set(itens.map((i: any) => i.plano_financeiro_id || i.plano_venda_id));

    const produtosAtivos = (data.opcoes_produtos || []).filter((p: any) => produtosComData.has(p.id));
    const planosAtivos = (data.opcoes_planos || []).filter((p: any) => planosComData.has(p.id));

    const centrosId = idsPublicosCentro(
      produtosAtivos.map((p: any) => {
        const cc = baseCC.find((c: any) => c.db_id === p.id);
        return {
          id: p.id,
          id_sienge: p.id_sienge || (cc?.id != null ? String(cc.id) : null),
        };
      }),
    ).sort((a, b) => Number(a) - Number(b));
    const produtos = Array.from(new Set(produtosAtivos.map((p: any) => parseCentroNome(p.nome).produto)));
    const plans = Array.from(new Set(planosAtivos.map((p: any) => p.nome)));
    const produtosComEmpresa = produtosAtivos.map((p: any) => {
      const cc = baseCC.find((c: any) => c.db_id === p.id);
      return {
        ...p,
        id_empresa: p.id_empresa || cc?.id_empresa || "",
        nome_empresa: p.nome_empresa || cc?.nome_empresa || "",
      };
    });
    const produtosEnriquecidos = enrichProdutosComEmpresaCadastro(produtosComEmpresa, empresasMap);
    const empresas = buildEmpresaLinkedOptions(produtosEnriquecidos);

    setActiveOptions({
      centrosId: centrosId.map(id => ({ value: String(id), label: String(id) })),
      produtos: produtos.map(p => ({ value: String(p), label: String(p) })),
      planos: plans.map(p => ({ value: String(p), label: String(p) })),
      empresasId: empresas.empresasId,
      empresasNome: empresas.empresasNome,
    });
  }, [baseCC, empresasMap]);

  const toggleMes = (mes: string) => {
    setMesesSelecionados(prev => prev.includes(mes) ? prev.filter(m => m !== mes) : [...prev, mes]);
  };

  const filtrosParams = useMemo(() => ({
    filtroMesesAtivo,
    mesesSelecionados,
    busca,
    idCentroCusto,
    produtoFiltro,
    planoFinanceiro,
    idEmpresa: filtroEmpresaIds,
    centrosCustoBase: baseCC
  }), [filtroMesesAtivo, mesesSelecionados, busca, idCentroCusto, produtoFiltro, planoFinanceiro, filtroEmpresaIds, baseCC]);

  const TABS = [
    { id: "consolidado", label: "Consolidado", icon: BarChart2 },
    { id: "despesas", label: "Despesas", icon: TrendingDown },
    { id: "receitas", label: "Receitas", icon: TrendingUp },
    { id: "vendas", label: "Vendas", icon: DollarSign },
    { id: "comparativo", label: "Comparativo de Versões", icon: GitCompare },
    { id: "visualizacao", label: "Visualização", icon: Eye },
  ] as const;

  return (
    <BudgetMatrixShell
      title="Orçado × Realizado"
      tall
      chrome={
        <>
          {holdingMldu && tab !== "comparativo" ? <HoldingMlduBanner avisos={holdingAvisos} /> : null}
          <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 flex flex-wrap items-end gap-3">
            <BudgetScopeBar
              scope="orcamento"
              holdingMldu={holdingMldu}
              onHoldingMlduChange={setHoldingMldu}
              canUseHoldingMldu={canUseHoldingMldu}
            />
            {loadingAnos ? (
              <span className="text-sm text-slate-500 py-2">Carregando anos…</span>
            ) : (
              <YearSelect value={ano} years={anosDisponiveis} onChange={setAno} />
            )}
            <div className="flex flex-wrap items-end gap-2 min-w-0 flex-1">
              <div className="flex items-center gap-2 pb-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Meses</span>
                {tab === "comparativo" && (
                  <span className="text-[10px] text-slate-400 hidden sm:inline">· recalcula KPIs</span>
                )}
                <button
                  type="button"
                  onClick={() => setFiltroMesesAtivo(!filtroMesesAtivo)}
                  className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${filtroMesesAtivo ? "bg-ml-green" : "bg-slate-300"}`}
                  aria-pressed={filtroMesesAtivo}
                  aria-label="Ativar filtro de meses"
                >
                  <div className={`absolute top-0.5 bottom-0.5 w-4 bg-white rounded-full transition-transform shadow-sm ${filtroMesesAtivo ? "translate-x-5" : "translate-x-0.5"}`} />
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-1 pb-0.5">
                {MESES.map((mes) => {
                  const isSelected = mesesSelecionados.includes(mes);
                  return (
                    <button
                      key={mes}
                      type="button"
                      onClick={() => toggleMes(mes)}
                      disabled={!filtroMesesAtivo}
                      className={`px-1.5 py-0.5 rounded-md border text-[11px] font-medium transition-colors ${!filtroMesesAtivo
                        ? "border-slate-200 text-slate-400 bg-slate-50 cursor-not-allowed opacity-50"
                        : isSelected
                          ? "border-ml-green text-ml-green bg-brand-green/5"
                          : "border-slate-200 text-slate-600 hover:border-slate-300 bg-white"
                        }`}
                    >
                      {mes}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
          <MonthlyGridFilterPanel
            values={{
              busca,
              filtroIdCentro: idCentroCusto,
              filtroProduto: produtoFiltro,
              filtroPlano: planoFinanceiro,
              filtroEmpresaIds,
            }}
            onChange={patchGridFilters}
            opcoesIdCentro={activeOptions.centrosId}
            opcoesProduto={activeOptions.produtos}
            opcoesPlano={activeOptions.planos}
            opcoesEmpresaId={activeOptions.empresasId}
            opcoesEmpresaNome={activeOptions.empresasNome}
            planoLabel={tab === "vendas" ? "Forma de Venda" : "Plano Financeiro"}
          />
        </>
      }
    >
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="flex overflow-x-auto overflow-y-hidden border-b border-slate-200 bg-slate-50 shrink-0">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => selectTab(id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm font-semibold whitespace-nowrap transition-all border-b-2 -mb-px ${tab === id
                ? "text-ml-green border-ml-green bg-white"
                : "text-slate-500 border-transparent hover:text-slate-700 hover:bg-white/50"
                }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        <div className={`flex-1 min-h-0 flex flex-col overflow-hidden ${tab === "comparativo" ? "px-2 pt-2 pb-2" : "px-3 pt-3 pb-3"}`}>
          {visitedTabs.has("consolidado") && (
            <div className={tab === "consolidado" ? "flex-1 min-h-0 flex flex-col overflow-hidden" : "hidden"}>
              <TabConsolidado ano={ano} consolidado={false} deptId={deptId} filtros={filtrosParams} holdingMldu={holdingMldu} onDataLoaded={handleDataLoaded} />
            </div>
          )}
          {visitedTabs.has("despesas") && (
            <div className={tab === "despesas" ? "flex-1 min-h-0 flex flex-col overflow-hidden" : "hidden"}>
              <TabDespesasReceitas tipo="despesas" ano={ano} consolidado={false} deptId={deptId} filtros={filtrosParams} holdingMldu={holdingMldu} onDataLoaded={handleDataLoaded} />
            </div>
          )}
          {visitedTabs.has("receitas") && (
            <div className={tab === "receitas" ? "flex-1 min-h-0 flex flex-col overflow-hidden" : "hidden"}>
              <TabDespesasReceitas tipo="receitas" ano={ano} consolidado={false} deptId={deptId} filtros={filtrosParams} holdingMldu={holdingMldu} onDataLoaded={handleDataLoaded} />
            </div>
          )}
          {visitedTabs.has("vendas") && (
            <div className={tab === "vendas" ? "flex-1 min-h-0 flex flex-col overflow-hidden" : "hidden"}>
              <TabVendas ano={ano} consolidado={false} deptId={deptId} filtros={filtrosParams} holdingMldu={holdingMldu} onDataLoaded={handleDataLoaded} />
            </div>
          )}
          {visitedTabs.has("comparativo") && (
            <div className={tab === "comparativo" ? "flex-1 min-h-0 flex flex-col overflow-hidden" : "hidden"}>
              <TabComparativo ano={ano} deptId={deptId} filtros={filtrosParams} onDataLoaded={handleDataLoaded} />
            </div>
          )}
          {visitedTabs.has("visualizacao") && (
            <div className={tab === "visualizacao" ? "flex-1 min-h-0 flex flex-col overflow-hidden" : "hidden"}>
              <TabVisualizacao ano={ano} consolidado={false} deptId={deptId} filtros={filtrosParams} holdingMldu={holdingMldu} onDataLoaded={handleDataLoaded} />
            </div>
          )}
        </div>
      </div>
    </BudgetMatrixShell>
  );
}
