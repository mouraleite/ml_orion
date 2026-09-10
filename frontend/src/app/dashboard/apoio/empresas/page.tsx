"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Pencil, Trash2, Building2, AlertCircle, Users, ArrowUpDown, ArrowUp, ArrowDown, RefreshCw, Info, Search, X } from "lucide-react";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { apoioService } from "@/services/apoio";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { CollapsibleFilterPanel } from "@/components/shared/CollapsibleFilterPanel";

const TIPO_STORAGE_KEY = "apoio_empresas_tipo";

const TIPOS_EMPRESA = [
  { value: "Holding", color: "bg-emerald-50 text-emerald-800 border-emerald-200" },
  { value: "SPE", color: "bg-sky-50 text-sky-800 border-sky-200" },
  { value: "Loteadora", color: "bg-teal-50 text-teal-800 border-teal-200" },
  { value: "Sócio", color: "bg-amber-50 text-amber-800 border-amber-200" },
  { value: "Parceiro", color: "bg-orange-50 text-orange-800 border-orange-200" },
  { value: "Administradora", color: "bg-indigo-50 text-indigo-800 border-indigo-200" },
  { value: "Outro", color: "bg-slate-100 text-slate-600 border-slate-200" },
];

function getTipoColor(tipo: string) {
  return TIPOS_EMPRESA.find((t) => t.value === tipo)?.color ?? "bg-slate-100 text-slate-600 border-slate-200";
}

