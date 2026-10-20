"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { Card } from "@/components/ui/Card";
import { Plus, FolderOpen, ArrowRight, Trash2, Copy } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { canCreateViabilidadeUser } from "@/lib/roles";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

interface Viability {
 id: number;
 project_name: string;
 status: string;
 created_at: string;
 versions?: Viability[];
}

export default function ViabilitiesListPage() {
 const [viabilities, setViabilities] = useState<Viability[]>([]);
 const [isLoading, setIsLoading] = useState(true);
 const [loadError, setLoadError] = useState("");
 const router = useRouter();
 const { user } = useAuth();
 
 const canCreate = canCreateViabilidadeUser(user);

 const fetchViabilities = async () => {
 try {
 setLoadError("");
 const { data } = await api.get("/viabilities/");
 setViabilities(Array.isArray(data) ? data : []);
 } catch (error) {
 console.error("Erro ao buscar projetos", error);
 setLoadError("Não foi possível carregar as viabilidades. Os cadastros continuam no sistema; tente de novo em instantes.");
 } finally {
 setIsLoading(false);
 }
 };

 useEffect(() => {
 fetchViabilities();
 }, []);

 const handleCreateNew = async () => {
 const name = prompt("Digite o nome do novo projeto de Viabilidade:");
 if (!name) return;
 
 try {
 const { data } = await api.post("/viabilities/", { project_name: name });
 router.push(`/dashboard/viabilities/${data.id}`);
 } catch (error) {
 alert("Erro ao criar viabilidade.");
 }
 };

 const handleDelete = async (id: number, e: React.MouseEvent) => {
 e.preventDefault();
 if (!(await confirmDialog("Tem certeza que deseja excluir esta viabilidade? Esta ação não pode ser desfeita.", { variant: "danger" }))) return;
 try {
 await api.delete(`/viabilities/${id}`);
 fetchViabilities();
 } catch (error) {
 alert("Erro ao excluir viabilidade.");
 }
 };

 const handleClone = async (id: number, e: React.MouseEvent) => {
 e.preventDefault();
 const customName = window.prompt("Digite um nome para o novo cenário (ou deixe em branco para o padrão):");
 if (customName === null) return; // User cancelled
 try {
 await api.post(`/viabilities/${id}/clone`, { custom_name: customName });
 fetchViabilities();
 } catch (error) {
 alert("Erro ao duplicar viabilidade.");
 }
 };

 return (
 <div className="space-y-6">
 <div className="flex justify-between items-center">
 <div>
 <h1 className="text-3xl font-bold tracking-tight text-slate-900">Projetos de Viabilidade</h1>
 <p className="text-slate-500 mt-1">Gerencie e consolide os cálculos de seus empreendimentos.</p>
 </div>
 {canCreate && (
 <Button onClick={handleCreateNew} variant="primary" className="flex items-center gap-2 shadow-sm">
 <Plus className="w-4 h-4" />
 Nova Viabilidade
 </Button>
 )}
 </div>

 {isLoading ? (
 <AppLoadingState />
 ) : loadError ? (
 <Card className="flex flex-col items-center justify-center p-12 text-center border-dashed">
 <h3 className="text-lg font-medium text-slate-900 mb-1">Não foi possível listar as viabilidades</h3>
 <p className="text-slate-500 max-w-sm mb-6">{loadError}</p>
 <Button onClick={fetchViabilities} variant="outline">Tentar de novo</Button>
 </Card>
 ) : viabilities.length === 0 ? (
 <Card className="flex flex-col items-center justify-center p-12 text-center border-dashed">
 <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
 <FolderOpen className="w-8 h-8 text-slate-400" />
 </div>
 <h3 className="text-lg font-medium text-slate-900 mb-1">Nenhum projeto encontrado</h3>
 <p className="text-slate-500 max-w-sm mb-6">Você ainda não tem nenhuma viabilidade cadastrada. Comece criando o seu primeiro projeto.</p>
 {canCreate && (
 <Button onClick={handleCreateNew} variant="outline" className="flex items-center gap-2">
 <Plus className="w-4 h-4" /> Criar Projeto
 </Button>
 )}
 </Card>
 ) : (
 <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
 {viabilities.map((v) => {
   // Todos os cenários da família: o raiz + os clones filhos
   const allScenarios = [v, ...(v.versions || [])];
   return (
   <div key={v.id} className="h-full">
   <Card 
     className="p-6 hover:border-green-500 hover:shadow-md transition-all cursor-pointer group h-full flex flex-col bg-white border-slate-200"
     onClick={() => router.push(`/dashboard/viabilities/${v.id}`)}
   >
  <div className="flex justify-between items-start mb-4">
  <div className="p-2.5 bg-green-50 text-green-700 rounded-lg group-hover:bg-green-100 transition-colors">
  <FolderOpen className="w-5 h-5" />
  </div>
  <div className="flex gap-2">
  <span className={`px-2.5 py-1 rounded text-xs font-semibold ${
  v.status === 'Aprovado' ? 'bg-green-100 text-green-800 border border-green-200' :
  v.status === 'Em Análise' ? 'bg-amber-100 text-amber-800 border border-amber-200' :
  'bg-slate-100 text-slate-700 border border-slate-200'
  }`}>
  {v.status}
  </span>
  {canCreate && (
  <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
  <button 
  onClick={(e) => handleClone(v.id, e)}
  className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
  title="Duplicar viabilidade"
  >
  <Copy className="w-4 h-4" />
  </button>
  <button 
  onClick={(e) => handleDelete(v.id, e)}
  className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
  title="Excluir viabilidade"
  >
  <Trash2 className="w-4 h-4" />
  </button>
  </div>
  )}
  </div>
  </div>
  <h3 className="text-lg font-bold text-slate-800 group-hover:text-green-700 transition-colors">
  {v.project_name}
  </h3>
   <p className="text-sm text-slate-500 mt-1 mb-4">
   Criado em: {new Date(v.created_at).toLocaleDateString('pt-BR')}
   </p>
   
   <div className="mb-4 flex-1">
     <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Cenários ({allScenarios.length})</p>
     <div className="space-y-1.5">
     {allScenarios.map(scenario => (
       <div 
         key={scenario.id} 
         className="text-sm text-slate-600 bg-slate-50 p-2 rounded flex justify-between items-center hover:bg-slate-100 hover:text-green-700 transition-colors"
         onClick={(e) => { 
           e.stopPropagation(); 
           router.push(`/dashboard/viabilities/${scenario.id}`); 
         }}
       >
          <span className="truncate pr-2">{scenario.project_name}</span>
          <ArrowRight className="w-3 h-3 opacity-50" />
       </div>
     ))}
     </div>
   </div>

   <div className="flex items-center justify-between border-t border-slate-100 pt-4">
   <span className="text-sm font-medium text-slate-600 group-hover:text-green-700">Acessar Projeto</span>
   <ArrowRight className="w-4 h-4 text-green-600 opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0" />
   </div>
   </Card>
   </div>
   );
 })}
 </div>
 )}
 </div>
 );
}
