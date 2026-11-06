"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getDespesasEmpreendimento } from "@/services/orcamentoDespesasEmpreendimento";
import { GROW_TREE_NAME_TH_CLASS, GROW_TREE_PAGE_CLASS, GrowTreeChevron, GrowTreeNameCell, GrowTreeSheet } from "@/components/shared/GrowTreeSheet";
import { useActiveDepartmentId, isDepartmentContextId } from "@/lib/useActiveDepartmentId";
import { OrcamentoFlyoutFilterBar, type OrcamentoModo } from "@/components/orcamento/OrcamentoFlyoutFilterBar";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { useEmpresaCadastroFilter } from "@/hooks/useEmpresaCadastroFilter";
import {
  formatMoedaCompact,
  formatPerc,
  MESES_STR,
} from "@/lib/orcamentoDesvioUi";
import {
  PERIODOS_KPI,
  hintPeriodo,
  legendaPeriodo,
  tituloPeriodo,
} from "@/lib/periodosFpa";
import { varPercDesvio } from "@/lib/semaforoDesvio";
import { DesvioLegend } from "@/components/orcamento/DesvioLegend";
import { PeriodoKpiCard } from "@/components/orcamento/PeriodoKpiCard";
import { SemaforoDesvio } from "@/components/orcamento/SemaforoDesvio";

const MESES_LABEL = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

type Periodo = "ano" | "ytd" | "ytg" | "fy";
type SerieKey = "n" | "n_mldu" | "ref" | "ref_mldu";

type PeriodoVals = {
  n: number;
  n_mldu: number;
  orcado: number;
  orcado_mldu: number;
  forecast: number;
  forecast_mldu: number;
};

type EmpRow = {
  kind: "empresa" | "grupo" | "centro" | "plano";
  id: string;
  codigo: string;
  descricao: string;
  produto_id?: number;
  empresa_id?: string;
  grupo?: string;
  meses_n?: Record<string, number>;
  meses_n_mldu?: Record<string, number>;
  meses_orcado?: Record<string, number>;
  meses_orcado_mldu?: Record<string, number>;
  meses_forecast?: Record<string, number>;
  meses_forecast_mldu?: Record<string, number>;
  total_n?: number;
  total_n_mldu?: number;
  total_orcado?: number;
  total_orcado_mldu?: number;
  total_forecast?: number;
  total_forecast_mldu?: number;
  periodos?: Record<Periodo, PeriodoVals>;
  filhos?: EmpRow[];
};

function moneyClass(v: number) {
  if (v < 0) return "text-red-600";
  if (v > 0) return "text-slate-800";
  return "text-slate-400";
}

function Num({ v }: { v: number }) {
  return <span className={`tabular-nums ${moneyClass(v)}`}>{formatMoedaCompact(v)}</span>;
}

function Perc({ v }: { v: number | null }) {
  if (v == null) return <span className="text-slate-300">—</span>;
  return <span className={`tabular-nums ${v < 0 ? "text-red-600" : "text-slate-700"}`}>{formatPerc(v)}</span>;
}

function refMes(row: EmpRow, modo: OrcamentoModo, mldu: boolean, mes?: string) {
  if (mes) {
    if (modo === "forecast") {
      return mldu ? row.meses_forecast_mldu?.[mes] || 0 : row.meses_forecast?.[mes] || 0;
    }
    return mldu ? row.meses_orcado_mldu?.[mes] || 0 : row.meses_orcado?.[mes] || 0;
  }
  if (modo === "forecast") return mldu ? row.total_forecast_mldu || 0 : row.total_forecast || 0;
  return mldu ? row.total_orcado_mldu || 0 : row.total_orcado || 0;
}

function nMes(row: EmpRow, mldu: boolean, mes?: string) {
  if (mes) return mldu ? row.meses_n_mldu?.[mes] || 0 : row.meses_n?.[mes] || 0;
  return mldu ? row.total_n_mldu || 0 : row.total_n || 0;
}

