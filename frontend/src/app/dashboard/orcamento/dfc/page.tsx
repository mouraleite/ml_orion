"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronDown, ChevronRight, FileSpreadsheet, GitCompare } from "lucide-react";
import { orcamentoService } from "@/services/orcamento";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId, isDepartmentContextId } from "@/lib/useActiveDepartmentId";
import { OrcamentoFlyoutFilterBar } from "@/components/orcamento/OrcamentoFlyoutFilterBar";
import { OrcamentoHeroStrip } from "@/components/orcamento/OrcamentoHeroStrip";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { useEmpresaCadastroFilter } from "@/hooks/useEmpresaCadastroFilter";
import { formatMoedaCompact, formatPerc, isDesvioFavoravel, MATERIALITY_THRESHOLD } from "@/lib/orcamentoDesvioUi";
import { DfcComparativoPanel } from "@/components/orcamento/DfcComparativoPanel";

const MESES_STR = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"] as const;
const MESES_LABEL = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

type SerieKey = "real" | "n1" | "orcado" | "forecast";

const SERIES: { key: SerieKey; label: string; short: string; locked?: boolean }[] = [
  { key: "real", label: "Realizado", short: "Real", locked: true },
  { key: "n1", label: "Ano anterior", short: "Ano anterior" },
  { key: "orcado", label: "Orçado", short: "Orç" },
  { key: "forecast", label: "Forecast", short: "FCST" },
];

type DfcRow = {
  kind: "categoria" | "plano";
  id: number;
  codigo: string;
  descricao: string;
  meses: Record<string, number>;
  meses_n1?: Record<string, number>;
  meses_orcado?: Record<string, number>;
  meses_forecast?: Record<string, number>;
  meses_ah?: Record<string, number | null>;
  meses_av?: Record<string, number | null>;
  total: number;
  total_n1: number;
  total_orcado: number;
  total_forecast?: number;
  ah: number | null;
  av: number | null;
  planos?: DfcRow[];
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

function serieValue(row: DfcRow, key: SerieKey, mes?: string) {
  if (mes) {
    if (key === "real") return row.meses?.[mes] || 0;
    if (key === "n1") return row.meses_n1?.[mes] || 0;
    if (key === "orcado") return row.meses_orcado?.[mes] || 0;
    return row.meses_forecast?.[mes] || 0;
  }
  if (key === "real") return row.total || 0;
  if (key === "n1") return row.total_n1 || 0;
  if (key === "orcado") return row.total_orcado || 0;
  return row.total_forecast || 0;
}

function percExcel(v: number | null | undefined) {
  if (v == null || Number.isNaN(v)) return "";
  return v * 100;
}

async function exportarDfcExcel(linhas: DfcRow[], active: SerieKey[], ano: number, ahAvMensal: boolean) {
  const XLSX = await import("xlsx");
  const nomeSerie = (key: SerieKey) => SERIES.find((s) => s.key === key)?.short || key;
  const headers = ["Código", "Descrição", "Tipo"];
  for (const mes of MESES_LABEL) {
    for (const key of active) headers.push(`${mes} ${nomeSerie(key)}`);
    if (ahAvMensal) {
      headers.push(`${mes} AH %`, `${mes} AV %`);
    }
  }
  for (const key of active) headers.push(`Total ${ano} ${nomeSerie(key)}`);
  headers.push("AH %", "AV %");

  const rows: (string | number)[][] = [];
  const pushRow = (row: DfcRow, tipo: string) => {
    const line: (string | number)[] = [row.codigo || "", row.descricao || "", tipo];
    for (const mes of MESES_STR) {
      for (const key of active) line.push(serieValue(row, key, mes));
      if (ahAvMensal) {
        line.push(percExcel(row.meses_ah?.[mes]));
        line.push(percExcel(row.meses_av?.[mes]));
      }
    }
    for (const key of active) line.push(serieValue(row, key));
    line.push(percExcel(row.ah));
    line.push(percExcel(row.av));
    rows.push(line);
  };
  for (const linha of linhas) {
    pushRow(linha, "Categoria");
    for (const plano of linha.planos || []) pushRow(plano, "Plano");
  }

  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "DFC");
  XLSX.writeFile(wb, `DFC_${ano}.xlsx`);
}

