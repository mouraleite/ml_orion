"use client";
import { useState, useEffect } from"react";
import { useParams, useRouter } from"next/navigation";
import { api } from"@/lib/api";
import { Button } from"@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { ArrowLeft, Save, Plus, CheckCircle, Clock, RotateCcw, Copy, Trash2 } from"lucide-react";
import { RevenueTab } from"@/components/viabilities/RevenueTab";
import { ConstructionTab } from"@/components/viabilities/ConstructionTab";
import { ExpensesTab } from"@/components/viabilities/ExpensesTab";
import { CurvesConfig } from"@/components/viabilities/CurvesConfig";
import { TaxesTab } from"@/components/viabilities/TaxesTab";
import { ExchangesTab } from"@/components/viabilities/ExchangesTab";
import { FundingTab } from"@/components/viabilities/FundingTab";
import dynamic from "next/dynamic";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
const SummaryTab = dynamic(() => import("@/components/viabilities/SummaryTab").then(m => m.SummaryTab), { ssr: false, loading: () => <AppLoadingState /> });
import { TrackingTab } from"@/components/viabilities/TrackingTab";
import { DocumentsTab } from"@/components/viabilities/DocumentsTab";
import PhysicalDataTab from"@/components/viabilities/PhysicalDataTab";
import { DatesTab } from "@/components/viabilities/DatesTab";
import { ComparisonTab } from "@/components/viabilities/ComparisonTab";
import { ObraAcompanhamentoField } from "@/components/viabilities/ObraAcompanhamentoField";
import { useAuth } from"@/contexts/AuthContext";
import { canWriteModule } from "@/lib/roles";
import { useUnsavedChanges } from "@/contexts/UnsavedChangesContext";

const ExecutiveSummaryTab = dynamic(() => import("@/components/viabilities/ExecutiveSummaryTab"), { ssr: false, loading: () => <AppLoadingState /> });

const TABS = ["Dados Físicos","Datas","Permutas","Receitas","Obras","Despesas","Curvas","Impostos","Funding","Documentos","Parecer Executivo","Resumo","Comparativo"];