function serieValue(row: EmpRow, key: SerieKey, modo: OrcamentoModo, mes?: string) {
  if (key === "n") return nMes(row, false, mes);
  if (key === "n_mldu") return nMes(row, true, mes);
  if (key === "ref") return refMes(row, modo, false, mes);
  return refMes(row, modo, true, mes);
}

function flatten(
  rows: EmpRow[],
  expanded: Set<string>,
  indent = 0,
  intoPlanos = false,
): { row: EmpRow; indent: number; hasKids: boolean }[] {
  const out: { row: EmpRow; indent: number; hasKids: boolean }[] = [];
  for (const row of rows) {
    const kids = row.filhos || [];
    const hasKids = intoPlanos ? kids.length > 0 : row.kind !== "centro" && kids.length > 0;
    out.push({ row, indent, hasKids });
    if (hasKids && expanded.has(row.id)) {
      out.push(...flatten(kids, expanded, indent + 1, intoPlanos));
    }
  }
  return out;
}

function collectIds(rows: EmpRow[], intoPlanos = false): string[] {
  const out: string[] = [];
  for (const row of rows) {
    out.push(row.id);
    if (intoPlanos || row.kind !== "centro") out.push(...collectIds(row.filhos || [], intoPlanos));
  }
  return out;
}

function filterTree(
  rows: EmpRow[],
  grupo: string,
  produtoId: number | "",
): EmpRow[] {
  return rows
    .map((row) => {
      if (row.kind === "grupo" && grupo && row.codigo !== grupo) return null;
      if (row.kind === "centro" && produtoId !== "" && row.produto_id !== produtoId) return null;
      const filhos = filterTree(row.filhos || [], grupo, produtoId);
      if (row.kind === "empresa" || row.kind === "grupo") {
        if (filhos.length === 0) return null;
        return { ...row, filhos };
      }
      return { ...row, filhos };
    })
    .filter((r): r is EmpRow => r != null);
}

function drillProduto(empresas: EmpRow[], produtoId: number): { nome: string; empresa: string; grupos: EmpRow[] } {
  const grupos: EmpRow[] = [];
  let nome = "";
  let empresa = "";
  for (const emp of empresas) {
    for (const g of emp.filhos || []) {
      const centro = (g.filhos || []).find((c) => c.produto_id === produtoId);
      if (!centro) continue;
      nome = centro.descricao;
      empresa = emp.descricao;
      grupos.push({
        ...centro,
        kind: "grupo",
        id: `${g.id}|p|${produtoId}`,
        codigo: g.codigo,
        descricao: g.descricao,
        filhos: centro.filhos || [],
      });
    }
  }
  return { nome, empresa, grupos };
}

function periodoVal(p: PeriodoVals | undefined, modo: OrcamentoModo, mldu: boolean) {
  if (!p) return { n: 0, ref: 0 };
  const n = mldu ? p.n_mldu : p.n;
  const ref = modo === "forecast" ? (mldu ? p.forecast_mldu : p.forecast) : (mldu ? p.orcado_mldu : p.orcado);
  return { n, ref };
}

