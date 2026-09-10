"use client";

import { useState, useEffect, useCallback, useMemo, type ReactNode } from "react";
import { Plus, Edit2, Trash2, Building2, ChevronRight, ChevronDown, LayoutGrid, FileText, CheckSquare, Square, Search, X, Minus, FolderTree, ArrowUp, ArrowDown, ArrowUpDown, ArrowDownAZ, ArrowUpZA, Eye, Copy, Link2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { departamentosService, Departamento, DeptCostCenter, DeptPlano } from "@/services/departamentos";
import { formatPlanId } from "@/lib/formatters";
import toast from "react-hot-toast";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { DeparaSiengePanel } from "./DeparaSiengePanel";
import { DiretoriasPanel } from "./DiretoriasPanel";

type PageView = "matriz" | "depara" | "diretorias";
type ActiveTab = "cost-centers" | "planos";
type CCStatusFilter = "all" | "ativo" | "inativo";
type CheckState = "all" | "none" | "partial";
type SortDir = "asc" | "desc";
type CCSortKey = "id" | "nome" | "status";

function compareSiengeId(a: string | undefined, b: string | undefined) {
  const na = parseInt(a || "0", 10);
  const nb = parseInt(b || "0", 10);
  if (!Number.isNaN(na) && !Number.isNaN(nb) && na !== nb) return na - nb;
  return (a || "").localeCompare(b || "", undefined, { numeric: true });
}

function getAnaliticas(planos: DeptPlano[]) {
  return planos.filter((p) => p.tipo === "R");
}

function getTotalizadoras(planos: DeptPlano[]) {
  return planos.filter((p) => p.tipo === "T");
}

/** Segmentos do código do plano (1.01.02), não o db_id cru — evita 11 cair dentro de 1. */
function planSegments(dbId: string | undefined) {
  return formatPlanId(dbId).split(".").filter(Boolean);
}

function isUnderPlan(childDbId: string | undefined, parentDbId: string | undefined) {
  const child = planSegments(childDbId);
  const parent = planSegments(parentDbId);
  if (parent.length === 0 || child.length <= parent.length) return false;
  return parent.every((seg, i) => seg === child[i]);
}

function isDirectChildPlan(childDbId: string | undefined, parentDbId: string | undefined) {
  const child = planSegments(childDbId);
  const parent = planSegments(parentDbId);
  return child.length === parent.length + 1 && parent.every((seg, i) => seg === child[i]);
}

function comparePlanDbId(a: string | undefined, b: string | undefined) {
  const pa = planSegments(a);
  const pb = planSegments(b);
  const n = Math.min(pa.length, pb.length);
  for (let i = 0; i < n; i++) {
    const na = parseInt(pa[i], 10);
    const nb = parseInt(pb[i], 10);
    if (!Number.isNaN(na) && !Number.isNaN(nb) && na !== nb) return na - nb;
    const cmp = pa[i].localeCompare(pb[i], undefined, { numeric: true });
    if (cmp) return cmp;
  }
  return pa.length - pb.length;
}

function getDescendantAnalytics(dbId: string, planos: DeptPlano[]) {
  return getAnaliticas(planos).filter((p) => isUnderPlan(p.db_id, dbId));
}

function getDirectChildTotalizadoras(parentDbId: string, totalizadoras: DeptPlano[]) {
  return totalizadoras
    .filter((t) => isDirectChildPlan(t.db_id, parentDbId))
    .sort((a, b) => comparePlanDbId(a.db_id, b.db_id));
}

function getRootTotalizadoras(totalizadoras: DeptPlano[]) {
  return totalizadoras
    .filter((t) => !totalizadoras.some((other) => isUnderPlan(t.db_id, other.db_id)))
    .sort((a, b) => comparePlanDbId(a.db_id, b.db_id));
}

function getGroupCheckState(items: DeptPlano[]): CheckState {
  if (items.length === 0) return "none";
  const permitted = items.filter((p) => p.permitido).length;
  if (permitted === 0) return "none";
  if (permitted === items.length) return "all";
  return "partial";
}

function getDirectAnalytics(parentDbId: string, planos: DeptPlano[]) {
  return getAnaliticas(planos)
    .filter((a) => isDirectChildPlan(a.db_id, parentDbId))
    .sort((a, b) => comparePlanDbId(a.db_id, b.db_id));
}

function totalizadoraTemLiberado(totaliz: DeptPlano, allPlanos: DeptPlano[]) {
  return getDescendantAnalytics(totaliz.db_id, allPlanos).some((p) => p.permitido);
}

function matchesPlanoSearch(plano: DeptPlano, term: string, allPlanos: DeptPlano[]) {
  if (!term) return true;
  const t = term.toLowerCase();
  if (plano.nome?.toLowerCase().includes(t)) return true;
  if (plano.db_id?.toLowerCase().includes(t)) return true;
  if (formatPlanId(plano.db_id).toLowerCase().includes(t)) return true;
  if (plano.tipo === "T") {
    return getDescendantAnalytics(plano.db_id, allPlanos).some(
      (a) => a.nome?.toLowerCase().includes(t) || a.db_id?.includes(t),
    );
  }
  return false;
}

export default function DepartamentosPage() {
  const [departamentos, setDepartamentos] = useState<Departamento[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [pageView, setPageView] = useState<PageView>("matriz");
  const [selectedDept, setSelectedDept] = useState<Departamento | null>(null);

  // Modal de criação/edição do departamento
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formNome, setFormNome] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // Conteúdo do painel de associações
  const [activeTab, setActiveTab] = useState<ActiveTab>("cost-centers");
  const [costCenters, setCostCenters] = useState<DeptCostCenter[]>([]);
  const [planos, setPlanos] = useState<DeptPlano[]>([]);
  const [isLoadingAssoc, setIsLoadingAssoc] = useState(false);
  const [searchCC, setSearchCC] = useState("");
  const [searchPlano, setSearchPlano] = useState("");
  const [buscaDept, setBuscaDept] = useState("");
  const [ccStatusFilter, setCcStatusFilter] = useState<CCStatusFilter>("all");
  const [somenteLiberados, setSomenteLiberados] = useState(false);
  const [expandedTotaliz, setExpandedTotaliz] = useState<Record<string, boolean>>({});
  const [deptSortDir, setDeptSortDir] = useState<SortDir>("asc");
  const [ccSort, setCcSort] = useState<{ key: CCSortKey; dir: SortDir }>({ key: "id", dir: "asc" });
  const [isCopyOpen, setIsCopyOpen] = useState(false);
  const [copyDir, setCopyDir] = useState<"trazer" | "enviar">("trazer");
  const [copyOtherId, setCopyOtherId] = useState<number | "">("");
  const [copyObras, setCopyObras] = useState(true);
  const [copyPlanos, setCopyPlanos] = useState(true);
  const [isCopying, setIsCopying] = useState(false);

  const persistDeptId = (id: number) => {
    try {
      sessionStorage.setItem("apoio_dept_selected_id", String(id));
    } catch {
      /* ignore */
    }
  };

  const selectDept = (dept: Departamento) => {
    setSelectedDept(dept);
    persistDeptId(dept.id);
  };

  const carregarDepartamentos = async () => {
    setIsLoading(true);
    try {
      const data = await departamentosService.getTodos();
      // Ordena alfabeticamente para melhor organização
      const sorted = data.sort((a, b) => a.nome.localeCompare(b.nome));
      setDepartamentos(sorted);
    } catch (err) {
      toast.error("Erro ao carregar departamentos.");
    } finally {
      setIsLoading(false);
    }
  };

  const carregarAssociacoes = useCallback(async (deptId: number) => {
    setIsLoadingAssoc(true);
    try {
      const [ccs, ps] = await Promise.all([
        departamentosService.getCostCenters(deptId),
        departamentosService.getPlanos(deptId),
      ]);
      setCostCenters(ccs);
      setPlanos(ps);
    } catch (err) {
      toast.error("Erro ao carregar associações.");
    } finally {
      setIsLoadingAssoc(false);
    }
  }, []);

  useEffect(() => {
    carregarDepartamentos();
  }, []);

  const selectedId = selectedDept?.id;

  useEffect(() => {
    if (selectedId == null) return;
    setCostCenters([]);
    setPlanos([]);
    carregarAssociacoes(selectedId);
    setSearchCC("");
    setSearchPlano("");
    setExpandedTotaliz({});
    setCcStatusFilter("all");
  }, [selectedId, carregarAssociacoes]);

  useEffect(() => {
    if (!selectedDept) return;
    const el = document.querySelector('[role="option"][aria-selected="true"]');
    if (el instanceof HTMLElement) el.scrollIntoView({ block: "nearest" });
  }, [selectedDept]);

  const handleOpenModal = (dept?: Departamento) => {
    if (dept) {
      setEditingId(dept.id);
      setFormNome(dept.nome);
    } else {
      setEditingId(null);
      setFormNome("");
    }
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    if (!formNome.trim()) {
      toast.error("O nome do departamento é obrigatório.");
      return;
    }
    setIsSaving(true);
    try {
      if (editingId) {
        const updated = await departamentosService.update(editingId, { nome: formNome, ativo: true });
        setDepartamentos(prev => prev.map(d => d.id === editingId ? updated : d).sort((a, b) => a.nome.localeCompare(b.nome)));
        if (selectedDept?.id === editingId) setSelectedDept(updated);
        toast.success("Departamento atualizado com sucesso!");
      } else {
        const novo = await departamentosService.create({ nome: formNome, ativo: true });
        setDepartamentos(prev => [...prev, novo].sort((a, b) => a.nome.localeCompare(b.nome)));
        selectDept(novo);
        toast.success("Novo departamento criado!");
      }
      setIsModalOpen(false);
    } catch (err) {
      toast.error("Erro ao salvar departamento.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!(await confirmDialog("Excluir este departamento? Todas as associações serão removidas permanentemente.", { variant: "danger" }))) return;
    try {
      await departamentosService.delete(id);
      const idx = departamentos.findIndex((d) => d.id === id);
      const remaining = departamentos.filter((d) => d.id !== id);
      setDepartamentos(remaining);
      if (selectedDept?.id === id) {
        const neighbor = remaining[Math.min(Math.max(idx, 0), remaining.length - 1)];
        if (neighbor) selectDept(neighbor);
        else setSelectedDept(null);
      }
      toast.success("Departamento excluído com sucesso.");
    } catch (err) {
      toast.error("Erro ao excluir o departamento.");
    }
  };

  const openCopyModal = () => {
    setCopyDir("trazer");
    setCopyOtherId("");
    setCopyObras(true);
    setCopyPlanos(true);
    setIsCopyOpen(true);
  };

  const handleCopyAutorizacoes = async () => {
    if (!selectedDept) return;
    if (copyOtherId === "") {
      toast.error("Selecione o outro departamento.");
      return;
    }
    if (!copyObras && !copyPlanos) {
      toast.error("Marque obras, planos ou os dois.");
      return;
    }
    const other = departamentos.find((d) => d.id === copyOtherId);
    const origemId = copyDir === "trazer" ? Number(copyOtherId) : selectedDept.id;
    const destId = copyDir === "trazer" ? selectedDept.id : Number(copyOtherId);
    const origemNome = copyDir === "trazer" ? (other?.nome || "origem") : selectedDept.nome;
    const destNome = copyDir === "trazer" ? selectedDept.nome : (other?.nome || "destino");
    const ok = await confirmDialog(
      `As autorizações de ${destNome} serão substituídas pelas de ${origemNome}. O que já estava liberado no destino some se não existir na origem.`,
      { title: "Copiar autorizações", confirmLabel: "Copiar", variant: "danger" },
    );
    if (!ok) return;
    setIsCopying(true);
    try {
      const res = await departamentosService.copiarAutorizacoes(destId, {
        origem_id: origemId,
        copiar_obras: copyObras,
        copiar_planos: copyPlanos,
      });
      setIsCopyOpen(false);
      const partes = [
        copyObras ? `${res.obras} obra(s)` : null,
        copyPlanos ? `${res.planos} plano(s)` : null,
      ].filter(Boolean);
      toast.success(`Copiado para ${res.destino}: ${partes.join(" e ")}.`);
      if (destId === selectedDept.id) {
        await carregarAssociacoes(selectedDept.id);
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erro ao copiar autorizações.");
    } finally {
      setIsCopying(false);
    }
  };

  const handleToggleCC = async (cc: DeptCostCenter) => {
    if (!selectedDept) return;
    try {
      await departamentosService.setCostCenter(selectedDept.id, cc.id, !cc.permitido);
      setCostCenters(prev => prev.map(c => c.id === cc.id ? { ...c, permitido: !c.permitido } : c));
    } catch (err) {
      toast.error("Erro ao atualizar associação do centro de custo.");
    }
  };

  const handleTogglePlano = async (plano: DeptPlano) => {
    if (!selectedDept) return;
    try {
      await departamentosService.setPlano(selectedDept.id, plano.id, !plano.permitido);
      setPlanos(prev => prev.map(p => p.id === plano.id ? { ...p, permitido: !p.permitido } : p));
    } catch (err) {
      toast.error("Erro ao atualizar associação do plano financeiro.");
    }
  };

  const handleToggleAllCC = async (value: boolean) => {
    if (!selectedDept) return;
    const ids = filteredCCs.map((cc) => cc.id);
    try {
      await departamentosService.setCostCentersBulk(selectedDept.id, ids, value);
      setCostCenters((prev) =>
        prev.map((c) => (ids.includes(c.id) ? { ...c, permitido: value } : c)),
      );
      toast.success(value ? "Centros de custo visíveis liberados!" : "Centros de custo visíveis removidos!");
    } catch {
      toast.error("Erro ao atualizar centros de custo em lote.");
    }
  };

  const handleToggleAllPlanos = async (value: boolean) => {
    if (!selectedDept) return;
    const ids = filteredAnaliticas.map((p) => p.id);
    try {
      await departamentosService.setPlanosBulk(selectedDept.id, ids, value);
      setPlanos((prev) =>
        prev.map((p) => (ids.includes(p.id) ? { ...p, permitido: value } : p)),
      );
      toast.success(value ? "Planos analíticos liberados!" : "Planos analíticos removidos!");
    } catch {
      toast.error("Erro ao atualizar planos em lote.");
    }
  };

  const handleToggleTotalizadora = async (dbId: string, value: boolean) => {
    if (!selectedDept) return;
    const descendants = getDescendantAnalytics(dbId, planos);
    if (descendants.length === 0) return;
    const ids = descendants.map((p) => p.id);
    try {
      await departamentosService.setPlanosBulk(selectedDept.id, ids, value);
      setPlanos((prev) =>
        prev.map((p) => (ids.includes(p.id) ? { ...p, permitido: value } : p)),
      );
    } catch {
      toast.error("Erro ao atualizar planos da totalizadora.");
    }
  };

  const toggleCcSort = (key: CCSortKey) => {
    setCcSort((prev) =>
      prev.key === key ? { key, dir: prev.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" },
    );
  };

  const renderCcSortIcon = (key: CCSortKey) => {
    if (ccSort.key !== key) {
      return <ArrowUpDown size={12} className="text-slate-400 opacity-0 group-hover:opacity-100" />;
    }
    return ccSort.dir === "asc"
      ? <ArrowUp size={12} className="text-ml-green" />
      : <ArrowDown size={12} className="text-ml-green" />;
  };

  const sortedCostCenters = useMemo(() => {
    const dir = ccSort.dir === "asc" ? 1 : -1;
    return [...costCenters].sort((a, b) => {
      let cmp = 0;
      if (ccSort.key === "id") {
        cmp = compareSiengeId(a.id_sienge, b.id_sienge);
      } else if (ccSort.key === "nome") {
        cmp = (a.nome || "").localeCompare(b.nome || "", "pt-BR", { sensitivity: "base" });
      } else {
        cmp = (a.status || "").localeCompare(b.status || "", "pt-BR", { sensitivity: "base" });
      }
      return cmp * dir;
    });
  }, [costCenters, ccSort]);

  const departamentosFiltrados = useMemo(() => {
    const t = buscaDept.trim().toLowerCase();
    const list = t
      ? departamentos.filter((d) => d.nome.toLowerCase().includes(t))
      : departamentos;
    const dir = deptSortDir === "asc" ? 1 : -1;
    return [...list].sort((a, b) => dir * a.nome.localeCompare(b.nome, "pt-BR", { sensitivity: "base" }));
  }, [departamentos, buscaDept, deptSortDir]);

  useEffect(() => {
    if (isLoading || selectedDept || departamentos.length === 0) return;
    let stored = "";
    try {
      stored = sessionStorage.getItem("apoio_dept_selected_id") || "";
    } catch {
      stored = "";
    }
    const found = stored ? departamentos.find((d) => String(d.id) === stored) : undefined;
    const pick = found ?? departamentos[0];
    setSelectedDept(pick);
    persistDeptId(pick.id);
  }, [isLoading, departamentos, selectedDept]);

  const filteredCCs = useMemo(() => {
    return sortedCostCenters.filter((cc) => {
      const term = searchCC.toLowerCase();
      const matchSearch =
        !term ||
        cc.nome?.toLowerCase().includes(term) ||
        cc.id_sienge?.toLowerCase().includes(term);
      const isAtivo = (cc.status || "").toLowerCase() === "ativo";
      const matchStatus =
        ccStatusFilter === "all" ||
        (ccStatusFilter === "ativo" && isAtivo) ||
        (ccStatusFilter === "inativo" && !isAtivo);
      const matchLiberado = !somenteLiberados || cc.permitido;
      return matchSearch && matchStatus && matchLiberado;
    });
  }, [sortedCostCenters, searchCC, ccStatusFilter, somenteLiberados]);

  const analiticas = useMemo(() => getAnaliticas(planos), [planos]);
  const totalizadoras = useMemo(() => getTotalizadoras(planos), [planos]);

  const filteredAnaliticas = useMemo(() => {
    const term = searchPlano.toLowerCase();
    return analiticas.filter((p) => {
      const matchSearch =
        !term ||
        p.nome?.toLowerCase().includes(term) ||
        p.db_id?.includes(term) ||
        formatPlanId(p.db_id).toLowerCase().includes(term);
      const matchLiberado = !somenteLiberados || p.permitido;
      return matchSearch && matchLiberado;
    });
  }, [analiticas, searchPlano, somenteLiberados]);

  const visibleTotalizRoots = useMemo(() => {
    let roots = getRootTotalizadoras(totalizadoras);
    if (searchPlano.trim()) {
      roots = roots.filter((t) => matchesPlanoSearch(t, searchPlano, planos));
    }
    if (somenteLiberados) {
      roots = roots.filter((t) => totalizadoraTemLiberado(t, planos));
    }
    return roots;
  }, [totalizadoras, planos, searchPlano, somenteLiberados]);

  const toggleExpandTotaliz = (dbId: string) => {
    setExpandedTotaliz((prev) => ({ ...prev, [dbId]: !prev[dbId] }));
  };

  useEffect(() => {
    if (activeTab !== "planos") return;
    const deveExpandir = Boolean(searchPlano.trim()) || somenteLiberados;
    if (!deveExpandir) return;
    const expanded: Record<string, boolean> = {};
    totalizadoras.forEach((t) => {
      const matchBusca = !searchPlano.trim() || matchesPlanoSearch(t, searchPlano, planos);
      const matchLiberado = !somenteLiberados || totalizadoraTemLiberado(t, planos);
      if (matchBusca && matchLiberado) expanded[t.db_id] = true;
    });
    setExpandedTotaliz((prev) => ({ ...prev, ...expanded }));
  }, [searchPlano, somenteLiberados, activeTab, totalizadoras, planos]);

  const renderPlanoCheck = (state: CheckState, onToggle: () => void) => {
    if (state === "all") {
      return <CheckSquare size={18} className="text-ml-green shrink-0" onClick={(e) => { e.stopPropagation(); onToggle(); }} />;
    }
    if (state === "partial") {
      return (
        <span
          className="inline-flex h-[18px] w-[18px] items-center justify-center rounded border-2 border-ml-green bg-emerald-50 shrink-0"
          onClick={(e) => { e.stopPropagation(); onToggle(); }}
        >
          <Minus size={12} className="text-ml-green" />
        </span>
      );
    }
    return <Square size={18} className="text-slate-300 shrink-0" onClick={(e) => { e.stopPropagation(); onToggle(); }} />;
  };

  const renderTotalizadoraNode = (totaliz: DeptPlano, depth: number): ReactNode => {
    const descendants = getDescendantAnalytics(totaliz.db_id, planos);
    const checkState = getGroupCheckState(descendants);
    const childTotaliz = getDirectChildTotalizadoras(totaliz.db_id, totalizadoras).filter(
      (t) => !somenteLiberados || totalizadoraTemLiberado(t, planos),
    );
    const directAnalytics = getDirectAnalytics(totaliz.db_id, planos).filter((a) =>
      filteredAnaliticas.some((f) => f.id === a.id),
    );
    const isExpanded = expandedTotaliz[totaliz.db_id] ?? depth === 0;
    const hasChildren = childTotaliz.length > 0 || directAnalytics.length > 0;

    if (searchPlano.trim() && !matchesPlanoSearch(totaliz, searchPlano, planos)) return null;
    if (somenteLiberados && !totalizadoraTemLiberado(totaliz, planos)) return null;

    return (
      <div key={totaliz.db_id} className="border-b border-slate-100 last:border-b-0">
        <div
          className={`flex items-center gap-2 px-4 py-2.5 hover:bg-slate-50 transition-colors ${depth === 0 ? "bg-slate-50/80" : "bg-white"}`}
          style={{ paddingLeft: `${16 + depth * 20}px` }}
        >
          {hasChildren ? (
            <button
              type="button"
              onClick={() => toggleExpandTotaliz(totaliz.db_id)}
              className="p-0.5 rounded text-slate-500 hover:bg-slate-200 shrink-0"
            >
              {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </button>
          ) : (
            <span className="w-5 shrink-0" />
          )}
          {renderPlanoCheck(checkState, () => handleToggleTotalizadora(totaliz.db_id, checkState !== "all"))}
          <FolderTree size={15} className="text-slate-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-slate-800 truncate">{totaliz.nome}</p>
            <p className="text-[10px] text-slate-400 font-mono">{formatPlanId(totaliz.db_id)} · Totalizadora · {descendants.filter((d) => d.permitido).length}/{descendants.length} planos</p>
          </div>
        </div>
        {isExpanded && (
          <>
            {[
              ...childTotaliz.map((node) => ({ kind: "T" as const, node })),
              ...directAnalytics.map((node) => ({ kind: "R" as const, node })),
            ]
              .sort((a, b) => comparePlanDbId(a.node.db_id, b.node.db_id))
              .map((row) =>
                row.kind === "T" ? (
                  renderTotalizadoraNode(row.node, depth + 1)
                ) : (
                  <div
                    key={row.node.id}
                    className={`flex items-center gap-2 py-2 pr-4 hover:bg-slate-50 cursor-pointer border-t border-slate-50 ${
                      row.node.permitido ? "bg-emerald-50/40" : "bg-white"
                    }`}
                    style={{ paddingLeft: `${36 + depth * 20}px` }}
                    onClick={() => handleTogglePlano(row.node)}
                  >
                    {row.node.permitido
                      ? <CheckSquare size={16} className="text-ml-green shrink-0" />
                      : <Square size={16} className="text-slate-300 shrink-0" />}
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs font-medium truncate ${row.node.permitido ? "text-slate-800" : "text-slate-600"}`}>{row.node.nome}</p>
                      <p className="text-[10px] text-slate-400 font-mono">{formatPlanId(row.node.db_id)}</p>
                    </div>
                  </div>
                ),
              )}
          </>
        )}
      </div>
    );
  };

  const selectByOffset = (delta: number) => {
    const list = departamentosFiltrados;
    if (!list.length) return;
    const idx = list.findIndex((d) => d.id === selectedDept?.id);
    const nextIdx = Math.min(list.length - 1, Math.max(0, (idx < 0 ? 0 : idx) + delta));
    selectDept(list[nextIdx]);
  };

  const obrasOk = costCenters.filter((c) => c.permitido).length;
  const planosOk = analiticas.filter((p) => p.permitido).length;

  return (
    <div className="w-full flex-1 min-h-0 flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shrink-0">
            <Building2 size={20} />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-slate-800">Departamentos</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              {pageView === "depara"
                ? "Casamento do nome Sienge com o departamento do Apoio."
                : pageView === "diretorias"
                  ? "Agrupe departamentos para visão gerencial por diretoria."
                  : "Quem vê quais obras e planos financeiros no orçamento."}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <div className="flex rounded-lg border border-slate-200 p-0.5 bg-slate-50">
            <button
              type="button"
              onClick={() => setPageView("matriz")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold ${
                pageView === "matriz" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Matriz
            </button>
            <button
              type="button"
              onClick={() => setPageView("diretorias")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold inline-flex items-center gap-1.5 ${
                pageView === "diretorias" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <FolderTree size={12} />
              Diretorias
            </button>
            <button
              type="button"
              onClick={() => setPageView("depara")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold inline-flex items-center gap-1.5 ${
                pageView === "depara" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <Link2 size={12} />
              De-para Sienge
            </button>
          </div>
          {pageView === "matriz" ? (
            <Button onClick={() => handleOpenModal()} className="gap-2 shadow-sm">
              <Plus size={16} /> Novo departamento
            </Button>
          ) : null}
        </div>
      </div>

      {pageView === "depara" ? (
        <DeparaSiengePanel departamentos={departamentos} />
      ) : pageView === "diretorias" ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex-1 min-h-0 overflow-auto">
          <DiretoriasPanel departamentos={departamentos} onChanged={() => void carregarDepartamentos()} />
        </div>
      ) : (
      <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0">
        {/* LISTA */}
        <div className="w-full lg:w-80 shrink-0 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden min-h-[280px]">
          <div className="px-3 py-3 border-b border-slate-100 space-y-2 shrink-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 flex items-center justify-between px-1">
              Estrutura
              <span className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setDeptSortDir((d) => (d === "asc" ? "desc" : "asc"))}
                  className="p-1 rounded-md text-slate-500 hover:text-ml-green hover:bg-emerald-50"
                  title={deptSortDir === "asc" ? "Ordem A–Z. Clique para Z–A." : "Ordem Z–A. Clique para A–Z."}
                  aria-label={deptSortDir === "asc" ? "Classificar Z–A" : "Classificar A–Z"}
                >
                  {deptSortDir === "asc" ? <ArrowDownAZ size={14} /> : <ArrowUpZA size={14} />}
                </button>
                <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded-full tabular-nums">{departamentos.length}</span>
              </span>
            </p>
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={buscaDept}
                onChange={(e) => setBuscaDept(e.target.value)}
                placeholder="Filtrar departamento…"
                className="w-full h-9 pl-8 pr-8 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-ml-green/20 focus:border-ml-green"
              />
              {buscaDept ? (
                <button type="button" onClick={() => setBuscaDept("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5">
                  <X size={14} />
                </button>
              ) : null}
            </div>
          </div>

          <div
            className="flex-1 overflow-y-auto outline-none"
            role="listbox"
            aria-label="Departamentos"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") { e.preventDefault(); selectByOffset(1); }
              if (e.key === "ArrowUp") { e.preventDefault(); selectByOffset(-1); }
            }}
          >
            {isLoading ? (
              <AppLoadingState />
            ) : departamentosFiltrados.map((dept) => {
              const active = selectedDept?.id === dept.id;
              return (
                <div
                  key={dept.id}
                  role="option"
                  aria-selected={active}
                  tabIndex={active ? 0 : -1}
                  className={`group flex items-center justify-between gap-1 px-3 py-2.5 cursor-pointer border-l-[3px] transition-colors ${
                    active
                      ? "bg-emerald-50/80 border-ml-green"
                      : "border-transparent hover:bg-slate-50"
                  }`}
                  onClick={() => selectDept(dept)}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dept.ativo ? "bg-ml-green" : "bg-slate-300"}`} />
                    <span className={`text-sm truncate ${active ? "font-semibold text-slate-900" : "font-medium text-slate-700"}`}>
                      {dept.nome}
                    </span>
                  </div>
                  <div className={`flex items-center shrink-0 ${active ? "opacity-100" : "opacity-0 group-hover:opacity-100 hover:opacity-100"}`}>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleOpenModal(dept); }}
                      className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-white rounded-md"
                      title="Renomear"
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleDelete(dept.id); }}
                      className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md"
                      title="Excluir"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
            {!isLoading && departamentosFiltrados.length === 0 && (
              <div className="p-8 flex flex-col items-center text-center text-slate-500 gap-2">
                <Building2 size={28} className="text-slate-300" />
                <p className="text-sm">
                  {buscaDept.trim() ? "Nenhum departamento com esse nome." : "Nenhum departamento cadastrado."}
                </p>
                {!buscaDept.trim() ? (
                  <button type="button" onClick={() => handleOpenModal()} className="text-sm font-semibold text-ml-green hover:underline">
                    Criar o primeiro
                  </button>
                ) : null}
              </div>
            )}
          </div>
        </div>

        {/* PAINEL DE ASSOCIAÇÕES */}
        <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden min-h-[320px] relative">
          {isLoading && !selectedDept ? (
            <AppLoadingState />
          ) : !selectedDept ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center px-6 gap-3">
              <div className="w-12 h-12 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
                <Building2 size={22} />
              </div>
              <p className="text-sm font-semibold text-slate-700">Nenhum departamento ainda</p>
              <p className="text-sm text-slate-500 max-w-sm">
                Crie o primeiro para definir quem vê quais obras e planos no orçamento.
              </p>
              <Button onClick={() => handleOpenModal()} className="gap-2 mt-1">
                <Plus size={16} /> Novo departamento
              </Button>
            </div>
          ) : (
            <>
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-start justify-between gap-3 shrink-0">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-base font-bold text-slate-800 truncate">{selectedDept.nome}</h2>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${
                      selectedDept.ativo ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-500"
                    }`}>
                      {selectedDept.ativo ? "Ativo" : "Inativo"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 tabular-nums">
                    {activeTab === "cost-centers"
                      ? (isLoadingAssoc ? "Obras que este departamento pode ver" : `${obrasOk} de ${costCenters.length} obras liberadas`)
                      : (isLoadingAssoc ? "Planos que este departamento pode ver" : `${planosOk} de ${analiticas.length} planos analíticos liberados`)}
                  </p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={openCopyModal}
                    className="inline-flex items-center gap-1.5 px-2.5 h-9 text-xs font-semibold text-slate-600 hover:text-ml-green rounded-lg border border-slate-200 hover:border-ml-green/40 hover:bg-emerald-50/50"
                    title="Copiar autorizações de outro departamento"
                  >
                    <Copy size={14} /> Copiar autorizações
                  </button>
                  <button
                    type="button"
                    onClick={() => handleOpenModal(selectedDept)}
                    className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-50 rounded-lg border border-transparent hover:border-slate-200"
                    title="Renomear"
                  >
                    <Edit2 size={15} />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(selectedDept.id)}
                    className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                    title="Excluir"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>

              <div className="flex px-5 border-b border-slate-200 bg-white shrink-0">
                <button
                  type="button"
                  onClick={() => setActiveTab("cost-centers")}
                  className={`flex items-center gap-1.5 px-3 py-2.5 text-sm font-semibold whitespace-nowrap border-b-2 -mb-px transition-colors ${
                    activeTab === "cost-centers"
                      ? "text-ml-green border-ml-green"
                      : "text-slate-500 border-transparent hover:text-slate-700"
                  }`}
                >
                  <LayoutGrid size={15} />
                  Obras
                  <span className={`ml-0.5 px-1.5 py-0.5 rounded-full text-[10px] tabular-nums ${
                    activeTab === "cost-centers" ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-500"
                  }`}>
                    {obrasOk}/{costCenters.length}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("planos")}
                  className={`flex items-center gap-1.5 px-3 py-2.5 text-sm font-semibold whitespace-nowrap border-b-2 -mb-px transition-colors ${
                    activeTab === "planos"
                      ? "text-ml-green border-ml-green"
                      : "text-slate-500 border-transparent hover:text-slate-700"
                  }`}
                >
                  <FileText size={15} />
                  Planos
                  <span className={`ml-0.5 px-1.5 py-0.5 rounded-full text-[10px] tabular-nums ${
                    activeTab === "planos" ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-500"
                  }`}>
                    {planosOk}/{analiticas.length}
                  </span>
                </button>
              </div>

              {/* CONTEÚDO DA ABA */}
              <div className="flex-1 overflow-hidden flex flex-col">
                {activeTab === "cost-centers" && (
                  <>
                    <div className="px-4 py-2.5 border-b border-slate-100 flex flex-wrap items-center gap-2 bg-white shrink-0">
                      <div className="relative flex-1 min-w-[180px]">
                        <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                          className="w-full pl-8 pr-8 h-9 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-ml-green/20 focus:border-ml-green"
                          placeholder="Buscar obra ou ID…"
                          value={searchCC}
                          onChange={e => setSearchCC(e.target.value)}
                        />
                        {searchCC && <button type="button" onClick={() => setSearchCC("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1"><X size={14} /></button>}
                      </div>
                      <div className="flex rounded-lg overflow-hidden border border-slate-200">
                        {(["all", "ativo", "inativo"] as const).map((f) => (
                          <button
                            key={f}
                            type="button"
                            onClick={() => setCcStatusFilter(f)}
                            className={`px-2.5 h-9 text-xs font-semibold transition-colors ${
                              ccStatusFilter === f
                                ? "bg-ml-green text-white"
                                : "bg-white text-slate-600 hover:bg-slate-50"
                            }`}
                          >
                            {f === "all" ? "Todas" : f === "ativo" ? "Ativas" : "Inativas"}
                          </button>
                        ))}
                      </div>
                      <button
                        type="button"
                        onClick={() => setSomenteLiberados((v) => !v)}
                        className={`inline-flex items-center gap-1.5 px-2.5 h-9 rounded-lg border text-xs font-semibold transition-colors ${
                          somenteLiberados
                            ? "bg-emerald-50 text-ml-green border-ml-green/40"
                            : "bg-white text-slate-600 border-slate-200 hover:border-ml-green hover:text-ml-green"
                        }`}
                        title={somenteLiberados ? "Mostrar todas as obras" : "Mostrar só as obras liberadas"}
                      >
                        <Eye size={14} />
                        Somente liberados
                      </button>
                      <div className="flex items-center gap-1.5 ml-auto">
                        <button
                          type="button"
                          onClick={() => handleToggleAllCC(true)}
                          className="text-xs font-semibold text-slate-600 hover:text-ml-green px-2.5 h-9 rounded-lg border border-slate-200 hover:border-ml-green/40 hover:bg-emerald-50/50"
                        >
                          Liberar visíveis
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleAllCC(false)}
                          className="text-xs font-semibold text-slate-600 hover:text-red-700 px-2.5 h-9 rounded-lg border border-slate-200 hover:border-red-200 hover:bg-red-50"
                        >
                          Remover visíveis
                        </button>
                      </div>
                    </div>
                    <div className="flex-1 overflow-y-auto">
                      {isLoadingAssoc ? (
                        <AppLoadingState />
                      ) : filteredCCs.length === 0 ? (
                        <div className="p-12 flex flex-col items-center text-center text-slate-400 gap-3">
                          <LayoutGrid size={32} className="text-slate-300" />
                          <span className="text-sm">
                            {searchCC.trim() || ccStatusFilter !== "all" || somenteLiberados
                              ? somenteLiberados && !searchCC.trim() && ccStatusFilter === "all"
                                ? "Nenhuma obra liberada neste departamento."
                                : "Nenhuma obra com esse filtro."
                              : "Nenhum centro de custo encontrado."}
                          </span>
                        </div>
                      ) : (
                        <table className="w-full text-left text-xs border-collapse tabular-nums">
                          <thead className="sticky top-0 z-10 bg-slate-50 text-[10px] uppercase tracking-wider text-slate-500">
                            <tr className="border-b border-slate-200">
                              <th className="w-10 px-3 py-2" />
                              {([
                                { key: "id" as const, label: "ID", className: "w-[90px]" },
                                { key: "nome" as const, label: "Obra", className: "" },
                                { key: "status" as const, label: "Status", className: "w-[88px]" },
                              ]).map((col) => (
                                <th
                                  key={col.key}
                                  className={`px-3 py-2 font-semibold ${col.className}`}
                                  aria-sort={ccSort.key === col.key ? (ccSort.dir === "asc" ? "ascending" : "descending") : "none"}
                                >
                                  <button
                                    type="button"
                                    onClick={() => toggleCcSort(col.key)}
                                    className="flex items-center gap-1 uppercase tracking-wider hover:text-slate-700"
                                    title={
                                      ccSort.key === col.key
                                        ? (ccSort.dir === "asc" ? "Ordem A–Z. Clique para Z–A." : "Ordem Z–A. Clique para A–Z.")
                                        : `Classificar por ${col.label}`
                                    }
                                  >
                                    {col.label} {renderCcSortIcon(col.key)}
                                  </button>
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {filteredCCs.map((cc) => (
                              <tr
                                key={cc.id}
                                className={`border-b border-slate-100 cursor-pointer ${
                                  cc.permitido ? "bg-emerald-50/50 hover:bg-emerald-50" : "bg-white hover:bg-slate-50"
                                }`}
                                onClick={() => handleToggleCC(cc)}
                              >
                                <td className="px-3 py-2">
                                  {cc.permitido
                                    ? <CheckSquare size={16} className="text-ml-green" />
                                    : <Square size={16} className="text-slate-300" />}
                                </td>
                                <td className="px-3 py-2 font-mono text-slate-600">
                                  {cc.id_sienge}
                                </td>
                                <td className="px-3 py-2">
                                  <p className={`font-medium truncate max-w-[420px] ${cc.permitido ? "text-slate-800" : "text-slate-600"}`} title={cc.nome}>
                                    {cc.nome}
                                  </p>
                                </td>
                                <td className="px-3 py-2">
                                  <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                                    (cc.status || "").toLowerCase() === "ativo" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"
                                  }`}>
                                    {cc.status || "—"}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </>
                )}

                {activeTab === "planos" && (
                  <>
                    <div className="px-4 py-2.5 border-b border-slate-100 flex flex-wrap items-center gap-2 bg-white shrink-0">
                      <div className="relative flex-1 min-w-[180px]">
                        <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                          className="w-full pl-8 pr-8 h-9 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-ml-green/20 focus:border-ml-green"
                          placeholder="Buscar plano ou totalizadora…"
                          value={searchPlano}
                          onChange={e => setSearchPlano(e.target.value)}
                        />
                        {searchPlano && <button type="button" onClick={() => setSearchPlano("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1"><X size={14} /></button>}
                      </div>
                      <button
                        type="button"
                        onClick={() => setSomenteLiberados((v) => !v)}
                        className={`inline-flex items-center gap-1.5 px-2.5 h-9 rounded-lg border text-xs font-semibold transition-colors ${
                          somenteLiberados
                            ? "bg-emerald-50 text-ml-green border-ml-green/40"
                            : "bg-white text-slate-600 border-slate-200 hover:border-ml-green hover:text-ml-green"
                        }`}
                        title={somenteLiberados ? "Mostrar todos os planos" : "Mostrar só os planos analíticos liberados"}
                      >
                        <Eye size={14} />
                        Somente liberados
                      </button>
                      <p className="text-[11px] text-slate-500 hidden xl:block">
                        Marque a totalizadora para liberar todos os planos abaixo.
                      </p>
                      <div className="flex items-center gap-1.5 ml-auto">
                        <button
                          type="button"
                          onClick={() => handleToggleAllPlanos(true)}
                          className="text-xs font-semibold text-slate-600 hover:text-ml-green px-2.5 h-9 rounded-lg border border-slate-200 hover:border-ml-green/40 hover:bg-emerald-50/50"
                        >
                          Liberar analíticos
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleAllPlanos(false)}
                          className="text-xs font-semibold text-slate-600 hover:text-red-700 px-2.5 h-9 rounded-lg border border-slate-200 hover:border-red-200 hover:bg-red-50"
                        >
                          Remover todos
                        </button>
                      </div>
                    </div>
                    <div className="flex-1 overflow-y-auto bg-white">
                      {isLoadingAssoc ? (
                        <AppLoadingState />
                      ) : visibleTotalizRoots.length === 0 ? (
                        <div className="p-12 flex flex-col items-center text-center text-slate-400 gap-3">
                          <FileText size={32} className="text-slate-300" />
                          <span className="text-sm">
                            {searchPlano.trim() || somenteLiberados
                              ? somenteLiberados && !searchPlano.trim()
                                ? "Nenhum plano analítico liberado neste departamento."
                                : "Nenhum plano com esse filtro."
                              : "Nenhum plano financeiro encontrado."}
                          </span>
                        </div>
                      ) : (
                        <div className="divide-y divide-slate-100">
                          {visibleTotalizRoots.map((t) => renderTotalizadoraNode(t, 0))}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </div>
      )}

      {/* MODAL CRIAR/EDITAR */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                {editingId ? "Editar Departamento" : "Novo Departamento"}
              </h2>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors">
                <X size={18} />
              </button>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-2">Nome do Departamento *</label>
                  <input
                    value={formNome}
                    onChange={e => setFormNome(e.target.value)}
                    placeholder="Ex: Controladoria, Novos Negócios..."
                    onKeyDown={e => e.key === "Enter" && handleSave()}
                    autoFocus
                    className="w-full h-11 px-4 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-ml-green/20 focus:border-ml-green"
                  />
                  <p className="text-xs text-slate-500 mt-2">
                    Este nome será utilizado para vincular usuários na tela de Segurança.
                  </p>
                </div>
              </div>
            </div>
            <div className="p-5 border-t border-slate-100 flex justify-end gap-3 bg-slate-50/50">
              <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSave} disabled={isSaving} isLoading={isSaving}>
                {editingId ? "Salvar" : "Criar departamento"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {isCopyOpen && selectedDept ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <Copy size={18} className="text-ml-green" /> Copiar autorizações
              </h2>
              <button type="button" onClick={() => setIsCopyOpen(false)} className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100">
                <X size={18} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-slate-600">
                Departamento atual: <span className="font-semibold text-slate-800">{selectedDept.nome}</span>
              </p>
              <div className="flex rounded-lg overflow-hidden border border-slate-200">
                <button
                  type="button"
                  onClick={() => setCopyDir("trazer")}
                  className={`flex-1 px-3 py-2 text-xs font-semibold ${copyDir === "trazer" ? "bg-ml-green text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
                >
                  Trazer para este
                </button>
                <button
                  type="button"
                  onClick={() => setCopyDir("enviar")}
                  className={`flex-1 px-3 py-2 text-xs font-semibold ${copyDir === "enviar" ? "bg-ml-green text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
                >
                  Enviar para outro
                </button>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  {copyDir === "trazer" ? "Copiar de" : "Enviar para"}
                </label>
                <SearchableSelect
                  placeholder="Selecione o departamento…"
                  value={copyOtherId}
                  onChange={(val) => setCopyOtherId(val === "" ? "" : Number(val))}
                  options={departamentos
                    .filter((d) => d.id !== selectedDept.id)
                    .map((d) => ({ id: d.id, label: d.nome }))}
                />
              </div>
              <div className="space-y-2">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">O que copiar</p>
                <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                  <input type="checkbox" className="rounded border-slate-300 text-ml-green focus:ring-ml-green" checked={copyObras} onChange={(e) => setCopyObras(e.target.checked)} />
                  Obras (centros de custo)
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                  <input type="checkbox" className="rounded border-slate-300 text-ml-green focus:ring-ml-green" checked={copyPlanos} onChange={(e) => setCopyPlanos(e.target.checked)} />
                  Planos financeiros
                </label>
              </div>
              <p className="text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                Substitui as autorizações do destino. Não altera o cadastro do departamento.
              </p>
            </div>
            <div className="p-5 border-t border-slate-100 flex justify-end gap-3 bg-slate-50/50">
              <Button variant="secondary" onClick={() => setIsCopyOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleCopyAutorizacoes} disabled={isCopying} isLoading={isCopying} className="gap-2">
                <Copy size={14} /> Copiar
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
