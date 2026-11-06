"use client";

import type { ReactNode } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

/**
 * Padrão ML Órion para telas de árvore + tabela larga
 * (DFC, DFC gerencial, Despesas por empreendimento, DFC de empreendimentos).
 *
 * A caixa cresce ao abrir os níveis; a página é que rola.
 * Não usar na grade editável de orçado × realizado — essa permanece com altura travada.
 */
export const GROW_TREE_PAGE_CLASS = "flex flex-col min-w-0 gap-4 pb-8";

export const GROW_TREE_NAME_TH_CLASS =
  "sticky left-0 z-40 bg-white text-left px-3 py-2 font-semibold border-b border-slate-200 align-bottom min-w-[360px] w-[360px]";

export const GROW_TREE_NAME_TD_CLASS =
  "sticky left-0 z-10 px-3 py-2.5 border-b border-slate-100 min-w-[360px] w-[360px]";

export const GROW_TREE_INDENT_PX = 20;

export function growTreeIndentStyle(level: number) {
  return { paddingLeft: Math.max(0, level) * GROW_TREE_INDENT_PX };
}

export function GrowTreeSheet({
  toolbar,
  children,
}: {
  toolbar: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm min-h-[28rem]">
      <div className="sticky top-0 z-30 flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-slate-100 bg-white rounded-t-2xl">
        {toolbar}
      </div>
      <div className="overflow-x-auto min-w-0">{children}</div>
    </div>
  );
}

export function GrowTreeNameCell({
  indent,
  bg = "bg-white",
  children,
}: {
  indent: number;
  bg?: string;
  children: ReactNode;
}) {
  return (
    <td className={`${GROW_TREE_NAME_TD_CLASS} ${bg}`}>
      <div className="flex items-start gap-1.5" style={growTreeIndentStyle(indent)}>
        {children}
      </div>
    </td>
  );
}

export function GrowTreeChevron({
  open,
  visible,
  onClick,
}: {
  open: boolean;
  visible: boolean;
  onClick?: () => void;
}) {
  if (!visible) return <span className="w-4 shrink-0" />;
  return (
    <button type="button" onClick={onClick} className="p-0.5 rounded hover:bg-slate-200 mt-0.5 shrink-0">
      {open ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
    </button>
  );
}
