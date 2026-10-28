"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronRight, FileSpreadsheet } from "lucide-react";
import { getDfcGerencial, type DfcGerencialAgrupamento } from "@/services/orcamentoDfcGerencial";
import { useActiveDepartmentId, isDepartmentContextId } from "@/lib/useActiveDepartmentId";
import { OrcamentoFlyoutFilterBar } from "@/components/orcamento/OrcamentoFlyoutFilterBar";
import { OrcamentoHeroStrip } from "@/components/orcamento/OrcamentoHeroStrip";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { useEmpresaCadastroFilter } from "@/hooks/useEmpresaCadastroFilter";
import {
  formatMoedaCompact,
  formatPerc,
  isDesvioFavoravel,
  MATERIALITY_THRESHOLD,
  MESES_STR,
} from "@/lib/orcamentoDesvioUi";

const MESES_LABEL = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

type SerieKey = "real" | "real_mldu" | "n1" | "n1_mldu" | "ref" | "ref_mldu";
type RefModo = "orcado" | "forecast";

const SERIES: { key: SerieKey; label: string; short: string; locked?: boolean }[] = [
  { key: "real", label: "Real cheio", short: "Real", locked: true },
  { key: "real_mldu", label: "Real MLDU", short: "MLDU" },
  { key: "n1", label: "Ano anterior cheio", short: "N-1" },
  { key: "n1_mldu", label: "Ano anterior MLDU", short: "N-1 MLDU" },
  { key: "ref", label: "Orçado cheio", short: "Orç" },
  { key: "ref_mldu", label: "Orçado MLDU", short: "Orç MLDU" },
];

