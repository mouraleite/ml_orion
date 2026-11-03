"use client";

import { useEffect, useMemo, useState } from "react";
import { apoioService } from "@/services/apoio";
import {
  mostraFlagAcompanharEmpreendimento,
  tipoEfetivoCentro,
} from "@/lib/acompanharEmpreendimento";

type Centro = {
  db_id: number;
  nome: string;
  tipo_sienge?: string;
  custom_data?: Record<string, unknown> | null;
  track_in_dashboard?: boolean;
};

type Props = {
  value: number | null | undefined;
  readonly?: boolean;
  onChange: (id: number | null) => void;
};

export function ObraAcompanhamentoField({ value, readonly, onChange }: Props) {
  const [centros, setCentros] = useState<Centro[]>([]);

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
    return centros
      .filter((c) =>
        mostraFlagAcompanharEmpreendimento({
          tipo: tipoEfetivoCentro(c),
          nome: c.nome || "",
          jaAcompanhado: Boolean(c.track_in_dashboard),
        }),
      )
      .sort((a, b) => (a.nome || "").localeCompare(b.nome || "", "pt-BR"));
  }, [centros]);

  const selecionado = opcoes.find((c) => c.db_id === value);
  const jaAcompanha = Boolean(selecionado?.track_in_dashboard);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-500 whitespace-nowrap">Obra no acompanhamento:</span>
        {readonly ? (
          <span className="text-xs text-slate-700">
            {selecionado?.nome || "Nenhuma"}
          </span>
        ) : (
          <select
            value={value ?? ""}
            onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
            className="max-w-xs rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 outline-none focus:ring-1 focus:ring-ml-green"
          >
            <option value="">Nenhuma — continua como Land Bank</option>
            {opcoes.map((c) => (
              <option key={c.db_id} value={c.db_id}>
                {c.nome}
                {c.track_in_dashboard ? " (já acompanha)" : ""}
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