function DfcLine({
  row,
  expanded,
  onToggle,
  indent,
  active,
  ahAvMensal,
}: {
  row: DfcRow;
  expanded: boolean;
  onToggle?: () => void;
  indent: number;
  active: SerieKey[];
  ahAvMensal: boolean;
}) {
  const isCat = row.kind !== "plano";
  const hasKids = isCat && (row.planos?.length || 0) > 0;
  return (
    <tr className={isCat ? "bg-white hover:bg-slate-50" : "bg-slate-50/70"}>
      <td className={`sticky left-6 md:left-8 z-10 px-3 py-2 border-b border-slate-100 min-w-[280px] ${isCat ? "bg-white" : "bg-slate-50"}`}>
        <div className="flex items-center gap-1" style={{ paddingLeft: indent * 16 }}>
          {hasKids ? (
            <button type="button" onClick={onToggle} className="p-0.5 rounded hover:bg-slate-200">
              {expanded ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
            </button>
          ) : (
            <span className="w-4" />
          )}
          <span className={`font-mono text-xs text-slate-400 w-14 shrink-0 ${isCat ? "" : "opacity-80"}`}>{row.codigo}</span>
          <span className={`text-sm truncate ${isCat ? "font-semibold text-slate-800" : "text-slate-600"}`}>{row.descricao}</span>
        </div>
      </td>
      {MESES_STR.map((m) => (
        <React.Fragment key={m}>
          {active.map((key, i) => (
            <td
              key={`${m}-${key}`}
              className={`px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap ${i === 0 ? "border-l border-slate-200" : ""} ${key === "real" ? "font-semibold" : ""}`}
            >
              <Num v={serieValue(row, key, m)} />
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
          <Num v={serieValue(row, key)} />
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

export default function OrcamentoDfcPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const modoComparar = searchParams.get("modo") === "comparar";
  const deptId = useActiveDepartmentId();
  const { holdingMldu, setHoldingMldu, canUseHoldingMldu } = useHoldingMldu("orcamento");
  const [ano, setAno] = useState(() => {
    const fromUrl = Number(searchParams.get("ano"));
    return fromUrl > 2000 ? fromUrl : new Date().getFullYear();
  });
  const [meses, setMeses] = useState<string[]>([]);
  const { filtroEmpresaIds, setFiltroEmpresaIds, empresaOpcoes, empresaIdsKey } = useEmpresaCadastroFilter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [onN1, setOnN1] = useState(true);
  const [onOrcado, setOnOrcado] = useState(true);
  const [onForecast, setOnForecast] = useState(false);
  const [onAhAvMensal, setOnAhAvMensal] = useState(false);
  const [forecastId, setForecastId] = useState<number | undefined>();
  const [forecasts, setForecasts] = useState<{ id: number; descricao: string }[]>([]);

  const setModo = (comparar: boolean) => {
    const params = new URLSearchParams(searchParams.toString());
    if (comparar) params.set("modo", "comparar");
    else params.delete("modo");
    params.set("ano", String(ano));
    router.replace(`/dashboard/orcamento/dfc?${params.toString()}`);
  };

  const active = useMemo<SerieKey[]>(() => {
    const keys: SerieKey[] = ["real"];
    if (onN1) keys.push("n1");
    if (onOrcado) keys.push("orcado");
    if (onForecast) keys.push("forecast");
    return keys;
  }, [onN1, onOrcado, onForecast]);

  const load = useCallback(async () => {
    if (modoComparar || !isDepartmentContextId(deptId)) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await orcamentoService.getDfc(
        ano,
        deptId,
        holdingMldu,
        meses,
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
    } finally {
      setLoading(false);
    }
  }, [ano, deptId, holdingMldu, meses, empresaIdsKey, forecastId, modoComparar]);

  useEffect(() => { load(); }, [load]);

  const linhas: DfcRow[] = data?.linhas || [];
  const liquido = data?.liquido ?? 0;
  const liquidoN1 = data?.liquido_n1 ?? 0;
  const varRs = liquido - liquidoN1;
  const varPerc = data?.ah_liquido ?? (liquidoN1 !== 0 ? varRs / Math.abs(liquidoN1) : 0);
  const favoravel = isDesvioFavoravel(varRs, "RESULTADO");
  const material = Math.abs(varPerc) >= MATERIALITY_THRESHOLD;

  const indentOf = (codigo: string) => (codigo.match(/\./g) || []).length;

  const toggle = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const expandirTodos = () => setExpanded(new Set(linhas.map((l) => l.id)));
  const recolherTodos = () => setExpanded(new Set());

  const visaoNome = data?.visao?.nome || "Visão DFC";
  const saidas = useMemo(() => liquido - (data?.total_entradas ?? 0), [liquido, data?.total_entradas]);
  const colSpanMes = active.length + (onAhAvMensal ? 2 : 0);

  return (
    <div className="w-max min-w-full">
      <div className="sticky left-0 z-30 w-[100cqw] max-w-[100cqw] space-y-4 bg-slate-50 px-6 md:px-8 pt-6 md:pt-8 pb-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">DFC</h1>
          <p className="text-slate-500 text-sm mt-1">
            {modoComparar
              ? `Comparativo de versões pela ${visaoNome} — mesma estrutura do demonstrativo.`
              : `Demonstrativo pela ${visaoNome} — realizado ${ano} vs ${ano - 1}, orçado e forecast. Saídas negativas.`}
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-0.5">
          <button
            type="button"
            onClick={() => setModo(false)}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              !modoComparar ? "bg-slate-800 text-white" : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            Demonstrativo
          </button>
          <button
            type="button"
            onClick={() => setModo(true)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              modoComparar ? "bg-slate-800 text-white" : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            <GitCompare className="w-3.5 h-3.5" />
            Comparar versões
          </button>
        </div>
      </div>

      <OrcamentoFlyoutFilterBar
        holdingMldu={holdingMldu}
        onHoldingMlduChange={setHoldingMldu}
        canUseHoldingMldu={canUseHoldingMldu}
        empresaOpcoes={empresaOpcoes}
        filtroEmpresaIds={filtroEmpresaIds}
        onEmpresaChange={setFiltroEmpresaIds}
        meses={meses}
        onMesesChange={setMeses}
        ano={ano}
        onAnoChange={setAno}
        showModo={false}
        forecasts={modoComparar ? [] : forecasts}
        forecastId={!modoComparar && onForecast ? (forecastId || "") : ""}
        onForecastIdChange={!modoComparar && onForecast ? (id) => setForecastId(id || undefined) : undefined}
        onRefresh={modoComparar ? undefined : load}
        loading={loading}
      />

      {holdingMldu && <HoldingMlduBanner avisos={data?.holding_avisos} />}
      </div>

      {modoComparar ? (
        <div className="px-6 md:px-8 pb-8">
        <DfcComparativoPanel
          ano={ano}
          deptId={deptId}
          holdingMldu={holdingMldu}
          meses={meses}
          empresaIds={filtroEmpresaIds}
          initialVersaoA={searchParams.get("versao_a") || undefined}
          initialVersaoB={searchParams.get("versao_b") || undefined}
        />
        </div>
      ) : (
        <>
      {!loading && (
        <div className="sticky left-0 z-30 w-[100cqw] max-w-[100cqw] px-6 md:px-8 pb-4 bg-slate-50">
        <OrcamentoHeroStrip
          refLabel={`Realizado ${ano - 1}`}
          refVal={liquidoN1}
          realVal={liquido}
          varRs={varRs}
          varPerc={varPerc || 0}
          favoravel={favoravel}
          material={material}
          refCaption="Caixa líquido"
          caption={`Entradas ${formatMoedaCompact(data?.total_entradas || 0)} · Saídas ${formatMoedaCompact(saidas)} · AV sobre total de entradas`}
        />
        </div>
      )}

      <div className="mx-6 md:mx-8 mb-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
        <div className="sticky left-6 md:left-8 z-20 w-[calc(100cqw-3rem)] md:w-[calc(100cqw-4rem)] flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-slate-100 bg-white">
          <h2 className="font-bold text-slate-700">
            {visaoNome}
            {data?.visao?.is_padrao ? <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">padrão</span> : null}
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mr-1">Séries</span>
            {SERIES.map((s) => {
              const on = s.key === "real" || (s.key === "n1" && onN1) || (s.key === "orcado" && onOrcado) || (s.key === "forecast" && onForecast);
              const toggleSerie = () => {
                if (s.locked) return;
                if (s.key === "n1") setOnN1((v) => !v);
                if (s.key === "orcado") setOnOrcado((v) => !v);
                if (s.key === "forecast") setOnForecast((v) => !v);
              };
              return (
                <button
                  key={s.key}
                  type="button"
                  onClick={toggleSerie}
                  disabled={s.locked}
                  className={`px-2 py-1 rounded-md text-[11px] font-semibold border transition ${
                    on ? "bg-ml-green text-white border-ml-green" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                  } ${s.locked ? "opacity-90 cursor-default" : ""}`}
                >
                  {s.label}
                </button>
              );
            })}
            {onForecast && forecasts.length > 0 && (
              <select
                value={forecastId || ""}
                onChange={(e) => setForecastId(e.target.value ? Number(e.target.value) : undefined)}
                className="border border-slate-200 rounded-md px-2 py-1 text-[11px] font-semibold text-slate-700 bg-white"
              >
                {forecasts.map((f) => (
                  <option key={f.id} value={f.id}>{f.descricao}</option>
                ))}
              </select>
            )}
            <button
              type="button"
              onClick={() => setOnAhAvMensal((v) => !v)}
              className={`px-2 py-1 rounded-md text-[11px] font-semibold border transition ${
                onAhAvMensal ? "bg-ml-green text-white border-ml-green" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              AH/AV mensal
            </button>
            <button type="button" onClick={expandirTodos} className="text-xs font-semibold text-ml-green hover:underline ml-2">Expandir planos</button>
            <button type="button" onClick={recolherTodos} className="text-xs font-semibold text-slate-500 hover:underline">Recolher</button>
            <button
              type="button"
              onClick={() => exportarDfcExcel(linhas, active, ano, onAhAvMensal)}
              disabled={loading || linhas.length === 0}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm disabled:opacity-50"
            >
              <FileSpreadsheet className="w-4 h-4 text-brand-green" /> Excel
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-6"><AppLoadingState /></div>
        ) : (
          <table className="w-full text-sm min-w-[1800px]">
              <thead className="sticky top-0 z-20 bg-white">
                <tr className="text-[10px] uppercase tracking-wider text-slate-400">
                  <th rowSpan={2} className="sticky left-6 md:left-8 z-40 bg-white text-left px-3 py-2 font-semibold border-b border-slate-200 align-bottom">Categoria</th>
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
                          {SERIES.find((s) => s.key === key)?.short}
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
                      {SERIES.find((s) => s.key === key)?.short}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {linhas.map((row) => {
                  const open = expanded.has(row.id);
                  return (
                    <React.Fragment key={row.id}>
                      <DfcLine
                        row={row}
                        expanded={open}
                        onToggle={() => toggle(row.id)}
                        indent={indentOf(row.codigo)}
                        active={active}
                        ahAvMensal={onAhAvMensal}
                      />
                      {open && row.planos?.map((plano) => (
                        <DfcLine
                          key={`${row.id}-${plano.id}`}
                          row={{ ...plano, kind: "plano" }}
                          expanded={false}
                          indent={indentOf(row.codigo) + 1}
                          active={active}
                          ahAvMensal={onAhAvMensal}
                        />
                      ))}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
        )}
      </div>

      <p className="sticky left-0 z-10 w-[100cqw] max-w-[100cqw] px-6 md:px-8 pb-8 text-xs text-slate-400 bg-slate-50">
        Fonte: mesmos números de Orçado × Realizado, agrupados pela visão do Apoio (lida a cada carga). Planos fora da visão não entram.
        Cada mês mostra as séries ligadas (Real {ano}, Real {ano - 1}, Orçado; Forecast opcional). AH e AV no total do ano; mensal é opcional (AV sobre as entradas daquele mês).
        {" "}Não substitui <Link href="/dashboard/orcamento/geracao-caixa" className="text-ml-green font-semibold hover:underline">Geração de Caixa</Link>.
      </p>
        </>
      )}
    </div>
  );
}