type GerencialRow = {
  kind: "empresa" | "categoria" | "plano" | "centro";
  id: string;
  codigo: string;
  descricao: string;
  meses_real?: Record<string, number>;
  meses_real_mldu?: Record<string, number>;
  meses_n1?: Record<string, number>;
  meses_n1_mldu?: Record<string, number>;
  meses_orcado?: Record<string, number>;
  meses_orcado_mldu?: Record<string, number>;
  meses_forecast?: Record<string, number>;
  meses_forecast_mldu?: Record<string, number>;
  meses_ah?: Record<string, number | null>;
  meses_av?: Record<string, number | null>;
  total_real?: number;
  total_real_mldu?: number;
  total_n1?: number;
  total_n1_mldu?: number;
  total_orcado?: number;
  total_orcado_mldu?: number;
  total_forecast?: number;
  total_forecast_mldu?: number;
  ah: number | null;
  av: number | null;
  filhos?: GerencialRow[];
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

function serieValue(row: GerencialRow, key: SerieKey, refModo: RefModo, mes?: string) {
  if (mes) {
    if (key === "real") return row.meses_real?.[mes] || 0;
    if (key === "real_mldu") return row.meses_real_mldu?.[mes] || 0;
    if (key === "n1") return row.meses_n1?.[mes] || 0;
    if (key === "n1_mldu") return row.meses_n1_mldu?.[mes] || 0;
    if (key === "ref") {
      return refModo === "forecast" ? row.meses_forecast?.[mes] || 0 : row.meses_orcado?.[mes] || 0;
    }
    return refModo === "forecast" ? row.meses_forecast_mldu?.[mes] || 0 : row.meses_orcado_mldu?.[mes] || 0;
  }
  if (key === "real") return row.total_real || 0;
  if (key === "real_mldu") return row.total_real_mldu || 0;
  if (key === "n1") return row.total_n1 || 0;
  if (key === "n1_mldu") return row.total_n1_mldu || 0;
  if (key === "ref") return refModo === "forecast" ? row.total_forecast || 0 : row.total_orcado || 0;
  return refModo === "forecast" ? row.total_forecast_mldu || 0 : row.total_orcado_mldu || 0;
}

function percExcel(v: number | null | undefined) {
  if (v == null || Number.isNaN(v)) return "";
  return v * 100;
}

function serieMeta(key: SerieKey, refModo: RefModo) {
  if (key === "ref") {
    return refModo === "forecast"
      ? { label: "Forecast cheio", short: "FCST" }
      : { label: "Orçado cheio", short: "Orç" };
  }
  if (key === "ref_mldu") {
    return refModo === "forecast"
      ? { label: "Forecast MLDU", short: "FCST MLDU" }
      : { label: "Orçado MLDU", short: "Orç MLDU" };
  }
  const s = SERIES.find((x) => x.key === key);
  return { label: s?.label || key, short: s?.short || key };
}

function flatten(rows: GerencialRow[], expanded: Set<string>, indent = 0): { row: GerencialRow; indent: number; hasKids: boolean }[] {
  const out: { row: GerencialRow; indent: number; hasKids: boolean }[] = [];
  for (const row of rows) {
    const kids = row.filhos || [];
    const hasKids = kids.length > 0;
    out.push({ row, indent, hasKids });
    if (hasKids && expanded.has(row.id)) {
      out.push(...flatten(kids, expanded, indent + 1));
    }
  }
  return out;
}

function collectIds(rows: GerencialRow[]): string[] {
  const out: string[] = [];
  for (const row of rows) {
    out.push(row.id);
    out.push(...collectIds(row.filhos || []));
  }
  return out;
}

async function exportarExcel(
  empresas: GerencialRow[],
  expanded: Set<string>,
  active: SerieKey[],
  refModo: RefModo,
  ano: number,
  ahAvMensal: boolean,
) {
  const XLSX = await import("xlsx");
  const headers = ["Nível", "Código", "Descrição"];
  for (const mes of MESES_LABEL) {
    for (const key of active) headers.push(`${mes} ${serieMeta(key, refModo).short}`);
    if (ahAvMensal) headers.push(`${mes} AH %`, `${mes} AV %`);
  }
  for (const key of active) headers.push(`Total ${ano} ${serieMeta(key, refModo).short}`);
  headers.push("AH %", "AV %");

  const kindLabel: Record<GerencialRow["kind"], string> = {
    empresa: "Empresa",
    categoria: "Visão",
    plano: "Plano",
    centro: "Centro de custo",
  };
  const rows: (string | number)[][] = [];
  for (const { row } of flatten(empresas, expanded)) {
    const line: (string | number)[] = [kindLabel[row.kind], row.codigo || "", row.descricao || ""];
    for (const mes of MESES_STR) {
      for (const key of active) line.push(serieValue(row, key, refModo, mes));
      if (ahAvMensal) {
        line.push(percExcel(row.meses_ah?.[mes]));
        line.push(percExcel(row.meses_av?.[mes]));
      }
    }
    for (const key of active) line.push(serieValue(row, key, refModo));
    line.push(percExcel(row.ah));
    line.push(percExcel(row.av));
    rows.push(line);
  }
  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "DFC gerencial");
  XLSX.writeFile(wb, `DFC_gerencial_${ano}.xlsx`);
}

