"use client";

import { Fragment, Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronDown, ChevronRight, FileSpreadsheet } from "lucide-react";
import { api } from "@/lib/api";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { CollapsibleFilterPanel } from "@/components/shared/CollapsibleFilterPanel";
import { formatMoedaCompact, formatMoedaK, MESES_STR } from "@/lib/orcamentoDesvioUi";

type Centro = { id: number; id_sienge?: string | null; nome?: string | null };
type Empreendimento = {
  id: string;
  project_name: string;
  city: string;
  status?: string;
  centros?: Centro[];
};
type PlanoDfc = {
  id: number | string;
  codigo: string;
  descricao: string;
  valores: Record<string, number>;
  valores_mes: Record<string, number>;
  total: number;
};
type LinhaDfc = {
  id: number;
  codigo: string;
  descricao: string;
  nivel: number;
  valores: Record<string, number>;
  valores_mes: Record<string, number>;
  total: number;
  planos?: PlanoDfc[];
};
type Conferencia = {
  lucro_dfc: number;
  lucro_lista: number;
  desvio: number;
  ok: boolean;
};
type DfcPayload = {
  empreendimento: Empreendimento;
  visao?: { nome?: string; is_padrao?: boolean };
  anos: string[];
  meses: string[];
  linhas: LinhaDfc[];
  conferencia: Conferencia;
};

const MESES_LABEL = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

function moneyClass(v: number) {
  if (v < 0) return "text-red-600";
  if (v > 0) return "text-slate-800";
  return "text-slate-400";
}

function Num({ v }: { v: number }) {
  return <span className={`tabular-nums ${moneyClass(v)}`}>{formatMoedaCompact(v)}</span>;
}

function mesesDoAno(ano: string) {
  return MESES_STR.map((_, i) => `${ano}-${String(i + 1).padStart(2, "0")}`);
}

function valorDaColuna(
  row: { valores?: Record<string, number>; valores_mes?: Record<string, number> },
  col: string,
  view: "ano" | "mes",
) {
  if (view === "mes") return row.valores_mes?.[col] || 0;
  return row.valores?.[col] || 0;
}

function parseAnosUrl(search: { get(name: string): string | null }) {
  const csv = (search.get("anos") || "").split(",").map((s) => s.trim()).filter(Boolean);
  if (csv.length) return csv;
  const legado = search.get("ano");
  return legado ? [legado] : [];
}

function buildDfcUrl(id: string, view: "ano" | "mes", anosSel: string[] = []) {
  const params = new URLSearchParams();
  if (id) params.set("id", id);
  if (view === "mes") params.set("view", "mes");
  if (view === "mes" && anosSel.length > 0) params.set("anos", anosSel.join(","));
  const qs = params.toString();
  return qs ? `/dashboard/tracking/dfc?${qs}` : "/dashboard/tracking/dfc";
}

async function exportarExcel(
  linhas: LinhaDfc[],
  colunas: string[],
  view: "ano" | "mes",
  labels: string[],
  nome: string,
) {
  const XLSX = await import("xlsx");
  const headers = ["Código", "Descrição", "Tipo", ...labels, "Vida"];
  const rows: (string | number)[][] = [];
  const push = (row: { codigo: string; descricao: string; valores?: Record<string, number>; valores_mes?: Record<string, number>; total: number }, tipo: string) => {
    rows.push([
      row.codigo || "",
      row.descricao || "",
      tipo,
      ...colunas.map((col) => valorDaColuna(row, col, view)),
      row.total || 0,
    ]);
  };
  for (const linha of linhas) {
    push(linha, "Categoria");
    for (const plano of linha.planos || []) push(plano, "Plano");
  }
  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "DFC");
  XLSX.writeFile(wb, `DFC_empreendimentos_${nome || "vida"}.xlsx`);
}

function TrackingDfcInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const idParam = searchParams.get("id") || "";
  const view = searchParams.get("view") === "mes" ? "mes" : "ano";
  const anosParam = parseAnosUrl(searchParams);

  const [empreendimentos, setEmpreendimentos] = useState<Empreendimento[]>([]);
  const [data, setData] = useState<DfcPayload | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDfc, setLoadingDfc] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [abertos, setAbertos] = useState<Set<number>>(new Set());

  useEffect(() => {
    let cancelled = false;
    setLoadingList(true);
    api
      .get("/tracking/dfc/empreendimentos", { timeout: 180000 })
      .then((res) => {
        if (cancelled) return;
        const items: Empreendimento[] = res.data?.items || [];
        setEmpreendimentos(items);
        const qs = new URLSearchParams(window.location.search);
        if (!qs.get("id") && items.length > 0) {
          const currentView = qs.get("view") === "mes" ? "mes" : "ano";
          router.replace(buildDfcUrl(items[0].id, currentView, parseAnosUrl(qs)));
        }
      })
      .catch(() => {
        if (!cancelled) setErro("Não foi possível carregar os empreendimentos.");
      })
      .finally(() => {
        if (!cancelled) setLoadingList(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    if (!idParam) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoadingDfc(true);
    setErro(null);
    setAbertos(new Set());
    api
      .get("/tracking/dfc", { params: { id: idParam }, timeout: 180000 })
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch(() => {
        if (!cancelled) {
          setData(null);
          setErro("Não foi possível montar o DFC deste empreendimento.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingDfc(false);
      });
    return () => {
      cancelled = true;
    };
  }, [idParam]);

  const anos = data?.anos || [];
  const anosFiltro = anos.filter((ano) => anosParam.includes(ano));
  const anosVisiveis = view === "mes" && anosFiltro.length > 0 ? anosFiltro : anos;
  const colunas = useMemo(() => {
    if (view === "mes") return anosVisiveis.flatMap((ano) => mesesDoAno(ano));
    return anos;
  }, [view, anosVisiveis, anos]);
  const colunaLabels = useMemo(() => {
    if (view === "mes") {
      return colunas.map((ym) => {
        const mes = Number(ym.slice(5, 7));
        return MESES_LABEL[mes - 1] || ym;
      });
    }
    return colunas;
  }, [view, colunas]);
  const excelLabels = useMemo(() => {
    if (view === "mes") {
      return colunas.map((ym) => {
        const ano = ym.slice(0, 4);
        const mes = Number(ym.slice(5, 7));
        return `${MESES_LABEL[mes - 1] || ym} ${ano}`;
      });
    }
    return colunas;
  }, [view, colunas]);

  const conferencia = data?.conferencia;
  const centros = data?.empreendimento?.centros || [];
  const visaoNome = data?.visao?.nome || "Visão DFC";
  const linhas = data?.linhas || [];
  const linhasComPlano = linhas.filter((l) => (l.planos || []).length > 0);
  const loading = loadingList || loadingDfc;

  const labelEmpreendimento = useMemo(() => {
    const item = empreendimentos.find((e) => e.id === idParam) || data?.empreendimento;
    if (!item) return "";
    return `${item.city} — ${item.project_name}`;
  }, [empreendimentos, idParam, data]);

  const irPara = (id: string, nextView: "ano" | "mes", nextAnos: string[] = []) => {
    const subset = nextView === "mes" && nextAnos.length > 0 && nextAnos.length < anos.length ? nextAnos : [];
    router.replace(buildDfcUrl(id, nextView, subset));
  };

  const toggleLinha = (id: number) => {
    setAbertos((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const limparFiltros = () => router.replace("/dashboard/tracking/dfc");

  return (
    <div className="flex flex-col flex-1 min-h-0 min-w-0 gap-4 overflow-hidden" translate="no" lang="pt-BR">
      <div className="shrink-0 space-y-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">DFC de empreendimentos</h1>
          <p className="text-slate-500 text-sm mt-1">
            Demonstrativo da vida do projeto pela {visaoNome} — mesmo caixa do acompanhamento. Saídas negativas.
          </p>
        </div>

        <CollapsibleFilterPanel
          activeFilterCount={(idParam ? 1 : 0) + (view === "mes" ? 1 : 0) + (anosFiltro.length > 0 ? 1 : 0)}
          defaultOpen
          onClear={limparFiltros}
        >
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-slate-500 font-medium mb-1 block">Empreendimento</label>
            <SearchableSelect
              options={empreendimentos.map((item) => ({
                id: item.id,
                label: `${item.city} — ${item.project_name}`,
              }))}
              value={idParam}
              onChange={(next) => {
                if (!next) {
                  limparFiltros();
                  return;
                }
                irPara(String(next), view, anosFiltro);
              }}
              placeholder="Todos"
              disabled={loadingList || empreendimentos.length === 0}
            />
          </div>
          <div className="min-w-[160px]">
            <label className="text-xs text-slate-500 font-medium mb-1 block">Período</label>
            <div className="flex items-center gap-1 rounded-lg border border-slate-300 bg-white p-0.5 h-[34px]">
              <button
                type="button"
                onClick={() => irPara(idParam, "ano")}
                className={`px-3 h-full rounded-md text-xs font-semibold transition-colors ${
                  view === "ano" ? "bg-ml-green text-white" : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                Ano
              </button>
              <button
                type="button"
                onClick={() => irPara(idParam, "mes")}
                className={`px-3 h-full rounded-md text-xs font-semibold transition-colors ${
                  view === "mes" ? "bg-ml-green text-white" : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                Mês
              </button>
            </div>
          </div>
          {view === "mes" ? (
            <div className="w-full md:w-56 z-10">
              <label className="text-xs text-slate-500 font-medium mb-1 block">Ano</label>
              <MultiSelect
                options={anos}
                value={anosFiltro}
                onChange={(vals) => irPara(idParam, "mes", vals)}
                placeholder="Todos"
                className="bg-white"
              />
            </div>
          ) : null}
        </CollapsibleFilterPanel>
      </div>

      {erro ? (
        <div className="shrink-0 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{erro}</div>
      ) : null}

      {conferencia && !loadingDfc ? (
        <div className="shrink-0 rounded-xl border border-slate-200 bg-white overflow-hidden">
          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] divide-y md:divide-y-0 md:divide-x divide-slate-100">
            <div className="px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5">Lucro da lista</p>
              <p className="text-xl font-bold text-slate-900 tabular-nums">{formatMoedaK(conferencia.lucro_lista)}</p>
              <p className="text-[11px] text-slate-500">Acompanhamento de empreendimentos</p>
            </div>
            <div
              className={`px-5 py-3 flex flex-col items-center justify-center text-center min-w-[168px] ${
                conferencia.ok ? "bg-emerald-50/80 text-emerald-800" : "bg-orange-50/80 text-orange-950"
              }`}
            >
              <p className="text-[10px] font-semibold uppercase tracking-wider opacity-70 mb-0.5">Desvio</p>
              <p className="text-xl font-bold tabular-nums">
                {conferencia.desvio > 0 ? "+" : ""}
                {formatMoedaK(conferencia.desvio)}
              </p>
            </div>
            <div className="px-4 py-3 md:text-right">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5">Lucro DFC</p>
              <p className="text-xl font-bold text-slate-900 tabular-nums">{formatMoedaK(conferencia.lucro_dfc)}</p>
            </div>
          </div>
          <div className="px-4 py-1.5 border-t border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-2">
            <span className="text-[11px] text-slate-500">
              {labelEmpreendimento}
              {centros.length > 0
                ? ` · centros ${centros.map((c) => c.id_sienge || c.nome).filter(Boolean).join(", ")}`
                : ""}
            </span>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                conferencia.ok ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
              }`}
            >
              {conferencia.ok ? "Confere" : "Diverge"}
            </span>
          </div>
        </div>
      ) : null}

      <div className="flex-1 min-h-0 flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="shrink-0 flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-slate-100 bg-white">
          <h2 className="font-bold text-slate-700">
            {visaoNome}
            {data?.visao?.is_padrao ? (
              <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">padrão</span>
            ) : null}
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            {linhasComPlano.length > 0 ? (
              <>
                <button
                  type="button"
                  onClick={() => setAbertos(new Set(linhasComPlano.map((l) => l.id)))}
                  className="text-xs font-semibold text-ml-green hover:underline"
                >
                  Expandir planos
                </button>
                <button type="button" onClick={() => setAbertos(new Set())} className="text-xs font-semibold text-slate-500 hover:underline">
                  Recolher
                </button>
              </>
            ) : null}
            <button
              type="button"
              onClick={() =>
                exportarExcel(
                  linhas,
                  colunas,
                  view,
                  excelLabels,
                  data?.empreendimento?.project_name || "vida",
                )
              }
              disabled={loading || linhas.length === 0}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm disabled:opacity-50"
            >
              <FileSpreadsheet className="w-4 h-4 text-brand-green" /> Excel
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-6">
            <AppLoadingState title="Montando o DFC da vida do projeto…" hint="Usa o mesmo caixa do acompanhamento." />
          </div>
        ) : (
          <div className="flex-1 min-h-0 overflow-auto">
            <table className="w-full text-sm min-w-[1100px]">
              <thead className="sticky top-0 z-20 bg-white">
                {view === "mes" ? (
                  <>
                    <tr className="text-[10px] uppercase tracking-wider text-slate-400">
                      <th
                        rowSpan={2}
                        className="sticky left-0 z-40 bg-white text-left px-3 py-2 font-semibold border-b border-slate-200 align-bottom"
                      >
                        Categoria
                      </th>
                      {anosVisiveis.map((ano) => (
                        <th
                          key={ano}
                          colSpan={12}
                          className="px-1.5 py-1 text-center font-semibold whitespace-nowrap border-b border-l border-slate-200"
                        >
                          {ano}
                        </th>
                      ))}
                      <th
                        rowSpan={2}
                        className="px-2 py-2 text-right font-semibold whitespace-nowrap border-b border-l border-slate-200 bg-slate-50 align-bottom"
                      >
                        Vida
                      </th>
                    </tr>
                    <tr className="text-[10px] uppercase tracking-wider text-slate-400">
                      {anosVisiveis.map((ano) =>
                        MESES_LABEL.map((mes, i) => (
                          <th
                            key={`${ano}-${i}`}
                            className={`px-1.5 py-1 text-right font-semibold whitespace-nowrap border-b border-slate-200 ${i === 0 ? "border-l" : ""}`}
                          >
                            {mes}
                          </th>
                        )),
                      )}
                    </tr>
                  </>
                ) : (
                  <tr className="text-[10px] uppercase tracking-wider text-slate-400">
                    <th className="sticky left-0 z-40 bg-white text-left px-3 py-2 font-semibold border-b border-slate-200">
                      Categoria
                    </th>
                    {colunaLabels.map((label, i) => (
                      <th
                        key={colunas[i] || label}
                        className="px-1.5 py-2 text-right font-semibold whitespace-nowrap border-b border-l border-slate-200"
                      >
                        {label}
                      </th>
                    ))}
                    <th className="px-2 py-2 text-right font-semibold whitespace-nowrap border-b border-l border-slate-200 bg-slate-50">
                      Vida
                    </th>
                  </tr>
                )}
              </thead>
              <tbody>
                {linhas.map((linha) => {
                  const temPlanos = (linha.planos || []).length > 0;
                  const aberto = abertos.has(linha.id);
                  const indent = linha.nivel;
                  return (
                    <Fragment key={linha.id}>
                      <tr className="bg-white hover:bg-slate-50">
                        <td className="sticky left-0 z-10 px-3 py-2 border-b border-slate-100 min-w-[280px] bg-white">
                          <div className="flex items-center gap-1" style={{ paddingLeft: indent * 16 }}>
                            {temPlanos ? (
                              <button
                                type="button"
                                onClick={() => toggleLinha(linha.id)}
                                className="p-0.5 rounded hover:bg-slate-200"
                                aria-expanded={aberto}
                              >
                                {aberto ? (
                                  <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                                ) : (
                                  <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                                )}
                              </button>
                            ) : (
                              <span className="w-4" />
                            )}
                            <span className="font-mono text-xs text-slate-400 w-14 shrink-0">{linha.codigo}</span>
                            <span className="text-sm truncate font-semibold text-slate-800">{linha.descricao}</span>
                          </div>
                        </td>
                        {colunas.map((col) => (
                          <td
                            key={col}
                            className="px-1.5 py-2 border-b border-l border-slate-100 text-right text-[11px] whitespace-nowrap font-semibold"
                          >
                            <Num v={valorDaColuna(linha, col, view)} />
                          </td>
                        ))}
                        <td className="px-2 py-2 border-b border-l border-slate-100 text-right text-[11px] font-semibold whitespace-nowrap bg-slate-50/80">
                          <Num v={linha.total || 0} />
                        </td>
                      </tr>
                      {aberto &&
                        (linha.planos || []).map((plano) => (
                          <tr key={`${linha.id}-${plano.id}`} className="bg-slate-50/70">
                            <td className="sticky left-0 z-10 px-3 py-2 border-b border-slate-100 min-w-[280px] bg-slate-50">
                              <div className="flex items-center gap-1" style={{ paddingLeft: (indent + 1) * 16 }}>
                                <span className="w-4" />
                                <span className="font-mono text-xs text-slate-400 w-14 shrink-0 opacity-80">{plano.codigo}</span>
                                <span className="text-sm truncate text-slate-600">{plano.descricao}</span>
                              </div>
                            </td>
                            {colunas.map((col) => (
                              <td
                                key={col}
                                className="px-1.5 py-2 border-b border-l border-slate-100 text-right text-[11px] whitespace-nowrap"
                              >
                                <Num v={valorDaColuna(plano, col, view)} />
                              </td>
                            ))}
                            <td className="px-2 py-2 border-b border-l border-slate-100 text-right text-[11px] font-semibold whitespace-nowrap bg-slate-50/80">
                              <Num v={plano.total || 0} />
                            </td>
                          </tr>
                        ))}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="shrink-0 text-xs text-slate-400">
        Fonte: mesmo caixa do acompanhamento de empreendimentos, agrupado pela visão do Apoio. Planos fora da visão caem em receita de vendas ou administrativas.
        A coluna Vida é o total do projeto. No recorte mensal, Ano em branco (Todos) mostra a vida inteira.
      </p>
    </div>
  );
}

export default function TrackingDfcPage() {
  return (
    <Suspense fallback={<AppLoadingState title="Carregando DFC…" />}>
      <TrackingDfcInner />
    </Suspense>
  );
}