function formatCnpj(value?: string) {
  const digits = (value || "").replace(/\D/g, "");
  if (digits.length !== 14) return value || "—";
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

function compareId(a: unknown, b: unknown) {
  const na = Number(a);
  const nb = Number(b);
  if (!Number.isNaN(na) && !Number.isNaN(nb) && na !== nb) return na - nb;
  return String(a ?? "").localeCompare(String(b ?? ""), "pt-BR", { numeric: true });
}

function tipoLabel(tipo?: string) {
  if (tipo === "Sócio PF") return "Pessoa física";
  return tipo || "—";
}

const emptyPartner = {
  tipo: "Sócio",
  partner_company_id: "",
  partner_user_id: "",
  partner_name: "",
  percentage: "",
  is_consolidated: false,
};

export default function EmpresasPage() {
  const [empresas, setEmpresas] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: "asc" | "desc" }>({ key: "id", direction: "asc" });
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");
  const [filtroTipo, setFiltroTipo] = useState("");
  const [filtroConsolidacao, setFiltroConsolidacao] = useState("");

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<any>(null);
  const [partners, setPartners] = useState<any[]>([]);
  const [isPartnersLoading, setIsPartnersLoading] = useState(false);
  const [usuariosSocios, setUsuariosSocios] = useState<{ id: number; full_name: string; email: string }[]>([]);
  const [newPartner, setNewPartner] = useState(emptyPartner);
  const [savingPartner, setSavingPartner] = useState(false);

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [companyToEdit, setCompanyToEdit] = useState<any>(null);
  const [editFormData, setEditFormData] = useState({ nome_fantasia: "" });
  const [savingEdit, setSavingEdit] = useState(false);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(TIPO_STORAGE_KEY);
      if (saved !== null) setFiltroTipo(saved);
    } catch {
      /* ignore */
    }
    loadEmpresas();
  }, []);

  const persistTipo = (tipo: string) => {
    setFiltroTipo(tipo);
    try {
      sessionStorage.setItem(TIPO_STORAGE_KEY, tipo);
    } catch {
      /* ignore */
    }
  };

  async function loadEmpresas() {
    setIsLoading(true);
    try {
      const data = await apoioService.getEmpresas();
      setEmpresas(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Erro ao carregar empresas.");
    } finally {
      setIsLoading(false);
    }
  }

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await apoioService.syncEmpresas();
      await loadEmpresas();
      toast.success("Sincronização concluída.");
    } catch {
      toast.error("Erro ao sincronizar empresas com o Sienge.");
    } finally {
      setIsSyncing(false);
    }
  };

  const extraFilterCount = [filtroStatus, filtroConsolidacao].filter(Boolean).length;

  const limparFiltros = () => {
    setBusca("");
    setFiltroStatus("");
    persistTipo("");
    setFiltroConsolidacao("");
  };

  const counts = useMemo(() => {
    const byTipo: Record<string, number> = {};
    let pendentes = 0;
    for (const emp of empresas) {
      if (!emp.tipo_empresa) pendentes += 1;
      else byTipo[emp.tipo_empresa] = (byTipo[emp.tipo_empresa] || 0) + 1;
    }
    return { total: empresas.length, pendentes, byTipo };
  }, [empresas]);

  const filteredEmpresas = useMemo(() => {
    const q = busca.trim().toLowerCase();
    const qDigits = q.replace(/\D/g, "");
    return empresas.filter((emp) => {
      if (q) {
        const hay = `${emp.razaoSocial || ""} ${emp.nomeFantasia || ""} ${emp.id || ""}`.toLowerCase();
        const cnpjDigits = String(emp.cnpj || "").replace(/\D/g, "");
        if (!hay.includes(q) && !(qDigits && cnpjDigits.includes(qDigits))) return false;
      }
      if (filtroStatus && emp.status !== filtroStatus) return false;
      if (filtroTipo === "Pendente" && emp.tipo_empresa) return false;
      if (filtroTipo && filtroTipo !== "Pendente" && emp.tipo_empresa !== filtroTipo) return false;
      if (filtroConsolidacao === "sim" && !(emp.is_consolidated ?? true)) return false;
      if (filtroConsolidacao === "nao" && (emp.is_consolidated ?? true)) return false;
      return true;
    });
  }, [empresas, busca, filtroStatus, filtroTipo, filtroConsolidacao]);

  const sortedEmpresas = useMemo(() => {
    const { key, direction } = sortConfig;
    const dir = direction === "asc" ? 1 : -1;
    return [...filteredEmpresas].sort((a, b) => {
      if (key === "id") return compareId(a.id, b.id) * dir;
      if (key === "is_consolidated") {
        const av = a.is_consolidated ?? true ? 1 : 0;
        const bv = b.is_consolidated ?? true ? 1 : 0;
        return (av - bv) * dir;
      }
      const aValue = String(a[key] ?? "").toLowerCase();
      const bValue = String(b[key] ?? "").toLowerCase();
      return aValue.localeCompare(bValue, "pt-BR") * dir;
    });
  }, [filteredEmpresas, sortConfig]);

  const handleSort = (key: string) => {
    setSortConfig((prev) =>
      prev.key === key ? { key, direction: prev.direction === "asc" ? "desc" : "asc" } : { key, direction: "asc" }
    );
  };

  const renderSortIcon = (key: string) => {
    if (sortConfig.key !== key) return <ArrowUpDown className="w-3 h-3 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />;
    return sortConfig.direction === "asc" ? <ArrowUp className="w-3 h-3 text-ml-green" /> : <ArrowDown className="w-3 h-3 text-ml-green" />;
  };

  const openPartnersModal = (emp: any) => {
    if (!emp.db_id) {
      toast.error("Aguarde a sincronização desta empresa com o banco.");
      return;
    }
    setSelectedCompany(emp);
    setNewPartner(emptyPartner);
    setIsModalOpen(true);
    loadPartners(emp.db_id);
    apoioService.getUsuariosParaSocios().then(setUsuariosSocios).catch(() => setUsuariosSocios([]));
  };

  const handleToggleConsolidacao = async (emp: any) => {
    if (!emp.db_id) {
      toast.error("Aguarde a sincronização desta empresa com o banco.");
      return;
    }
    const entraHoje = emp.is_consolidated ?? true;
    const ok = await confirmDialog(
      entraHoje
        ? "Tirar esta empresa do consolidado? As telas que usam essa marca passam a ignorá-la."
        : "Incluir esta empresa no consolidado?",
      {
        title: entraHoje ? "Tirar do consolidado" : "Incluir no consolidado",
        confirmLabel: entraHoje ? "Tirar" : "Incluir",
        variant: entraHoje ? "danger" : "default",
      }
    );
    if (!ok) return;
    const novo = !entraHoje;
    setEmpresas((current) => current.map((e) => (e.id === emp.id ? { ...e, is_consolidated: novo } : e)));
    try {
      await apoioService.updateCompany(emp.db_id, { is_consolidated: novo });
      toast.success(novo ? "Empresa incluída no consolidado." : "Empresa retirada do consolidado.");
    } catch {
      toast.error("Erro ao atualizar consolidação.");
      loadEmpresas();
    }
  };

  const handleChangeStatus = async (emp: any) => {
    if (!emp.db_id) return;
    const novoStatus = emp.status === "Ativa" ? "Inativa" : "Ativa";
    const ok = await confirmDialog(
      novoStatus === "Inativa" ? "Inativar esta empresa?" : "Reativar esta empresa?",
      {
        title: novoStatus === "Inativa" ? "Inativar empresa" : "Reativar empresa",
        confirmLabel: novoStatus === "Inativa" ? "Inativar" : "Reativar",
        variant: novoStatus === "Inativa" ? "danger" : "default",
      }
    );
    if (!ok) return;
    setEmpresas((current) => current.map((e) => (e.id === emp.id ? { ...e, status: novoStatus } : e)));
    try {
      await apoioService.updateCompany(emp.db_id, { status: novoStatus });
      toast.success(novoStatus === "Ativa" ? "Empresa reativada." : "Empresa inativada.");
    } catch {
      toast.error("Erro ao atualizar o status.");
      loadEmpresas();
    }
  };

  const handleChangeTipoEmpresa = async (emp: any, novoTipo: string) => {
    if (!emp.db_id) return;
    setEmpresas((current) => current.map((e) => (e.id === emp.id ? { ...e, tipo_empresa: novoTipo } : e)));
    try {
      await apoioService.updateCompany(emp.db_id, { tipo_empresa: novoTipo });
    } catch {
      toast.error("Erro ao atualizar o tipo.");
      loadEmpresas();
    }
  };

  const loadPartners = (db_id: number) => {
    setIsPartnersLoading(true);
    apoioService
      .getCompanyPartners(db_id)
      .then((data) => setPartners(Array.isArray(data) ? data : []))
      .catch(() => {
        toast.error("Erro ao carregar sócios.");
        setPartners([]);
      })
      .finally(() => setIsPartnersLoading(false));
  };

  const handleAddPartner = async () => {
    const pct = parseFloat(String(newPartner.percentage).replace(",", "."));
    if (Number.isNaN(pct) || pct < 0 || pct > 100) {
      toast.error("Informe um percentual entre 0 e 100.");
      return;
    }
    if (newPartner.tipo === "Sócio" && !newPartner.partner_company_id) {
      toast.error("Selecione a empresa sócia.");
      return;
    }
    if (newPartner.tipo === "Sócio PF" && !newPartner.partner_user_id) {
      toast.error("Selecione o usuário pessoa física.");
      return;
    }
    if (newPartner.tipo === "Parceiro" && !newPartner.partner_name.trim()) {
      toast.error("Informe o nome do parceiro.");
      return;
    }
    setSavingPartner(true);
    try {
      await apoioService.addCompanyPartner(selectedCompany.db_id, {
        tipo: newPartner.tipo,
        partner_company_id: newPartner.partner_company_id ? parseInt(newPartner.partner_company_id, 10) : null,
        partner_user_id: newPartner.partner_user_id ? parseInt(newPartner.partner_user_id, 10) : null,
        partner_name: newPartner.partner_name,
        percentage: pct,
        is_consolidated: newPartner.is_consolidated,
      });
      setNewPartner({ ...emptyPartner, tipo: newPartner.tipo });
      loadPartners(selectedCompany.db_id);
      toast.success("Vínculo adicionado.");
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Erro ao vincular sócio.");
    } finally {
      setSavingPartner(false);
    }
  };

  const handleDeletePartner = async (partnerId: number) => {
    const ok = await confirmDialog("Remover este sócio da composição? O cadastro da empresa ou do usuário permanece.", {
      title: "Remover sócio",
      confirmLabel: "Remover",
      variant: "danger",
    });
    if (!ok) return;
    try {
      await apoioService.deleteCompanyPartner(selectedCompany.db_id, partnerId);
      loadPartners(selectedCompany.db_id);
      toast.success("Sócio removido.");
    } catch {
      toast.error("Erro ao remover sócio.");
    }
  };

  const openEditModal = (emp: any) => {
    if (!emp.db_id) {
      toast.error("Aguarde a sincronização desta empresa com o banco.");
      return;
    }
    setCompanyToEdit(emp);
    setEditFormData({
      nome_fantasia: emp.nomeFantasia && emp.nomeFantasia !== "N/A" ? emp.nomeFantasia : "",
    });
    setIsEditModalOpen(true);
  };

  const handleEditCompany = async () => {
    if (!companyToEdit?.db_id) return;
    setSavingEdit(true);
    try {
      await apoioService.updateCompany(companyToEdit.db_id, { nome_fantasia: editFormData.nome_fantasia });
      setIsEditModalOpen(false);
      toast.success("Nome fantasia atualizado.");
      loadEmpresas();
    } catch {
      toast.error("Erro ao salvar a empresa.");
    } finally {
      setSavingEdit(false);
    }
  };

  const totalParticipacao = partners.reduce((sum, p) => sum + (Number(p.percentage) || 0), 0);
  const totalOk = Math.abs(totalParticipacao - 100) < 0.05;

  const tipoTabs: { value: string; label: string; count: number; activeClass?: string }[] = [
    { value: "", label: "Todas", count: counts.total },
    { value: "Pendente", label: "Pendentes", count: counts.pendentes, activeClass: "bg-red-50 text-red-700 border-red-200" },
    ...TIPOS_EMPRESA.map((t) => ({ value: t.value, label: t.value, count: counts.byTipo[t.value] || 0 })),
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shrink-0">
            <Building2 size={20} />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-slate-800">Cadastro de Empresas</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Empresas do Sienge: tipo, consolidado e sócios. A razão social vem do ERP.
            </p>
          </div>
        </div>
        <Button onClick={handleSync} disabled={isSyncing} isLoading={isSyncing} className="gap-2 shrink-0">
          {!isSyncing ? <RefreshCw size={16} /> : null}
          {isSyncing ? "Sincronizando…" : "Atualizar sincronização"}
        </Button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 px-4 py-3 grid sm:grid-cols-3 gap-3 sm:gap-6">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-ml-green">1 · Classificar</p>
          <p className="text-xs text-slate-600 mt-0.5">Defina o tipo (Holding, SPE, Sócio…). Pendentes precisam de classificação.</p>
        </div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-ml-green">2 · Sócios</p>
          <p className="text-xs text-slate-600 mt-0.5">Empresa, pessoa física (usuário) ou nome avulso, com o % de cada um.</p>
        </div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-ml-green">3 · Consolidado</p>
          <p className="text-xs text-slate-600 mt-0.5">O interruptor define se a empresa entra nas telas consolidadas. O sistema confirma antes de alterar.</p>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row lg:items-center gap-3">
        <div className="flex flex-wrap gap-2 flex-1 min-w-0">
          {tipoTabs.map((tab) => {
            const isActive = filtroTipo === tab.value;
            return (
              <button
                key={tab.value || "todas"}
                type="button"
                onClick={() => persistTipo(tab.value)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
                  isActive
                    ? tab.activeClass || "bg-ml-green text-white border-ml-green"
                    : "bg-white text-slate-600 border-slate-200 hover:border-ml-green hover:text-ml-green"
                }`}
              >
                {tab.label}
                <span className={`px-1.5 py-0.5 rounded-full ${isActive ? "bg-white/20 text-current" : "bg-slate-100 text-slate-500"}`}>
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>
        <div className="relative w-full lg:w-72 shrink-0">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Nome, ID ou CNPJ…"
            className="w-full pl-8 pr-8 py-2 text-sm border border-slate-200 rounded-lg bg-white text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-ml-green/20 focus:border-ml-green"
          />
          {busca ? (
            <button
              type="button"
              onClick={() => setBusca("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              title="Limpar busca"
            >
              <X className="w-4 h-4" />
            </button>
          ) : null}
        </div>
      </div>

      <CollapsibleFilterPanel activeFilterCount={extraFilterCount} onClear={limparFiltros}>
        <div className="flex-1 min-w-[140px]">
          <label className="text-xs text-slate-500 font-medium mb-1 block">Status</label>
          <SearchableSelect
            placeholder="Todos"
            value={filtroStatus}
            onChange={(val) => setFiltroStatus(val === "" ? "" : String(val))}
            options={[
              { id: "Ativa", label: "Ativa" },
              { id: "Inativa", label: "Inativa" },
            ]}
          />
        </div>
        <div className="flex-1 min-w-[150px]">
          <label className="text-xs text-slate-500 font-medium mb-1 block">Consolidação</label>
          <SearchableSelect
            placeholder="Todos"
            value={filtroConsolidacao}
            onChange={(val) => setFiltroConsolidacao(val === "" ? "" : String(val))}
            options={[
              { id: "sim", label: "No consolidado" },
              { id: "nao", label: "Fora" },
            ]}
          />
        </div>
      </CollapsibleFilterPanel>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between gap-3">
          <p className="text-xs text-slate-500">
            {isLoading ? "Carregando…" : `Mostrando ${sortedEmpresas.length} de ${empresas.length} empresa(s)`}
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50" onClick={() => handleSort("id")}>
                  <div className="flex items-center gap-2">ID {renderSortIcon("id")}</div>
                </th>
                <th className="px-4 py-3 cursor-pointer group select-none hover:bg-slate-100/50" onClick={() => handleSort("nomeFantasia")}>
                  <div className="flex items-center gap-2">Empresa {renderSortIcon("nomeFantasia")}</div>
                </th>
                <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50" onClick={() => handleSort("cnpj")}>
                  <div className="flex items-center gap-2">CNPJ {renderSortIcon("cnpj")}</div>
                </th>
                <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50" onClick={() => handleSort("status")}>
                  <div className="flex items-center gap-2">Status {renderSortIcon("status")}</div>
                </th>
                <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50" onClick={() => handleSort("is_consolidated")}>
                  <div className="flex items-center justify-center gap-2">Consolidado {renderSortIcon("is_consolidated")}</div>
                </th>
                <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50" onClick={() => handleSort("tipo_empresa")}>
                  <div className="flex items-center gap-2">Tipo {renderSortIcon("tipo_empresa")}</div>
                </th>
                <th className="px-4 py-3 text-right whitespace-nowrap">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={7}>
                    <AppLoadingState />
                  </td>
                </tr>
              ) : (
                sortedEmpresas.map((emp) => (
                  <tr key={emp.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-4 py-3 text-slate-500 font-mono text-xs whitespace-nowrap">{emp.id}</td>
                    <td className="px-4 py-3 min-w-[220px] max-w-[360px]">
                      <p className="font-semibold text-slate-800 leading-tight truncate" title={emp.nomeFantasia || emp.razaoSocial}>
                        {emp.nomeFantasia && emp.nomeFantasia !== "N/A" ? emp.nomeFantasia : emp.razaoSocial || "—"}
                      </p>
                      {emp.nomeFantasia && emp.razaoSocial && emp.nomeFantasia !== emp.razaoSocial ? (
                        <p className="text-xs text-slate-400 mt-0.5 truncate" title={emp.razaoSocial}>
                          {emp.razaoSocial}
                        </p>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-slate-500 whitespace-nowrap font-mono text-xs">{formatCnpj(emp.cnpj)}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => handleChangeStatus(emp)}
                        title={emp.status === "Ativa" ? "Clique para inativar" : "Clique para reativar"}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border transition-colors ${
                          emp.status === "Ativa"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                            : "bg-slate-100 text-slate-500 border-slate-200 hover:bg-slate-200"
                        }`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${emp.status === "Ativa" ? "bg-emerald-500" : "bg-slate-400"}`} />
                        {emp.status}
                      </button>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <label
                        className="relative inline-flex items-center cursor-pointer"
                        title={emp.is_consolidated ?? true ? "No consolidado — clique para tirar" : "Fora do consolidado — clique para incluir"}
                      >
                        <input
                          type="checkbox"
                          className="sr-only peer"
                          checked={emp.is_consolidated ?? true}
                          onChange={() => handleToggleConsolidacao(emp)}
                        />
                        <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-ml-green" />
                      </label>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <select
                        value={emp.tipo_empresa ?? ""}
                        onChange={(e) => handleChangeTipoEmpresa(emp, e.target.value)}
                        className={`text-xs font-semibold px-2 py-1 rounded-full border cursor-pointer focus:ring-2 focus:ring-ml-green/30 focus:outline-none appearance-none pr-6 ${
                          emp.tipo_empresa ? getTipoColor(emp.tipo_empresa) : "bg-red-50 text-red-600 border-red-200"
                        }`}
                        style={{
                          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23666' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
                          backgroundRepeat: "no-repeat",
                          backgroundPosition: "right 4px center",
                        }}
                      >
                        <option value="" disabled>
                          Pendente
                        </option>
                        {TIPOS_EMPRESA.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.value}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => openPartnersModal(emp)}
                          className="inline-flex items-center gap-1 px-2 py-1.5 text-xs font-medium text-ml-green hover:bg-emerald-50 rounded-lg transition-colors"
                          title="Estrutura societária"
                        >
                          <Users className="w-4 h-4" /> Sócios
                        </button>
                        <button
                          type="button"
                          onClick={() => openEditModal(emp)}
                          className="p-1.5 text-slate-400 hover:text-ml-green hover:bg-emerald-50 rounded-lg transition-colors"
                          title="Editar nome fantasia"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          {!isLoading && sortedEmpresas.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <AlertCircle className="w-8 h-8 text-slate-300 mx-auto mb-3" />
              {extraFilterCount || filtroTipo || busca ? (
                <>
                  <p className="font-medium text-slate-600">Nenhuma empresa neste recorte</p>
                  <p className="text-sm mt-1">
                    Ajuste a busca ou{" "}
                    <button type="button" onClick={limparFiltros} className="text-ml-green font-medium hover:underline">
                      limpar os filtros
                    </button>
                    .
                  </p>
                </>
              ) : (
                <p>Nenhuma empresa sincronizada. Use Atualizar sincronização.</p>
              )}
            </div>
          ) : null}
        </div>
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={`Sócios — ${selectedCompany?.nomeFantasia || selectedCompany?.razaoSocial || ""}`} size="lg">
        <div className="space-y-6">
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <h3 className="text-sm font-semibold text-slate-800">Adicionar vínculo</h3>
            <p className="text-xs text-slate-500 mt-0.5 mb-4">
              Empresa cadastrada, pessoa física do cadastro de usuários, ou um nome avulso.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1.5 block">1. Tipo do vínculo</label>
                <select
                  className="w-full border border-slate-200 rounded-lg text-sm p-2.5 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-ml-green/20 focus:border-ml-green"
                  value={newPartner.tipo}
                  onChange={(e) =>
                    setNewPartner({ ...newPartner, tipo: e.target.value, partner_company_id: "", partner_user_id: "", partner_name: "" })
                  }
                >
                  <option value="Sócio">Sócio — outra empresa</option>
                  <option value="Sócio PF">Sócio — pessoa física (usuário)</option>
                  <option value="Parceiro">Parceiro — nome avulso</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1.5 block">
                  2.{" "}
                  {newPartner.tipo === "Sócio"
                    ? "Qual empresa é o sócio?"
                    : newPartner.tipo === "Sócio PF"
                      ? "Qual usuário é o sócio?"
                      : "Nome do parceiro"}
                </label>
                {newPartner.tipo === "Sócio" ? (
                  <SearchableSelect
                    options={empresas
                      .filter((e) => e.db_id && e.db_id !== selectedCompany?.db_id)
                      .map((e) => ({ id: String(e.db_id), label: e.nomeFantasia || e.razaoSocial }))}
                    value={newPartner.partner_company_id}
                    onChange={(value) => setNewPartner({ ...newPartner, partner_company_id: value === "" ? "" : String(value) })}
                    placeholder="— Selecione uma empresa —"
                  />
                ) : newPartner.tipo === "Sócio PF" ? (
                  <SearchableSelect
                    options={usuariosSocios.map((u) => ({ id: u.id, label: u.full_name }))}
                    value={newPartner.partner_user_id === "" ? "" : Number(newPartner.partner_user_id)}
                    onChange={(value) => setNewPartner({ ...newPartner, partner_user_id: value === "" ? "" : String(value) })}
                    placeholder="— Selecione um usuário —"
                  />
                ) : (
                  <input
                    type="text"
                    className="w-full border border-slate-200 rounded-lg text-sm p-2.5 bg-white text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-ml-green/20 focus:border-ml-green"
                    placeholder="Ex.: João da Silva"
                    value={newPartner.partner_name}
                    onChange={(e) => setNewPartner({ ...newPartner, partner_name: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddPartner();
                      }
                    }}
                  />
                )}
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1.5 block">3. Participação (%)</label>
                <div className="relative">
                  <input
                    type="text"
                    inputMode="decimal"
                    className="w-full border border-slate-200 rounded-lg text-sm p-2.5 pr-8 bg-white text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-ml-green/20 focus:border-ml-green"
                    placeholder="Ex.: 29,49"
                    value={newPartner.percentage}
                    onChange={(e) => setNewPartner({ ...newPartner, percentage: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddPartner();
                      }
                    }}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-medium">%</span>
                </div>
              </div>
              <div className="flex items-end pb-1">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    className="rounded border-slate-300 text-ml-green focus:ring-ml-green"
                    checked={newPartner.is_consolidated}
                    onChange={(e) => setNewPartner({ ...newPartner, is_consolidated: e.target.checked })}
                  />
                  <span>
                    <span className="text-sm font-medium text-slate-700 block">Consolida balanço deste vínculo</span>
                    <span className="text-xs text-slate-400">Sócios da holding costumam ficar desmarcados</span>
                  </span>
                </label>
              </div>
            </div>
            <div className="mt-5 flex justify-end border-t border-slate-200 pt-4">
              <Button onClick={handleAddPartner} isLoading={savingPartner} className="gap-2">
                <Plus className="w-4 h-4" /> Vincular
              </Button>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between gap-3 mb-3">
              <h3 className="text-sm font-semibold text-slate-800">Composição atual</h3>
              {partners.length > 0 ? (
                <p className={`text-xs font-semibold ${totalOk ? "text-emerald-700" : "text-amber-700"}`}>
                  Soma {totalParticipacao.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%
                  {totalOk ? " · 100%" : " · confira se fecha 100%"}
                </p>
              ) : null}
            </div>
            {isPartnersLoading ? (
              <AppLoadingState />
            ) : partners.length === 0 ? (
              <p className="text-sm text-slate-500">Nenhum sócio vinculado a esta empresa.</p>
            ) : (
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-600">
                    <tr>
                      <th className="p-3">Nome</th>
                      <th className="p-3">Tipo</th>
                      <th className="p-3 text-center">%</th>
                      <th className="p-3 text-center">Consolida</th>
                      <th className="p-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {partners.map((p) => (
                      <tr key={p.id}>
                        <td className="p-3 font-medium text-slate-800">{p.partner_name}</td>
                        <td className="p-3 text-slate-500">{tipoLabel(p.tipo)}</td>
                        <td className="p-3 text-center font-semibold text-slate-700">
                          {Number(p.percentage).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%
                        </td>
                        <td className="p-3 text-center">
                          <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${p.is_consolidated ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                            {p.is_consolidated ? "Sim" : "Não"}
                          </span>
                        </td>
                        <td className="p-3 text-right">
                          <button type="button" onClick={() => handleDeletePartner(p.id)} className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg" title="Remover">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </Modal>

      <Modal isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)} title="Editar empresa" size="md">
        <div className="space-y-4">
          <div className="flex items-start gap-2 rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 text-xs text-slate-500">
            <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            A razão social vem do Sienge e não pode ser alterada aqui.
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1">Razão social</label>
            <Input value={companyToEdit?.razaoSocial || ""} disabled className="bg-slate-50 text-slate-500" />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1">Nome fantasia</label>
            <Input
              value={editFormData.nome_fantasia}
              onChange={(e) => setEditFormData({ ...editFormData, nome_fantasia: e.target.value })}
              placeholder="Como a empresa aparece no sistema"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsEditModalOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleEditCompany} isLoading={savingEdit}>
              Salvar
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
