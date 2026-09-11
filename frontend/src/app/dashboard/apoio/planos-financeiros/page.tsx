"use client";

import { useState, useEffect } from"react";
import { apoioService } from"@/services/apoio";
import { 
 RefreshCw, Wallet
} from"lucide-react";
import { Button } from"@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { formatPlanId } from"@/lib/formatters";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { CollapsibleFilterPanel } from "@/components/shared/CollapsibleFilterPanel";
import { FilterSearchField } from "@/components/shared/FilterSearchField";

export default function PlanosFinanceirosPage() {
 const [planos, setPlanos] = useState<any[]>([]);
 const [isLoading, setIsLoading] = useState(true);
 const [isSyncing, setIsSyncing] = useState(false);

 const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>({ key:"db_sienge_id", direction:"asc" });

 // --- Filtros ---
 const [busca, setBusca] = useState("");
 const [filtroTipo, setFiltroTipo] = useState("");
 const [filtroAtiva, setFiltroAtiva] = useState("");
 const [filtroRedutora, setFiltroRedutora] = useState("");
 const [filtroImposto, setFiltroImposto] = useState("");

 useEffect(() => {
 loadPlanos();
 }, []);

 const loadPlanos = async () => {
 setIsLoading(true);
 const data = await apoioService.getPlanosFinanceiros();
 setPlanos(data);
 setIsLoading(false);
 };

 const handleSync = async () => {
 setIsSyncing(true);
 try {
 await apoioService.syncPlanosFinanceiros();
 await loadPlanos();
 } catch (error) {
 console.error("Erro na sincronização:", error);
 alert("Erro ao sincronizar planos financeiros.");
 } finally {
 setIsSyncing(false);
 }
 };

 const limparFiltros = () => {
 setBusca("");
 setFiltroTipo("");
 setFiltroAtiva("");
 setFiltroRedutora("");
 setFiltroImposto("");
 };

 // ── Ordenação e Filtros ──────────────────────────────────────────────────────
 const handleSort = (key: string) => {
 let direction:"asc" |"desc" ="asc";
 if (sortConfig && sortConfig.key === key && sortConfig.direction ==="asc") {
 direction ="desc";
 }
 setSortConfig({ key, direction });
 };

 const renderSortIcon = (key: string) => {
 if (sortConfig?.key !== key) return <span className="text-slate-300">↕</span>;
 return sortConfig.direction ==="asc" ? <span className="text-brand-orange font-bold">↑</span> : <span className="text-brand-orange font-bold">↓</span>;
 };

 const filteredPlanos = planos.filter(p => {
 const term = busca.toLowerCase();
 const nome = p.name ? p.name.toLowerCase() :"";
 const id = p.db_sienge_id ? String(p.db_sienge_id).toLowerCase() :"";

 if (term && !nome.includes(term) && !id.includes(term)) return false;
 
 if (filtroTipo && p.tpConta !== filtroTipo) return false;
 if (filtroAtiva && p.flAtiva !== filtroAtiva) return false;
 if (filtroRedutora && p.flRedutora !== filtroRedutora) return false;
 if (filtroImposto && p.flImposto !== filtroImposto) return false;

 return true;
 });

 const sortedPlanos = [...filteredPlanos].sort((a, b) => {
 if (!sortConfig) return 0;
 
 const key = sortConfig.key;
 let valA = a[key] ??"";
 let valB = b[key] ??"";

 if (key ==="db_sienge_id") {
 valA = parseInt(valA) || 0;
 valB = parseInt(valB) || 0;
 } else {
 valA = String(valA).toLowerCase();
 valB = String(valB).toLowerCase();
 }

 if (valA < valB) return sortConfig.direction ==="asc" ? -1 : 1;
 if (valA > valB) return sortConfig.direction ==="asc" ? 1 : -1;
 return 0;
 });

 const mapTipoConta = (tp: string) => {
 if (tp ==="R") return"Analítica (R)";
 if (tp ==="T") return"Sintética (T)";
 return tp;
 };

 const renderFlag = (flag: string) => {
 if (flag ==="S") return <span className="inline-flex items-center gap-1 text-brand-green bg-brand-green/10 px-2 py-0.5 rounded-full text-xs font-semibold border border-brand-green/20">Sim</span>;
 if (flag ==="N") return <span className="inline-flex items-center gap-1 text-slate-500 bg-slate-50 px-2 py-0.5 rounded-full text-xs border border-slate-200">Não</span>;
 return flag;
 };

 const renderAtiva = (flag: string) => {
 if (flag ==="S") return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border bg-brand-green/10 text-brand-green border-brand-green/20"><span className="w-1.5 h-1.5 rounded-full bg-brand-green"/> Ativa</span>;
 if (flag ==="N") return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border bg-slate-100 text-slate-500 border-slate-200"><span className="w-1.5 h-1.5 rounded-full bg-slate-400"/> Inativa</span>;
 return flag;
 };

 // Coletar tipos únicos para filtros
 const tiposUnicos = Array.from(new Set(planos.map(p => p.tpConta).filter(Boolean))).sort();

 return (
 <div className="p-8 max-w-[1400px] mx-auto space-y-6 animate-in fade-in duration-300">
 <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
 <div>
 <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
 <Wallet className="w-6 h-6 text-brand-orange" />
 Planos Financeiros
 </h1>
 <p className="text-slate-500 text-sm mt-1">Gerencie os planos financeiros (Categorias de Pagamento) integrados com o Sienge.</p>
 </div>
 <Button 
 className="gap-2" 
 onClick={handleSync}
 disabled={isSyncing}
 >
 {isSyncing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
 {isSyncing ?"Sincronizando..." :"Atualizar Sincronização"}
 </Button>
 </div>

 <CollapsibleFilterPanel
 activeFilterCount={[busca, filtroTipo, filtroAtiva, filtroRedutora, filtroImposto].filter(Boolean).length}
 onClear={limparFiltros}
 >
 <FilterSearchField value={busca} onChange={setBusca} placeholder="Nome ou ID Sienge..." />
 <div className="flex-1 min-w-[140px]">
 <label className="text-xs text-slate-500 font-medium mb-1 block">Tipo</label>
 <SearchableSelect
 placeholder="Todos"
 value={filtroTipo}
 onChange={(val) => setFiltroTipo(String(val))}
 options={tiposUnicos.map((t) => ({ id: t as string, label: mapTipoConta(t as string) }))}
 />
 </div>
 <div className="flex-1 min-w-[130px]">
 <label className="text-xs text-slate-500 font-medium mb-1 block">Status</label>
 <SearchableSelect
 placeholder="Todos"
 value={filtroAtiva}
 onChange={(val) => setFiltroAtiva(String(val))}
 options={[
 { id: "S", label: "Ativa" },
 { id: "N", label: "Inativa" },
 ]}
 />
 </div>
 <div className="flex-1 min-w-[150px]">
 <label className="text-xs text-slate-500 font-medium mb-1 block">Conta Redutora</label>
 <SearchableSelect
 placeholder="Todas"
 value={filtroRedutora}
 onChange={(val) => setFiltroRedutora(String(val))}
 options={[
 { id: "S", label: "Sim" },
 { id: "N", label: "Não" },
 ]}
 />
 </div>
 <div className="flex-1 min-w-[150px]">
 <label className="text-xs text-slate-500 font-medium mb-1 block">Conta Imposto</label>
 <SearchableSelect
 placeholder="Todas"
 value={filtroImposto}
 onChange={(val) => setFiltroImposto(String(val))}
 options={[
 { id: "S", label: "Sim" },
 { id: "N", label: "Não" },
 ]}
 />
 </div>
 </CollapsibleFilterPanel>

 <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
 <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
 <h2 className="text-sm font-semibold text-slate-800">Resultados</h2>
 <span className="text-xs font-medium text-slate-500 bg-white border border-slate-200 px-2 py-0.5 rounded-full">
 {sortedPlanos.length} {sortedPlanos.length === 1 ? "plano" : "planos"}
 </span>
 </div>
 <div className="overflow-x-auto">
 <table className="w-full text-left text-sm">
 <thead className="bg-white text-slate-600 font-semibold border-b border-slate-200 sticky top-0">
 <tr>
 <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort('db_sienge_id')}>
 <div className="flex items-center gap-2">ID Sienge {renderSortIcon('db_sienge_id')}</div>
 </th>
 <th className="px-4 py-3 cursor-pointer group select-none hover:bg-slate-100/50 transition-colors w-full" onClick={() => handleSort('name')}>
 <div className="flex items-center gap-2">Nome do Plano {renderSortIcon('name')}</div>
 </th>
 <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort('flAtiva')}>
 <div className="flex items-center justify-center gap-2">Status {renderSortIcon('flAtiva')}</div>
 </th>
 <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors" onClick={() => handleSort('tpConta')}>
 <div className="flex items-center gap-2">Tipo de Conta {renderSortIcon('tpConta')}</div>
 </th>
 <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors text-center" onClick={() => handleSort('flRedutora')}>
 <div className="flex items-center justify-center gap-2">Redutora {renderSortIcon('flRedutora')}</div>
 </th>
 <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors text-center" onClick={() => handleSort('flImposto')}>
 <div className="flex items-center justify-center gap-2">Imposto {renderSortIcon('flImposto')}</div>
 </th>
 <th className="px-4 py-3 whitespace-nowrap cursor-pointer group select-none hover:bg-slate-100/50 transition-colors text-center" onClick={() => handleSort('flAdiantamento')}>
 <div className="flex items-center justify-center gap-2">Adiantamento {renderSortIcon('flAdiantamento')}</div>
 </th>
 </tr>
 </thead>
 <tbody className="divide-y divide-slate-100">
 {isLoading ? (
 <tr>
 <td colSpan={7}>
 <AppLoadingState />
 </td>
 </tr>
 ) : sortedPlanos.length === 0 ? (
 <tr>
 <td colSpan={7} className="px-6 py-10">
 <div className="text-center space-y-2">
 <p className="text-sm font-medium text-slate-600">Nenhum plano financeiro encontrado</p>
 <p className="text-xs text-slate-400">Ajuste os filtros ou limpe a busca.</p>
 <button type="button" onClick={limparFiltros} className="text-xs font-semibold text-brand-green hover:underline">
 Limpar filtros
 </button>
 </div>
 </td>
 </tr>
 ) : sortedPlanos.map((plano, idx) => (
 <tr key={plano.id} className={`hover:bg-slate-50 transition-colors ${idx % 2 === 1 ? "bg-slate-50/60" : "bg-white"}`}>
 <td className="px-4 py-3 whitespace-nowrap">
 <span className="text-sm font-mono text-slate-600 bg-slate-50 px-2 py-1 rounded">
 {formatPlanId(plano.db_sienge_id)}
 </span>
 </td>
 <td className="px-4 py-3 font-semibold text-slate-800">
 <div className="max-w-[300px] xl:max-w-[500px] truncate" title={plano.name}>{plano.name}</div>
 </td>
 <td className="px-4 py-3 whitespace-nowrap text-center">
 {renderAtiva(plano.flAtiva)}
 </td>
 <td className="px-4 py-3 whitespace-nowrap">
 <span className="text-slate-600 font-medium">
 {mapTipoConta(plano.tpConta)}
 </span>
 </td>
 <td className="px-4 py-3 whitespace-nowrap text-center">
 {renderFlag(plano.flRedutora)}
 </td>
 <td className="px-4 py-3 whitespace-nowrap text-center">
 {renderFlag(plano.flImposto)}
 </td>
 <td className="px-4 py-3 whitespace-nowrap text-center">
 {renderFlag(plano.flAdiantamento)}
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </div>
 </div>
 );
}
