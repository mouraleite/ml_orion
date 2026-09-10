"use client";

import { useEffect, useMemo, useState } from "react";
import { Building2, Layers } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { SearchableSelect } from "@/components/ui/SearchableSelect";

interface DepartmentFilterProps {
  className?: string;
}

export function DepartmentFilter({ className = "" }: DepartmentFilterProps) {
  const { user, activeDepartamentoId, setActiveDepartamentoId } = useAuth();

  const diretorias = user?.diretorias ?? [];
  const departamentos = user?.departamentos ?? [];

  const [diretoriaId, setDiretoriaId] = useState<number | null>(null);
  const [checkedIds, setCheckedIds] = useState<string[]>([]);

  const diretoriaOptions = useMemo(
    () => diretorias.map((di) => ({ id: di.id, label: di.nome })),
    [diretorias],
  );

  const memberIdSet = useMemo(() => {
    if (diretoriaId == null) return null;
    const di = diretorias.find((d) => d.id === diretoriaId);
    return new Set(di?.departamento_ids ?? []);
  }, [diretoriaId, diretorias]);

  const deptOptions = useMemo(() => {
    const list =
      memberIdSet == null
        ? departamentos
        : departamentos.filter((d) => memberIdSet.has(d.id));
    return list.map((dept) => ({
      value: String(dept.id),
      label: dept.nome,
    }));
  }, [departamentos, memberIdSet]);

  const resolveDiretoriaForDept = (deptId: number): number | null => {
    const fromDept = departamentos.find((d) => d.id === deptId)?.diretoria_id;
    if (fromDept != null) return fromDept;
    const hit = diretorias.find((di) => (di.departamento_ids ?? []).includes(deptId));
    return hit?.id ?? null;
  };

  // Sincroniza do contexto no login / troca de usuário.
  useEffect(() => {
    if (!user) return;

    if (activeDepartamentoId < 0) {
      const diId = -activeDepartamentoId;
      setDiretoriaId(diId);
      const di = diretorias.find((d) => d.id === diId);
      const ids = (di?.departamento_ids ?? [])
        .filter((id) => departamentos.some((d) => d.id === id))
        .map(String);
      setCheckedIds(ids.length ? ids : []);
      return;
    }

    if (activeDepartamentoId === 0) {
      setDiretoriaId(null);
      setCheckedIds(departamentos.map((d) => String(d.id)));
      return;
    }

    const diId = resolveDiretoriaForDept(activeDepartamentoId);
    setDiretoriaId(diId);
    setCheckedIds([String(activeDepartamentoId)]);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só no login/troca de user
  }, [user?.id]);

  // Se a lista filtrada mudar (ex.: trocou diretoria), mantém checkedIds coerentes.
  useEffect(() => {
    if (deptOptions.length === 0) {
      setCheckedIds([]);
      return;
    }
    const allowed = new Set(deptOptions.map((o) => o.value));
    setCheckedIds((prev) => {
      const next = prev.filter((id) => allowed.has(id));
      if (next.length > 0) return next;
      // Diretoria recém-escolhida: marca todos os membros (= leitura da diretoria).
      if (diretoriaId != null) return deptOptions.map((o) => o.value);
      return prev;
    });
  }, [deptOptions, diretoriaId]);

  if (!user) return null;

  const showFilter =
    user.pode_ver_todos_departamentos ||
    departamentos.length > 1 ||
    diretorias.length > 0;

  if (!showFilter) return null;

  const applyDeptSelection = (vals: string[]) => {
    setCheckedIds(vals);
    if (vals.length === 0) return;

    if (vals.length >= deptOptions.length && deptOptions.length > 0) {
      if (diretoriaId != null) {
        setActiveDepartamentoId(-diretoriaId);
      } else {
        setActiveDepartamentoId(0);
      }
      return;
    }

    setActiveDepartamentoId(Number(vals[vals.length - 1]));
  };

  const onDiretoriaChange = (value: string | number | "") => {
    if (value === "" || value == null) {
      setDiretoriaId(null);
      const all = departamentos.map((d) => String(d.id));
      setCheckedIds(all);
      setActiveDepartamentoId(0);
      return;
    }
    const id = Number(value);
    setDiretoriaId(id);
    const di = diretorias.find((d) => d.id === id);
    const ids = (di?.departamento_ids ?? [])
      .filter((deptId) => departamentos.some((d) => d.id === deptId))
      .map(String);
    setCheckedIds(ids);
    setActiveDepartamentoId(-id);
  };

  return (
    <div className={`flex flex-wrap items-end gap-3 ${className}`}>
      {diretorias.length > 0 && (
        <div className="min-w-[180px] max-w-[260px]">
          <label className="flex items-center gap-1 text-xs font-semibold text-slate-600 mb-1.5">
            <Layers className="w-3.5 h-3.5 text-[#F5883A]" />
            Diretoria
          </label>
          <SearchableSelect
            options={diretoriaOptions}
            value={diretoriaId ?? ""}
            onChange={onDiretoriaChange}
            placeholder="Todas"
            clearable
          />
        </div>
      )}

      <div className="min-w-[220px] max-w-[320px]">
        <label className="flex items-center gap-1 text-xs font-semibold text-slate-600 mb-1.5">
          <Building2 className="w-3.5 h-3.5 text-[#F5883A]" />
          Departamento
        </label>
        <MultiSelect
          options={deptOptions}
          value={checkedIds}
          onChange={applyDeptSelection}
          placeholder={diretoriaId != null ? "Membros da diretoria…" : "Selecione…"}
          showSelectAll
        />
      </div>
    </div>
  );
}
