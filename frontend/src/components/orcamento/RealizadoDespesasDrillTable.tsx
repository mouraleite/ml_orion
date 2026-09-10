"use client";

import React, { useMemo } from "react";
import { FileText } from "lucide-react";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

export interface ParcelaDespesa {
  id?: number;
  produto_id?: number;
  produto_nome?: string;
  plano_id?: number;
  plano_nome?: string;
  credor: string;
  documento_nome: string;
  documento_numero: string;
  titulo?: string;
  autorizacao?: string;
  transaction_date?: string | null;
  mes?: string;
  valor: number;
}

const MESES_LABEL: Record<string, string> = {
  jan: "Jan", fev: "Fev", mar: "Mar", abr: "Abr", mai: "Mai", jun: "Jun",
  jul: "Jul", ago: "Ago", set: "Set", out: "Out", nov: "Nov", dez: "Dez",
};

export const formatMoedaDrill = (v: number) =>
  (v ?? 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

interface Props {
  transacoes: ParcelaDespesa[];
  loading?: boolean;
  compact?: boolean;
  showProdutoPlano?: boolean;
  mesesVisiveis?: string[];
  emptyMessage?: string;
}

export function RealizadoDespesasDrillTable({
  transacoes,
  loading = false,
  compact = false,
  showProdutoPlano = false,
  mesesVisiveis,
  emptyMessage = "Nenhuma parcela paga encontrada para este recorte.",
}: Props) {
  const grouped = useMemo(() => {
    if (!mesesVisiveis?.length) return null;
    const map = new Map<string, ParcelaDespesa & { valores: Record<string, number> }>();
    for (const t of transacoes) {
      const key = `${t.credor}|${t.documento_nome}|${t.documento_numero}|${t.titulo ?? ""}|${t.autorizacao ?? ""}`;
      if (!map.has(key)) {
        map.set(key, {
          ...t,
          valores: Object.fromEntries([...mesesVisiveis, "total"].map((m) => [m, 0])),
        });
      }
      const row = map.get(key)!;
      const mes = t.mes || "total";
      if (mesesVisiveis.includes(mes)) {
        row.valores[mes] = (row.valores[mes] || 0) + t.valor;
      }
      row.valores.total = (row.valores.total || 0) + t.valor;
    }
    return Array.from(map.values()).sort((a, b) => (b.valores.total || 0) - (a.valores.total || 0));
  }, [transacoes, mesesVisiveis]);

  if (loading) {
    return <AppLoadingState />;
  }

  if (!transacoes.length) {
    return (
      <div className="py-4 px-3 text-slate-400 text-xs flex items-center gap-2">
        <FileText className="w-4 h-4 shrink-0 opacity-50" />
        {emptyMessage}
      </div>
    );
  }

  const pad = compact ? "px-2 py-1.5" : "px-3 py-2";
  const textSize = compact ? "text-[11px]" : "text-xs";

  if (grouped && mesesVisiveis) {
    const cols = [...mesesVisiveis, "total"];
    return (
      <div className="overflow-x-auto">
        <table className={`w-full ${textSize} border-collapse min-w-max`}>
          <thead>
            <tr className="bg-slate-100/80 text-slate-600 uppercase font-semibold">
              <th className={`${pad} text-left min-w-[140px]`}>Credor</th>
              <th className={`${pad} text-left min-w-[120px]`}>Documento</th>
              <th className={`${pad} text-left min-w-[90px]`}>Nº doc.</th>
              <th className={`${pad} text-left min-w-[120px]`}>Autorização</th>
              {cols.map((m) => (
                <th key={m} className={`${pad} text-right whitespace-nowrap`}>
                  {m === "total" ? "Total" : MESES_LABEL[m] || m}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grouped.map((row, i) => (
              <tr key={i} className="border-t border-slate-100 hover:bg-slate-50/80">
                <td className={`${pad} text-slate-700 max-w-[180px] truncate`} title={row.credor}>{row.credor}</td>
                <td className={`${pad} text-slate-600 max-w-[140px] truncate`} title={row.documento_nome}>{row.documento_nome}</td>
                <td className={`${pad} text-slate-500 tabular-nums`}>{row.documento_numero}</td>
                <td className={`${pad} text-slate-600 max-w-[140px] truncate`} title={row.autorizacao}>{row.autorizacao || "—"}</td>
                {cols.map((m) => (
                  <td key={m} className={`${pad} text-right tabular-nums ${m === "total" ? "font-semibold border-l border-slate-100" : ""}`}>
                    {formatMoedaDrill(row.valores[m] || 0)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  const total = transacoes.reduce((s, t) => s + t.valor, 0);

  return (
    <div className="overflow-x-auto">
      <table className={`w-full ${textSize} border-collapse min-w-max`}>
        <thead>
          <tr className="bg-slate-100/80 text-slate-600 uppercase font-semibold">
            {showProdutoPlano && (
              <>
                <th className={`${pad} text-left`}>Produto</th>
                <th className={`${pad} text-left`}>Plano</th>
              </>
            )}
            <th className={`${pad} text-left`}>Data</th>
            <th className={`${pad} text-left min-w-[140px]`}>Credor</th>
            <th className={`${pad} text-left min-w-[120px]`}>Documento</th>
            <th className={`${pad} text-left`}>Nº doc.</th>
            <th className={`${pad} text-left min-w-[120px]`}>Autorização</th>
            <th className={`${pad} text-right`}>Valor</th>
          </tr>
        </thead>
        <tbody>
          {transacoes.map((t, i) => (
            <tr key={t.id ?? i} className="border-t border-slate-100 hover:bg-slate-50/80">
              {showProdutoPlano && (
                <>
                  <td className={`${pad} text-slate-600 max-w-[120px] truncate`} title={t.produto_nome}>{t.produto_nome}</td>
                  <td className={`${pad} text-slate-500 max-w-[120px] truncate`} title={t.plano_nome}>{t.plano_nome}</td>
                </>
              )}
              <td className={`${pad} text-slate-500 whitespace-nowrap tabular-nums`}>
                {t.transaction_date
                  ? new Date(t.transaction_date + "T12:00:00").toLocaleDateString("pt-BR")
                  : "—"}
              </td>
              <td className={`${pad} text-slate-700 max-w-[180px] truncate`} title={t.credor}>{t.credor}</td>
              <td className={`${pad} text-slate-600 max-w-[140px] truncate`} title={t.documento_nome}>{t.documento_nome}</td>
              <td className={`${pad} text-slate-500 tabular-nums`}>{t.documento_numero}</td>
              <td className={`${pad} text-slate-600 max-w-[140px] truncate`} title={t.autorizacao}>{t.autorizacao || "—"}</td>
              <td className={`${pad} text-right tabular-nums font-medium text-slate-800`}>{formatMoedaDrill(t.valor)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-slate-200 bg-slate-50 font-semibold">
            <td colSpan={showProdutoPlano ? 7 : 5} className={`${pad} text-slate-700`}>Total</td>
            <td className={`${pad} text-right tabular-nums text-slate-900`}>{formatMoedaDrill(total)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

export function exportParcelasCsv(transacoes: ParcelaDespesa[], filename = "realizado-despesas.csv") {
  const header = ["Data", "Produto", "Plano", "Credor", "Documento", "NumeroDocumento", "Autorizacao", "Valor"];
  const lines = transacoes.map((t) => [
    t.transaction_date ?? "",
    t.produto_nome ?? "",
    t.plano_nome ?? "",
    t.credor,
    t.documento_nome,
    t.documento_numero,
    t.autorizacao ?? "",
    String(t.valor),
  ].map((c) => `"${String(c).replace(/"/g, '""')}"`).join(";"));
  const blob = new Blob(["\uFEFF" + [header.join(";"), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
