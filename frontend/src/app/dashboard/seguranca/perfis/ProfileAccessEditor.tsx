"use client";

import { useMemo, useState } from "react";
import { ArrowLeft, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ACCESS_MODULES, flattenAccessEntries, type AccessGroup, type AccessModuleDef } from "@/lib/menuCatalog";
import {
  moduleScreenStats,
  setEntries,
  setEntry,
  setModuleWrite,
  isModuleWriteEnabled,
  type PermissionsMap,
} from "@/lib/accessMatrix";

export type ProfileFormData = {
  name: string;
  description: string;
  is_active: boolean;
  permissions: PermissionsMap;
};

type Props = {
  title: string;
  formData: ProfileFormData;
  onChange: (next: ProfileFormData) => void;
  onCancel: () => void;
  onSave: () => void;
  saving?: boolean;
};

function groupHint(group: AccessGroup) {
  if (group.title === "Dashboard de Orçamento") {
    return "Mesmas telas do submenu Orçamento — cada uma com liberação própria.";
  }
  if (group.title === "Relatórios") {
    return "Cada relatório do submenu é uma tela.";
  }
  if (group.title === "Telas") {
    return "Itens deste módulo no menu.";
  }
  return "Submenu do menu lateral — tela a tela.";
}

export function ProfileAccessEditor({ title, formData, onChange, onCancel, onSave, saving }: Props) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();

  const visibleModules = useMemo(() => {
    return ACCESS_MODULES.map((mod) => ({
      ...mod,
      groups: mod.groups
        .map((group) => ({
          ...group,
          entries: q
            ? group.entries.filter(
                (e) =>
                  e.name.toLowerCase().includes(q) ||
                  group.title.toLowerCase().includes(q) ||
                  mod.title.toLowerCase().includes(q),
              )
            : group.entries,
        }))
        .filter((group) => group.entries.length > 0),
    })).filter((mod) => mod.groups.length > 0);
  }, [q]);

  const footerBits = ACCESS_MODULES.map((mod) => {
    const stats = moduleScreenStats(mod, formData.permissions);
    if (stats.granted === 0) return null;
    return `${mod.title}: ${stats.granted} de ${stats.total}`;
  }).filter(Boolean);

  const updatePerms = (permissions: PermissionsMap) => onChange({ ...formData, permissions });

  const toggleModule = (moduleTitle: string, value: boolean) => {
    const mod = ACCESS_MODULES.find((m) => m.title === moduleTitle);
    if (!mod) return;
    updatePerms(setEntries(formData.permissions, moduleTitle, flattenAccessEntries(mod).map((e) => e.permKey), value));
  };

  const scrollToModule = (id: string) => {
    document.getElementById(`perfil-mod-${id}`)?.scrollIntoView({ block: "start", behavior: "smooth" });
  };

  const renderModule = (mod: AccessModuleDef) => {
    const stats = moduleScreenStats(mod, formData.permissions);
    const canWrite = isModuleWriteEnabled(formData.permissions, mod.title, formData.name);
    return (
      <section key={mod.id} id={`perfil-mod-${mod.id}`} className="scroll-mt-3 space-y-3">
        <div className="flex items-center justify-between gap-3 px-1">
          <div>
            <h2 className="text-base font-bold text-slate-800">{mod.title}</h2>
            <p className="text-xs text-slate-500 mt-0.5 tabular-nums">
              {stats.granted} de {stats.total} telas
              {canWrite ? " · pode criar e alterar" : " · somente visualização"}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              className="text-xs font-medium text-emerald-700 hover:underline"
              onClick={() => toggleModule(mod.title, true)}
            >
              Marcar módulo
            </button>
            <span className="text-slate-300">·</span>
            <button
              type="button"
              className="text-xs font-medium text-slate-500 hover:underline"
              onClick={() => toggleModule(mod.title, false)}
            >
              Limpar
            </button>
          </div>
        </div>
        <div className="flex rounded-xl overflow-hidden border border-slate-200 w-fit">
          <button
            type="button"
            onClick={() => updatePerms(setModuleWrite(formData.permissions, mod.title, false))}
            className={`px-3 py-1.5 text-xs font-semibold ${
              !canWrite ? "bg-slate-700 text-white" : "bg-white text-slate-600 hover:bg-slate-50"
            }`}
          >
            Somente visualização
          </button>
          <button
            type="button"
            onClick={() => updatePerms(setModuleWrite(formData.permissions, mod.title, true))}
            className={`px-3 py-1.5 text-xs font-semibold ${
              canWrite ? "bg-ml-green text-white" : "bg-white text-slate-600 hover:bg-slate-50"
            }`}
          >
            Pode criar e alterar
          </button>
        </div>
        {mod.groups.map((group) => {
          const keys = group.entries.map((e) => e.permKey);
          const bucket = formData.permissions[mod.title] || {};
          const granted = group.entries.filter((e) => e.kind === "screen" && bucket[e.permKey]).length;
          const screenTotal = group.entries.filter((e) => e.kind === "screen").length;
          return (
            <div key={`${mod.id}-${group.title}`} className="rounded-xl border border-slate-200 overflow-hidden bg-white">
              <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-800">{group.title}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">{groupHint(group)}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {screenTotal > 0 ? (
                    <span className="text-[11px] tabular-nums text-slate-400 mr-1">
                      {granted}/{screenTotal}
                    </span>
                  ) : null}
                  <button
                    type="button"
                    className="text-xs font-medium text-emerald-700 hover:underline"
                    onClick={() => updatePerms(setEntries(formData.permissions, mod.title, keys, true))}
                  >
                    Marcar todas
                  </button>
                  <span className="text-slate-300">·</span>
                  <button
                    type="button"
                    className="text-xs font-medium text-slate-500 hover:underline"
                    onClick={() => updatePerms(setEntries(formData.permissions, mod.title, keys, false))}
                  >
                    Nenhuma
                  </button>
                </div>
              </div>
              <div className="divide-y divide-slate-50">
                {group.entries.map((entry) => (
                  <label
                    key={entry.permKey}
                    className="flex items-start gap-2.5 cursor-pointer hover:bg-slate-50 px-4 py-2.5"
                  >
                    <input
                      type="checkbox"
                      checked={!!bucket[entry.permKey]}
                      onChange={(e) =>
                        updatePerms(setEntry(formData.permissions, mod.title, entry.permKey, e.target.checked))
                      }
                      className="mt-0.5 w-4 h-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-600"
                    />
                    <span className="min-w-0">
                      <span className="block text-sm text-slate-800">{entry.name}</span>
                    </span>
                  </label>
                ))}
              </div>
            </div>
          );
        })}
      </section>
    );
  };

  return (
    <div className="w-full h-full min-h-0 flex flex-col gap-4">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm shrink-0">
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 mb-4"
        >
          <ArrowLeft size={16} /> Voltar à lista
        </button>
        <h1 className="text-xl font-bold text-slate-800">{title}</h1>
        <p className="text-sm text-slate-500 mt-1">
          Todas as telas de todos os módulos, iguais ao menu. Em cada módulo, o teto: se o perfil só vê ou também cria/altera. No colaborador, Permissão ainda pode deixar a pessoa só vendo.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nome do perfil</label>
            <Input
              value={formData.name}
              onChange={(e) => onChange({ ...formData, name: e.target.value })}
              placeholder="Ex: Gestor Financeiro"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Status</label>
            <select
              className="w-full flex h-10 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              value={formData.is_active ? "true" : "false"}
              onChange={(e) => onChange({ ...formData, is_active: e.target.value === "true" })}
            >
              <option value="true">Ativo</option>
              <option value="false">Inativo</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Descrição</label>
            <Input
              value={formData.description}
              onChange={(e) => onChange({ ...formData, description: e.target.value })}
              placeholder="Breve descrição do perfil"
            />
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 bg-white rounded-xl border border-slate-200 shadow-sm flex overflow-hidden">
        <aside className="w-64 shrink-0 border-r border-slate-200 overflow-y-auto bg-slate-50/80">
          <div className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Ir ao módulo
          </div>
          {ACCESS_MODULES.map((mod) => {
            const stats = moduleScreenStats(mod, formData.permissions);
            const allOn = stats.total > 0 && stats.granted === stats.total;
            const someOn = stats.granted > 0 && !allOn;
            const canWrite = isModuleWriteEnabled(formData.permissions, mod.title, formData.name);
            return (
              <button
                key={mod.title}
                type="button"
                onClick={() => scrollToModule(mod.id)}
                className="w-full flex items-center gap-3 px-4 py-3 text-left border-l-2 border-transparent text-slate-600 hover:bg-white/70 hover:border-emerald-600 hover:text-slate-900 transition-colors"
              >
                <input
                  type="checkbox"
                  checked={allOn}
                  ref={(el) => {
                    if (el) el.indeterminate = someOn;
                  }}
                  onChange={(e) => {
                    e.stopPropagation();
                    toggleModule(mod.title, e.target.checked);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  className="w-4 h-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-600"
                />
                <span className="flex-1 min-w-0">
                  <span className="block text-sm font-medium truncate">{mod.title}</span>
                  <span className="block text-xs text-slate-400">
                    {stats.granted} de {stats.total} · {canWrite ? "alterar" : "só ver"}
                  </span>
                </span>
              </button>
            );
          })}
        </aside>

        <section className="flex-1 min-w-0 flex flex-col">
          <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center gap-3 shrink-0">
            <div className="flex-1">
              <h2 className="text-base font-semibold text-slate-800">Telas por módulo</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Role a lista ou use o menu à esquerda. Telas e criar/alterar são independentes.
              </p>
            </div>
            <div className="w-full sm:w-64">
              <Input
                icon={<Search size={16} />}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buscar tela ou módulo…"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-8">
            {visibleModules.length === 0 ? (
              <p className="text-sm text-slate-500 py-8 text-center">Nenhuma tela neste filtro.</p>
            ) : (
              visibleModules.map(renderModule)
            )}
          </div>
        </section>
      </div>

      <div className="bg-white px-5 py-3 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
        <p className="text-sm text-slate-500">
          {footerBits.length > 0 ? footerBits.join(" · ") : "Nenhuma tela marcada"}
        </p>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={onCancel} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={onSave} isLoading={saving}>
            Salvar perfil
          </Button>
        </div>
      </div>
    </div>
  );
}
