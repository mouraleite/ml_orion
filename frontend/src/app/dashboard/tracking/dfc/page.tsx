"use client";

import { Fragment, Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronDown, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { CollapsibleFilterPanel } from "@/components/shared/CollapsibleFilterPanel";

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

const MESES_CURTO = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

const formatMi = (val: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(val);

function formatCelula(val: number) {
  if (Math.abs(val) < 0.5) return "—";
  const abs = Math.abs(val);
  const sign = val < 0 ? "-" : "";
  if (abs >= 1_000_000) return `${sign}R$ ${(abs / 1_000_000).toFixed(1)} mi`;
  if (abs >= 1_000) return `${sign}R$ ${(abs / 1_000).toFixed(0)} mil`;
  return formatMi(val);
}

function corValor(val: number) {
  if (Math.abs(val) < 0.5) return "text-slate-300";
  if (val < 0) return "text-red-600";
  return "text-slate-800";
}

function labelMes(ym: string) {
  const [ano, mes] = ym.split("-");
  const idx = Number(mes) - 1;
  if (!ano || idx < 0 || idx > 11) return ym;
  return `${MESES_CURTO[idx]}/${ano.slice(2)}`;
}

function mesesDoAno(ano: string) {
  return MESES_CURTO.map((_, i) => `${ano}-${String(i + 1).padStart(2, "0")}`);
}

function valorDaColuna(row: { valores?: Record<string, number>; valores_mes?: Record<string, number> }, col: string, view: "ano" | "mes") {
  if (view === "mes") return row.valores_mes?.[col] || 0;
  return row.valores?.[col] || 0;
}

function buildDfcUrl(id: string, view: "ano" | "mes", anoMes: string) {
  const params = new URLSearchParams();
  if (id) params.set("id", id);
  if (view === "mes") params.set("view", "mes");
  if (view === "mes" && anoMes) params.set("ano", anoMes);
  const qs = params.toString();
  return qs ? `/dashboard/tracking/dfc?${qs}` : "/dashboard/tracking/dfc";
}

function TrackingDfcInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const idParam = searchParams.get("id") || "";
  const view = searchParams.get("view") === "mes" ? "mes" : "ano";
  const anoParam = searchParams.get("ano") || "";

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
          router.replace(buildDfcUrl(items[0].id, currentView, qs.get("ano") || ""));
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
  const anoMes = anoParam && anos.includes(anoParam) ? anoParam : anos[anos.length - 1] || "";

  const colunas = useMemo(() => {
    if (view === "mes") return anoMes ? mesesDoAno(anoMes) : [];
    return anos;
  }, [view, anoMes, anos]);

  const conferencia = data?.conferencia;
  const centros = data?.empreendimento?.centros || [];
  const visaoNome = data?.visao?.nome || "Visão DFC";
  const linhasComPlano = (data?.linhas || []).filter((l) => (l.planos || []).length > 0);

  const labelEmpreendimento = useMemo(() => {
    const item = empreendimentos.find((e) => e.id === idParam) || data?.empreendimento;
    if (!item) return "";
    return `${item.city} — ${item.project_name}`;
  }, [empreendimentos, idParam, data]);

  const irPara = (id: string, nextView: "ano" | "mes", nextAno: string) => {
    router.replace(buildDfcUrl(id, nextView, nextAno));
  };

  const toggleLinha = (id: number) => {
    setAbertos((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300" translate="no" lang="pt-BR">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">DFC DE EMPREENDIMENTOS</h1>
        <p className="text-sm text-slate-500 mt-1">
          Vida do projeto no padrão DFC. Mesmo caixa do acompanhamento — não usa orçamento nem forecast.
        </p>
      </div>

      <CollapsibleFilterPanel
        activeFilterCount={(idParam ? 1 : 0) + (view === "mes" ? 1 : 0)}
        defaultOpen
        onClear={() => router.replace("/dashboard/tracking/dfc")}
      >
        <div className="flex-1 min-w-[280px]">
          <label className="text-xs text-slate-500 font-medium mb-1 block">Empreendimento</label>
          <SearchableSelect
            options={empreendimentos.map((item) => ({
              id: item.id,
              label: `${item.city} — ${item.project_name}`,
            }))}
            value={idParam}
            onChange={(next) => {
              if (!next) {
                router.replace("/dashboard/tracking/dfc");
                return;
              }
              irPara(String(next), view, anoMes);
            }}
            placeholder="Todos"
            disabled={loadingList || empreendimentos.length === 0}
          />
        </div>
        <div className="min-w-[160px]">
          <label className="text-xs text-slate-500 font-medium mb-1 block">Período</label>
          <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-0.5">
            <button
              type="button"
              onClick={() => irPara(idParam, "ano", anoMes)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                view === "ano" ? "bg-slate-800 text-white" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              Ano
            </button>
            <button
              type="button"
              onClick={() => irPara(idParam, "mes", anoMes || anos[anos.length - 1] || "")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                view === "mes" ? "bg-slate-800 text-white" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              Mês
            </button>
          </div>
        </div>
        {view === "mes" ? (
          <div className="min-w-[140px]">
            <label className="text-xs text-slate-500 font-medium mb-1 block">Ano</label>
            <SearchableSelect
              options={anos.map((ano) => ({ id: ano, label: ano }))}
              value={anoMes}
              onChange={(next) => irPara(idParam, "mes", String(next || ""))}
              placeholder="Todos"
              disabled={!anos.length}
              clearable={false}
            />
          </div>
        ) : null}
      </CollapsibleFilterPanel>
      {centros.length > 0 && (
        <p className="text-xs text-slate-500 -mt-2">
          Centros somados: {centros.map((c) => c.id_sienge || c.nome).filter(Boolean).join(" · ")}
        </p>
      )}

      {conferencia && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4 border border-slate-200 shadow-sm">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Lucro DFC (vida)</p>
            <p className={`text-xl font-bold tabular-nums ${corValor(conferencia.lucro_dfc)}`}>
              {formatCelula(conferencia.lucro_dfc)}
            </p>
          </Card>
          <Card className="p-4 border border-slate-200 shadow-sm">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Lucro da lista</p>
            <p className={`text-xl font-bold tabular-nums ${corValor(conferencia.lucro_lista)}`}>
              {formatCelula(conferencia.lucro_lista)}
            </p>
          </Card>
          <Card className="p-4 border border-slate-200 shadow-sm">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Desvio</p>
            <p className={`text-xl font-bold tabular-nums ${corValor(conferencia.desvio)}`}>
              {formatCelula(conferencia.desvio)}
            </p>
          </Card>
          <Card
            className={`p-4 border shadow-sm ${
              conferencia.ok ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"
            }`}
          >
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Conferência</p>
            <p className={`text-sm font-bold ${conferencia.ok ? "text-emerald-700" : "text-amber-800"}`}>
              {conferencia.ok ? "Lucro do DFC bate com a lista" : "Lucro do DFC diverge da lista"}
            </p>
            <p className="text-xs text-slate-500 mt-1">{labelEmpreendimento}</p>
          </Card>
        </div>
      )}

      {erro && (
        <Card className="p-4 border border-red-200 bg-red-50 text-sm text-red-700">{erro}</Card>
      )}

      {(loadingList || loadingDfc) && (
        <AppLoadingState title="Montando o DFC da vida do projeto…" hint="Usa o mesmo caixa do acompanhamento." />
      )}

      {!loadingDfc && data && (
        <Card className="p-0 border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-bold text-slate-700">
              {visaoNome}
              {data.visao?.is_padrao ? (
                <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">padrão</span>
              ) : null}
            </h2>
            <div className="flex items-center gap-3">
              {linhasComPlano.length > 0 ? (
                <>
                  <button
                    type="button"
                    onClick={() => setAbertos(new Set(linhasComPlano.map((l) => l.id)))}
                    className="text-xs font-semibold text-ml-green hover:underline"
                  >
                    Expandir planos
                  </button>
                  <button
                    type="button"
                    onClick={() => setAbertos(new Set())}
                    className="text-xs font-semibold text-slate-500 hover:underline"
                  >
                    Recolher
                  </button>
                </>
              ) : null}
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Total da vida</span>
            </div>
          </div>
          <div className="overflow-auto max-h-[70vh]">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 z-10 bg-slate-50 text-[10px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="text-left font-semibold px-4 py-2 sticky left-0 bg-slate-50 min-w-[300px] shadow-[1px_0_0_0_#e2e8f0]">
                    Grupo DFC
                  </th>
                  {colunas.map((col) => (
                    <th key={col} className="text-right font-semibold px-3 py-2 min-w-[88px] tabular-nums">
                      {view === "mes" ? labelMes(col) : col}
                    </th>
                  ))}
                  <th className="text-right font-semibold px-4 py-2 min-w-[120px] bg-slate-100">Vida</th>
                </tr>
              </thead>
              <tbody>
                {(data.linhas || []).map((linha) => {
                  const topo = linha.nivel === 0;
                  const temPlanos = (linha.planos || []).length > 0;
                  const aberto = abertos.has(linha.id);
                  return (
                    <Fragment key={linha.id}>
                      <tr className={topo ? "bg-slate-50/80 font-semibold" : "hover:bg-slate-50/60"}>
                        <td
                          className={`px-4 py-1.5 sticky left-0 ${topo ? "bg-slate-50" : "bg-white"} shadow-[1px_0_0_0_#e2e8f0]`}
                          style={{ paddingLeft: `${16 + linha.nivel * 14}px` }}
                        >
                          {temPlanos ? (
                            <button
                              type="button"
                              onClick={() => toggleLinha(linha.id)}
                              className="inline-flex items-center gap-1 text-left"
                              aria-expanded={aberto}
                            >
                              {aberto ? (
                                <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                              ) : (
                                <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                              )}
                              <span className="text-[10px] text-slate-400 mr-1 tabular-nums">{linha.codigo}</span>
                              {linha.descricao}
                            </button>
                          ) : (
                            <>
                              <span className="text-[10px] text-slate-400 mr-2 tabular-nums">{linha.codigo}</span>
                              {linha.descricao}
                            </>
                          )}
                        </td>
                        {colunas.map((col) => {
                          const valor = valorDaColuna(linha, col, view);
                          return (
                            <td key={col} className={`px-3 py-1.5 text-right tabular-nums ${corValor(valor)}`}>
                              {formatCelula(valor)}
                            </td>
                          );
                        })}
                        <td className={`px-4 py-1.5 text-right tabular-nums bg-slate-50 ${corValor(linha.total || 0)}`}>
                          {formatCelula(linha.total || 0)}
                        </td>
                      </tr>
                      {aberto &&
                        (linha.planos || []).map((plano) => (
                          <tr key={`${linha.id}-${plano.id}`} className="hover:bg-slate-50/40 text-[13px]">
                            <td
                              className="px-4 py-1 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] text-slate-600"
                              style={{ paddingLeft: `${32 + linha.nivel * 14}px` }}
                            >
                              {plano.codigo ? (
                                <span className="text-[10px] text-slate-400 mr-2 tabular-nums">{plano.codigo}</span>
                              ) : null}
                              {plano.descricao}
                            </td>
                            {colunas.map((col) => {
                              const valor = valorDaColuna(plano, col, view);
                              return (
                                <td key={col} className={`px-3 py-1 text-right tabular-nums ${corValor(valor)}`}>
                                  {formatCelula(valor)}
                                </td>
                              );
                            })}
                            <td className={`px-4 py-1 text-right tabular-nums bg-slate-50 ${corValor(plano.total || 0)}`}>
                              {formatCelula(plano.total || 0)}
                            </td>
                          </tr>
                        ))}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
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
