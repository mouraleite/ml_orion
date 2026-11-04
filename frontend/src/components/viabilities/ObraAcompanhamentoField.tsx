"use client";

import { useEffect, useMemo, useState } from "react";
import { apoioService } from "@/services/apoio";
import {
  opcoesObraAcompanhamento,
  rotuloCentroIdNome,
  type CentroObraOpcao,
} from "@/lib/acompanharEmpreendimento";

type Props = {
  value: number | null | undefined;
  readonly?: boolean;
  onChange: (id: number | null) => void;
};

function rotuloOpcao(c: CentroObraOpcao): string {
  const base = rotuloCentroIdNome(c.id, c.nome);
  return c.track_in_dashboard ? `${base} (já acompanha)` : base;
}

export function ObraAcompanhamentoField({ value, readonly, onChange }: Props) {
  const [centros, setCentros] = useState<CentroObraOpcao[]>([]);

  useEffect(() => {
    let alive = true;
    apoioService.getCentrosCusto().then((rows) => {
      if (alive) setCentros(Array.isArray(rows) ? rows : []);
    }).catch(() => {
      if (alive) setCentros([]);
    });
    return () => {
      alive = false;
    };
  }, []);

  const opcoes = useMemo(() => {
    const filtradas = opcoesObraAcompanhamento(centros);
    if (value == null) return filtradas;
    if (filtradas.some((c) => c.db_id === value)) return filtradas;
    const atual = centros.find((c) => c.db_id === value);
    return atual ? [atual, ...filtradas] : filtradas;
  }, [centros, value]);

  const selecionado = opcoes.find((c) => c.db_id === value) || centros.find((c) => c.db_id === value);
  const jaAcompanha = Boolean(selecionado?.track_in_dashboard);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-sm text-slate-500 whitespace-nowrap">Obra no acompanhamento:</span>
        {readonly ? (
          <span className="text-xs text-slate-700 truncate" title={selecionado ? rotuloOpcao(selecionado) : undefined}>
            {selecionado ? rotuloCentroIdNome(selecionado.id, selecionado.nome) : "Nenhuma"}
          </span>
        ) : (
          <select
            value={value ?? ""}
            onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
            className="min-w-[280px] max-w-xl rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 outline-none focus:ring-1 focus:ring-ml-green"
          >
            <option value="">Nenhuma — continua como Land Bank</option>
            {opcoes.map((c) => (
              <option key={c.db_id} value={c.db_id}>
                {rotuloOpcao(c)}
              </option>
            ))}
          </select>
        )}
      </div>
      {jaAcompanha ? (
        <p className="text-[11px] text-slate-500">
          Esta obra já está no acompanhamento. O Land Bank não aparece na lista.
        </p>
      ) : (
        <p className="text-[11px] text-slate-400">
          Quando esta obra for marcada para acompanhar, o Land Bank sai da lista.
        </p>
      )}
    </div>
  );
}
