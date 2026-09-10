"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Trash2, Save } from "lucide-react";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import {
  departamentosService,
  Departamento,
  Diretoria,
} from "@/services/departamentos";

export function DiretoriasPanel({
  departamentos,
  onChanged,
}: {
  departamentos: Departamento[];
  onChanged?: () => void;
}) {
  const [rows, setRows] = useState<Diretoria[]>([]);
  const [loading, setLoading] = useState(true);
  const [nomeNovo, setNomeNovo] = useState("");
  const [savingId, setSavingId] = useState<number | null>(null);

  const operacionais = useMemo(
    () => departamentos.filter((d) => d.ativo),
    [departamentos],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await departamentosService.listDiretorias());
    } catch {
      toast.error("Não foi possível carregar as diretorias.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const criar = async () => {
    const nome = nomeNovo.trim();
    if (!nome) return;
    try {
      await departamentosService.createDiretoria({ nome, ativo: true, departamento_ids: [] });
      setNomeNovo("");
      toast.success("Diretoria criada.");
      await load();
      onChanged?.();
    } catch {
      toast.error("Não foi possível criar a diretoria.");
    }
  };

  const salvar = async (row: Diretoria) => {
    setSavingId(row.id);
    try {
      await departamentosService.updateDiretoria(row.id, {
        nome: row.nome,
        ativo: row.ativo,
        departamento_ids: row.departamento_ids,
      });
      toast.success("Diretoria salva.");
      await load();
      onChanged?.();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Não foi possível salvar.");
    } finally {
      setSavingId(null);
    }
  };

  const remover = async (id: number) => {
    try {
      await departamentosService.deleteDiretoria(id);
      toast.success("Diretoria removida.");
      await load();
      onChanged?.();
    } catch {
      toast.error("Não foi possível remover.");
    }
  };

  const toggleDept = (row: Diretoria, deptId: number) => {
    const has = row.departamento_ids.includes(deptId);
    const departamento_ids = has
      ? row.departamento_ids.filter((id) => id !== deptId)
      : [...row.departamento_ids, deptId];
    setRows((prev) => prev.map((r) => (r.id === row.id ? { ...r, departamento_ids } : r)));
  };

  if (loading) return <AppLoadingState title="Carregando diretorias…" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        Uma diretoria pode ter vários departamentos (incluindo Corporativo). O mesmo departamento
        não pode estar em duas diretorias.
      </p>

      <div className="flex flex-wrap gap-2 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs font-semibold text-slate-600">Nova diretoria</label>
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={nomeNovo}
            onChange={(e) => setNomeNovo(e.target.value)}
            placeholder="Ex.: Operações"
          />
        </div>
        <Button type="button" onClick={() => void criar()} className="gap-1">
          <Plus className="w-4 h-4" /> Criar
        </Button>
      </div>

      <div className="space-y-3">
        {rows.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
            Nenhuma diretoria cadastrada ainda.
          </div>
        )}
        {rows.map((row) => (
          <div key={row.id} className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
            <div className="flex flex-wrap gap-2 items-center justify-between">
              <input
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-800 min-w-[200px]"
                value={row.nome}
                onChange={(e) =>
                  setRows((prev) =>
                    prev.map((r) => (r.id === row.id ? { ...r, nome: e.target.value } : r)),
                  )
                }
              />
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  disabled={savingId === row.id}
                  onClick={() => void salvar(row)}
                  className="gap-1"
                >
                  <Save className="w-4 h-4" /> Salvar
                </Button>
                <Button type="button" variant="outline" onClick={() => void remover(row.id)} className="gap-1 text-red-600">
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {operacionais.map((d) => {
                const checked = row.departamento_ids.includes(d.id);
                const other = rows.find(
                  (r) => r.id !== row.id && r.departamento_ids.includes(d.id),
                );
                return (
                  <label
                    key={d.id}
                    className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs cursor-pointer ${
                      checked
                        ? "border-[#2E864D] bg-emerald-50 text-emerald-800"
                        : other
                          ? "border-slate-100 text-slate-400"
                          : "border-slate-200 text-slate-700"
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="rounded"
                      checked={checked}
                      disabled={Boolean(other)}
                      onChange={() => toggleDept(row, d.id)}
                    />
                    {d.nome}
                    {d.is_residual ? " (residual)" : ""}
                    {other ? ` (em ${other.nome})` : ""}
                  </label>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