export default function ViabilityDetailsPage() {
 const { id } = useParams();
 const router = useRouter();
 const [activeTab, setActiveTab] = useState(0);
 const [project, setProject] = useState<any>(null);
 const [phases, setPhases] = useState<any[]>([]);
 const [scenarios, setScenarios] = useState<any[]>([]);
  const [activePhaseId, setActivePhaseId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();
  const { hasUnsavedChanges, setHasUnsavedChanges } = useUnsavedChanges();
 
 
  const handleTabClick = async (idx: number) => {
    if (activeTab === idx) return;
    if (hasUnsavedChanges) {
      if (await confirmDialog("Você tem alterações não salvas nesta aba. Deseja sair sem salvar?", {
        title: "Sair sem salvar",
        confirmLabel: "Sair sem salvar",
      })) {
        setHasUnsavedChanges(false);
        setActiveTab(idx);
      }
    } else {
      setActiveTab(idx);
    }
  };

  const handlePhaseClick = async (id: number) => {
    if (activePhaseId === id) return;
    if (hasUnsavedChanges) {
      if (await confirmDialog("Você tem alterações não salvas nesta aba. Deseja sair sem salvar?", {
        title: "Sair sem salvar",
        confirmLabel: "Sair sem salvar",
      })) {
        setHasUnsavedChanges(false);
        setActivePhaseId(id);
      }
    } else {
      setActivePhaseId(id);
    }
  };

  const handleBack = async () => {
    if (hasUnsavedChanges) {
      if (await confirmDialog("Você tem alterações não salvas. Deseja sair sem salvar?", {
        title: "Sair sem salvar",
        confirmLabel: "Sair sem salvar",
      })) {
        setHasUnsavedChanges(false);
        router.push("/dashboard/viabilities");
      }
    } else {
      router.push("/dashboard/viabilities");
    }
  };

  const isReadonly = !canWriteModule(user, "Rentabilidade de Produtos");

 useEffect(() => {
 const fetchProjectAndPhases = async () => {
 try {
 const projRes = await api.get(`/viabilities/${id}`);
 setProject(projRes.data);

 const phaseRes = await api.get(`/viabilities/${id}/phases`);
 setPhases(phaseRes.data);
 if (phaseRes.data.length > 0) {
 setActivePhaseId(phaseRes.data[0].id);
 }
 
 try {
   const scenRes = await api.get(`/viabilities/${id}/scenarios`);
   setScenarios(scenRes.data);
 } catch (e) {
   console.error("Erro ao buscar cenários", e);
 }
 } catch (e) {
  console.error(e);
  setError("Não foi possível conectar ao servidor para carregar o projeto. Verifique se a API está no ar.");
  }
  };
  if (id) fetchProjectAndPhases();
 }, [id]);

 const toggleGlobalFlag = async (field: string) => {
 try {
 const newVal = !project[field];
 await api.put(`/viabilities/${id}`, { [field]: newVal });
 setProject({ ...project, [field]: newVal });
 } catch (e) {
 alert("Erro ao salvar configuração.");
 }
 };

 const updateGlobalField = async (field: string, value: any) => {
 try {
 await api.put(`/viabilities/${id}`, { [field]: value });
 setProject({ ...project, [field]: value });
 } catch (e) {
 alert("Erro ao salvar campo global.");
 }
 };

 const updateGlobalFields = async (updates: Record<string, any>) => {
    try {
      await api.put(`/viabilities/${id}`, updates);
      setProject({ ...project, ...updates });
    } catch (e) {
      alert("Erro ao salvar configurações globais.");
    }
  };

 const handleStatusChange = async (newStatus: string) => {
 try {
 await api.put(`/viabilities/${id}/status`, { status: newStatus });
 setProject({ ...project, status: newStatus });
 } catch (e) {
 alert("Erro ao alterar o status do projeto.");
 }
 };

 const isProjectReadonly = project?.status === "Aprovado" || isReadonly;

  const handleGenerateNewScenario = async () => {
    if (hasUnsavedChanges) {
      if (!(await confirmDialog("Você tem alterações não salvas na aba atual que não serão incluídas no novo cenário. Deseja continuar?", {
        title: "Gerar novo cenário",
        confirmLabel: "Continuar",
      }))) {
        return;
      }
    }
    
    const customName = window.prompt("Digite um nome para o novo cenário (ou deixe em branco para o padrão):");
    if (customName === null) return; // User cancelled
    
    try {
      const res = await api.post(`/viabilities/${id}/clone`, { custom_name: customName });
      router.push(`/dashboard/viabilities/${res.data.id}`);
   } catch (e) {
     alert("Erro ao gerar novo cenário.");
   }
 };

  if (error) {
    return (
      <div className="p-8 mt-10 max-w-lg mx-auto bg-red-50 border border-red-200 rounded-xl text-center shadow-sm">
        <h2 className="text-xl font-bold text-red-600 mb-2">Erro de Conexão</h2>
        <p className="text-red-500 mb-6">{error}</p>
        <Button onClick={() => window.location.reload()} className="bg-red-600 hover:bg-red-700 text-white">
          Tentar novamente
        </Button>
      </div>
    );
  }

  if (!project || !activePhaseId) return (
    <AppLoadingState />
  );

  return (
 <div className="space-y-6">
 {/* Header */}
 <div className="flex items-start justify-between border-b border-slate-200 pb-4 print:hidden">
 <div className="flex items-center gap-4">
 <button 
 onClick={handleBack}
 className="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-500"
 >
 <ArrowLeft className="w-5 h-5" />
 </button>
 <div>
 {scenarios.length > 1 ? (
 <div className="flex items-center">
 <select 
 className="text-2xl font-bold tracking-tight text-slate-900 bg-transparent border-none cursor-pointer hover:bg-slate-50 rounded-md focus:ring-0 -ml-2 pl-2 pr-8 py-1 appearance-none outline-none"
 value={id}
 onChange={async (e) => {
 if(hasUnsavedChanges && !(await confirmDialog("Alterações não salvas serão perdidas. Continuar?", {
   title: "Trocar cenário",
   confirmLabel: "Continuar",
 }))) return;
 router.push(`/dashboard/viabilities/${e.target.value}`);
 }}
 >
 {scenarios.map(s => (
 <option key={s.id} value={s.id} className="text-base font-normal">
 {s.project_name} {s.is_root ? "(Cenário Original)" : ""}
 </option>
 ))}
 </select>
 <div className="pointer-events-none -ml-6 text-slate-400">
 <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
 </div>
 </div>
 ) : (
 <h1 className="text-2xl font-bold tracking-tight text-slate-900">{project.project_name}</h1>
 )}
 <div className="flex items-center gap-3 mt-1">
 <span className="text-sm text-slate-500">Status:</span>
 {!isReadonly ? (
   <select
     value={project.status}
     onChange={(e) => handleStatusChange(e.target.value)}
     className={`px-2 py-0.5 rounded-full text-xs font-medium border-0 cursor-pointer outline-none hover:opacity-80 transition-opacity ${
       project.status === 'Aprovado' ? 'bg-green-100 text-green-700' :
       project.status === 'Em Aprovação' ? 'bg-amber-100 text-amber-700' :
       'bg-slate-100 text-slate-700'
     }`}
   >
     <option value="Rascunho">Rascunho</option>
     <option value="Em Andamento">Em Andamento</option>
     <option value="Em Aprovação">Em Aprovação</option>
     <option value="Aprovado">Aprovado</option>
   </select>
 ) : (
   <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
     project.status === 'Aprovado' ? 'bg-green-100 text-green-700' :
     project.status === 'Em Aprovação' ? 'bg-amber-100 text-amber-700' :
     'bg-slate-100 text-slate-700'
   }`}>
     {project.status}
   </span>
 )}
 {project.version_of_id && (
 <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-brand-green/10 text-brand-dark-green">
 Nova Versão
 </span>
 )}
 </div>
 <div className="mt-2">
   <ObraAcompanhamentoField
     value={project.obra_cost_center_id}
     readonly={isReadonly}
     onChange={(id) => {
       setProject({ ...project, obra_cost_center_id: id });
       updateGlobalField("obra_cost_center_id", id);
     }}
   />
 </div>
 </div>
 </div>
 
 {/* Controles de Workflow & Parâmetros */}
 <div className="flex gap-4 items-center">
  {!isReadonly && (
    <>
      <Button onClick={handleGenerateNewScenario} variant="outline" size="sm" className="gap-2 border-ml-green text-ml-dark hover:bg-ml-green/10">
        <Copy className="w-4 h-4" /> Gerar Novo Cenário
      </Button>
      {project.version_of_id && (
        <Button 
          onClick={async () => {
            if (await confirmDialog("Tem certeza que deseja excluir este cenário? Esta ação não pode ser desfeita.", { variant: "danger" })) {
              try {
                await api.delete(`/viabilities/${id}`);
                router.push(`/dashboard/viabilities/${project.version_of_id}`);
              } catch (e) {
                alert("Erro ao excluir cenário.");
              }
            }
          }} 
          variant="outline" 
          size="sm" 
          className="gap-2 text-red-600 border-red-200 hover:bg-red-50"
        >
          <Trash2 className="w-4 h-4" /> Excluir Cenário
        </Button>
      )}
    </>
  )}
 {project.status === "Rascunho" && (
 <Button onClick={() => handleStatusChange("Em Andamento")} size="sm" className="bg-blue-600 hover:bg-blue-700 text-white gap-2">
 <Clock className="w-4 h-4" /> Iniciar Análise
 </Button>
 )}
 {project.status === "Em Andamento" && (
 <Button onClick={() => handleStatusChange("Em Aprovação")} size="sm" className="bg-amber-500 hover:bg-amber-600 text-white gap-2">
 <Clock className="w-4 h-4" /> Solicitar Aprovação
 </Button>
 )}
 {project.status === "Em Aprovação" && (
 <>
 <Button onClick={() => handleStatusChange("Em Andamento")} variant="outline" size="sm" className="gap-2">
 <RotateCcw className="w-4 h-4" /> Retornar
 </Button>
 <Button onClick={() => handleStatusChange("Aprovado")} size="sm" className="bg-green-600 hover:bg-green-700 text-white gap-2">
 <CheckCircle className="w-4 h-4" /> Aprovar Projeto
 </Button>
 </>
 )}
 {project.status === "Aprovado" && (
 <Button onClick={() => handleStatusChange("Em Andamento")} variant="outline" size="sm" className="gap-2 text-red-600 border-red-200 hover:bg-red-50">
 <RotateCcw className="w-4 h-4" /> Reabrir Projeto
 </Button>
 )}

 <label className="flex items-center gap-2 text-sm cursor-pointer">
 <input 
 type="checkbox" 
 checked={project.tem_multiplas_fases} 
 onChange={() => !isReadonly && toggleGlobalFlag("tem_multiplas_fases")}
 disabled={isReadonly}
 className="w-4 h-4 rounded text-ml-green focus:ring-ml-green border-slate-300"
 />
 <span className="font-medium text-slate-700">Tem Múltiplas Fases?</span>
 </label>

 <div className="w-px h-8 bg-slate-200 mx-2"></div>

 <div className="flex items-center gap-2">
 <span className="text-sm font-medium text-slate-700">Taxa VPL/AVP (% a.a.):</span>
 <input 
 type="number"
 value={project.taxa_desconto_vpl || 12}
 onChange={(e) => !isReadonly && setProject({...project, taxa_desconto_vpl: parseFloat(e.target.value) || 12})}
 onBlur={(e) => !isReadonly && updateGlobalField("taxa_desconto_vpl", parseFloat(e.target.value) || 12)}
 disabled={isReadonly}
 className="w-20 px-2 py-1 text-sm border rounded bg-white text-slate-900 border-slate-300 focus:outline-none focus:ring-1 focus:ring-ml-green"
 step="0.1"
 />
 </div>
 </div>
 </div>

 {/* Seletor de Fases (se ativado) */}
 {project.tem_multiplas_fases && (
 <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200 print:hidden">
 <span className="text-sm font-semibold text-slate-700 ml-2">Fase Atual:</span>
 {phases.map(p => (
 <Button 
 key={p.id}
 variant={p.id === activePhaseId ?"primary" :"secondary"}
 size="sm"
 onClick={() => handlePhaseClick(p.id)}
 >
 {p.name}
 </Button>
 ))}
 <Button variant="ghost" size="sm" className="ml-auto">
 <Plus className="w-4 h-4 mr-1" /> Adicionar Fase
 </Button>
 </div>
 )}

 {/* Tabs Navigation */}
 <div className="flex overflow-x-auto border-b border-slate-200 hide-scrollbar print:hidden">
 {TABS.map((tab, idx) => (
 <button
 key={tab}
 onClick={() => handleTabClick(idx)}
 className={`whitespace-nowrap px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
 activeTab === idx 
 ?"border-ml-green text-ml-green" 
 :"border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
 }`}
 >
 {tab}
 </button>
 ))}
 </div>

 {/* Tab Content Area */}
 <div className="bg-white rounded-xl shadow-sm border border-slate-100 min-h-[500px] print:border-none print:shadow-none print:min-h-0 print:bg-transparent">
 {TABS[activeTab] === "Dados Físicos" && <PhysicalDataTab 
          phaseId={activePhaseId} 
          isReadonly={isReadonly}
          projectId={project.id}
          initialProjectName={project.project_name}
          initialCity={project.city}
          onProjectUpdate={(data) => setProject({ ...project, ...data })}
        />}
 {TABS[activeTab] === "Datas" && <DatesTab phaseId={activePhaseId} isReadonly={isReadonly} />}
 {TABS[activeTab] === "Permutas" && <ExchangesTab phaseId={activePhaseId} isReadonly={isProjectReadonly} />}
 {TABS[activeTab] === "Receitas" && <RevenueTab phaseId={activePhaseId} project={project} onUpdateProject={updateGlobalFields} isReadonly={isReadonly} />}
 {TABS[activeTab] === "Obras" && <ConstructionTab phaseId={activePhaseId} project={project} onUpdateProject={updateGlobalFields} isReadonly={isReadonly} />}
 {TABS[activeTab] === "Despesas" && <ExpensesTab phaseId={activePhaseId} project={project} onUpdateProject={updateGlobalFields} isReadonly={isReadonly} />}
 {TABS[activeTab] === "Curvas" && <CurvesConfig phaseId={activePhaseId} isReadonly={isReadonly} />}
 {TABS[activeTab] === "Impostos" && <TaxesTab phaseId={activePhaseId} isReadonly={isReadonly} />}
 {TABS[activeTab] === "Funding" && <FundingTab phaseId={activePhaseId} isReadonly={isReadonly} />}
 {TABS[activeTab] === "Documentos" && <DocumentsTab phaseId={activePhaseId} />}
 {TABS[activeTab] === "Parecer Executivo" && <ExecutiveSummaryTab 
      viabilityId={Number(id)} 
      parecerExecutivo={project?.parecer_executivo} 
      parecerOriginalIa={project?.parecer_original_ia}
      onChange={(val) => setProject({ ...project, parecer_executivo: val })} 
      onSave={async (val) => await updateGlobalField("parecer_executivo", val)}
    />}
 {TABS[activeTab] === "Resumo" && <SummaryTab phaseId={activePhaseId} userRole={user?.role} project={project} />}
 {TABS[activeTab] === "Comparativo" && <ComparisonTab viabilityId={Number(id)} />}
 </div>
 </div>
 );
}
