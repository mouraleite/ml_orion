"use client";

import Link from "next/link";
import { BarChart2, Layers, Receipt } from "lucide-react";
import {
  buildDespesasDeepLinks,
  type OrcamentoLinkParams,
} from "@/lib/orcamentoNavigation";

interface OrcamentoDeepLinksProps {
  params: OrcamentoLinkParams;
  variant?: "inline" | "compact" | "menu";
  className?: string;
}

export function OrcamentoDeepLinks({
  params,
  variant = "inline",
  className = "",
}: OrcamentoDeepLinksProps) {
  const links = buildDespesasDeepLinks(params);

  if (variant === "compact") {
    return (
      <div className={`inline-flex items-center gap-1 ${className}`}>
        <Link
          href={links.analitico1}
          title="Analítico I"
          className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        >
          <BarChart2 className="w-3.5 h-3.5" />
        </Link>
        <Link
          href={links.analitico2}
          title="Analítico II"
          className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        >
          <Layers className="w-3.5 h-3.5" />
        </Link>
        <Link
          href={links.realizadoCp}
          title="Realizado detalhado — Contas a Pagar"
          className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
        >
          <Receipt className="w-3.5 h-3.5" />
        </Link>
      </div>
    );
  }

  if (variant === "menu") {
    return (
      <div className={`flex flex-wrap items-center gap-2 text-[11px] ${className}`}>
        <span className="text-slate-500 font-medium">Detalhar:</span>
        <Link href={links.analitico1} className="font-semibold text-ml-green hover:underline">
          Analítico I
        </Link>
        <span className="text-slate-300">·</span>
        <Link href={links.analitico2} className="font-semibold text-ml-green hover:underline">
          Analítico II
        </Link>
        <span className="text-slate-300">·</span>
        <Link href={links.realizadoCp} className="font-semibold text-red-600 hover:underline">
          Realizado detalhado
        </Link>
      </div>
    );
  }

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <Link
        href={links.analitico1}
        className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-slate-600 bg-white border border-slate-200 rounded-md hover:bg-slate-50"
      >
        <BarChart2 className="w-3 h-3" />
        Analítico I
      </Link>
      <Link
        href={links.analitico2}
        className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-slate-600 bg-white border border-slate-200 rounded-md hover:bg-slate-50"
      >
        <Layers className="w-3 h-3" />
        Analítico II
      </Link>
      <Link
        href={links.realizadoCp}
        className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-red-700 bg-red-50 border border-red-100 rounded-md hover:bg-red-100"
      >
        <Receipt className="w-3 h-3" />
        Realizado detalhado
      </Link>
    </div>
  );
}
