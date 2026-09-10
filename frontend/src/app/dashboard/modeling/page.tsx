"use client";
import { Card } from"@/components/ui/Card";
import { UploadCloud, FileSpreadsheet } from"lucide-react";

export default function ModelingPage() {
 return (
 <div className="space-y-6 animate-in fade-in duration-300">
 <div>
 <h1 className="text-3xl font-bold tracking-tight text-slate-900">Modelagem Avançada</h1>
 <p className="text-slate-500 mt-1">Importação e integração com a Modelagem Mestre.</p>
 </div>

 <div className="grid md:grid-cols-2 gap-6">
 <Card className="p-8 border-dashed border-2 border-slate-200 bg-slate-50/50 flex flex-col items-center justify-center text-center space-y-4 hover:bg-slate-50 transition-colors cursor-pointer">
 <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center">
 <UploadCloud className="w-8 h-8" />
 </div>
 <div>
 <h3 className="text-lg font-bold text-slate-900">Fazer Upload</h3>
 <p className="text-sm text-slate-500 max-w-xs mt-1">Faça o upload da sua planilha de Modelagem Mestre para extrair as premissas avançadas.</p>
 </div>
 </Card>

 <Card className="p-8 border-0 shadow-sm flex flex-col justify-center space-y-4">
 <div className="flex items-center gap-3">
 <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">
 <FileSpreadsheet className="w-6 h-6" />
 </div>
 <div>
 <h3 className="font-bold text-slate-900">Módulo em Construção</h3>
 <p className="text-sm text-slate-500">Este módulo processará cálculos complexos isolados.</p>
 </div>
 </div>
 <div className="bg-slate-100 p-4 rounded-lg text-sm text-slate-600">
 A integração com o Motor de Viabilidade ocorrerá extraindo as curvas e premissas finais, mantendo a performance da aplicação principal intacta.
 </div>
 </Card>
 </div>
 </div>
 );
}
