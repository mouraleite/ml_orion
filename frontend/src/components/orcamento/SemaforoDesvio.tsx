"use client";

import { estadoSemaforo } from "@/lib/semaforoDesvio";
import type { DesvioTipo } from "@/lib/orcamentoDesvioUi";

export function SemaforoDesvio({
  n,
  ref,
  tipo,
  className = "",
}: {
  n: number;
  ref: number;
  tipo: DesvioTipo;
  className?: string;
}) {
  const s = estadoSemaforo(n, ref, tipo);
  return <span title={s.titulo} className={`inline-block w-2 h-2 rounded-full shrink-0 ${s.cor} ${className}`} />;
}
