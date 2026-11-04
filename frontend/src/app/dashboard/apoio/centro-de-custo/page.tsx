"use client";

import { useState, useEffect } from "react";
import { RefreshCw, Plus, Settings2, X, AlertCircle, Trash2, FolderTree, ArrowUpDown, ArrowUp, ArrowDown, Pencil, Building2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { apoioService } from "@/services/apoio";
import { api } from "@/lib/api";
import { CollapsibleFilterPanel } from "@/components/shared/CollapsibleFilterPanel";
import { FilterSearchField } from "@/components/shared/FilterSearchField";
import toast from "react-hot-toast";
import { confirmDialog } from "@/components/ui/confirmDialog";
import {
  centroEhSateliteDeProduto,
  mostraFlagAcompanharEmpreendimento,
  tipoEfetivoCentro,
} from "@/lib/acompanharEmpreendimento";
import { rotuloTipoSienge } from "@/lib/tipoCentroCusto";
import {
  TEXTO_INICIO_CURVA,
  TEXTO_TERRENO_MANUAL,
  formatarMesPt,
  linhasAlertaTerreno,
  mesSugeridoInicio,
  mostraInicioTerreno,
} from "@/lib/terrenoManualCadastro";

const FIELD_CLASS =
  "w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-ml-green/20 focus:border-ml-green text-slate-800 bg-white";

// ── Helpers de parse ─────────────────────────────────────────────────────────

function parseCentroNome(nome: string): { cidade: string; produto: string } {
 if (!nome) return { cidade:"—", produto:"—" };

 // Regra 7: qualquer registro com AUTOMÓVEL → FROTA
 if (nome.toUpperCase().includes("AUTOMÓVEL") || nome.toUpperCase().includes("AUTOMOVEL")) {
 return { cidade:"FROTA", produto:"FROTA" };
 }

 // Padrão:"CIDADE - PRODUTO [- SUFIXO]"
 const partes = nome.split(" -").map((p) => p.trim());

 if (partes.length >= 2) {
 const cidade = partes[0];
 const sufixos = ["INATIVO","ATIVO","ENCERRADO","SUSPENSO"];
 const ultimaParte = partes[partes.length - 1].toUpperCase();
 const temSufixo = sufixos.includes(ultimaParte);

 let produto: string;
 if (partes.length === 2 && !temSufixo) {
 produto = partes[1];
 } else if (partes.length === 2 && temSufixo) {
 produto = partes[1];
 } else {
 const meioParts = temSufixo ? partes.slice(1, -1) : partes.slice(1);
 produto = meioParts.join(" -");
 }
 return { cidade, produto };
 }

 return { cidade:"—", produto: nome };
}

function produtoOverride(custom: Record<string, unknown> | undefined) {
  const raw = custom?.__produto_override;
  return typeof raw === "string" ? raw.trim() : "";
}

function produtoExibido(nome: string, custom: Record<string, unknown> | undefined) {
  return produtoOverride(custom) || parseCentroNome(nome).produto;
}

// ── Componente ───────────────────────────────────────────────────────────────

export default function CentroDeCustoPage() {
 const [centros, setCentros] = useState<any[]>([]);
 const [colunas, setColunas] = useState<any[]>([]);
 const [isLoading, setIsLoading] = useState(true);
 const [isSyncing, setIsSyncing] = useState(false);

 // Estados dos Modais
 const [isManageColsOpen, setIsManageColsOpen] = useState(false);
 const [isEditModalOpen, setIsEditModalOpen] = useState(false);
 const [editingCC, setEditingCC] = useState<any>(null);
 const [editFormData, setEditFormData] = useState<any>({});
 const [editStatus, setEditStatus] = useState("Ativo");
  const [viabilities, setViabilities] = useState<any[]>([]);
  const [curves, setCurves] = useState<any[]>([]);
  const [editTrackInDashboard, setEditTrackInDashboard] = useState(false);
  const [editProjectPhase, setEditProjectPhase] = useState("Em Andamento");
  const [editManualLandCost, setEditManualLandCost] = useState<number>(0);
  const [editLandCurveId, setEditLandCurveId] = useState<number | "">("");
  const [editLandStartDate, setEditLandStartDate] = useState<string>("");
  const [editApportionmentRules, setEditApportionmentRules] = useState<any[]>([]);
  const [editPartnershipRuleId, setEditPartnershipRuleId] = useState<number | "">("");
  const [editProduto, setEditProduto] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [primeiroMesObra, setPrimeiroMesObra] = useState<{
    primeiro_mes_caixa: string | null;
    primeiro_mes_desembolso: string | null;
  } | null>(null);
  const [carregandoPrimeiroMes, setCarregandoPrimeiroMes] = useState(false);

 // Form do Gerenciador de Colunas
 const [newColName, setNewColName] = useState("");
 const [newColType, setNewColType] = useState("text");

  const [configs, setConfigs] = useState<any[]>([]);

 // ── Load ─────────────────────────────────────────────────────────────────────
  async function loadData() {
    setIsLoading(true);
    try {
      const [dataCentros, dataColunas, resViab, resCurves, resConfigs] = await Promise.all([
        apoioService.getCentrosCusto(),
        apoioService.getCustomColumns("centro_custo"),
        api.get("/viabilities/"),
        api.get("/curves/"),
        api.get("/partnership")
      ]);
      setCentros(dataCentros);
      setColunas(dataColunas);
      setViabilities(resViab.data);
      setCurves(resCurves.data);
      setConfigs(resConfigs.data);
    } catch (e) {
      console.error(e);
      toast.error("Erro ao carregar centros de custo.");
    } finally {
      setIsLoading(false);
    }
  }

 async function handleSync() {
 setIsSyncing(true);
 try {
 await apoioService.syncCentrosCusto();
 await loadData();
 toast.success("Sincronização concluída.");
 } catch (e) {
 console.error("Erro na sincronização", e);
 toast.error("Erro ao sincronizar centros de custo.");
 } finally {
 setIsSyncing(false);
 }
 }

 useEffect(() => { loadData(); }, []);

  useEffect(() => {
    if (!isEditModalOpen || !editingCC?.db_id) {
      setPrimeiroMesObra(null);
      return;
    }
    let cancelado = false;
    setCarregandoPrimeiroMes(true);
    apoioService.getPrimeiroMesCaixa(editingCC.db_id)
      .then((data) => {
        if (!cancelado) {
          setPrimeiroMesObra({
            primeiro_mes_caixa: data.primeiro_mes_caixa,
            primeiro_mes_desembolso: data.primeiro_mes_desembolso,
          });
        }
      })
      .catch(() => {
        if (!cancelado) setPrimeiroMesObra(null);
      })
      .finally(() => {
        if (!cancelado) setCarregandoPrimeiroMes(false);
      });
    return () => { cancelado = true; };
  }, [isEditModalOpen, editingCC?.db_id]);

 // ── Ações: Colunas Dinâmicas ─────────────────────────────────────────────────
 async function handleCreateColumn() {
 if (!newColName.trim()) return;
 try {
 await apoioService.createCustomColumn({
 field_name: newColName,
 field_type: newColType,
 entity_type:"centro_custo"
 });
 setNewColName("");
 setNewColType("text");
 await loadData();
 } catch (e) {
 alert("Erro ao criar coluna.");
 }
 }

 async function handleDeleteColumn(id: number) {
 if (!(await confirmDialog("Tem certeza que deseja excluir esta coluna? Os dados preenchidos serão mantidos no banco mas não serão mais exibidos.", { variant: "danger" }))) return;
 try {
 await apoioService.deleteCustomColumn(id);
 await loadData();
 } catch (e) {
 alert("Erro ao excluir coluna.");
 }
 }

 // ── Ações: Edição do Centro de Custo ──────────────────────────────────────────
  function openEditModal(cc: any) {
    setEditingCC(cc);
    // Preenche o form data com o json salvo ou vazio
    setEditFormData(cc.custom_data || {});
    setEditStatus(cc.status || "Ativo");
    setEditTrackInDashboard(cc.track_in_dashboard || false);
    setEditProjectPhase(cc.project_phase || "Em Andamento");
    setEditManualLandCost(Number(cc.manual_land_cost) || 0);
    setEditLandCurveId(cc.land_payment_curve_id || "");
    setEditLandStartDate(cc.land_payment_start_date || "");
    setEditApportionmentRules(cc.apportionment_rules || []);
    setEditPartnershipRuleId(cc.custom_data?.partnership_config_id || "");
    setEditProduto(produtoExibido(cc.nome, cc.custom_data));
    setIsEditModalOpen(true);
  }

  async function handleSaveEdit() {
    if (!editingCC) {
      alert("Nenhum centro de custo selecionado para edição.");
      return;
    }

    // Validação de colunas percentuais (Agrupamento pelos 3 primeiros dígitos do ID do Sienge)
    for (const col of colunas) {
      if (col.field_type === "percent") {
        let sumOther = 0;
        const prefixoAtual = String(editingCC.id).substring(0, 3);
        // Verifica se o centro de custo sendo editado é alvo de algum rateio (o que o torna independente)
        const isEditingExempt = centros.some(cc => {
          if (cc.id === editingCC.id) {
            return editApportionmentRules.some(r => String(r.project_prefix) === String(editingCC.id) || String(r.viability_id) === String(editingCC.id));
          } else {
            return (cc.apportionment_rules || []).some((r: any) => String(r.project_prefix) === String(editingCC.id) || String(r.viability_id) === String(editingCC.id));
          }
        });

        centros.forEach(cc => {
          if (cc.id !== editingCC.id) {
            const prefixoCC = String(cc.id).substring(0, 3);
            
            // Verifica se o 'cc' da iteração é alvo de rateio (o que o torna independente e o remove da soma do prefixo)
            const isCCExempt = centros.some(other => 
              (other.apportionment_rules || []).some((r: any) => String(r.project_prefix) === String(cc.id) || String(r.viability_id) === String(cc.id))
            );

            // Trava puramente por Prefixo e Empresa (Ignoramos o Nome para evitar quebra por digitação errada)
            // Se o centro de custo for independente (isExempt), ele NÃO entra na soma.
            if (prefixoCC === prefixoAtual && cc.id_empresa === editingCC.id_empresa) {
              if (!isEditingExempt && !isCCExempt) {
                const rawVal = String(cc.custom_data?.[col.field_name] || "0").replace(",", ".");
                sumOther += (Number(rawVal) || 0);
              }
            }
          }
        });
        
        const rawNewVal = String(editFormData[col.field_name] || "0").replace(",", ".");
        const newValue = Number(rawNewVal) || 0;
        const total = sumOther + newValue;
        
        if (total > 100) {
          alert(`A soma da coluna "${col.field_name}" para o empreendimento (Prefixo ${prefixoAtual}) não pode ultrapassar 100%.\n\nOutros Centros: ${sumOther}%\nValor Atual: ${newValue}%\nTotal: ${total.toFixed(2)}%`);
          return;
        }
      }
    }

    setIsSaving(true);
    try {
      const padrao = parseCentroNome(editingCC.nome).produto;
      const nomeProduto = editProduto.trim();
      const updatedCustomData = {
        ...editFormData,
        partnership_config_id: editPartnershipRuleId === "" ? null : Number(editPartnershipRuleId),
        // null limpa o override no JSON (update do backend faz merge, não delete)
        __produto_override: nomeProduto && nomeProduto !== padrao ? nomeProduto : null,
        __tipo_override: editFormData.__tipo_override || null,
      };

      const podeEnviarFlag = mostraFlagAcompanharEmpreendimento({
        tipo: tipoEfetivoCentro({
          tipo_sienge: editingCC.tipo_sienge,
          custom_data: { ...editingCC.custom_data, ...editFormData },
        }),
        nome: editingCC.nome,
        jaAcompanhado: Boolean(editingCC.track_in_dashboard),
      });
      await apoioService.updateCentroCusto(editingCC.db_id, { 
        custom_data: updatedCustomData,
        status: editStatus,
        ...(podeEnviarFlag ? { track_in_dashboard: editTrackInDashboard } : {}),
        project_phase: editProjectPhase,
        manual_land_cost: editManualLandCost,
        land_payment_curve_id: editLandCurveId === "" ? null : Number(editLandCurveId),
        land_payment_start_date: editLandStartDate || null,
        apportionment_rules: editApportionmentRules
      } as any);
      setIsEditModalOpen(false);
      setEditingCC(null);
      await loadData();
      toast.success("Centro de custo atualizado.");
    } catch (e) {
      toast.error("Erro ao atualizar centro de custo.");
    } finally {
      setIsSaving(false);
    }
  }

 // ── Ordenação e Filtros ──────────────────────────────────────────────────────
 const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>({ key:"id", direction:"asc" });
 const handleSort = (key: string) => {
 let direction:"asc" |"desc" ="asc";
 if (sortConfig?.key === key && sortConfig.direction ==="asc") direction ="desc";
 setSortConfig({ key, direction });
 };
 const renderSortIcon = (key: string) => {
 if (sortConfig?.key !== key) return <ArrowUpDown className="w-3 h-3 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />;
 if (sortConfig.direction ==="asc") return <ArrowUp className="w-3 h-3 text-ml-green" />;
 return <ArrowDown className="w-3 h-3 text-ml-green" />;
 };

 const [busca, setBusca] = useState("");
 const [filtroEmpresa, setFiltroEmpresa] = useState<string[]>([]);
 const [filtroCidade, setFiltroCidade] = useState<string[]>([]);
 const [filtroProduto, setFiltroProduto] = useState<string[]>([]);
 const [filtroId, setFiltroId] = useState<string[]>([]);
 const [filtroTipo, setFiltroTipo] = useState<string[]>([]);
 const [filtroStatus, setFiltroStatus] = useState<string[]>(["Ativo"]);

 const limparFiltros = () => {
 setBusca("");
 setFiltroEmpresa([]);
 setFiltroCidade([]);
 setFiltroProduto([]);
 setFiltroId([]);
 setFiltroTipo([]);
 setFiltroStatus(["Ativo"]);
 };

 const centrosEnriquecidos = centros.map((cc) => {
 const parsed = parseCentroNome(cc.nome);
 const produto = produtoExibido(cc.nome, cc.custom_data);
 return {
   ...cc,
   tipo_sienge: rotuloTipoSienge(cc.tipo_sienge),
   cidade: parsed.cidade,
   produto,
   produtoPadrao: parsed.produto,
   produtoEditado: Boolean(produtoOverride(cc.custom_data)),
 };
 });

 const empresasUnicas = Array.from(new Set(centros.map((c) => c.id_empresa).filter(Boolean))).sort((a, b) => a - b).map(String);
 const cidadesUnicas = Array.from(new Set(centrosEnriquecidos.map((c) => c.cidade).filter((c) => c !=="—"))).sort();
 const produtosUnicos = Array.from(new Set(centrosEnriquecidos.map((c) => c.produto).filter((c) => c !=="—"))).sort();
 const idsUnicos = Array.from(new Set(centros.map((c) => String(c.id)))).sort((a, b) => Number(a) - Number(b));
 const tiposUnicos = Array.from(new Set(centrosEnriquecidos.map((c) => c.tipo_sienge).filter(Boolean))).sort();
  const mesSugeridoTerreno = mesSugeridoInicio({
    primeiroMesCaixa: primeiroMesObra?.primeiro_mes_caixa,
    primeiroMesDesembolso: primeiroMesObra?.primeiro_mes_desembolso,
  });

 const filtered = centrosEnriquecidos.filter((cc) => {
 const q = busca.toLowerCase();
 if (q && !(
 String(cc.id).includes(q) ||
 cc.nome?.toLowerCase().includes(q) ||
 cc.cidade?.toLowerCase().includes(q) ||
 cc.produto?.toLowerCase().includes(q) ||
 cc.tipo_sienge?.toLowerCase().includes(q)
 )) return false;
 if (filtroEmpresa.length > 0 && !filtroEmpresa.includes(String(cc.id_empresa))) return false;
 if (filtroCidade.length > 0 && !filtroCidade.includes(cc.cidade)) return false;
 if (filtroProduto.length > 0 && !filtroProduto.includes(cc.produto)) return false;
 if (filtroId.length > 0 && !filtroId.includes(String(cc.id))) return false;
 if (filtroTipo.length > 0 && !filtroTipo.includes(cc.tipo_sienge)) return false;
 if (filtroStatus.length > 0 && !filtroStatus.includes(cc.status)) return false;
 return true;
 });

 const sorted = [...filtered].sort((a, b) => {
 if (!sortConfig) return 0;
 const { key, direction } = sortConfig;
 
 // Tratamento para colunas customizadas
 const isCustom = colunas.some(c => c.field_name === key);
 let aVal = isCustom ? (a.custom_data?.[key] ??"") : (a[key] ??"");
 let bVal = isCustom ? (b.custom_data?.[key] ??"") : (b[key] ??"");
 
 if (typeof aVal ==="string") aVal = aVal.toLowerCase();
 if (typeof bVal ==="string") bVal = bVal.toLowerCase();

 if (aVal < bVal) return direction ==="asc" ? -1 : 1;
 if (aVal > bVal) return direction ==="asc" ? 1 : -1;
 return 0;
 });

 return (
 <div className="space-y-6">
 <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
 <div className="flex items-center gap-3 min-w-0">
 <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shrink-0">
 <FolderTree size={20} />
 </div>
 <div className="min-w-0">
 <h1 className="text-xl font-bold text-slate-800">Centros de Custo</h1>
 <p className="text-sm text-slate-500 mt-0.5">
 Obras e centros sincronizados com o Sienge — tipo, produto e participação.
 </p>
 </div>
 </div>
 <div className="flex items-center gap-3 shrink-0">
 <Button variant="secondary" className="gap-2" onClick={() => setIsManageColsOpen(true)}>
 <Settings2 size={16} />
 Gerenciar colunas
 </Button>
 <Button onClick={handleSync} disabled={isSyncing} isLoading={isSyncing} className="gap-2">
 {!isSyncing ? <RefreshCw size={16} /> : null}
 {isSyncing ? "Sincronizando…" : "Atualizar sincronização"}
 </Button>
 </div>
 </div>

 <CollapsibleFilterPanel
 activeFilterCount={[
 busca,
 filtroEmpresa.length ? "e" : "",
 filtroCidade.length ? "c" : "",
 filtroProduto.length ? "p" : "",
 filtroId.length ? "i" : "",
 filtroTipo.length ? "t" : "",
 (filtroStatus.length > 0 && !(filtroStatus.length === 1 && filtroStatus[0] === "Ativo")) ? "s" : "",
 ].filter(Boolean).length}
 onClear={limparFiltros}
 >
 <FilterSearchField value={busca} onChange={setBusca} placeholder="ID, nome, cidade..." />

 <div className="flex-1 min-w-[140px]">
 <label className="text-xs text-slate-500 font-medium mb-1 block">Tipo</label>
 <MultiSelect
 options={tiposUnicos}
 value={filtroTipo}
 onChange={setFiltroTipo}
 placeholder="Todos"
 />
 </div>

 <div className="flex-1 min-w-[140px]">
 <label className="text-xs text-slate-500 font-medium mb-1 block">Cidade</label>
 <MultiSelect
 options={cidadesUnicas}
 value={filtroCidade}
 onChange={setFiltroCidade}
 placeholder="Todas"
 />
 </div>

 <div className="flex-1 min-w-[150px]">
 <label className="text-xs text-slate-500 font-medium mb-1 block">Produto</label>
 <MultiSelect
 options={produtosUnicos}
 value={filtroProduto}
 onChange={setFiltroProduto}
 placeholder="Todos"
 />
 </div>

 <div className="flex-1 min-w-[160px]">
 <label className="text-xs text-slate-500 font-medium mb-1 block">Empresa</label>
 <MultiSelect
 options={empresasUnicas}
 value={filtroEmpresa}
 onChange={setFiltroEmpresa}
 placeholder="Todas"
 />
 </div>

 <div className="flex-1 min-w-[130px]">
 <label className="text-xs text-slate-500 font-medium mb-1 block">Status</label>
 <MultiSelect
 options={["Ativo", "Inativo"]}
 value={filtroStatus}
 onChange={setFiltroStatus}
 placeholder="Todos"
 />
 </div>

 <div className="flex-1 min-w-[160px]">
 <label className="text-xs text-slate-500 font-medium mb-1 block">ID Centro de Custo</label>
 <MultiSelect
 options={idsUnicos}
 value={filtroId}
 onChange={setFiltroId}
 placeholder="Todos"
 />
 </div>
 </CollapsibleFilterPanel>

 {/* Tabela */}
 <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto overflow-y-auto max-h-[calc(100vh-220px)] relative">
 <table className="w-full text-left text-sm">
 <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 sticky top-0 z-10 shadow-sm">
 <tr>
 <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("id")}>
 <div className="flex items-center gap-2">ID {renderSortIcon("id")}</div>
 </th>
 <th className="px-4 py-3 cursor-pointer group select-none hover:bg-slate-100/50 transition-colors max-w-[200px]" onClick={() => handleSort("nome")}>
 <div className="flex items-center gap-2">Centro de Custo {renderSortIcon("nome")}</div>
 </th>
 <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("status")}>
 <div className="flex items-center gap-2">Status {renderSortIcon("status")}</div>
 </th>
 <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("tipo_sienge")}>
 <div className="flex items-center gap-2">Tipo {renderSortIcon("tipo_sienge")}</div>
 </th>
 <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("cidade")}>
 <div className="flex items-center gap-2">Cidade {renderSortIcon("cidade")}</div>
 </th>
 <th className="px-4 py-3 cursor-pointer group select-none hover:bg-slate-100/50 transition-colors max-w-[150px]" onClick={() => handleSort("produto")}>
 <div className="flex items-center gap-2">Produto {renderSortIcon("produto")}</div>
 </th>
 <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort("id_empresa")}>
 <div className="flex items-center gap-2">ID Empresa {renderSortIcon("id_empresa")}</div>
 </th>
 <th className="px-4 py-3 cursor-pointer group select-none hover:bg-slate-100/50 transition-colors max-w-[200px]" onClick={() => handleSort("nome_empresa")}>
 <div className="flex items-center gap-2">Empresa {renderSortIcon("nome_empresa")}</div>
 </th>
 
 {/* Colunas Dinâmicas Renderizadas no Header */}
 {colunas.map((col) => (
 <th key={col.id} className="px-4 py-3 cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort(col.field_name)}>
 <div className="flex items-center gap-2">
 {col.field_name} {renderSortIcon(col.field_name)}
 </div>
 </th>
 ))}

 <th className="px-4 py-3 text-center">Ações</th>
 </tr>
 </thead>
 <tbody className="divide-y divide-slate-100">
 {isLoading ? (
 <tr>
 <td colSpan={9 + colunas.length}>
 <AppLoadingState />
 </td>
 </tr>
 ) : sorted.map((cc) => (
 <tr key={cc.id} className="hover:bg-slate-50/50 transition-colors">
 <td className="px-4 py-3 text-slate-500 font-mono text-xs whitespace-nowrap">{cc.id}</td>
 <td className="px-4 py-3 text-slate-700 max-w-[200px]" title={cc.nome}>
    <div className="flex items-center gap-2">
      <span className="truncate">{cc.nome}</span>
      {cc.track_in_dashboard && (
        <span className="shrink-0 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-100" title="Acompanhado no Painel de Produtos">
          Painel
        </span>
      )}
    </div>
 </td>
 <td className="px-4 py-3 whitespace-nowrap">
 {cc.status ==="Ativo" ? (
 <span className="inline-flex items-center px-2 py-1 rounded-md bg-green-50 text-green-700 text-xs font-medium border border-green-200">Ativo</span>
 ) : (
 <span className="inline-flex items-center px-2 py-1 rounded-md bg-red-50 text-red-700 text-xs font-medium border border-red-200">Inativo</span>
 )}
 </td>
 <td className="px-4 py-3 whitespace-nowrap">
 {cc.tipo_sienge ? <span className="inline-flex items-center px-2 py-1 rounded-md bg-blue-50 text-blue-600 text-xs font-medium border border-blue-100">{cc.tipo_sienge}</span> : <span className="text-slate-300 italic text-xs">—</span>}
 </td>
 <td className="px-4 py-3 whitespace-nowrap">
 {cc.cidade ==="—" ? <span className="text-slate-300 italic text-xs">—</span> : <span className="text-slate-700 font-medium">{cc.cidade}</span>}
 </td>
 <td className="px-4 py-3 max-w-[180px]" title={cc.produto}>
 {cc.produto === "—" ? (
  <span className="text-slate-300 italic text-xs">—</span>
 ) : (
  <div className="min-w-0">
    <p className="text-slate-700 truncate">{cc.produto}</p>
    {cc.produtoEditado ? (
      <p className="text-[10px] text-ml-green font-medium">Nome editado</p>
    ) : null}
  </div>
 )}
 </td>
 <td className="px-4 py-3 whitespace-nowrap">
 {cc.id_empresa ? <span className="inline-flex items-center px-2 py-1 rounded-md bg-slate-100 text-slate-600 text-xs font-mono border border-slate-200">{cc.id_empresa}</span> : <span className="text-slate-300 italic text-xs">—</span>}
 </td>
 <td className="px-4 py-3 max-w-[200px] truncate" title={cc.nome_empresa}>
 {cc.nome_empresa ? <span className="text-slate-600 text-sm font-medium">{cc.nome_empresa}</span> : <span className="text-slate-300 italic text-xs">—</span>}
 </td>
 
 {/* Dados das colunas dinâmicas */}
 {colunas.map((col) => {
 const val = cc.custom_data?.[col.field_name];
 return (
 <td key={col.id} className="px-4 py-3">
 {val !== undefined && val !=="" && val !== false && val !== null ? (
 <span className="text-slate-700 font-medium">
 {col.field_type ==="boolean" ? (val ?"Sim" :"Não") : 
 col.field_type ==="percent" ? `${val}%` : val}
 </span>
 ) : (
 <span className="text-slate-300 italic text-xs">—</span>
 )}
 </td>
 );
 })}

 <td className="px-4 py-3 text-center">
 <button onClick={() => openEditModal(cc)} className="p-2 text-slate-400 hover:text-ml-green hover:bg-emerald-50 rounded-lg transition-colors" title="Editar">
 <Pencil className="w-4 h-4" />
 </button>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 {!isLoading && sorted.length === 0 && (
 <div className="p-12 text-center text-slate-500">
 <AlertCircle className="w-8 h-8 text-slate-300 mb-3" />
 <p className="font-medium text-slate-600">Nenhum centro de custo encontrado</p>
 </div>
 )}
 </div>

 {/* MODAL: GERENCIAR COLUNAS */}
 {isManageColsOpen && (
 <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
 <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
 <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
 <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
 <Settings2 className="w-5 h-5 text-ml-green" />
 Gerenciar Colunas
 </h2>
 <button onClick={() => setIsManageColsOpen(false)} className="text-slate-400 hover:text-slate-600 transition-colors p-1 hover:bg-slate-100 rounded-md">
 <X className="w-5 h-5" />
 </button>
 </div>
 
 <div className="p-6 space-y-6">
 <div className="space-y-4">
 <h3 className="text-sm font-semibold text-slate-700">Colunas Existentes</h3>
 {colunas.length === 0 ? (
 <p className="text-sm text-slate-500 italic">Nenhuma coluna customizada criada.</p>
 ) : (
 <ul className="space-y-2">
 {colunas.map(c => (
 <li key={c.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-100">
 <div>
 <span className="font-medium text-slate-700 block text-sm">{c.field_name}</span>
 <span className="text-xs text-slate-500 uppercase tracking-wider">{c.field_type}</span>
 </div>
 <button onClick={() => handleDeleteColumn(c.id)} className="text-slate-400 hover:text-red-500 p-1.5 rounded-md hover:bg-white transition-colors" title="Excluir Coluna">
 <Trash2 className="w-4 h-4" />
 </button>
 </li>
 ))}
 </ul>
 )}
 </div>

 <div className="border-t border-slate-100 pt-6 space-y-4">
 <h3 className="text-sm font-semibold text-slate-700">Adicionar Nova Coluna</h3>
 <div className="flex gap-2">
 <div className="flex-1 space-y-1">
 <input 
 type="text" 
 placeholder="Nome da Coluna (Ex: Status Extra)" 
 value={newColName}
 onChange={(e) => setNewColName(e.target.value)}
 className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-ml-green/40 focus:border-ml-green text-slate-800"
 />
 </div>
 <div className="w-32 space-y-1">
 <select 
 value={newColType}
 onChange={(e) => setNewColType(e.target.value)}
 className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-ml-green/40 focus:border-ml-green text-slate-800"
 >
 <option value="text">Texto</option>
 <option value="number">Número</option>
 <option value="boolean">Checkbox</option>
 <option value="percent">Percentual</option>
 </select>
 </div>
 </div>
 <Button onClick={handleCreateColumn} className="w-full gap-2">
 <Plus className="w-4 h-4" /> Adicionar Coluna
 </Button>
 </div>
 </div>
 </div>
 </div>
 )}

 {/* MODAL: EDITAR CENTRO DE CUSTO */}
 {isEditModalOpen && editingCC && (
 <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
 <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl flex flex-col overflow-hidden max-h-[90vh]">
 <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50 shrink-0">
 <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
 <Pencil className="w-5 h-5 text-ml-green" />
 Editar centro de custo
 </h2>
 <button onClick={() => setIsEditModalOpen(false)} className="text-slate-400 hover:text-slate-600 transition-colors p-1 hover:bg-slate-100 rounded-md">
 <X className="w-5 h-5" />
 </button>
 </div>
 
 <div className="p-6 space-y-6 overflow-y-auto flex-1">
 <div className="space-y-1 bg-emerald-50/60 p-4 rounded-xl border border-emerald-100">
 <p className="text-xs text-slate-500 font-mono">ID {editingCC.id}</p>
 <p className="font-semibold text-slate-800">{editingCC.nome}</p>
 {editingCC.nome_empresa ? (
  <p className="text-xs text-slate-600 flex items-center gap-1.5 pt-1">
    <Building2 size={12} className="text-slate-400" />
    {editingCC.nome_empresa}
    {editingCC.id_empresa ? <span className="font-mono text-slate-400">· empresa {editingCC.id_empresa}</span> : null}
  </p>
 ) : null}
 </div>

 <div className="space-y-1.5 border-b border-slate-100 pb-4">
 <label className="text-sm font-semibold text-slate-700 block">Status</label>
 <select
 value={editStatus}
 onChange={(e) => setEditStatus(e.target.value)}
 className={FIELD_CLASS}
 >
 <option value="Ativo">Ativo</option>
 <option value="Inativo">Inativo</option>
 </select>
 </div>

 <div className="space-y-1.5 border-b border-slate-100 pb-4">
 <div className="flex items-center justify-between gap-2">
   <label className="text-sm font-semibold text-slate-700 block">Classificação / Tipo</label>
   <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
     editFormData["__tipo_override"] ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-500"
   }`}>
     {editFormData["__tipo_override"] ? "Manual" : "Sienge"}
   </span>
 </div>
 <select
 value={editFormData["__tipo_override"] || editingCC.tipo_sienge || ""}
 onChange={(e) => setEditFormData({ ...editFormData, "__tipo_override": e.target.value })}
 className={FIELD_CLASS}
 >
 <option value="">Usar classificação do Sienge{editingCC.custom_data?.__tipo_sienge_cache ? ` (${editingCC.custom_data.__tipo_sienge_cache})` : ""}</option>
 <option value="Obra e Centro de Custo">Obra e Centro de Custo</option>
 <option value="Somente Obra">Somente Obra</option>
 <option value="Somente Centro de Custo">Somente Centro de Custo</option>
 <option value="Centro de Custo associado à Obra">Centro de Custo associado à Obra</option>
 </select>
 <p className="text-xs text-slate-500">O sistema cruza o ID com a obra no Sienge. Override manual a sync não apaga.</p>
 </div>

 <div className="space-y-1.5 border-b border-slate-100 pb-4">
 <div className="flex items-center justify-between gap-2">
   <label className="text-sm font-semibold text-slate-700 block">Nome do produto</label>
   {editProduto.trim() && editProduto.trim() !== parseCentroNome(editingCC.nome).produto ? (
     <button
       type="button"
       onClick={() => setEditProduto(parseCentroNome(editingCC.nome).produto)}
       className="text-xs font-semibold text-ml-green hover:underline"
     >
       Voltar ao padrão
     </button>
   ) : null}
 </div>
 <input
   value={editProduto}
   onChange={(e) => setEditProduto(e.target.value)}
   className={FIELD_CLASS}
   placeholder={parseCentroNome(editingCC.nome).produto}
 />
 <p className="text-xs text-slate-500">
   Padrão extraído do nome Sienge: <span className="font-medium text-slate-600">{parseCentroNome(editingCC.nome).produto}</span>.
   Se editar, vale só neste centro de custo.
 </p>
 </div>
        {/* Acompanhamento no Painel: só cabeçalho da obra (e satélite já marcado, para desmarcar). */}
        {mostraFlagAcompanharEmpreendimento({
          tipo: tipoEfetivoCentro({
            tipo_sienge: editingCC.tipo_sienge,
            custom_data: { ...editingCC.custom_data, ...editFormData },
          }),
          nome: editingCC.nome,
          jaAcompanhado: Boolean(editingCC.track_in_dashboard),
        }) && (
        <div className="space-y-4 border-b border-slate-100 pb-4">
          <label className="flex items-center gap-2 cursor-pointer mt-2">
            <input 
              type="checkbox"
              checked={editTrackInDashboard}
              onChange={(e) => setEditTrackInDashboard(e.target.checked)}
              className="w-4 h-4 text-ml-green rounded border-slate-300 focus:ring-ml-green"
            />
            <span className="text-sm font-semibold text-slate-700 block">Acompanhar Empreendimento no Painel de Produtos?</span>
          </label>
          {centroEhSateliteDeProduto(editingCC.nome) ? (
            <p className="text-xs text-amber-700">Este centro não é o cabeçalho da obra. Desmarque para não criar um card extra; obras, marketing e parceria já entram pelo produto.</p>
          ) : (
            <p className="text-xs text-slate-500">Marcar aqui já puxa obras, marketing, comercial e parceria do mesmo produto.</p>
          )}
          
          {editTrackInDashboard && (
            <div className="space-y-4 pl-6 border-l-2 border-ml-green/20 mt-3">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700 block">Regra de Parceria Aplicável</label>
                <select
                  value={editPartnershipRuleId}
                  onChange={(e) => setEditPartnershipRuleId(e.target.value === "" ? "" : Number(e.target.value))}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-ml-green/40 focus:border-ml-green text-slate-800 bg-white"
                >
                  <option value="">Nenhuma Regra (Sem Rateio)</option>
                  {configs.map(rule => (
                    <option key={rule.id} value={rule.id}>{rule.name}</option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 italic mt-1">O percentual do parceiro será lido do campo "Participação" nas colunas customizadas.</p>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700 block">Fase do Produto</label>
                <select
                  value={editProjectPhase}
                  onChange={(e) => setEditProjectPhase(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-ml-green/40 focus:border-ml-green text-slate-800 bg-white"
                >
                  <option value="Em Andamento">Em Andamento</option>
                  <option value="Encerrado">Encerrado</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700 block">Valor Manual do Terreno (R$)</label>
                <input
                  type="text"
                  value={
                    editManualLandCost === 0 || editManualLandCost === undefined 
                      ? "" 
                      : editManualLandCost.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                  }
                  onChange={(e) => {
                    const rawValue = e.target.value.replace(/\D/g, '');
                    setEditManualLandCost(Number(rawValue) / 100);
                  }}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-ml-green/40 focus:border-ml-green text-slate-800"
                  placeholder="0,00"
                />
                <p className="text-xs text-slate-500">{TEXTO_TERRENO_MANUAL}</p>
              </div>

              {mostraInicioTerreno(editManualLandCost) && (
                <div className="space-y-3 border-l-2 border-ml-green pl-3 py-1">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-sm font-semibold text-slate-700 block">Início do Pagamento</label>
                      <input
                        type="month"
                        value={editLandStartDate}
                        onChange={(e) => setEditLandStartDate(e.target.value)}
                        className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-ml-green/40 focus:border-ml-green text-slate-800"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-semibold text-slate-700 block">Curva de Desembolso</label>
                      <select
                        value={editLandCurveId}
                        onChange={(e) => setEditLandCurveId(e.target.value === "" ? "" : Number(e.target.value))}
                        className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-ml-green/40 focus:border-ml-green text-slate-800 bg-white"
                      >
                        <option value="">À Vista (Sem Curva)</option>
                        {curves
                          .filter((c) => c.tipo?.toLowerCase().includes('aquisi'))
                          .map((curve) => (
                            <option key={curve.id} value={curve.id}>
                              {curve.nome}
                            </option>
                          ))}
                      </select>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500">{TEXTO_INICIO_CURVA}</p>
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 space-y-2">
                    {carregandoPrimeiroMes && !primeiroMesObra ? (
                      <p className="text-xs text-amber-900">Buscando o primeiro mês de caixa desta obra…</p>
                    ) : (
                      linhasAlertaTerreno({
                        primeiroMesCaixa: primeiroMesObra?.primeiro_mes_caixa,
                        primeiroMesDesembolso: primeiroMesObra?.primeiro_mes_desembolso,
                      }).map((linha) => (
                        <p key={linha} className="text-xs text-amber-950">{linha}</p>
                      ))
                    )}
                    {mesSugeridoTerreno ? (
                        <button
                          type="button"
                          disabled={editLandStartDate === mesSugeridoTerreno}
                          onClick={() => setEditLandStartDate(mesSugeridoTerreno)}
                          className="text-xs font-semibold text-amber-950 underline decoration-amber-400 underline-offset-2 disabled:no-underline disabled:opacity-60"
                        >
                          {editLandStartDate === mesSugeridoTerreno
                            ? `Início já está em ${formatarMesPt(mesSugeridoTerreno)}`
                            : `Usar ${formatarMesPt(mesSugeridoTerreno)}`}
                        </button>
                    ) : null}
                    {!editLandStartDate ? (
                      <p className="text-xs text-amber-800">Sem mês inicial, lista e detalhe ainda não usam o mesmo mês — escolha um.</p>
                    ) : null}
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-700 block flex items-center justify-between">
                  Regras de Rateio
                  <button 
                    onClick={() => setEditApportionmentRules([...editApportionmentRules, { project_prefix: "", rule_type: "VGV", percentage: 100 }])}
                    className="text-xs text-ml-green hover:text-emerald-800 font-medium flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" /> Adicionar Rateio
                  </button>
                </label>
                
                {editApportionmentRules.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">Nenhuma regra definida. Custo total irá para este Centro.</p>
                ) : (
                  <div className="space-y-2">
                    {editApportionmentRules.map((rule, idx) => (
                      <div key={idx} className="flex gap-2 items-center bg-slate-50 p-2 rounded-lg border border-slate-100 w-full overflow-hidden">
                        <select
                          value={rule.project_prefix || ""}
                          onChange={(e) => {
                            const newRules = [...editApportionmentRules];
                            newRules[idx].project_prefix = e.target.value;
                            setEditApportionmentRules(newRules);
                          }}
                          className="flex-1 w-0 min-w-0 px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-ml-green text-ellipsis overflow-hidden whitespace-nowrap"
                        >
                          <option value="">Selecione um Empreendimento...</option>
                          {centros
                            .filter(cc => String(cc.id).substring(0, 3) === String(editingCC.id).substring(0, 3))
                            .sort((a, b) => a.id - b.id)
                            .map(cc => (
                              <option key={cc.id} value={cc.id}>{cc.id} - {cc.nome}</option>
                            ))}
                        </select>
                        <select
                          value={rule.rule_type}
                          onChange={(e) => {
                            const newRules = [...editApportionmentRules];
                            newRules[idx].rule_type = e.target.value;
                            setEditApportionmentRules(newRules);
                          }}
                          className="w-24 px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-ml-green"
                        >
                          <option value="VGV">% VGV</option>
                          <option value="Obra">% Obra</option>
                          <option value="Fixo">% Fixo</option>
                        </select>
                        <input
                          type="number"
                          step="0.01"
                          value={rule.percentage}
                          onChange={(e) => {
                            const newRules = [...editApportionmentRules];
                            newRules[idx].percentage = e.target.value === "" ? "" : Number(e.target.value);
                            setEditApportionmentRules(newRules);
                          }}
                          className="w-16 px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-ml-green"
                          placeholder="%"
                        />
                        <button
                          onClick={() => {
                            const newRules = editApportionmentRules.filter((_, i) => i !== idx);
                            setEditApportionmentRules(newRules);
                          }}
                          className="text-slate-400 hover:text-red-500"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        )}

 {colunas.length === 0 ? (
 <div className="text-center py-6 text-slate-500">
 <AlertCircle className="w-8 h-8 text-slate-300 mb-2" />
 <p className="text-sm">Você ainda não criou nenhuma coluna customizada.</p>
 <p className="text-xs mt-1">Use o botão"Gerenciar Colunas" para criar campos extras.</p>
 </div>
 ) : (
 <div className="space-y-4">
 {colunas.map((col) => (
 <div key={col.id} className="space-y-1.5">
 <label className="text-sm font-semibold text-slate-700 block">
 {col.field_name}
 </label>
 {col.field_type === "percent" && /participa/i.test(col.field_name) ? (
  <p className="text-xs text-slate-500 mb-1">
    Participação de {editingCC.nome_empresa || "esta empresa"} neste produto
    {editProduto.trim() ? ` (${editProduto.trim()})` : ""}.
    Usada na parceria do painel e, com Consolidação MLDU ligada, no fator (empresa × este %). Sem o checkbox, o orçamento não muda.
  </p>
 ) : null}
 {col.field_type ==="boolean" ? (
 <label className="flex items-center gap-2 cursor-pointer mt-2">
 <input 
 type="checkbox"
 checked={editFormData[col.field_name] || false}
 onChange={(e) => setEditFormData({ ...editFormData, [col.field_name]: e.target.checked })}
 className="w-4 h-4 text-ml-green rounded border-slate-300 focus:ring-ml-green"
 />
 <span className="text-sm text-slate-600">Ativar</span>
 </label>
 ) : col.field_type ==="percent" ? (
 <div className="relative">
 <input
 type="number"
 step="any"
 min="0"
 max="100"
 value={editFormData[col.field_name] ||""}
 onChange={(e) => {
   let v = e.target.value;
   if (v && Number(v) > 100) v = "100";
   if (v && Number(v) < 0) v = "0";
   setEditFormData({ ...editFormData, [col.field_name]: v });
 }}
 className="w-full pl-3 pr-8 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-ml-green/40 focus:border-ml-green text-slate-800"
 />
 <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">%</span>
 </div>
 ) : (
 <input
 type={col.field_type ==="number" ?"number" :"text"}
 value={editFormData[col.field_name] ||""}
 onChange={(e) => setEditFormData({ ...editFormData, [col.field_name]: e.target.value })}
 className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-ml-green/40 focus:border-ml-green text-slate-800"
 />
 )}
 </div>
 ))}
 </div>
 )}

 </div>
 <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50 shrink-0">
 <Button variant="secondary" onClick={() => setIsEditModalOpen(false)}>
 Cancelar
 </Button>
 <Button onClick={handleSaveEdit} disabled={isSaving} isLoading={isSaving}>
 Salvar
 </Button>
 </div>
 </div>
 </div>
 )}
 </div>
 );
}
