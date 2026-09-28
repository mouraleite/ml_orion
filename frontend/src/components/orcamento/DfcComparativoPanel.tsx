"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, FileSpreadsheet, GitCompare } from "lucide-react";
import { orcamentoService } from "@/services/orcamento";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { formatMoedaCompact, formatPerc } from "@/lib/orcamentoDesvioUi";
import { isDepartmentContextId } from "@/lib/useActiveDepartmentId";

const MESES_STR = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"] as const;

type CompRow = {
  kind: "categoria" | "plano";
  id: number;
  codigo: string;
  descricao: string;
  total_a: number;
  total_b: number;
  var_rs: number;
  var_perc: number | null;
  meses_a?: Record<string, number>;
  meses_b?: Record<string, number>;
  meses_var?: Record<string, number>;
  planos?: CompRow[];
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

async function exportComparativoExcel(
  linhas: CompRow[],
  labelA: string,
  labelB: string,
  ano: number,
  porMes: boolean,
) {
  const XLSX = await import("xlsx");
  const headers = ["Código", "Descrição", "Tipo", labelA, labelB, "Var. R$", "Var. %"];
  if (porMes) {
    for (const m of MESES_STR) {
      headers.push(`${m} ${labelA}`, `${m} ${labelB}`, `${m} Var`);
    }
  }
  const rows: (string | number)[][] = [];
  const push = (row: CompRow, tipo: string) => {
    const line: (string | number)[] = [
      row.codigo || "",
      row.descricao || "",
      tipo,
      row.total_a || 0,
      row.total_b || 0,
      row.var_rs || 0,
      row.var_perc == null ? "" : row.var_perc * 100,
    ];
    if (porMes) {
      for (const m of MESES_STR) {
        line.push(row.meses_a?.[m] || 0, row.meses_b?.[m] || 0, row.meses_var?.[m] || 0);
      }
    }
    rows.push(line);
  };
  for (const linha of linhas) {
    push(linha, "Categoria");
    for (const plano of linha.planos || []) push(plano, "Plano");
  }
  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "DFC Comparativo");
  XLSX.writeFile(wb, `DFC_comparativo_${ano}.xlsx`);
}

function CompLine({
  row,
  expanded,
  onToggle,
  indent,
  porMes,
}: {
  row: CompRow;
  expanded: boolean;
  onToggle?: () => void;
  indent: number;
  porMes: boolean;
}) {
  const isCat = row.kind !== "plano";
  const hasKids = isCat && (row.planos?.length || 0) > 0;
  return (
    <tr className={isCat ? "bg-white hover:bg-slate-50" : "bg-slate-50/70"}>
      <td className="sticky left-0 z-10 bg-inherit px-3 py-2 border-b border-slate-100 min-w-[280px]">
        <div className="flex items-center gap-1" style={{ paddingLeft: indent * 16 }}>
          {hasKids ? (
            <button type="button" onClick={onToggle} className="p-0.5 rounded hover:bg-slate-200">
              {expanded ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
            </button>
          ) : (
            <span className="w-4" />
          )}
          <span className={`font-mono text-xs text-slate-400 w-14 shrink-0`}>{row.codigo}</span>
          <span className={`text-sm truncate ${isCat ? "font-semibold text-slate-800" : "text-slate-600"}`}>{row.descricao}</span>
        </div>
      </td>
      {!porMes && (
        <>
          <td className="px-2 py-2 border-b border-slate-100 text-right text-xs whitespace-nowrap border-l border-slate-200">
            <Num v={row.total_a} />
          </td>
          <td className="px-2 py-2 border-b border-slate-100 text-right text-xs whitespace-nowrap">
            <Num v={row.total_b} />
          </td>
          <td className="px-2 py-2 border-b border-slate-100 text-right text-xs font-semibold whitespace-nowrap">
            <Num v={row.var_rs} />
          </td>
          <td className="px-2 py-2 border-b border-slate-100 text-right text-xs whitespace-nowrap">
            <Perc v={row.var_perc} />
          </td>
        </>
      )}
      {porMes &&
        MESES_STR.map((m) => (
          <React.Fragment key={m}>
            <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap border-l border-slate-200">
              <Num v={row.meses_a?.[m] || 0} />
            </td>
            <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] whitespace-nowrap">
              <Num v={row.meses_b?.[m] || 0} />
            </td>
            <td className="px-1.5 py-2 border-b border-slate-100 text-right text-[11px] font-semibold whitespace-nowrap">
              <Num v={row.meses_var?.[m] || 0} />
            </td>
          </React.Fragment>
        ))}
    </tr>
  );
}

