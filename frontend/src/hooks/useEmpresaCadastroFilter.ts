"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apoioService } from "@/services/apoio";
import { buildEmpresaLinkedOptions } from "@/lib/gridFilters";

const STORAGE_KEY = "orcamento_dashboard_empresa_ids";

function readStoredIds(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.map((v) => String(v).trim()).filter(Boolean);
  } catch {
    return [];
  }
}

export function useEmpresaCadastroFilter() {
  const [filtroEmpresaIds, setFiltroEmpresaIdsState] = useState<string[]>([]);
  const [empresaOpcoes, setEmpresaOpcoes] = useState(() => buildEmpresaLinkedOptions([]));

  useEffect(() => {
    setFiltroEmpresaIdsState(readStoredIds());
    apoioService
      .getEmpresas()
      .then((list) => {
        setEmpresaOpcoes(
          buildEmpresaLinkedOptions(
            (list || [])
              .map((e: { id?: string | number; nomeFantasia?: string; razaoSocial?: string; nome?: string }) => ({
                id_empresa: e.id != null && e.id !== "" ? String(e.id) : "",
                nome_empresa: e.nomeFantasia || e.razaoSocial || e.nome || "",
              }))
              .filter((e: { id_empresa: string }) => e.id_empresa),
          ),
        );
      })
      .catch(() => {});
  }, []);

  const setFiltroEmpresaIds = useCallback((ids: string[]) => {
    setFiltroEmpresaIdsState(ids);
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
    } catch {
      /* ignore quota / private mode */
    }
  }, []);

  const empresaIdsKey = useMemo(() => filtroEmpresaIds.join(","), [filtroEmpresaIds]);

  return {
    filtroEmpresaIds,
    setFiltroEmpresaIds,
    empresaOpcoes,
    empresaIdsKey,
  };
}
