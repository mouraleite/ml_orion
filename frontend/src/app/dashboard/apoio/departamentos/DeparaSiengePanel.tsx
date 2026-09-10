"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, X, Link2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import {
  departamentosService,
  Departamento,
  DeparaAutorizacao,
  CorporativoResidual,
} from "@/services/departamentos";
import toast from "react-hot-toast";

function ehResidual(dept: Departamento) {
  if (dept.is_residual) return true;
  const n = dept.nome
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
  return n === "corporativo" || n === "consolidado - sienge" || n.replace(/ /g, "") === "consolidadosienge";
}

export function DeparaSiengePanel({ departamentos }: { departamentos: Departamento[] }) {
  const [rows, setRows] = useState<DeparaAutorizacao[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [busca, setBusca] = useState("");
  const [residual, setResidual] = useState<CorporativoResidual | null>(null);

  const destinos = useMemo(
    () => [
      { id: "", label: "Corporativo (residual)" },
      ...departamentos
        .filter((d) => !ehResidual(d))
        .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"))
        .map((d) => ({ id: d.id, label: d.nome })),
    ],
    [departamentos],
  );

  const carregar = useCallback(async () => {
    setIsLoading(true);
    try {
      setRows(await departamentosService.listDepara());
      try {
        setResidual(await departamentosService.residualCorporativo());
      } catch {
        setResidual(null);
      }
    } catch {
      toast.error("Erro ao carregar o de-para Sienge.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const data = await departamentosService.syncDepara();
      setRows(data);
      toast.success(`${data.length} nome(s) do Sienge sincronizado(s).`);
    } catch {
      toast.error("Não foi possível sincronizar os departamentos do Sienge.");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleMap = async (row: DeparaAutorizacao, value: string | number | "") => {
    const departamento_id = value === "" ? null : Number(value);
    setSavingId(row.id);
    try {
      const updated = await departamentosService.updateDepara(row.id, departamento_id);
      setRows((prev) => prev.map((r) => (r.id === row.id ? updated : r)));
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erro ao salvar o casamento.");
    } finally {
      setSavingId(null);
    }
  };

  const filtradas = useMemo(() => {
    const t = busca.trim().toLowerCase();
    if (!t) return rows;
    return rows.filter((r) => {
      const dest = r.departamento_nome || (r.corporativo ? "corporativo" : "");
      return (
        r.nome_sienge.toLowerCase().includes(t) ||
        dest.toLowerCase().includes(t) ||
        String(r.sienge_department_id ?? "").includes(t)
      );
    });
  }, [rows, busca]);

  const semCadastro = rows.filter((r) => r.corporativo).length;

  return (
    <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden min-h-[320px]">
      <div className="px-5 py-3.5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-start justify-between gap-3 shrink-0">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Link2 size={16} className="text-ml-green shrink-0" />
            <h2 className="text-base font-bold text-slate-800">De-para Sienge</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Nome da autorização (contas a pagar) → departamento do Apoio. Sem cadastro vai para Corporativo.
            {" "}Ainda não altera orçado nem realizado.
          </p>
          {residual ? (
            <p className="text-[11px] text-slate-500 mt-1.5 tabular-nums">
              Residual: {residual.planos_residuais} plano(s) sem matriz · {residual.planos_comuns} comum(ns) · {residual.planos_exclusivos} exclusivo(s)
              {residual.orcamentos_sem_departamento ? ` · ${residual.orcamentos_sem_departamento} orçamento(s) sem departamento` : ""}
            </p>
          ) : null}
        </div>
        <Button onClick={handleSync} isLoading={isSyncing} className="gap-2 shrink-0" size="sm">
          <RefreshCw size={14} />
          Sincronizar do Sienge
        </Button>
      </div>

      <div className="px-4 py-3 border-b border-slate-100 flex flex-wrap items-center gap-2 shrink-0">
        <div className="relative flex-1 min-w-[180px]">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Filtrar nome Sienge ou departamento…"
            className="w-full h-9 pl-8 pr-8 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-ml-green/20 focus:border-ml-green"
          />
          {busca ? (
            <button type="button" onClick={() => setBusca("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5">
              <X size={14} />
            </button>
          ) : null}
        </div>
        <span className="text-[11px] text-slate-500 tabular-nums">
          {rows.length} nome(s)
          {rows.length > 0 ? ` · ${semCadastro} no Corporativo` : ""}
        </span>
      </div>

      {isLoading ? (
        <AppLoadingState />
      ) : rows.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-6 gap-3">
          <div className="w-12 h-12 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
            <Link2 size={22} />
          </div>
          <p className="text-sm font-semibold text-slate-700">Nenhum nome Sienge ainda</p>
          <p className="text-sm text-slate-500 max-w-sm">
            Sincronize os departamentos do Sienge para validar o casamento com o Apoio.
          </p>
          <Button onClick={handleSync} isLoading={isSyncing} className="gap-2 mt-1">
            <RefreshCw size={16} /> Sincronizar do Sienge
          </Button>
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-50 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Nome Sienge</th>
                <th className="px-4 py-2.5 font-semibold w-24">ID</th>
                <th className="px-4 py-2.5 font-semibold min-w-[240px]">Departamento no ML Órion</th>
                <th className="px-4 py-2.5 font-semibold w-28">Origem</th>
              </tr>
            </thead>
            <tbody>
              {filtradas.map((row) => (
                <tr key={row.id} className="border-t border-slate-100 hover:bg-slate-50/80">
                  <td className="px-4 py-2 font-medium text-slate-800">{row.nome_sienge}</td>
                  <td className="px-4 py-2 text-slate-500 tabular-nums font-mono text-xs">
                    {row.sienge_department_id ?? "—"}
                  </td>
                  <td className="px-4 py-2">
                    <SearchableSelect
                      options={destinos}
                      value={row.departamento_id ?? ""}
                      onChange={(v) => handleMap(row, v)}
                      placeholder="Corporativo (residual)"
                      clearable={false}
                      disabled={savingId === row.id}
                      className="max-w-sm"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${
                        row.definido_manual
                          ? "bg-slate-100 text-slate-600"
                          : "bg-emerald-50 text-emerald-800"
                      }`}
                    >
                      {row.definido_manual ? "Manual" : "Sugerido"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtradas.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-slate-500">Nenhum nome com esse filtro.</p>
          ) : null}
        </div>
      )}
    </div>
  );
}