function Line({
  row,
  expanded,
  onToggle,
  onOpenCentro,
  indent,
  hasKids,
  active,
  modo,
  corte,
  clickCentro,
}: {
  row: EmpRow;
  expanded: boolean;
  onToggle: () => void;
  onOpenCentro?: () => void;
  indent: number;
  hasKids: boolean;
  active: SerieKey[];
  modo: OrcamentoModo;
  corte: number;
  clickCentro: boolean;
}) {
  const isEmp = row.kind === "empresa";
  const isGrupo = row.kind === "grupo";
  const bg = isEmp ? "bg-slate-50" : isGrupo ? "bg-white" : "bg-slate-50/70";
  return (
    <tr className={`${bg} hover:bg-slate-50`}>
      <GrowTreeNameCell indent={indent} bg={bg}>
          <GrowTreeChevron open={expanded} visible={hasKids} onClick={onToggle} />
          <span className={`font-mono text-xs text-slate-400 w-14 shrink-0 mt-0.5 ${isGrupo ? "" : "opacity-80"}`}>{row.codigo}</span>
          {clickCentro && row.kind === "centro" && onOpenCentro ? (
            <button type="button" onClick={onOpenCentro} className="text-sm text-ml-green font-semibold hover:underline text-left leading-snug">
              {row.descricao}
            </button>
          ) : (
            <span className={`text-sm leading-snug ${isEmp ? "font-bold text-slate-900" : isGrupo ? "font-semibold text-slate-800" : "text-slate-600"}`}>
              {row.descricao}
            </span>
          )}
      </GrowTreeNameCell>
      {MESES_STR.map((m, mi) => {
        const n = serieValue(row, "n", modo, m);
        const ref = serieValue(row, "ref", modo, m);
        const nM = serieValue(row, "n_mldu", modo, m);
        const refM = serieValue(row, "ref_mldu", modo, m);
        const showMldu = active.includes("n_mldu") || active.includes("ref_mldu");
        return (
          <React.Fragment key={m}>
            {active.includes("n") ? (
              <td className={`px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap border-l border-slate-200 ${mi >= corte ? "bg-sky-50/40" : ""}`}>
                <Num v={n} />
              </td>
            ) : null}
            {active.includes("ref") ? (
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap">
                <Num v={ref} />
              </td>
            ) : null}
            {active.includes("n") && active.includes("ref") ? (
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap">
                <span className="inline-flex items-center justify-end gap-1">
                  <SemaforoDesvio n={n} ref={ref} tipo="DESPESAS" />
                  <Num v={n - ref} />
                </span>
              </td>
            ) : null}
            {showMldu && active.includes("n_mldu") ? (
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap border-l border-slate-100">
                <Num v={nM} />
              </td>
            ) : null}
            {showMldu && active.includes("ref_mldu") ? (
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap">
                <Num v={refM} />
              </td>
            ) : null}
            {showMldu && active.includes("n_mldu") && active.includes("ref_mldu") ? (
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap">
                <span className="inline-flex items-center justify-end gap-1">
                  <SemaforoDesvio n={nM} ref={refM} tipo="DESPESAS" />
                  <Num v={nM - refM} />
                </span>
              </td>
            ) : null}
          </React.Fragment>
        );
      })}
      {(["ano"] as const).map(() => {
        const n = serieValue(row, "n", modo);
        const ref = serieValue(row, "ref", modo);
        const nM = serieValue(row, "n_mldu", modo);
        const refM = serieValue(row, "ref_mldu", modo);
        const showMldu = active.includes("n_mldu") || active.includes("ref_mldu");
        return (
          <React.Fragment key="tot">
            {active.includes("n") ? (
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] font-semibold whitespace-nowrap bg-slate-50/80 border-l border-slate-200">
                <Num v={n} />
              </td>
            ) : null}
            {active.includes("ref") ? (
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] font-semibold whitespace-nowrap bg-slate-50/80">
                <Num v={ref} />
              </td>
            ) : null}
            {active.includes("n") && active.includes("ref") ? (
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] font-semibold whitespace-nowrap bg-slate-50/80">
                <span className="inline-flex items-center justify-end gap-1">
                  <SemaforoDesvio n={n} ref={ref} tipo="DESPESAS" />
                  <Num v={n - ref} />
                </span>
              </td>
            ) : null}
            {showMldu && active.includes("n_mldu") ? (
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] font-semibold whitespace-nowrap bg-slate-50/80">
                <Num v={nM} />
              </td>
            ) : null}
            {showMldu && active.includes("ref_mldu") ? (
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] font-semibold whitespace-nowrap bg-slate-50/80">
                <Num v={refM} />
              </td>
            ) : null}
            {showMldu && active.includes("n_mldu") && active.includes("ref_mldu") ? (
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] font-semibold whitespace-nowrap bg-slate-50/80">
                <span className="inline-flex items-center justify-end gap-1">
                  <SemaforoDesvio n={nM} ref={refM} tipo="DESPESAS" />
                  <Num v={nM - refM} />
                </span>
              </td>
            ) : null}
          </React.Fragment>
        );
      })}
      <td className="px-2 py-2 border-b border-slate-100 text-right text-xs whitespace-nowrap border-l border-slate-200">
        <Perc v={varPercDesvio(serieValue(row, "n", modo), serieValue(row, "ref", modo))} />
      </td>
    </tr>
  );
}

