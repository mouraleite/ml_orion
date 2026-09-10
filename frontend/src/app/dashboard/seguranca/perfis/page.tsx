"use client";

import { useState, useEffect } from "react";
import { Plus, Edit2, Trash2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { accessProfilesService, AccessProfile } from "@/services/accessProfiles";
import { toast } from "react-hot-toast";
import { hydratePermissions, persistPermissions, ensureWriteFlags } from "@/lib/accessMatrix";
import { ProfileAccessEditor, type ProfileFormData } from "./ProfileAccessEditor";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

const emptyForm = (): ProfileFormData => ({
  name: "",
  description: "",
  is_active: true,
  permissions: ensureWriteFlags({}, ""),
});

export default function PerfisAcessoPage() {
  const [perfis, setPerfis] = useState<AccessProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<ProfileFormData>(emptyForm);

  const carregarPerfis = async () => {
    setIsLoading(true);
    try {
      const data = await accessProfilesService.getAll();
      setPerfis(data);
    } catch (err) {
      console.error(err);
      toast.error("Erro ao carregar perfis.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    carregarPerfis();
  }, []);

  const handleOpenEditor = (perfil?: AccessProfile) => {
    if (perfil) {
      setEditingId(perfil.id);
      setFormData({
        name: perfil.name,
        description: perfil.description || "",
        is_active: perfil.is_active,
        permissions: ensureWriteFlags(hydratePermissions(perfil.permissions || {}), perfil.name),
      });
    } else {
      setEditingId(null);
      setFormData(emptyForm());
    }
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast.error("Nome é obrigatório.");
      return;
    }
    setSaving(true);
    const payload = {
      ...formData,
      permissions: persistPermissions(formData.permissions),
    };
    try {
      if (editingId) {
        await accessProfilesService.update(editingId, payload);
        toast.success("Perfil atualizado!");
      } else {
        await accessProfilesService.create(payload);
        toast.success("Perfil criado!");
      }
      setIsEditing(false);
      carregarPerfis();
    } catch (err) {
      toast.error("Erro ao salvar perfil.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!(await confirmDialog("Tem certeza que deseja excluir este perfil?", { variant: "danger" }))) return;
    try {
      await accessProfilesService.delete(id);
      toast.success("Perfil excluído.");
      carregarPerfis();
    } catch (err: any) {
      if (err.response?.status === 400) {
        toast.error("Não é possível excluir: existem usuários vinculados.");
      } else {
        toast.error("Erro ao excluir.");
      }
    }
  };

  if (isEditing) {
    return (
      <ProfileAccessEditor
        title={editingId ? "Editar perfil" : "Novo perfil"}
        formData={formData}
        onChange={setFormData}
        onCancel={() => setIsEditing(false)}
        onSave={handleSave}
        saving={saving}
      />
    );
  }

  return (
    <div className="w-full h-full flex flex-col space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
            <ShieldCheck size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Perfis de Acesso</h1>
            <p className="text-sm text-slate-500">
              Libere as telas do menu — inclusive as do Dashboard de Orçamento — por perfil.
            </p>
          </div>
        </div>
        <Button onClick={() => handleOpenEditor()} className="gap-2 shrink-0 shadow-sm">
          <Plus size={16} /> Novo Perfil
        </Button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex-1 flex flex-col overflow-hidden">
        {isLoading ? (
          <AppLoadingState />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-500 uppercase bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-4 font-semibold">Perfil</th>
                  <th className="px-6 py-4 font-semibold">Descrição</th>
                  <th className="px-6 py-4 font-semibold text-center">Status</th>
                  <th className="px-6 py-4 font-semibold text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {perfis.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-800">{p.name}</td>
                    <td className="px-6 py-4 text-slate-500">{p.description || "-"}</td>
                    <td className="px-6 py-4 text-center">
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          p.is_active
                            ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20"
                            : "bg-rose-50 text-rose-700 ring-1 ring-rose-600/20"
                        }`}
                      >
                        {p.is_active ? "Ativo" : "Inativo"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleOpenEditor(p)}
                          className="p-2 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(p.id)}
                          className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {perfis.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                      Nenhum perfil cadastrado.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
