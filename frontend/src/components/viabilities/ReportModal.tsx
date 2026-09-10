"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { X, Printer, Settings, Plus, Minus, Maximize } from "lucide-react";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

const ViabilityReport = dynamic(
  () => import('./ViabilityReport').then((mod) => mod.ViabilityReport),
  { ssr: false, loading: () => <AppLoadingState /> }
);

interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  project: any;
  physicalData: any;
  datesData: any;
  allColumns: any[];
  exchangesData: any;
}

export function ReportModal({
  isOpen,
  onClose,
  project,
  physicalData,
  datesData,
  allColumns,
  exchangesData
}: ReportModalProps) {
  const [step, setStep] = useState<"config" | "preview">("config");

  // State para as configurações do relatório
  const [viewsToPrint, setViewsToPrint] = useState<string[]>(["Global"]);
  const [cashflowGranularity, setCashflowGranularity] = useState<"month" | "quarter" | "semester" | "year">("year");
  const [includeCashflow, setIncludeCashflow] = useState(true);
  const [includeComparative, setIncludeComparative] = useState(true);
  const [includeSchedule, setIncludeSchedule] = useState(true);
  const [orientation, setOrientation] = useState<"portrait" | "landscape">("portrait");
  const [zoom, setZoom] = useState(100);
  const [fitMode, setFitMode] = useState<"width" | "page">("width");

  // Derivar as visões disponíveis
  const currentDataCol = allColumns.find(c => c.isCurrent) || allColumns[0];
  const sourceData = currentDataCol?.rawData || {};
  const partnerNames = sourceData.indicators_parceiros ? Object.keys(sourceData.indicators_parceiros) : [];
  const availableViews = partnerNames.length > 0 ? ["Global", "Empreendedor", ...partnerNames] : ["Global", "Empreendedor", "Parceiro", "Investidor"];

  const toggleView = (view: string) => {
    setViewsToPrint(prev => 
      prev.includes(view) ? prev.filter(v => v !== view) : [...prev, view]
    );
  };

  const handlePrint = () => {
    window.print();
  };

  const toggleFit = () => {
    if (fitMode === "width") {
      // Ajustar à página (Altura) - Diminui para caber na tela
      const pageHeight = orientation === "landscape" ? 794 : 1122;
      const availableHeight = window.innerHeight - 120; // Espaço do header e margens
      const newZoom = Math.floor((availableHeight / pageHeight) * 100);
      setZoom(Math.min(Math.max(newZoom, 20), 200)); 
      setFitMode("page");
    } else {
      // Voltar para o tamanho original (100%)
      setZoom(100);
      setFitMode("width");
    }
  };

  if (!isOpen) return null;

  // Renderização em Tela Cheia para o Preview
  if (step === "preview") {
    return (
      <div className="fixed inset-0 z-50 bg-slate-100 flex flex-col h-screen w-screen overflow-hidden print:absolute print:h-auto print:overflow-visible print:bg-white">
        {/* Barra de Ações Fixa (Não é impressa) */}
        <div className="bg-ml-dark text-white p-4 flex justify-between items-center shadow-md print:hidden shrink-0">
          <div className="flex items-center gap-4">
             <button onClick={() => setStep("config")} className="flex items-center gap-2 text-white/80 hover:text-white font-medium transition-colors">
               &larr; Voltar às Configurações
             </button>
             <h2 className="text-lg font-bold">Pré-visualização do Relatório</h2>
          </div>
          <div className="flex items-center gap-4">
             <div className="flex items-center bg-white/10 rounded-md p-1 mr-2">
               <button onClick={() => setZoom(z => Math.max(z - 10, 50))} className="p-1 hover:bg-white/20 rounded text-white transition-colors" title="Reduzir">
                 <Minus className="w-4 h-4" />
               </button>
               <span className="text-sm font-medium w-12 text-center select-none">{zoom}%</span>
               <button onClick={() => setZoom(z => Math.min(z + 10, 200))} className="p-1 hover:bg-white/20 rounded text-white transition-colors" title="Ampliar">
                 <Plus className="w-4 h-4" />
               </button>
               <div className="w-px h-4 bg-white/20 mx-1"></div>
               <button onClick={toggleFit} className="p-1 hover:bg-white/20 rounded text-white transition-colors" title={fitMode === "width" ? "Ajustar à página" : "Voltar para 100%"}>
                 <Maximize className="w-4 h-4" />
               </button>
             </div>
             <Button onClick={handlePrint} className="bg-ml-green hover:bg-ml-green-light text-white flex items-center gap-2">
               <Printer className="w-4 h-4" /> Imprimir / Salvar PDF
             </Button>
             <Button variant="ghost" onClick={onClose} className="text-slate-300 hover:text-white">
               <X className="w-5 h-5" />
             </Button>
          </div>
        </div>

        {/* Área de rolagem do relatório */}
        <div className="flex-1 overflow-auto p-8 print:p-0 bg-slate-100 print:bg-white print:overflow-visible flex flex-col items-center">
           <div 
             className={`${orientation === "landscape" ? "max-w-[297mm] min-w-[297mm]" : "max-w-[210mm] min-w-[210mm]"} mx-auto bg-white shadow-xl print:shadow-none print:w-full print:max-w-full print:min-w-0 print:mx-0 origin-top transition-transform duration-200 print:transition-none`}
             style={{ transform: `scale(${zoom / 100})`, marginBottom: `${Math.max(0, (zoom - 100) * 2)}px` }}
           >
             <style dangerouslySetInnerHTML={{__html: `
                @media print {
                  body { visibility: hidden; }
                  #report-root-container, #report-root-container * { visibility: visible; }
                  #report-root-container { position: absolute; left: 0; top: 0; width: 100%; box-sizing: border-box; padding: 0 10px; }
                }
             `}} />
             <div id="report-root-container">
               <ViabilityReport
                 project={project}
                 physicalData={physicalData}
                 datesData={datesData}
                 allColumns={allColumns}
                 viewsToPrint={viewsToPrint.length > 0 ? viewsToPrint : ["Global"]}
                 cashflowGranularity={cashflowGranularity}
                 includeCashflow={includeCashflow}
                 includeComparative={includeComparative}
                 includeSchedule={includeSchedule}
                 exchangesData={exchangesData}
                 orientation={orientation}
               />
             </div>
           </div>
        </div>
      </div>
    );
  }

  // Renderização do Modal de Configuração
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Configurar Relatório de Viabilidade" size="lg">
      <div className="space-y-6">
        
        {/* Perspectivas */}
        <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
           <h3 className="font-bold text-slate-800 mb-3 text-sm uppercase tracking-wide">Perspectivas a Incluir</h3>
           <div className="grid grid-cols-2 gap-3">
             {availableViews.map(view => (
               <label key={view} className="flex items-center gap-3 cursor-pointer p-2 hover:bg-slate-100 rounded">
                 <input 
                   type="checkbox" 
                   checked={viewsToPrint.includes(view)}
                   onChange={() => toggleView(view)}
                   className="w-4 h-4 text-ml-green ml-checkbox"
                 />
                 <span className="text-sm font-medium text-slate-700">{view}</span>
               </label>
             ))}
           </div>
           {viewsToPrint.length === 0 && (
             <p className="text-red-500 text-xs mt-2">Selecione ao menos uma perspectiva para gerar o relatório.</p>
           )}
        </div>

        <div className="grid grid-cols-2 gap-6">
          {/* Opções de Seções */}
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
             <h3 className="font-bold text-slate-800 mb-3 text-sm uppercase tracking-wide">Seções do Relatório</h3>
             <div className="space-y-3">
               <label className="flex items-center gap-3 cursor-pointer">
                 <input type="checkbox" checked disabled className="w-4 h-4 text-slate-400 cursor-not-allowed" />
                 <span className="text-sm text-slate-500">Capa e Ficha Técnica (Obrigatório)</span>
               </label>
               <label className="flex items-center gap-3 cursor-pointer">
                 <input type="checkbox" checked disabled className="w-4 h-4 text-slate-400 cursor-not-allowed" />
                 <span className="text-sm text-slate-500">Indicadores e DRE (Obrigatório)</span>
               </label>
               <label className="flex items-center gap-3 cursor-pointer hover:bg-slate-100 p-1 -ml-1 rounded">
                 <input type="checkbox" checked={includeCashflow} onChange={e => setIncludeCashflow(e.target.checked)} className="w-4 h-4 text-ml-green ml-checkbox" />
                 <span className="text-sm font-medium text-slate-700">Fluxo de Caixa (Gráfico + Tabela)</span>
               </label>
               <label className="flex items-center gap-3 cursor-pointer hover:bg-slate-100 p-1 -ml-1 rounded">
                 <input type="checkbox" checked={includeComparative} onChange={e => setIncludeComparative(e.target.checked)} className="w-4 h-4 text-ml-green ml-checkbox" />
                 <span className="text-sm font-medium text-slate-700">Comparativo de Cenários</span>
               </label>
             </div>
          </div>

          {/* Granularidade e Orientação */}
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
             <h3 className="font-bold text-slate-800 mb-3 text-sm uppercase tracking-wide">Granularidade do Fluxo</h3>
             <div className="space-y-2 mb-6">
               {[
                 { id: "month", label: "Mensal" },
                 { id: "quarter", label: "Trimestral" },
                 { id: "semester", label: "Semestral" },
                 { id: "year", label: "Anual (Recomendado)" }
               ].map(opt => (
                 <label key={opt.id} className="flex items-center gap-3 cursor-pointer hover:bg-slate-100 p-1 rounded">
                   <input 
                     type="radio" 
                     name="granularity"
                     value={opt.id}
                     checked={cashflowGranularity === opt.id}
                     onChange={() => setCashflowGranularity(opt.id as any)}
                     className="w-4 h-4 text-ml-green"
                   />
                   <span className="text-sm font-medium text-slate-700">{opt.label}</span>
                 </label>
               ))}
             </div>

             <h3 className="font-bold text-slate-800 mb-3 text-sm uppercase tracking-wide">Orientação da Página</h3>
             <div className="flex gap-4">
               <label className="flex items-center gap-2 cursor-pointer">
                 <input 
                   type="radio" 
                   name="orientation" 
                   checked={orientation === "portrait"} 
                   onChange={() => setOrientation("portrait")} 
                   className="text-ml-green"
                 />
                 <span className="text-sm">Retrato</span>
               </label>
               <label className="flex items-center gap-2 cursor-pointer">
                 <input 
                   type="radio" 
                   name="orientation" 
                   checked={orientation === "landscape"} 
                   onChange={() => setOrientation("landscape")} 
                   className="text-ml-green"
                 />
                 <span className="text-sm">Paisagem</span>
               </label>
             </div>
          </div>
        </div>

        <div className="flex justify-end gap-4 mt-8 pt-4 border-t">
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button 
            className="bg-ml-dark hover:bg-slate-800 text-white"
            disabled={viewsToPrint.length === 0}
            onClick={() => setStep("preview")}
          >
            Gerar Relatório (Preview)
          </Button>
        </div>
      </div>
    </Modal>
  );
}