export default function DespesasEmpreendimentoPage() {
  const deptId = useActiveDepartmentId();
  const [ano, setAno] = useState(2026);
  const { filtroEmpresaIds, setFiltroEmpresaIds, empresaOpcoes, empresaIdsKey } = useEmpresaCadastroFilter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [modo, setModo] = useState<OrcamentoModo>("orcado");
  const [corte, setCorte] = useState(9);
  const [forecastId, setForecastId] = useState<number | undefined>();
  const [forecasts, setForecasts] = useState<{ id: number; descricao: string }[]>([]);
  const [onN, setOnN] = useState(true);
  const [onRef, setOnRef] = useState(true);
  const [onNMldu, setOnNMldu] = useState(true);
  const [onRefMldu, setOnRefMldu] = useState(true);
  const [grupoFiltro, setGrupoFiltro] = useState("");
  const [produtoFiltro, setProdutoFiltro] = useState<number | "">("");
  const [drillId, setDrillId] = useState<number | null>(null);

  const active = useMemo<SerieKey[]>(() => {
    const keys: SerieKey[] = [];
    if (onN) keys.push("n");
    if (onRef) keys.push("ref");
    if (onNMldu) keys.push("n_mldu");
    if (onRefMldu) keys.push("ref_mldu");
    return keys;
  }, [onN, onRef, onNMldu, onRefMldu]);

  const load = useCallback(async () => {
    if (!isDepartmentContextId(deptId)) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await getDespesasEmpreendimento(
        ano,
        deptId,
        corte,
        empresaIdsKey ? empresaIdsKey.split(",") : [],
        forecastId,
      );
      setData(res);
      const list = res.versoes_disponiveis || [];
      setForecasts(list);
      const ids = new Set(list.map((v: { id: number }) => v.id));
      if (!forecastId || (list.length > 0 && !ids.has(forecastId))) {
        const next =
          (res.active_forecast_id && ids.has(res.active_forecast_id) && res.active_forecast_id)
          || list[0]?.id;
        if (next && next !== forecastId) setForecastId(next);
      }
      setExpanded(new Set((res.empresas || []).map((e: EmpRow) => e.id)));
    } finally {
      setLoading(false);
    }
  }, [ano, deptId, corte, empresaIdsKey, forecastId]);

  useEffect(() => { load(); }, [load]);

  const empresas: EmpRow[] = data?.empresas || [];
  const filtradas = useMemo(
    () => filterTree(empresas, grupoFiltro, produtoFiltro),
    [empresas, grupoFiltro, produtoFiltro],
  );
  const drill = drillId != null ? drillProduto(filtradas, drillId) : null;
  const raiz = drill ? drill.grupos : filtradas;
  const intoPlanos = !!drill;
  const linhas = useMemo(
    () => flatten(raiz, expanded, 0, intoPlanos),
    [raiz, expanded, intoPlanos],
  );

  const anoRef = data?.ano_ref || ano + 1;
  const nLabel = `${ano}`;
  const refLabel = modo === "forecast" ? `Fcst ${anoRef}` : `Orç ${anoRef}`;
  const periodosFonte = drill?.grupos.reduce(
    (acc, g) => {
      const p = g.periodos;
      if (!p) return acc;
      const next = { ...acc };
      (["ano", "ytd", "ytg", "fy"] as Periodo[]).forEach((k) => {
        const a = next[k] || { n: 0, n_mldu: 0, orcado: 0, orcado_mldu: 0, forecast: 0, forecast_mldu: 0 };
        const b = p[k];
        next[k] = {
          n: a.n + (b?.n || 0),
          n_mldu: a.n_mldu + (b?.n_mldu || 0),
          orcado: a.orcado + (b?.orcado || 0),
          orcado_mldu: a.orcado_mldu + (b?.orcado_mldu || 0),
          forecast: a.forecast + (b?.forecast || 0),
          forecast_mldu: a.forecast_mldu + (b?.forecast_mldu || 0),
        };
      });
      return next;
    },
    {} as Record<Periodo, PeriodoVals>,
  ) || data?.periodos;

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const colSpanMes = (
    (active.includes("n") ? 1 : 0)
    + (active.includes("ref") ? 1 : 0)
    + (active.includes("n") && active.includes("ref") ? 1 : 0)
    + (active.includes("n_mldu") ? 1 : 0)
    + (active.includes("ref_mldu") ? 1 : 0)
    + (active.includes("n_mldu") && active.includes("ref_mldu") ? 1 : 0)
  );

  return (
    <div className={GROW_TREE_PAGE_CLASS}>
      <div className="shrink-0 space-y-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Análise de Orçamento</h1>
          <p className="text-slate-500 text-sm mt-1">
            YTD real {ano}, YTG forecast, FY contra {modo === "forecast" ? "forecast" : "orçado"} {anoRef}.
            Cheio e MLDU lado a lado. Despesa positiva.
          </p>
        </div>

        <OrcamentoFlyoutFilterBar
          holdingMldu={false}
          onHoldingMlduChange={() => undefined}
          canUseHoldingMldu={false}
          empresaOpcoes={empresaOpcoes}
          filtroEmpresaIds={filtroEmpresaIds}
          onEmpresaChange={setFiltroEmpresaIds}
          meses={[]}
          onMesesChange={() => undefined}
          hideMeses
          ano={ano}
          onAnoChange={setAno}
          showModo
          modo={modo}
          onModoChange={setModo}
          forecasts={forecasts}
          forecastId={forecastId || ""}
          onForecastIdChange={(id) => setForecastId(id || undefined)}
          sempreMostrarVersaoForecast
          onRefresh={load}
          loading={loading}
        >
          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Corte YTD</label>
            <select
              value={corte}
              onChange={(e) => setCorte(Number(e.target.value))}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 bg-white"
            >
              {MESES_LABEL.map((m, i) => (
                <option key={m} value={i + 1}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Grupo</label>
            <select
              value={grupoFiltro}
              onChange={(e) => setGrupoFiltro(e.target.value)}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 bg-white max-w-[220px]"
            >
              <option value="">Todos</option>
              {(data?.grupos || []).map((g: { codigo: string; descricao: string }) => (
                <option key={g.codigo} value={g.codigo}>{g.codigo} {g.descricao}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Empreendimento</label>
            <select
              value={produtoFiltro === "" ? "" : String(produtoFiltro)}
              onChange={(e) => setProdutoFiltro(e.target.value ? Number(e.target.value) : "")}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 bg-white max-w-[240px]"
            >
              <option value="">Todos</option>
              {(data?.centros || []).map((c: { produto_id: number; nome: string }) => (
                <option key={c.produto_id} value={c.produto_id}>{c.nome}</option>
              ))}
            </select>
          </div>
        </OrcamentoFlyoutFilterBar>
      </div>

      {!loading && periodosFonte ? (
        <div className="shrink-0 grid grid-cols-1 sm:grid-cols-3 gap-3">
          {PERIODOS_KPI.map((k) => {
            const pv = periodoVal(periodosFonte[k], modo, false);
            return (
              <PeriodoKpiCard
                key={k}
                titulo={tituloPeriodo(k)}
                legenda={legendaPeriodo(k, corte)}
                hint={hintPeriodo(k)}
                n={pv.n}
                ref={pv.ref}
                nLabel={nLabel}
                refLabel={refLabel}
                tipo="DESPESAS"
              />
            );
          })}
        </div>
      ) : null}
      {!loading && periodosFonte ? <DesvioLegend className="shrink-0" /> : null}

      <GrowTreeSheet
        toolbar={
          <>
          <h2 className="font-bold text-slate-700">
            {drill ? (
              <span className="flex items-center gap-2">
                <button type="button" onClick={() => setDrillId(null)} className="text-xs font-semibold text-ml-green hover:underline">
                  Navegação
                </button>
                <span className="text-slate-400">/</span>
                <span>{drill.nome}</span>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{drill.empresa}</span>
              </span>
            ) : (
              <>
                Navegação
                {data?.visao?.nome ? <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">{data.visao.nome}</span> : null}
              </>
            )}
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mr-1">Séries</span>
            {([
              { key: "n" as const, on: onN, set: setOnN, label: `${ano} cheio` },
              { key: "ref" as const, on: onRef, set: setOnRef, label: `${refLabel} cheio` },
              { key: "n_mldu" as const, on: onNMldu, set: setOnNMldu, label: `${ano} MLDU` },
              { key: "ref_mldu" as const, on: onRefMldu, set: setOnRefMldu, label: `${refLabel} MLDU` },
            ]).map((s) => (
              <button
                key={s.key}
                type="button"
                onClick={() => s.set((v) => !v)}
                className={`px-2 py-1 rounded-md text-[11px] font-semibold border transition ${
                  s.on ? "bg-ml-green text-white border-ml-green" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                }`}
              >
                {s.label}
              </button>
            ))}
            <button type="button" onClick={() => setExpanded(new Set(collectIds(raiz, intoPlanos)))} className="text-xs font-semibold text-ml-green hover:underline ml-2">Expandir</button>
            <button type="button" onClick={() => setExpanded(new Set(raiz.map((e) => e.id)))} className="text-xs font-semibold text-slate-500 hover:underline">Recolher</button>
          </div>
          </>
        }
      >
        {loading ? (
          <div className="p-6"><AppLoadingState /></div>
        ) : (
            <table className="w-full text-sm min-w-[2200px]">
              <thead className="sticky top-0 z-20 bg-white">
                <tr className="text-[10px] uppercase tracking-wider text-slate-400">
                  <th rowSpan={2} className={GROW_TREE_NAME_TH_CLASS}>
                    {drill ? "Grupo / Plano" : "Empresa / Grupo / Empreendimento"}
                  </th>
                  {MESES_LABEL.map((m, i) => (
                    <th key={m} colSpan={colSpanMes} className={`px-1.5 py-1 text-center font-semibold whitespace-nowrap border-b border-l border-slate-200 ${i + 1 > corte ? "bg-sky-50/60" : ""}`}>
                      {m}
                    </th>
                  ))}
                  <th colSpan={colSpanMes} className="px-1.5 py-1 text-center font-semibold bg-slate-50 whitespace-nowrap border-b border-l border-slate-200">
                    Total
                  </th>
                  <th rowSpan={2} className="px-2 py-2 text-right font-semibold whitespace-nowrap border-b border-l border-slate-200 align-bottom">Var %</th>
                </tr>
                <tr className="text-[9px] uppercase tracking-wider text-slate-400 border-b border-slate-200">
                  {MESES_STR.map((m, i) => (
                    <React.Fragment key={m}>
                      {active.includes("n") ? (
                        <th className={`px-1.5 py-1 text-right font-semibold whitespace-nowrap border-l border-slate-200 ${i + 1 > corte ? "bg-sky-50/60" : ""}`}>
                          {i + 1 > corte ? `Fcst ${ano}` : `Real ${ano}`}
                        </th>
                      ) : null}
                      {active.includes("ref") ? (
                        <th className="px-1.5 py-1 text-right font-semibold whitespace-nowrap">{refLabel}</th>
                      ) : null}
                      {active.includes("n") && active.includes("ref") ? (
                        <th className="px-1.5 py-1 text-right font-semibold whitespace-nowrap">Var</th>
                      ) : null}
                      {active.includes("n_mldu") ? (
                        <th className="px-1.5 py-1 text-right font-semibold whitespace-nowrap">MLDU {i + 1 > corte ? "Fcst" : "Real"}</th>
                      ) : null}
                      {active.includes("ref_mldu") ? (
                        <th className="px-1.5 py-1 text-right font-semibold whitespace-nowrap">MLDU {refLabel}</th>
                      ) : null}
                      {active.includes("n_mldu") && active.includes("ref_mldu") ? (
                        <th className="px-1.5 py-1 text-right font-semibold whitespace-nowrap">Var MLDU</th>
                      ) : null}
                    </React.Fragment>
                  ))}
                  {active.includes("n") ? <th className="px-1.5 py-1 text-right font-semibold bg-slate-50 whitespace-nowrap border-l border-slate-200">{nLabel}</th> : null}
                  {active.includes("ref") ? <th className="px-1.5 py-1 text-right font-semibold bg-slate-50 whitespace-nowrap">{refLabel}</th> : null}
                  {active.includes("n") && active.includes("ref") ? <th className="px-1.5 py-1 text-right font-semibold bg-slate-50 whitespace-nowrap">Var</th> : null}
                  {active.includes("n_mldu") ? <th className="px-1.5 py-1 text-right font-semibold bg-slate-50 whitespace-nowrap">MLDU {nLabel}</th> : null}
                  {active.includes("ref_mldu") ? <th className="px-1.5 py-1 text-right font-semibold bg-slate-50 whitespace-nowrap">MLDU {refLabel}</th> : null}
                  {active.includes("n_mldu") && active.includes("ref_mldu") ? <th className="px-1.5 py-1 text-right font-semibold bg-slate-50 whitespace-nowrap">Var MLDU</th> : null}
                </tr>
              </thead>
              <tbody>
                {linhas.length === 0 ? (
                  <tr>
                    <td colSpan={2 + 13 * Math.max(colSpanMes, 1)} className="px-4 py-10 text-center text-sm text-slate-500">
                      Sem despesas nos grupos 05.01–05.11 neste departamento. Orçamentos importados ficam em Corporativo — troque o departamento no filtro.
                    </td>
                  </tr>
                ) : linhas.map(({ row, indent, hasKids }) => (
                  <Line
                    key={row.id}
                    row={row}
                    expanded={expanded.has(row.id)}
                    onToggle={() => toggle(row.id)}
                    onOpenCentro={row.produto_id != null ? () => {
                      const pid = row.produto_id as number;
                      const d = drillProduto(filtradas, pid);
                      setDrillId(pid);
                      setExpanded(new Set(d.grupos.map((g) => g.id)));
                    } : undefined}
                    indent={indent}
                    hasKids={hasKids}
                    active={active}
                    modo={modo}
                    corte={corte}
                    clickCentro={!drill}
                  />
                ))}
              </tbody>
            </table>
        )}
      </GrowTreeSheet>

      {(data?.holding_avisos || []).length > 0 ? (
        <p className="shrink-0 text-xs text-amber-700">{(data.holding_avisos as string[]).join(" · ")}</p>
      ) : null}
      <p className="shrink-0 text-xs text-slate-400">
        Fonte: mesmos números do orçamento (despesas, realizado e forecast). Planos fora da Visão DFC 05.01–05.11 não entram; 05.08 e 09.01* ficam de fora.
        Semáforo: materialidade R$ 5.000, tolerância 5%, limite 10%. {" "}
        Conferência com o <Link href="/dashboard/orcamento/dfc-gerencial" className="text-ml-green font-semibold hover:underline">DFC gerencial</Link>.
      </p>
    </div>
  );
}
