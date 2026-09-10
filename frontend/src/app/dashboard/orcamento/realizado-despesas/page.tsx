"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { orcamentoService } from "@/services/orcamento";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId, isDepartmentContextId } from "@/lib/useActiveDepartmentId";
import {
  RealizadoDespesasDrillTable,
  ParcelaDespesa,
  exportParcelasCsv,
  formatMoedaDrill,
} from "@/components/orcamento/RealizadoDespesasDrillTable";
import { useOrcamentoDeepLinkFilters } from "@/lib/orcamentoNavigation";
import { OrcamentoFlyoutFilterBar } from "@/components/orcamento/OrcamentoFlyoutFilterBar";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { useEmpresaCadastroFilter } from "@/hooks/useEmpresaCadastroFilter";
import { filterItensPorEmpresaIds } from "@/lib/gridFilters";
import {
  AlertTriangle, Download, BarChart2, Search, Layers, ArrowLeft,
} from "lucide-react";

export default function RealizadoDespesasPage() {
  const router = useRouter();
  const deptId = useActiveDepartmentId();
  const { holdingMldu, setHoldingMldu, canUseHoldingMldu } = useHoldingMldu("orcamento");
  const [ano, setAno] = useState(new Date().getFullYear());
  const [meses, setMeses] = useState<string[]>([]);
  const { filtroEmpresaIds, setFiltroEmpresaIds, empresaOpcoes } = useEmpresaCadastroFilter();
  const [produtoId, setProdutoId] = useState<number | "">("");
  const [planoId, setPlanoId] = useState<number | "">("");
  const [busca, setBusca] = useState("");
  const [buscaApplied, setBuscaApplied] = useState("");

  useOrcamentoDeepLinkFilters({
    setAno,
    setMeses,
    setProdutoId,
    setPlanoId,
    setBusca,
    setBuscaApplied,
  });

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isDepartmentContextId(deptId)) return;
    setLoading(true);
    setError(null);
    try {
      const res = await orcamentoService.getRealizadoDespesas(ano, deptId, {
        holdingMldu,
        produtoId: produtoId === "" ? undefined : produtoId,
        planoId: planoId === "" ? undefined : planoId,
        busca: buscaApplied.trim() || undefined,
      });
      setData(res);
    } catch {
      setError("Erro ao carregar parcelas de Contas a Pagar.");
    } finally {
      setLoading(false);
    }
  }, [ano, deptId, holdingMldu, produtoId, planoId, buscaApplied]);

  useEffect(() => { load(); }, [load]);

  const transacoes: ParcelaDespesa[] = filterItensPorEmpresaIds(
    data?.transacoes || [],
    data?.opcoes_produtos || [],
    filtroEmpresaIds,
  );
  const filtered = meses.length
    ? transacoes.filter((t) => t.mes && meses.includes(t.mes))
    : transacoes;
  const total = filtered.reduce((s, t) => s + t.valor, 0);

  const produtos = data?.opcoes_produtos || [];
  const planos = data?.opcoes_planos || [];

  return (
    <div className="space-y-4 pb-10 flex flex-col min-h-[calc(100vh-120px)]">
      <div className="shrink-0">
        <button
          type="button"
          onClick={() => {
            if (typeof window !== "undefined" && window.history.length > 1) {
              router.back();
              return;
            }
            router.push("/dashboard/orcamento/realizado");
          }}
          className="inline-flex items-center gap-1 text-sm font-semibold text-slate-500 hover:text-slate-800 mb-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Voltar
        </button>
        <h1 className="text-2xl font-bold text-slate-800">Realizado Detalhado — Contas a Pagar</h1>
        <p className="text-slate-500 text-sm mt-1">
          Parcelas pagas do Sienge: credor, documento, número e valor
        </p>
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
        mesesPlaceholder="Todos os meses"
        ano={ano}
        onAnoChange={setAno}
        showModo={false}
        onRefresh={load}
        loading={loading}
      >
        <select
          value={produtoId}
          onChange={(e) => setProdutoId(e.target.value === "" ? "" : Number(e.target.value))}
          className="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white min-w-[160px]"
        >
          <option value="">Todos os produtos</option>
          {produtos.map((p: any) => (
            <option key={p.id} value={p.id}>{p.nome}</option>
          ))}
        </select>
        <select
          value={planoId}
          onChange={(e) => setPlanoId(e.target.value === "" ? "" : Number(e.target.value))}
          className="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white min-w-[180px]"
        >
          <option value="">Todos os planos</option>
          {planos.map((p: any) => (
            <option key={p.id} value={p.id}>{p.nome}</option>
          ))}
        </select>
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") setBuscaApplied(busca);
            }}
            placeholder="Buscar credor, documento ou nº…"
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-white"
          />
        </div>
        <button
          type="button"
          onClick={() => setBuscaApplied(busca)}
          className="px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          Buscar
        </button>
        <button
          type="button"
          onClick={() => exportParcelasCsv(filtered, `realizado-cp-${ano}.csv`)}
          disabled={!filtered.length}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-40"
        >
          <Download className="w-4 h-4" />
          CSV
        </button>
        <Link
          href="/dashboard/orcamento/analitico-gastos-2"
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <Layers className="w-4 h-4" />
          Analítico II
        </Link>
        <Link
          href="/dashboard/orcamento/analitico-gastos-1"
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <BarChart2 className="w-4 h-4" />
          Analítico I
        </Link>
      </OrcamentoFlyoutFilterBar>

      {holdingMldu && <HoldingMlduBanner avisos={data?.holding_avisos} />}

      <p className="text-[11px] text-slate-500 tabular-nums shrink-0 px-1">
        <strong className="text-slate-800">{filtered.length}</strong> parcelas
        <span className="mx-2 text-slate-300">·</span>
        Total <strong className="text-slate-800">{formatMoedaDrill(total)}</strong>
        <span className="mx-2 text-slate-300">·</span>
        Fonte: Sienge · CP pagas
      </p>

      {error && (
        <div className="flex items-center gap-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl px-4 py-3 text-sm">
          <AlertTriangle className="w-5 h-5 shrink-0" />{error}
        </div>
      )}

      <div className="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <AppLoadingState />
        ) : (
          <div className="p-2 overflow-auto max-h-[calc(100vh-380px)]">
            <RealizadoDespesasDrillTable
              transacoes={filtered}
              showProdutoPlano
              emptyMessage="Nenhuma parcela paga encontrada. Verifique se o sync Sienge (Contas a Pagar) foi executado para o ano."
            />
          </div>
        )}
      </div>
    </div>
  );
}