function DfcLine({
  row,
  expanded,
  onToggle,
  indent,
  hasKids,
  active,
  refModo,
  ahAvMensal,
}: {
  row: GerencialRow;
  expanded: boolean;
  onToggle?: () => void;
  indent: number;
  hasKids: boolean;
  active: SerieKey[];
  refModo: RefModo;
  ahAvMensal: boolean;
}) {
  const isEmp = row.kind === "empresa";
  const isCat = row.kind === "categoria" || isEmp;
  const bg = isEmp ? "bg-slate-50" : isCat ? "bg-white" : "bg-slate-50/70";
  return (
    <tr className={`${bg} hover:bg-slate-50`}>
      <td className={`sticky left-0 z-10 px-3 py-2 border-b border-slate-100 min-w-[280px] ${bg}`}>
        <div className="flex items-center gap-1" style={{ paddingLeft: indent * 16 }}>
          {hasKids ? (
            <button type="button" onClick={onToggle} className="p-0.5 rounded hover:bg-slate-200">
              {expanded ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
            </button>
          ) : (
            <span className="w-4" />
          )}
          <span className={`font-mono text-xs text-slate-400 w-14 shrink-0 ${isCat ? "" : "opacity-80"}`}>{row.codigo}</span>
          <span className={`text-sm truncate ${isEmp ? "font-bold text-slate-900" : isCat ? "font-semibold text-slate-800" : "text-slate-600"}`}>
            {row.descricao}
          </span>
        </div>
      </td>
      {MESES_STR.map((m) => (
        <React.Fragment key={m}>
          {active.map((key, i) => (
            <td
              key={`${m}-${key}`}
              className={`px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap ${i === 0 ? "border-l border-slate-200" : ""} ${key === "real" ? "font-semibold" : ""}`}
            >
              <Num v={serieValue(row, key, refModo, m)} />
            </td>
          ))}
          {ahAvMensal ? (
            <>
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap">
                <Perc v={row.meses_ah?.[m] ?? null} />
              </td>
              <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap">
                <Perc v={row.meses_av?.[m] ?? null} />
              </td>
            </>
          ) : null}
        </React.Fragment>
      ))}
      {active.map((key, i) => (
        <td
          key={`tot-${key}`}
          className={`px-1.5 py-2 border-b border-slate-100 text-right text-[11px] font-semibold whitespace-nowrap bg-slate-50/80 ${i === 0 ? "border-l border-slate-200" : ""}`}
        >
          <Num v={serieValue(row, key, refModo)} />
        </td>
      ))}
      <td className="px-2 py-2 border-b border-slate-100 text-right text-xs whitespace-nowrap border-l border-slate-200">
        <Perc v={row.ah} />
      </td>
      <td className="px-2 py-2 border-b border-slate-100 text-right text-xs whitespace-nowrap">
        <Perc v={row.av} />
      </td>
    </tr>
  );
}

export default function OrcamentoDfcGerencialPage() {
  const deptId = useActiveDepartmentId();
  const [ano, setAno] = useState(() => new Date().getFullYear());
  const [meses, setMeses] = useState<string[]>([]);
  const { filtroEmpresaIds, setFiltroEmpresaIds, empresaOpcoes, empresaIdsKey } = useEmpresaCadastroFilter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [onRealMldu, setOnRealMldu] = useState(true);
  const [onN1, setOnN1] = useState(true);
  const [onN1Mldu, setOnN1Mldu] = useState(true);
  const [onRef, setOnRef] = useState(true);
  const [onRefMldu, setOnRefMldu] = useState(true);
  const [onAhAvMensal, setOnAhAvMensal] = useState(false);
  const [refModo, setRefModo] = useState<RefModo>("orcado");
  const [agrupamento, setAgrupamento] = useState<DfcGerencialAgrupamento>("visao");
  const [forecastId, setForecastId] = useState<number | undefined>();
  const [forecasts, setForecasts] = useState<{ id: number; descricao: string }[]>([]);

  const active = useMemo<SerieKey[]>(() => {
    const keys: SerieKey[] = ["real"];
    if (onRealMldu) keys.push("real_mldu");
    if (onN1) keys.push("n1");
    if (onN1Mldu) keys.push("n1_mldu");
    if (onRef) keys.push("ref");
    if (onRefMldu) keys.push("ref_mldu");
    return keys;
  }, [onRealMldu, onN1, onN1Mldu, onRef, onRefMldu]);

  const load = useCallback(async () => {
    if (!isDepartmentContextId(deptId)) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await getDfcGerencial(
        ano,
        deptId,
        meses,
        empresaIdsKey ? empresaIdsKey.split(",") : [],
        forecastId,
        agrupamento,
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
      setExpanded(new Set((res.empresas || []).map((e: GerencialRow) => e.id)));
    } finally {
      setLoading(false);
    }
  }, [ano, deptId, meses, empresaIdsKey, forecastId, agrupamento]);

  useEffect(() => { load(); }, [load]);

  const empresas: GerencialRow[] = data?.empresas || [];
  const linhas = useMemo(() => flatten(empresas, expanded), [empresas, expanded]);
  const liquido = data?.liquido ?? 0;
  const liquidoN1 = data?.liquido_n1 ?? 0;
  const varRs = liquido - liquidoN1;
  const varPerc = data?.ah_liquido ?? (liquidoN1 !== 0 ? varRs / Math.abs(liquidoN1) : 0);
  const favoravel = isDesvioFavoravel(varRs, "RESULTADO");
  const material = Math.abs(varPerc) >= MATERIALITY_THRESHOLD;
  const visaoNome = data?.visao?.nome || "Visão DFC";
  const saidas = useMemo(() => liquido - (data?.total_entradas ?? 0), [liquido, data?.total_entradas]);
  const colSpanMes = active.length + (onAhAvMensal ? 2 : 0);

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const expandirTodos = () => setExpanded(new Set(collectIds(empresas)));
  const recolherTodos = () => setExpanded(new Set(empresas.map((e) => e.id)));

  const chipOn = (key: SerieKey) =>
    key === "real"
    || (key === "real_mldu" && onRealMldu)
    || (key === "n1" && onN1)
    || (key === "n1_mldu" && onN1Mldu)
    || (key === "ref" && onRef)
    || (key === "ref_mldu" && onRefMldu);

  const toggleSerie = (key: SerieKey) => {
    if (key === "real") return;
    if (key === "real_mldu") setOnRealMldu((v) => !v);
    if (key === "n1") setOnN1((v) => !v);
    if (key === "n1_mldu") setOnN1Mldu((v) => !v);
    if (key === "ref") setOnRef((v) => !v);
    if (key === "ref_mldu") setOnRefMldu((v) => !v);
  };

  return (
    <div className="flex flex-col flex-1 min-h-0 min-w-0 gap-4 overflow-hidden">
      <div className="shrink-0 space-y-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">DFC gerencial</h1>
          <p className="text-slate-500 text-sm mt-1">
            Mesmos números do DFC, por empresa, visão, plano e centro de custo. Cheio e MLDU lado a lado. Saídas negativas.
          </p>
        </div>

        <OrcamentoFlyoutFilterBar
          holdingMldu={false}
          onHoldingMlduChange={() => undefined}
          canUseHoldingMldu={false}
          empresaOpcoes={empresaOpcoes}
          filtroEmpresaIds={filtroEmpresaIds}
          onEmpresaChange={setFiltroEmpresaIds}
          meses={meses}
          onMesesChange={setMeses}
          ano={ano}
          onAnoChange={setAno}
          showModo
          modo={refModo}
          onModoChange={setRefModo}
          forecasts={forecasts}
          forecastId={refModo === "forecast" ? (forecastId || "") : ""}
          onForecastIdChange={refModo === "forecast" ? (id) => setForecastId(id || undefined) : undefined}
          onRefresh={load}
          loading={loading}
        />
      </div>

      {!loading && (
        <div className="shrink-0">
          <OrcamentoHeroStrip
            refLabel={`Realizado ${ano - 1}`}
            refVal={liquidoN1}
            realVal={liquido}
            varRs={varRs}
            varPerc={varPerc || 0}
            favoravel={favoravel}
            material={material}
            refCaption="Caixa líquido cheio"
            caption={`Entradas ${formatMoedaCompact(data?.total_entradas || 0)} · Saídas ${formatMoedaCompact(saidas)} · MLDU ${formatMoedaCompact(data?.liquido_real_mldu || 0)} · AV sobre total de entradas`}
          />
        </div>
      )}

      <div className="flex-1 min-h-0 flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="shrink-0 flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-slate-100 bg-white">
          <h2 className="font-bold text-slate-700">
            {visaoNome}
            {data?.visao?.is_padrao ? <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">padrão</span> : null}
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mr-1">Agrupar</span>
            <button
              type="button"
              onClick={() => setAgrupamento("visao")}
              className={`px-2 py-1 rounded-md text-[11px] font-semibold border transition ${
                agrupamento === "visao" ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              Empresa → Visão
            </button>
            <button
              type="button"
              onClick={() => setAgrupamento("centro")}
              className={`px-2 py-1 rounded-md text-[11px] font-semibold border transition ${
                agrupamento === "centro" ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              Empresa → CC
            </button>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 ml-2 mr-1">Séries</span>
            {SERIES.map((s) => {
              const meta = serieMeta(s.key, refModo);
              return (
                <button
                  key={s.key}
                  type="button"
                  onClick={() => toggleSerie(s.key)}
                  disabled={s.locked}
                  className={`px-2 py-1 rounded-md text-[11px] font-semibold border transition ${
                    chipOn(s.key) ? "bg-ml-green text-white border-ml-green" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                  } ${s.locked ? "opacity-90 cursor-default" : ""}`}
                >
                  {meta.label}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => setOnAhAvMensal((v) => !v)}
              className={`px-2 py-1 rounded-md text-[11px] font-semibold border transition ${
                onAhAvMensal ? "bg-ml-green text-white border-ml-green" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              AH/AV mensal
            </button>
            <button type="button" onClick={expandirTodos} className="text-xs font-semibold text-ml-green hover:underline ml-2">Expandir</button>
            <button type="button" onClick={recolherTodos} className="text-xs font-semibold text-slate-500 hover:underline">Recolher</button>
            <button
              type="button"
              onClick={() => exportarExcel(empresas, new Set(collectIds(empresas)), active, refModo, ano, onAhAvMensal)}
              disabled={loading || empresas.length === 0}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm disabled:opacity-50"
            >
              <FileSpreadsheet className="w-4 h-4 text-brand-green" /> Excel
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-6"><AppLoadingState /></div>
        ) : (
          <div className="flex-1 min-h-0 overflow-auto">
            <table className="w-full text-sm min-w-[1800px]">
              <thead className="sticky top-0 z-20 bg-white">
                <tr className="text-[10px] uppercase tracking-wider text-slate-400">
                  <th rowSpan={2} className="sticky left-0 z-40 bg-white text-left px-3 py-2 font-semibold border-b border-slate-200 align-bottom">
                    {agrupamento === "centro" ? "Empresa / CC / Visão" : "Empresa / Visão / Plano"}
                  </th>
                  {MESES_LABEL.map((m) => (
                    <th key={m} colSpan={colSpanMes} className="px-1.5 py-1 text-center font-semibold whitespace-nowrap border-b border-l border-slate-200">
                      {m}
                    </th>
                  ))}
                  <th colSpan={colSpanMes} className="px-1.5 py-1 text-center font-semibold bg-slate-50 whitespace-nowrap border-b border-l border-slate-200">
                    Total {ano}
                  </th>
                  <th rowSpan={2} className="px-2 py-2 text-right font-semibold whitespace-nowrap border-b border-l border-slate-200 align-bottom">AH %</th>
                  <th rowSpan={2} className="px-2 py-2 text-right font-semibold whitespace-nowrap border-b border-slate-200 align-bottom">AV %</th>
                </tr>
                <tr className="text-[9px] uppercase tracking-wider text-slate-400 border-b border-slate-200">
                  {MESES_LABEL.map((m) => (
                    <React.Fragment key={m}>
                      {active.map((key, i) => (
                        <th key={`${m}-${key}`} className={`px-1.5 py-1 text-right font-semibold whitespace-nowrap ${i === 0 ? "border-l border-slate-200" : ""}`}>
                          {serieMeta(key, refModo).short}
                        </th>
                      ))}
                      {onAhAvMensal ? (
                        <>
                          <th className="px-1.5 py-1 text-right font-semibold whitespace-nowrap">AH %</th>
                          <th className="px-1.5 py-1 text-right font-semibold whitespace-nowrap">AV %</th>
                        </>
                      ) : null}
                    </React.Fragment>
                  ))}
                  {active.map((key, i) => (
                    <th key={`tot-h-${key}`} className={`px-1.5 py-1 text-right font-semibold bg-slate-50 whitespace-nowrap ${i === 0 ? "border-l border-slate-200" : ""}`}>
                      {serieMeta(key, refModo).short}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {linhas.map(({ row, indent, hasKids }) => (
                  <DfcLine
                    key={row.id}
                    row={row}
                    expanded={expanded.has(row.id)}
                    onToggle={() => toggle(row.id)}
                    indent={indent}
                    hasKids={hasKids}
                    active={active}
                    refModo={refModo}
                    ahAvMensal={onAhAvMensal}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="shrink-0 text-xs text-slate-400">
        Fonte: mesmos números do DFC (Orçado × Realizado pela visão do Apoio). Planos fora da visão não entram. Cheio = 100%; MLDU = participação da empresa × do centro.
        N-1 é só o realizado do ano anterior. {" "}
        Conferência com o <Link href="/dashboard/orcamento/dfc" className="text-ml-green font-semibold hover:underline">DFC</Link>.
      </p>
    </div>
  );
}