export function DfcComparativoPanel({
  ano,
  deptId,
  holdingMldu,
  meses,
  empresaIds,
  initialVersaoA,
  initialVersaoB,
}: {
  ano: number;
  deptId: number;
  holdingMldu: boolean;
  meses: string[];
  empresaIds: string[];
  initialVersaoA?: string;
  initialVersaoB?: string;
}) {
  const [versaoA, setVersaoA] = useState(initialVersaoA || "");
  const [versaoB, setVersaoB] = useState(initialVersaoB || "");
  const [versoes, setVersoes] = useState<{ id: string; descricao: string }[]>([]);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [porMes, setPorMes] = useState(false);

  useEffect(() => {
    if (initialVersaoA) setVersaoA(initialVersaoA);
    if (initialVersaoB) setVersaoB(initialVersaoB);
  }, [initialVersaoA, initialVersaoB]);

  const load = useCallback(async () => {
    if (!isDepartmentContextId(deptId) || !versaoA || !versaoB) {
      setData(null);
      return;
    }
    setLoading(true);
    try {
      const res = await orcamentoService.getDfcComparativo(
        ano,
        deptId,
        versaoA,
        versaoB,
        holdingMldu,
        meses.length ? meses : undefined,
        empresaIds.length ? empresaIds : undefined,
      );
      setData(res);
      setVersoes(res.versoes_disponiveis || []);
      setExpanded(new Set((res.linhas || []).map((l: CompRow) => l.id)));
    } catch (e) {
      console.error(e);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [ano, deptId, versaoA, versaoB, holdingMldu, meses, empresaIds]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!isDepartmentContextId(deptId)) return;
    orcamentoService
      .listarVersoes(ano, "CONSOLIDADO", deptId)
      .then((v) => setVersoes(Array.isArray(v) ? v : []))
      .catch(() => {});
  }, [ano, deptId]);

  const linhas: CompRow[] = data?.linhas || [];
  const labelA = data?.label_a || versoes.find((v) => v.id === versaoA)?.descricao || "Versão A";
  const labelB = data?.label_b || versoes.find((v) => v.id === versaoB)?.descricao || "Versão B";
  const indentOf = (codigo: string) => (codigo.match(/\./g) || []).length;

  const hero = useMemo(() => {
    if (!data) return null;
    return {
      a: data.liquido_a || 0,
      b: data.liquido_b || 0,
      varRs: data.var_liquido || 0,
      varPerc: data.var_liquido_perc,
    };
  }, [data]);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[200px] flex-1">
            <label className="block text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-1">Versão base</label>
            <select
              value={versaoA}
              onChange={(e) => setVersaoA(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white"
            >
              <option value="">Selecione…</option>
              {versoes.map((v) => (
                <option key={v.id} value={v.id}>{v.descricao}</option>
              ))}
            </select>
          </div>
          <div className="min-w-[200px] flex-1">
            <label className="block text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-1">Versão comparada</label>
            <select
              value={versaoB}
              onChange={(e) => setVersaoB(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white"
            >
              <option value="">Selecione…</option>
              {versoes.map((v) => (
                <option key={`b-${v.id}`} value={v.id}>{v.descricao}</option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={load}
            disabled={!versaoA || !versaoB || loading}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold bg-ml-green text-white disabled:opacity-50"
          >
            <GitCompare className="w-4 h-4" />
            Comparar no DFC
          </button>
        </div>
        <p className="text-[11px] text-slate-500 mt-2">
          Mesma árvore da Visão DFC — colunas Base · Comparada · variação. Saídas negativas.
        </p>
      </div>

      {hero && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-[10px] font-semibold uppercase text-slate-400">Líquido · {labelA}</p>
            <p className="text-lg font-bold tabular-nums text-slate-800 mt-1"><Num v={hero.a} /></p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-[10px] font-semibold uppercase text-slate-400">Líquido · {labelB}</p>
            <p className="text-lg font-bold tabular-nums text-slate-800 mt-1"><Num v={hero.b} /></p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-[10px] font-semibold uppercase text-slate-400">Variação R$</p>
            <p className="text-lg font-bold tabular-nums mt-1"><Num v={hero.varRs} /></p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-[10px] font-semibold uppercase text-slate-400">Variação %</p>
            <p className="text-lg font-bold tabular-nums mt-1"><Perc v={hero.varPerc} /></p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-slate-100">
          <h2 className="font-bold text-slate-700">
            {data?.visao?.nome || "Visão DFC"}
            <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">comparativo</span>
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setPorMes((v) => !v)}
              className={`px-2 py-1 rounded-md text-[11px] font-semibold border ${
                porMes ? "bg-ml-green text-white border-ml-green" : "bg-white text-slate-600 border-slate-200"
              }`}
            >
              Por mês
            </button>
            <button type="button" onClick={() => setExpanded(new Set(linhas.map((l) => l.id)))} className="text-xs font-semibold text-ml-green hover:underline">
              Expandir
            </button>
            <button type="button" onClick={() => setExpanded(new Set())} className="text-xs font-semibold text-slate-500 hover:underline">
              Recolher
            </button>
            <button
              type="button"
              disabled={!linhas.length}
              onClick={() => exportComparativoExcel(linhas, labelA, labelB, ano, porMes)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50"
            >
              <FileSpreadsheet className="w-4 h-4" /> Excel completo
            </button>
          </div>
        </div>

        {!versaoA || !versaoB ? (
          <p className="p-8 text-center text-sm text-slate-500">Selecione as duas versões para montar o DFC comparativo.</p>
        ) : loading ? (
          <div className="p-6"><AppLoadingState /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className={`w-full text-sm ${porMes ? "min-w-[2200px]" : "min-w-[720px]"}`}>
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-200">
                  <th className="sticky left-0 z-20 bg-white text-left px-3 py-2 font-semibold">Categoria</th>
                  {!porMes && (
                    <>
                      <th className="px-2 py-2 text-right font-semibold border-l border-slate-200 max-w-[140px] truncate">{labelA}</th>
                      <th className="px-2 py-2 text-right font-semibold max-w-[140px] truncate">{labelB}</th>
                      <th className="px-2 py-2 text-right font-semibold">Var. R$</th>
                      <th className="px-2 py-2 text-right font-semibold">Var. %</th>
                    </>
                  )}
                  {porMes &&
                    MESES_STR.map((m) => (
                      <th key={m} colSpan={3} className="px-1 py-2 text-center font-semibold border-l border-slate-200 uppercase">
                        {m}
                      </th>
                    ))}
                </tr>
                {porMes && (
                  <tr className="text-[9px] uppercase tracking-wider text-slate-400 border-b border-slate-200">
                    <th className="sticky left-0 z-20 bg-white" />
                    {MESES_STR.map((m) => (
                      <React.Fragment key={m}>
                        <th className="px-1 py-1 text-right font-semibold border-l border-slate-200">A</th>
                        <th className="px-1 py-1 text-right font-semibold">B</th>
                        <th className="px-1 py-1 text-right font-semibold">Δ</th>
                      </React.Fragment>
                    ))}
                  </tr>
                )}
              </thead>
              <tbody>
                {linhas.map((row) => {
                  const open = expanded.has(row.id);
                  return (
                    <React.Fragment key={row.id}>
                      <CompLine
                        row={row}
                        expanded={open}
                        onToggle={() =>
                          setExpanded((prev) => {
                            const next = new Set(prev);
                            next.has(row.id) ? next.delete(row.id) : next.add(row.id);
                            return next;
                          })
                        }
                        indent={indentOf(row.codigo)}
                        porMes={porMes}
                      />
                      {open &&
                        (row.planos || []).map((p) => (
                          <CompLine key={p.id} row={p} expanded={false} indent={indentOf(row.codigo) + 1} porMes={porMes} />
                        ))}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
            {!linhas.length && (
              <p className="p-8 text-center text-sm text-slate-500">Sem linhas na Visão DFC para estas versões.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
