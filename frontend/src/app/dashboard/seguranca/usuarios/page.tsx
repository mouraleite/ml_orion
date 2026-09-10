"use client";

import { useState, useEffect, useMemo } from "react";
import {
  Plus, Edit2, Trash2, AlertCircle, RefreshCw,
  ArrowUpDown, ArrowUp, ArrowDown,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";
import { accessProfilesService, AccessProfile } from "@/services/accessProfiles";
import { departamentosService, Departamento } from "@/services/departamentos";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { CollapsibleFilterPanel } from "@/components/shared/CollapsibleFilterPanel";
import { FilterSearchField } from "@/components/shared/FilterSearchField";
import { isAdmin, isReadOnlyVisitor } from "@/lib/roles";

function permissionSelectValue(role: string): string {
  if (isAdmin(role)) return "ADMIN";
  if (isReadOnlyVisitor(role)) return "READ_ONLY";
  return "Usuario";
}

interface User {
  id: number;
  full_name: string;
  email: string;
  cpf: string | null;
  departamento: string | null;
  cargo: string | null;
  nivel: string | null;
  avatar: string | null;
  sienge_id: number | null;
  is_active: boolean;
  role: string;
  perfil_id?: number | null;
  perfil_ids?: number[];
  perfis?: { id: number; name: string }[];
  departamentos?: { id: number; nome: string }[];
}

interface SiengeColaborador {
  id: number;
  name: string;
  cpf: string;
  email: string;
}

const NAME_SMALL_WORDS = new Set(["de", "da", "do", "dos", "das", "e", "del", "di"]);

function onlyDigits(value: string | null | undefined) {
  return (value || "").replace(/\D/g, "");
}

function formatCpfDisplay(cpf: string | null | undefined) {
  const digits = onlyDigits(cpf);
  if (digits.length === 11) return digits.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
  return (cpf || "").trim();
}

function formatPersonName(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .map((word, index) => {
      const lower = word.toLocaleLowerCase("pt-BR");
      if (index > 0 && NAME_SMALL_WORDS.has(lower)) return lower;
      if (!lower) return word;
      return lower.charAt(0).toLocaleUpperCase("pt-BR") + lower.slice(1);
    })
    .join(" ");
}

function foldPersonKey(value: string | null | undefined) {
  return formatPersonName(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR")
    .replace(/\s+/g, " ")
    .trim();
}

function isSiengeColabRegistered(colab: SiengeColaborador, users: User[]) {
  const sid = String(colab.id);
  const cpf = onlyDigits(colab.cpf);
  const email = (colab.email || "").trim().toLowerCase();
  const name = foldPersonKey(colab.name);
  return users.some((u) => {
    if (u.sienge_id != null && String(u.sienge_id) === sid) return true;
    if (cpf.length === 11 && onlyDigits(u.cpf) === cpf) return true;
    if (email && (u.email || "").trim().toLowerCase() === email) return true;
    if (name && foldPersonKey(u.full_name) === name) return true;
    return false;
  });
}

function isLikelyCompany(colab: SiengeColaborador) {
  const digits = onlyDigits(colab.cpf);
  if (digits.length === 14) return true;
  return /\b(LTDA|EIRELI|S\/A|S\.A\.|ME)\b/i.test(colab.name || "");
}

function deptNames(user: { departamentos?: { id: number; nome: string }[]; departamento: string | null }) {
  if (user.departamentos?.length) return user.departamentos.map((d) => d.nome);
  return user.departamento ? [user.departamento] : [];
}

function linkedDepartamentoIds(user: User, erpDepartamentos: Departamento[]): string[] {
  const fromLinks = (user.departamentos ?? []).map((d) => String(d.id));
  if (fromLinks.length) return fromLinks;
  const legado = (user.departamento || "").trim().toLowerCase();
  if (!legado) return [];
  const match = erpDepartamentos.find((d) => d.nome.trim().toLowerCase() === legado);
  return match ? [String(match.id)] : [];
}

function linkedPerfilIds(user: User): string[] {
  if (user.perfis?.length) return user.perfis.map((p) => String(p.id));
  if (user.perfil_ids?.length) return user.perfil_ids.map(String);
  if (user.perfil_id) return [String(user.perfil_id)];
  return [];
}

function legadoNomeFromIds(ids: string[], erpDepartamentos: Departamento[]): string {
  for (const id of ids) {
    const nome = erpDepartamentos.find((d) => String(d.id) === id)?.nome;
    if (nome) return nome;
  }
  return "";
}

function DepartmentChips({
  departamentos,
  legado,
}: {
  departamentos?: { id: number; nome: string }[];
  legado: string | null;
}) {
  const nomes = deptNames({ departamentos, departamento: legado });
  if (nomes.length === 0) {
    return <span className="text-slate-400">—</span>;
  }
  return (
    <div className="flex flex-wrap gap-1" title={nomes.join(", ")}>
      {nomes.map((nome) => (
        <span
          key={nome}
          className="inline-flex max-w-full items-center rounded-md bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-600 break-words"
        >
          {nome}
        </span>
      ))}
    </div>
  );
}

export default function UsuariosPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [siengeColabs, setSiengeColabs] = useState<SiengeColaborador[]>([]);
  const [perfis, setPerfis] = useState<AccessProfile[]>([]);
  const [erpDepartamentos, setErpDepartamentos] = useState<Departamento[]>([]);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  const [busca, setBusca] = useState("");
  const [filtroDepartamento, setFiltroDepartamento] = useState("");
  const [filtroCargo, setFiltroCargo] = useState("");
  const [filtroNivel, setFiltroNivel] = useState("");
  const [filtroPerfil, setFiltroPerfil] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: "asc" | "desc" }>({
    key: "full_name",
    direction: "asc",
  });

  const [formData, setFormData] = useState({
    nome: "",
    email: "",
    cpf: "",
    cargo: "",
    nivel: "",
    senha: "",
    ativo: "true",
    role: "READ_ONLY",
    sienge_id: "",
    perfil_ids: [] as string[],
    departamento_ids: [] as string[],
  });

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [resUsers, resColabs, perfisData, erpDepts] = await Promise.all([
        api.get("/users"),
        api.get("/users/sienge/colaboradores"),
        accessProfilesService.getAll(),
        departamentosService.getAll(),
      ]);
      setUsers(resUsers.data);
      setSiengeColabs(resColabs.data);
      setPerfis(perfisData);
      setErpDepartamentos(erpDepts);
    } catch (err) {
      console.error("Erro ao carregar dados:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleOpenModal = (user?: User) => {
    if (user) {
      setEditingUser(user);
      setFormData({
        nome: user.full_name || "",
        email: user.email || "",
        cpf: user.cpf || "",
        cargo: user.cargo || "",
        nivel: user.nivel || "",
        senha: "", // Não exibe a senha atual
        ativo: user.is_active ? "true" : "false",
        role: permissionSelectValue(user.role || "READ_ONLY"),
        sienge_id: user.sienge_id ? user.sienge_id.toString() : "",
        perfil_ids: linkedPerfilIds(user),
        departamento_ids: linkedDepartamentoIds(user, erpDepartamentos),
      });
    } else {
      setEditingUser(null);
      setFormData({
        nome: "",
        email: "",
        cpf: "",
        cargo: "",
        nivel: "",
        senha: "",
        ativo: "true",
        role: "READ_ONLY",
        sienge_id: "",
        perfil_ids: [],
        departamento_ids: [],
      });
    }
    setIsModalOpen(true);
  };

  const handleSelectSiengeColab = (val: string | number | "") => {
    if (!val) {
      setFormData((prev) => ({ ...prev, sienge_id: "" }));
      return;
    }
    const colab = siengeColabs.find((c) => String(c.id) === String(val));
    if (!colab) return;
    setFormData((prev) => ({
      ...prev,
      nome: formatPersonName(colab.name || prev.nome),
      email: colab.email || prev.email,
      cpf: formatCpfDisplay(colab.cpf) || prev.cpf,
      sienge_id: String(colab.id),
    }));
  };

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSyncing(true);
    
    // Gerar Iniciais para Avatar
    const parts = formData.nome.trim().split(' ');
    const avatar = parts.length > 0 ? (parts[0][0] + (parts.length > 1 ? parts[parts.length-1][0] : '')).toUpperCase() : "U";

    const payload: any = {
      full_name: formData.nome,
      email: formData.email,
      cpf: formData.cpf,
      departamento: legadoNomeFromIds(formData.departamento_ids, erpDepartamentos) || null,
      cargo: formData.cargo,
      nivel: formData.nivel,
      is_active: formData.ativo === "true",
      role: formData.role,
      avatar: avatar,
      sienge_id: formData.sienge_id ? parseInt(formData.sienge_id) : null,
      perfil_ids: formData.perfil_ids.map((id) => parseInt(id, 10)),
      perfil_id: formData.perfil_ids[0] ? parseInt(formData.perfil_ids[0], 10) : null,
      departamento_ids: formData.departamento_ids.map((id) => parseInt(id, 10)),
    };

    if (formData.senha) {
      payload.password = formData.senha;
    }

    try {
      if (editingUser) {
        await api.put(`/users/${editingUser.id}`, payload);
      } else {
        await api.post("/users", payload);
      }
      setIsModalOpen(false);
      await fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Erro ao salvar usuário");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (await confirmDialog("Tem certeza que deseja excluir este colaborador?", { variant: "danger" })) {
      try {
        await api.delete(`/users/${id}`);
        await fetchData();
      } catch (err) {
        console.error(err);
        alert("Erro ao excluir usuário");
      }
    }
  };

  const limparFiltros = () => {
    setBusca("");
    setFiltroDepartamento("");
    setFiltroCargo("");
    setFiltroNivel("");
    setFiltroPerfil("");
    setFiltroStatus("");
  };

  const handleSort = (key: string) => {
    setSortConfig((atual) => ({
      key,
      direction: atual.key === key && atual.direction === "asc" ? "desc" : "asc",
    }));
  };

  const renderSortIcon = (key: string) => {
    if (sortConfig.key !== key) {
      return <ArrowUpDown className="w-3 h-3 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />;
    }
    return sortConfig.direction === "asc"
      ? <ArrowUp className="w-3 h-3 text-[#F5883A]" />
      : <ArrowDown className="w-3 h-3 text-[#F5883A]" />;
  };

  const siengeOptions = useMemo(() => {
    return [...siengeColabs]
      .filter((c) => onlyDigits(c.cpf).length === 11 && !isLikelyCompany(c))
      .filter((c) => !isSiengeColabRegistered(c, users))
      .sort((a, b) => (a.name || "").localeCompare(b.name || "", "pt-BR", { sensitivity: "base" }))
      .map((c) => ({
        id: String(c.id),
        label: c.cpf ? `${formatPersonName(c.name)} · ${formatCpfDisplay(c.cpf)}` : formatPersonName(c.name),
      }));
  }, [siengeColabs, users]);

  const opcoes = useMemo(() => {
    const departamentos = new Set<string>();
    const cargos = new Set<string>();
    const niveis = new Set<string>();
    for (const u of users) {
      deptNames(u).forEach((n) => departamentos.add(n));
      if (u.cargo) cargos.add(u.cargo);
      if (u.nivel) niveis.add(u.nivel);
    }
    return {
      departamentos: [...departamentos].sort((a, b) => a.localeCompare(b, "pt-BR")),
      cargos: [...cargos].sort((a, b) => a.localeCompare(b, "pt-BR")),
      niveis: [...niveis].sort((a, b) => a.localeCompare(b, "pt-BR")),
    };
  }, [users]);

  const sortValue = (user: User, key: string): string => {
    if (key === "departamento") return deptNames(user).join(", ").toLowerCase();
    if (key === "status") return user.is_active ? "ativo" : "inativo";
    const raw = user[key as keyof User];
    return String(raw ?? "").toLowerCase();
  };

  const sortedUsers = useMemo(() => {
    const term = busca.trim().toLowerCase();
    const filtered = users.filter((u) => {
      if (term) {
        const hay = [
          u.full_name,
          u.email,
          u.cpf,
          u.cargo,
          u.nivel,
          ...deptNames(u),
        ].join(" ").toLowerCase();
        if (!hay.includes(term)) return false;
      }
      if (filtroDepartamento && !deptNames(u).includes(filtroDepartamento)) return false;
      if (filtroCargo && u.cargo !== filtroCargo) return false;
      if (filtroNivel && u.nivel !== filtroNivel) return false;
      const userPerfilIds = linkedPerfilIds(u);
      if (filtroPerfil === "nenhum" && userPerfilIds.length) return false;
      if (filtroPerfil && filtroPerfil !== "nenhum" && !userPerfilIds.includes(filtroPerfil)) return false;
      if (filtroStatus === "ativo" && !u.is_active) return false;
      if (filtroStatus === "inativo" && u.is_active) return false;
      return true;
    });
    return [...filtered].sort((a, b) => {
      const valA = sortValue(a, sortConfig.key);
      const valB = sortValue(b, sortConfig.key);
      const cmp = valA.localeCompare(valB, "pt-BR");
      return sortConfig.direction === "asc" ? cmp : -cmp;
    });
  }, [users, busca, filtroDepartamento, filtroCargo, filtroNivel, filtroPerfil, filtroStatus, sortConfig]);

  return (
    <div className="space-y-6 min-w-0 max-w-full">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Cadastro de Usuários</h1>
          <p className="text-slate-500 text-sm mt-1">Gerencie os acessos, cargos e permissões do sistema.</p>
        </div>
        <Button 
          onClick={() => handleOpenModal()} 
          className="bg-[#F5883A] hover:bg-[#d97732] text-white font-bold"
        >
          <Plus className="w-4 h-4 mr-2" />
          Novo Colaborador
        </Button>
      </div>

      <CollapsibleFilterPanel
        activeFilterCount={[busca, filtroDepartamento, filtroCargo, filtroNivel, filtroPerfil, filtroStatus].filter(Boolean).length}
        onClear={limparFiltros}
      >
        <FilterSearchField
          value={busca}
          onChange={setBusca}
          placeholder="Nome, e-mail, CPF ou departamento..."
        />
        <div className="flex-1 min-w-[160px]">
          <label className="text-xs text-slate-500 font-medium mb-1 block">Departamento</label>
          <SearchableSelect
            placeholder="Todos"
            value={filtroDepartamento}
            onChange={(val) => setFiltroDepartamento(String(val))}
            options={opcoes.departamentos.map((d) => ({ id: d, label: d }))}
          />
        </div>
        <div className="flex-1 min-w-[140px]">
          <label className="text-xs text-slate-500 font-medium mb-1 block">Cargo</label>
          <SearchableSelect
            placeholder="Todos"
            value={filtroCargo}
            onChange={(val) => setFiltroCargo(String(val))}
            options={opcoes.cargos.map((c) => ({ id: c, label: c }))}
          />
        </div>
        <div className="flex-1 min-w-[130px]">
          <label className="text-xs text-slate-500 font-medium mb-1 block">Nível</label>
          <SearchableSelect
            placeholder="Todos"
            value={filtroNivel}
            onChange={(val) => setFiltroNivel(String(val))}
            options={opcoes.niveis.map((n) => ({ id: n, label: n }))}
          />
        </div>
        <div className="flex-1 min-w-[140px]">
          <label className="text-xs text-slate-500 font-medium mb-1 block">Perfil</label>
          <SearchableSelect
            placeholder="Todos"
            value={filtroPerfil}
            onChange={(val) => setFiltroPerfil(String(val))}
            options={[
              { id: "nenhum", label: "Sem perfil" },
              ...perfis.map((p) => ({ id: String(p.id), label: p.name })),
            ]}
          />
        </div>
        <div className="flex-1 min-w-[120px]">
          <label className="text-xs text-slate-500 font-medium mb-1 block">Status</label>
          <SearchableSelect
            placeholder="Todos"
            value={filtroStatus}
            onChange={(val) => setFiltroStatus(String(val))}
            options={[
              { id: "ativo", label: "Ativo" },
              { id: "inativo", label: "Inativo" },
            ]}
          />
        </div>
      </CollapsibleFilterPanel>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden min-w-0">
        <div className="overflow-x-hidden">
          <table className="w-full table-fixed text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="px-3 py-3 w-[16%] cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("full_name")}>
                  <div className="flex items-center gap-1">Colaborador {renderSortIcon("full_name")}</div>
                </th>
                <th className="px-3 py-3 w-[11%] whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("cpf")}>
                  <div className="flex items-center gap-1">CPF {renderSortIcon("cpf")}</div>
                </th>
                <th className="px-3 py-3 w-[16%] cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("email")}>
                  <div className="flex items-center gap-1">E-mail {renderSortIcon("email")}</div>
                </th>
                <th className="px-3 py-3 w-[28%] cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("departamento")}>
                  <div className="flex items-center gap-1">Departamento {renderSortIcon("departamento")}</div>
                </th>
                <th className="px-3 py-3 w-[10%] cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("cargo")}>
                  <div className="flex items-center gap-1">Cargo {renderSortIcon("cargo")}</div>
                </th>
                <th className="px-3 py-3 w-[8%] cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("nivel")}>
                  <div className="flex items-center gap-1">Nível {renderSortIcon("nivel")}</div>
                </th>
                <th className="px-3 py-3 w-[6%] cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("status")}>
                  <div className="flex items-center gap-1">Status {renderSortIcon("status")}</div>
                </th>
                <th className="px-3 py-3 w-[5%] text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={8}>
                    <AppLoadingState />
                  </td>
                </tr>
              ) : sortedUsers.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-slate-500">
                    {users.length === 0 ? (
                      <>
                        <AlertCircle className="w-8 h-8 text-slate-300 mb-3 mx-auto" />
                        Nenhum colaborador encontrado.
                      </>
                    ) : (
                      <>
                        <p className="font-medium text-slate-600">Nenhum colaborador encontrado</p>
                        <p className="text-sm mt-1">
                          Tente ajustar ou{" "}
                          <button onClick={limparFiltros} className="text-[#F5883A] underline hover:no-underline">limpar os filtros</button>.
                        </p>
                      </>
                    )}
                  </td>
                </tr>
              ) : sortedUsers.map((user) => (
                <tr key={user.id} className="hover:bg-slate-50/50 transition-colors align-top">
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-8 h-8 shrink-0 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs">
                        {user.avatar || "U"}
                      </div>
                      <span className="font-semibold text-slate-800 break-words leading-snug">{user.full_name}</span>
                    </div>
                  </td>
                  <td className="px-3 py-3 text-slate-500 whitespace-nowrap">{user.cpf || "—"}</td>
                  <td className="px-3 py-3 text-slate-500 break-all leading-snug">{user.email}</td>
                  <td className="px-3 py-3">
                    <DepartmentChips
                      departamentos={user.departamentos}
                      legado={user.departamento}
                    />
                  </td>
                  <td className="px-3 py-3 text-slate-700 break-words leading-snug">{user.cargo || "—"}</td>
                  <td className="px-3 py-3">
                    {user.nivel ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-600 whitespace-nowrap">
                        {user.nivel}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-3 py-3">
                    {user.is_active ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700 whitespace-nowrap">
                        Ativo
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-500 whitespace-nowrap">
                        Inativo
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => handleOpenModal(user)} className="p-1.5 text-slate-400 hover:text-[#F5883A] transition-colors" title="Editar">
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleDelete(user.id)} className="p-1.5 text-slate-400 hover:text-red-500 transition-colors" title="Excluir">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                {editingUser ? "Editar Colaborador" : "Novo Colaborador"}
              </h2>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600 text-2xl leading-none">&times;</button>
            </div>
            
            <div className="p-6 overflow-y-auto">
              {!editingUser && (
                <div className="mb-6 p-4 bg-orange-50 border border-orange-100 rounded-xl">
                  <label className="text-sm font-semibold text-[#d97732] mb-2 block">
                    Preenchimento automático (Sienge)
                  </label>
                  <SearchableSelect
                    options={siengeOptions}
                    value={formData.sienge_id}
                    onChange={handleSelectSiengeColab}
                    placeholder="Busque por nome ou CPF..."
                    className="bg-white"
                  />
                  <p className="text-xs text-orange-700/80 mt-2">
                    {siengeOptions.length === 0
                      ? "Ninguém pendente: quem já está cadastrado no sistema não aparece aqui."
                      : `${siengeOptions.length} pessoa${siengeOptions.length === 1 ? "" : "s"} ainda sem cadastro, em ordem A–Z. Quem já está no sistema não entra nesta lista.`}
                  </p>
                </div>
              )}

              <form id="userForm" onSubmit={handleSaveUser} className="grid grid-cols-1 md:grid-cols-2 gap-5">
                
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">Nome Completo *</label>
                  <Input required placeholder="Nome completo" value={formData.nome} onChange={e => setFormData({...formData, nome: e.target.value})} />
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">E-mail *</label>
                  <Input type="email" required placeholder="email@empresa.com" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">CPF</label>
                  <Input placeholder="000.000.000-00" value={formData.cpf} onChange={e => setFormData({...formData, cpf: e.target.value})} />
                </div>

                <div className="space-y-1.5 md:col-span-2">
                  <label className="text-sm font-semibold text-slate-700">Departamentos</label>
                  <MultiSelect
                    options={erpDepartamentos.map((d) => ({ value: String(d.id), label: d.nome }))}
                    value={formData.departamento_ids}
                    onChange={(vals) => setFormData({ ...formData, departamento_ids: vals })}
                    placeholder="Selecione um ou mais departamentos..."
                  />
                  <p className="text-xs text-slate-500">Um só campo. Pode marcar vários. Diretor enxerga todos automaticamente.</p>
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">Cargo *</label>
                  <Input required placeholder="Ex: Analista Financeiro" value={formData.cargo} onChange={e => setFormData({...formData, cargo: e.target.value})} />
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">Nível Hierárquico *</label>
                  <select required className="w-full h-10 px-3 py-2 rounded-md border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#F5883A]/20 focus:border-[#F5883A]"
                    value={formData.nivel} onChange={e => setFormData({...formData, nivel: e.target.value})}>
                    <option value="">Selecione...</option>
                    <option value="Diretoria">Diretoria</option>
                    <option value="Gerência">Gerência</option>
                    <option value="Coordenação">Coordenação</option>
                    <option value="Supervisão">Supervisão</option>
                    <option value="Analista">Analista</option>
                  </select>
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">Permissão</label>
                  <select className="w-full h-10 px-3 py-2 rounded-md border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#F5883A]/20 focus:border-[#F5883A]"
                    value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})}>
                    <option value="READ_ONLY">Somente visualização</option>
                    <option value="Usuario">Pode criar e alterar</option>
                    <option value="ADMIN">Administrador (acesso total)</option>
                  </select>
                  <p className="text-xs text-slate-500">Duas pessoas no mesmo perfil: uma só vê; a outra cria e altera nos módulos que o perfil libera.</p>
                </div>

                <div className={`space-y-1.5 md:col-span-2 ${formData.role === "ADMIN" ? "pointer-events-none opacity-50" : ""}`}>
                  <label className="text-sm font-semibold text-slate-700">Perfil de Acesso</label>
                  <MultiSelect
                    options={perfis.map((p) => ({ value: String(p.id), label: p.name }))}
                    value={formData.perfil_ids}
                    onChange={(vals) => setFormData({ ...formData, perfil_ids: vals })}
                    placeholder="Selecione um ou mais perfis..."
                  />
                  <p className="text-xs text-slate-500">Pode marcar vários. As telas somam. Quem pode criar/alterar grava se algum perfil liberar. Administrador não precisa de perfil.</p>
                </div>

                <div className="space-y-1.5 md:col-span-2">
                  <label className="text-sm font-semibold text-slate-700">Status</label>
                  <select className="w-full h-10 px-3 py-2 rounded-md border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#F5883A]/20 focus:border-[#F5883A]"
                    value={formData.ativo} onChange={e => setFormData({...formData, ativo: e.target.value})}>
                    <option value="true">Ativo</option>
                    <option value="false">Inativo</option>
                  </select>
                </div>

                <div className="space-y-1.5 md:col-span-2">
                  <label className="text-sm font-semibold text-slate-700">
                    {editingUser ? "Nova Senha (deixe em branco para manter)" : "Senha (opcional)"}
                  </label>
                  <Input type="text" placeholder="Vazio = só Microsoft SSO" value={formData.senha} onChange={e => setFormData({...formData, senha: e.target.value})} />
                  {!editingUser && (
                    <p className="text-xs text-slate-500 mt-1">
                      Deixe em branco para login só com Microsoft. O e-mail deve ser o corporativo (@mouraleite.com.br).
                    </p>
                  )}
                </div>
              </form>
            </div>

            <div className="p-6 border-t border-slate-100 flex items-center justify-end gap-3 bg-slate-50">
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" form="userForm" disabled={isSyncing} className="bg-[#F5883A] hover:bg-[#d97732] text-white">
                {isSyncing ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : null}
                {editingUser ? "Salvar Alterações" : "Cadastrar Colaborador"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
