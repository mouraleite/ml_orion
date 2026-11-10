"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";

export type TipoTaxaIpca = "% a.a." | "% a.m.";

/** Converte a taxa digitada em taxa mensal decimal (a.a. → (1+i)^(1/12) − 1). */
export function taxaMensalIpca(valor: number, tipo: TipoTaxaIpca): number {
  const i = valor / 100;
  if (tipo === "% a.m.") return i;
  return Math.pow(1 + i, 1 / 12) - 1;
}

/**
 * Pergunta a taxa de IPCA e a unidade antes de aplicar em cascata no ticket médio.
 * Antes era um prompt sem unidade que aplicava o valor como taxa mensal
 * (4,5 digitado pensando no ano virava ~62% até dezembro).
 */
export function IpcaCascataModal({
  onClose,
  onConfirm,
}: {
  onClose: () => void;
  onConfirm: (taxaMensal: number, descricao: string) => void;
}) {
  const [valor, setValor] = useState("");
  const [tipo, setTipo] = useState<TipoTaxaIpca>("% a.a.");
  const num = parseFloat(valor.replace(",", "."));
  const valido = !isNaN(num) && num > -100;
  const mensal = valido ? taxaMensalIpca(num, tipo) : 0;
  const fmt = (x: number) => x.toLocaleString("pt-BR", { maximumFractionDigits: 4 });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
        <h2 className="text-lg font-bold text-slate-800 mb-1">Aplicar IPCA em cascata</h2>
        <p className="text-sm text-slate-500 mb-4">Corrige o ticket médio dos meses seguintes, mês a mês.</p>
        <div className="flex gap-2">
          <input
            autoFocus
            inputMode="decimal"
            className="flex-1 p-2 border border-slate-300 rounded-md"
            placeholder="Ex.: 4,5"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && valido) onConfirm(mensal, `${fmt(num)}${tipo}`); }}
          />
          <select
            className="p-2 border border-slate-300 rounded-md"
            value={tipo}
            onChange={(e) => setTipo(e.target.value as TipoTaxaIpca)}
          >
            <option value="% a.a.">% a.a.</option>
            <option value="% a.m.">% a.m.</option>
          </select>
        </div>
        {valido && (
          <p className="text-xs text-slate-500 mt-2">
            Equivale a {fmt(mensal * 100)}% ao mês ({fmt((Math.pow(1 + mensal, 12) - 1) * 100)}% em 12 meses).
          </p>
        )}
        <div className="flex justify-end gap-2 pt-5">
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={() => onConfirm(mensal, `${fmt(num)}${tipo}`)} disabled={!valido}>Aplicar</Button>
        </div>
      </div>
    </div>
  );
}
