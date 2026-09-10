"use client";

import { useState, useEffect, useMemo, useRef } from"react";
import { api } from"@/lib/api";
import { Plus, Edit2, Trash2, Save, X, Settings2, Download, Upload, AlertCircle } from"lucide-react";
import { Button } from"@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import * as XLSX from 'xlsx';

interface StandardCurve {
 id: number;
 nome: string;
 tipo: string;
 classificacao: string;
 valores_meses_json: { meses: number[] } | any;
}

export default function CurvasPage() {
 const [curves, setCurves] = useState<StandardCurve[]>([]);
 const [loading, setLoading] = useState(true);
 const [editingId, setEditingId] = useState<number | null>(null);
 const [formData, setFormData] = useState<Partial<StandardCurve>>({});
 const [activeTab, setActiveTab] = useState<string>("");
 
 // Para o modal de Geração Automática
 const [showGenerateModal, setShowGenerateModal] = useState(false);
 const [generateData, setGenerateData] = useState({
 tipo:"obras",
 modelo:"s-curve",
 meses: 36
 });

 // Ref para o input de importação de arquivo
 const fileInputRef = useRef<HTMLInputElement>(null);

 useEffect(() => {
 loadCurves();
 }, []);

 const loadCurves = async () => {
 try {
 setLoading(true);
 const res = await api.get("/curves/");
 setCurves(res.data);
 } catch (e) {
 console.error(e);
 alert("Erro ao carregar curvas.");
 } finally {
 setLoading(false);
 }
 };

 const handleGenerateSubmit = async () => {
 try {
 await api.post("/curves/generate-defaults", generateData);
 await loadCurves();
 setShowGenerateModal(false);
 alert("Curva padrão gerada com sucesso!");
 } catch (e: any) {
 alert(e.response?.data?.detail ||"Erro ao gerar curva.");
 }
 };

 const handleCreateNew = () => {
 setEditingId(0); // 0 means new
 const defaultTipo = activeTab ||"vendas";
 setFormData({ nome:"", tipo: defaultTipo, classificacao:"Custo", valores_meses_json: { meses: ["10.00","20.00","30.00","40.00"] } });
 };

 const handleEdit = (c: StandardCurve) => {
 setEditingId(c.id);
 const formattedMeses = (c.valores_meses_json?.meses || []).map((v: any) => Number(v).toFixed(2));
 setFormData({ ...c, valores_meses_json: { meses: formattedMeses } });
 };

 const handleCancel = () => {
 setEditingId(null);
 setFormData({});
 };

 const handleSave = async () => {
 try {
 const payload = { ...formData };
 
 let sum = 0;
 if (payload.valores_meses_json && Array.isArray(payload.valores_meses_json.meses)) {
 payload.valores_meses_json.meses = payload.valores_meses_json.meses.map((v: any) => {
 const val = parseFloat(v) || 0;
 sum += val;
 return val;
 });
 }

 // Validação de 100%
 if (Math.abs(sum - 100) > 0.01) {
 alert(`Atenção: A soma dos percentuais deve ser exatamente 100%. Atualmente a soma é ${sum.toFixed(2)}%. Por favor, ajuste os valores.`);
 return;
 }

 if (editingId === 0) {
 await api.post("/curves/", payload);
 } else {
 await api.put(`/curves/${editingId}`, payload);
 }
 setEditingId(null);
 await loadCurves();
 } catch (e: any) {
 alert(e.response?.data?.detail ||"Erro ao salvar curva.");
 }
 };

 const handleDelete = async (id: number) => {
 if (!(await confirmDialog("Deseja realmente excluir esta curva? Ela pode estar em uso.", { variant: "danger" }))) return;
 try {
 await api.delete(`/curves/${id}`);
 await loadCurves();
 } catch (e: any) {
 alert(e.response?.data?.detail ||"Erro ao excluir curva.");
 }
 };

 // Pega os tipos únicos cadastrados
 const uniqueTypes = useMemo(() => {
 const dbTypes = curves.map(c => c.tipo.toLowerCase());
 const allTypes = Array.from(new Set(dbTypes));
 
 return allTypes.sort((a, b) => {
 if (a === 'vendas') return -1;
 if (b === 'vendas') return 1;
 if (a === 'obras') return -1;
 if (b === 'obras') return 1;
 return a.localeCompare(b);
 });
 }, [curves]);

 useEffect(() => {
 if (uniqueTypes.length > 0 && !activeTab) {
 setActiveTab(uniqueTypes[0]);
 }
 }, [uniqueTypes, activeTab]);

 if (loading) return <AppLoadingState />;

 const currentSum = Array.isArray(formData.valores_meses_json?.meses) 
 ? formData.valores_meses_json.meses.reduce((acc: number, val: any) => acc + (parseFloat(val) || 0), 0) 
 : 0;

 const formatName = (str: string) => {
 const lowercaseWords = ['e', 'de', 'da', 'do', 'das', 'dos'];
 return str.toLowerCase().split(' ').map((word, idx) => {
 if (idx > 0 && lowercaseWords.includes(word)) return word;
 return word.charAt(0).toUpperCase() + word.slice(1);
 }).join(' ');
 };

 return (
 <div className="p-8 space-y-6">
 <div className="flex justify-between items-center mb-6">
 <div>
 <h1 className="text-2xl font-bold text-slate-800">Gestão de Curvas</h1>
 <p className="text-slate-500">Cadastre e gerencie as curvas físico-financeiras para orçamentos e cronogramas.</p>
 </div>
 <div className="space-x-3">
 <Button variant="outline" onClick={() => setShowGenerateModal(true)}>
 <Settings2 className="w-4 h-4 mr-2" /> Gerador Padrão (Sistema)
 </Button>
 <Button onClick={handleCreateNew}>
 <Plus className="w-4 h-4 mr-2" /> Nova Curva
 </Button>
 </div>
 </div>

 {/* Tabs Navigation */}
 <div className="flex overflow-x-auto border-b border-slate-200 hide-scrollbar mb-6">
 {uniqueTypes.map(tipo => (
 <button
 key={tipo}
 onClick={() => setActiveTab(tipo)}
 className={`whitespace-nowrap px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
 activeTab === tipo
 ?"border-blue-600 text-blue-600" 
 :"border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
 }`}
 >
 {formatName(tipo)}
 </button>
 ))}
 </div>

 <div className="space-y-8">
 {uniqueTypes.filter(t => t === activeTab).map(tipo => {
 const typeCurves = curves.filter(c => c.tipo.toLowerCase() === tipo);
 
 return (
 <div key={tipo} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
 <div className="p-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
 <h2 className="font-semibold text-slate-800">Curvas de {formatName(tipo)}</h2>
 <span className="text-xs font-medium text-slate-500 bg-slate-200 px-2 py-1 rounded-full">
 {typeCurves.length}
 </span>
 </div>
 <table className="w-full text-left border-collapse">
 <thead>
 <tr className="bg-white text-slate-600 border-b text-sm">
 <th className="p-4 font-medium">Nome</th>
 <th className="p-4 font-medium">Classificação</th>
 <th className="p-4 font-medium text-center">Nº de Meses</th>
 <th className="p-4 font-medium text-right">Ações</th>
 </tr>
 </thead>
 <tbody className="divide-y divide-slate-100">
 {typeCurves.map(c => (
 <tr key={c.id} className="hover:bg-slate-50 transition-colors bg-white">
 <td className="p-4 font-medium text-slate-800">{c.nome}</td>
 <td className="p-4">
 <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${c.classificacao === 'Custo' ? 'bg-orange-100 text-orange-800' : c.classificacao === 'Receita' ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'}`}>
 {c.classificacao || 'Custo'}
 </span>
 </td>
 <td className="p-4 text-center text-slate-600">
 {Array.isArray(c.valores_meses_json) ? c.valores_meses_json.length : (c.valores_meses_json?.meses?.length || 0)}
 </td>
 <td className="p-4 text-right">
 <div className="flex justify-end gap-2">
 <button onClick={() => handleEdit(c)} className="p-2 text-slate-400 hover:text-blue-600 transition-colors">
 <Edit2 className="w-4 h-4" />
 </button>
 <button onClick={() => handleDelete(c.id)} className="p-2 text-slate-400 hover:text-red-600 transition-colors">
 <Trash2 className="w-4 h-4" />
 </button>
 </div>
 </td>
 </tr>
 ))}
 {typeCurves.length === 0 && (
 <tr className="bg-white">
 <td colSpan={4} className="p-8 text-center text-slate-500">Nenhuma curva cadastrada nesta categoria.</td>
 </tr>
 )}
 </tbody>
 </table>
 <div className="p-4 bg-slate-50 border-t border-slate-200">
 <Button 
 variant="outline" 
 className="w-full border-dashed text-slate-500 hover:text-slate-800 hover:bg-slate-100" 
 onClick={handleCreateNew}
 >
 <Plus className="w-4 h-4 mr-2" /> Adicionar nova curva de {formatName(tipo)}
 </Button>
 </div>
 </div>
 );
 })}
 </div>

 {/* Modal de Nova/Editar Curva */}
 {editingId !== null && (
 <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
 <div className="bg-white rounded-xl shadow-2xl w-full max-h-[90vh] flex flex-col">
 <div className="p-6 border-b flex justify-between items-center shrink-0">
 <h2 className="text-xl font-bold">{editingId === 0 ?"Nova Curva" :"Editar Curva"}</h2>
 <button onClick={handleCancel} className="text-slate-400 hover:text-slate-600">
 <X className="w-6 h-6" />
 </button>
 </div>
 
 <div className="p-6 overflow-y-auto space-y-6">
 <div className="grid md:grid-cols-3 gap-4">
 <div>
 <label className="block text-sm font-medium text-slate-700 mb-1">Nome</label>
 <input
 type="text"
 value={formData.nome ||""}
 onChange={e => setFormData({ ...formData, nome: e.target.value })}
 className="ml-input"
 placeholder="Ex: Curva Padrão S-Curve 36m"
 />
 </div>
 <div>
 <label className="block text-sm font-medium text-slate-700 mb-1">Tipo da Curva (Categoria)</label>
 <input
 type="text"
 list="curve-types"
 value={formData.tipo ||""}
 onChange={e => setFormData({ ...formData, tipo: e.target.value })}
 className="ml-input"
 placeholder="Digite ou selecione o tipo"
 />
 <datalist id="curve-types">
 {uniqueTypes.map(t => <option key={t} value={t} />)}
 </datalist>
 </div>
 <div>
 <label className="block text-sm font-medium text-slate-700 mb-1">Classificação Financeira</label>
 <div className="flex gap-4 mt-2">
 <label className="flex items-center gap-2 cursor-pointer">
 <input 
 type="radio" 
 name="classificacao" 
 value="Custo" 
 checked={formData.classificacao === 'Custo'}
 onChange={(e) => setFormData({ ...formData, classificacao: e.target.value })}
 className="text-brand-green focus:ring-brand-green"
 />
 <span className="text-sm text-slate-700">Custo</span>
 </label>
 <label className="flex items-center gap-2 cursor-pointer">
 <input 
 type="radio" 
 name="classificacao" 
 value="Despesa" 
 checked={formData.classificacao === 'Despesa'}
 onChange={(e) => setFormData({ ...formData, classificacao: e.target.value })}
 className="text-brand-green focus:ring-brand-green"
 />
 <span className="text-sm text-slate-700">Despesa</span>
 </label>
 <label className="flex items-center gap-2 cursor-pointer">
 <input 
 type="radio" 
 name="classificacao" 
 value="Receita" 
 checked={formData.classificacao === 'Receita'}
 onChange={(e) => setFormData({ ...formData, classificacao: e.target.value })}
 className="text-brand-green focus:ring-brand-green"
 />
 <span className="text-sm text-slate-700">Receita</span>
 </label>
 </div>
 </div>
 </div>
 
 <div>
 <div className="flex justify-between items-end mb-2">
 <div>
 <label className="block text-sm font-medium text-slate-700">Valores dos Meses (%)</label>
 <p className="text-xs text-slate-500">Configure o avanço para cada mês. A soma total deve ser exatamente 100%.</p>
 </div>
 <div className={`text-sm font-bold px-3 py-1 rounded-md ${Math.abs(currentSum - 100) < 0.01 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
 Soma: {currentSum.toFixed(2)}%
 </div>
 </div>
 
 {Math.abs(currentSum - 100) >= 0.01 && (
 <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 p-3 rounded-lg border border-red-100 mb-4 mt-2">
 <AlertCircle className="w-4 h-4 shrink-0" />
 <span>Para que o resultado do Estudo reflita corretamente os parâmetros, certifique-se de que a soma dos percentuais listados seja exatamente 100%.</span>
 </div>
 )}

 <div className="grid grid-cols-4 sm:grid-cols-6 lg:grid-cols-10 gap-2 mt-4">
 {Array.isArray(formData.valores_meses_json?.meses) && formData.valores_meses_json.meses.map((val: number, idx: number) => (
 <div key={idx} className="flex flex-col relative group">
 <span className="text-[10px] text-slate-400 text-center mb-1 font-medium">Mês {idx + 1}</span>
 <input
 type="number"
 step="0.01"
 value={val}
 onChange={e => {
 const newMeses = [...formData.valores_meses_json.meses];
 newMeses[idx] = e.target.value;
 setFormData({ ...formData, valores_meses_json: { meses: newMeses } });
 }}
 onBlur={e => {
 const newMeses = [...formData.valores_meses_json.meses];
 const parsed = parseFloat(e.target.value) || 0;
 newMeses[idx] = parsed.toFixed(2);
 setFormData({ ...formData, valores_meses_json: { meses: newMeses } });
 }}
 className="px-1 py-1.5 border-[1.5px] border-slate-300 rounded text-xs w-full text-center bg-white text-slate-800 focus:border-brand-orange focus:shadow-[0_0_0_3px_rgba(245,136,58,0.15)] outline-none transition-all"
 />
 <button 
 onClick={() => {
 const newMeses = formData.valores_meses_json.meses.filter((_: any, i: number) => i !== idx);
 setFormData({ ...formData, valores_meses_json: { meses: newMeses }});
 }}
 className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-4 h-4 text-[10px] items-center justify-center hidden group-hover:flex shadow-sm hover:bg-red-600"
 title="Remover mês"
 >
 ×
 </button>
 </div>
 ))}
 <button
 onClick={() => {
 const current = Array.isArray(formData.valores_meses_json?.meses) ? formData.valores_meses_json.meses : [];
 setFormData({ ...formData, valores_meses_json: { meses: [...current,"0.00"] } });
 }}
 className="flex flex-col items-center justify-center border-[1.5px] border-dashed border-slate-300 rounded text-slate-500 hover:text-brand-orange hover:border-brand-orange hover:bg-orange-50 transition-colors py-1.5 h-[52px] mt-4"
 >
 <Plus className="w-4 h-4 mb-0.5" />
 <span className="text-[10px] font-medium">Add Mês</span>
 </button>
 </div>
 </div>
 </div>

 {/* Botões de Importação/Exportação Excel */}
 <div className="px-6 pb-4 flex items-center gap-3 border-t border-slate-100 pt-4">
 <Button
 variant="outline"
 onClick={() => {
 const numMeses = formData.valores_meses_json?.meses?.length || 12;
 const wsData: (string | number)[][] = [["Mês","Percentual (%)"]];
 for (let i = 1; i <= numMeses; i++) {
 wsData.push([i, 0]);
 }
 const ws = XLSX.utils.aoa_to_sheet(wsData);
 ws['!cols'] = [{ wch: 8 }, { wch: 16 }];
 const wb = XLSX.utils.book_new();
 XLSX.utils.book_append_sheet(wb, ws,"Modelo");
 XLSX.writeFile(wb, `modelo_curva_${formData.tipo || 'padrao'}.xlsx`);
 }}
 className="text-sm"
 >
 <Download className="w-4 h-4 mr-2" />
 Baixar Modelo (Excel)
 </Button>
 <Button
 variant="outline"
 onClick={() => fileInputRef.current?.click()}
 className="text-sm"
 >
 <Upload className="w-4 h-4 mr-2" />
 Importar Planilha
 </Button>
 <input
 ref={fileInputRef}
 type="file"
 accept=".xlsx,.xls,.csv"
 className="hidden"
 onChange={(e) => {
 const file = e.target.files?.[0];
 if (!file) return;
 const reader = new FileReader();
 reader.onload = (evt) => {
 try {
 const data = new Uint8Array(evt.target?.result as ArrayBuffer);
 const workbook = XLSX.read(data, { type: 'array' });
 const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
 const rows: any[][] = XLSX.utils.sheet_to_json(firstSheet, { header: 1 });
 
 // Pular o header
 const dataRows = rows.slice(1).filter(r => r.length >= 2);
 let meses = dataRows.map(r => {
   let raw = r[1];
   if (typeof raw === 'string') {
     raw = raw.replace('%', '');
   }
   return parseFloat(String(raw).replace(',', '.')) || 0;
 });
 
 let sum = meses.reduce((a, b) => a + b, 0);
 
 // Se a soma for próxima a 1 (0.9 a 1.1), significa que o Excel exportou no formato decimal de porcentagem
 if (sum > 0.5 && sum <= 1.05) {
   meses = meses.map(m => m * 100);
   sum = meses.reduce((a, b) => a + b, 0);
 }

 // Arredonda para 2 casas
 meses = meses.map(m => parseFloat(m.toFixed(2)));
 sum = meses.reduce((a, b) => a + b, 0);
 
 if (Math.abs(sum - 100) > 0.05) {
 alert(`⚠️ A soma dos percentuais importados é ${sum.toFixed(2)}%.\n\nA soma deve ser exatamente 100%. Por favor, corrija a planilha e importe novamente.`);
 return;
 }
 
 setFormData({
 ...formData,
 valores_meses_json: { meses: meses.map(v => v.toFixed(2)) }
 });
 
 alert(`✅ ${meses.length} meses importados com sucesso! Soma: ${sum.toFixed(2)}%`);
 } catch (err) {
 alert("Erro ao ler a planilha. Verifique o formato do arquivo.");
 console.error(err);
 }
 };
 reader.readAsArrayBuffer(file);
 e.target.value = '';
 }}
 />
 <span className="text-xs text-slate-400 ml-auto">Formatos: .xlsx, .xls, .csv</span>
 </div>

 <div className="p-6 border-t bg-slate-50 flex justify-end gap-3 shrink-0 rounded-b-xl">
 <Button variant="outline" onClick={handleCancel}>Cancelar</Button>
 <Button onClick={handleSave}>
 <Save className="w-4 h-4 mr-2" /> Salvar Curva
 </Button>
 </div>
 </div>
 </div>
 )}

 {/* Modal do Gerador */}
 {showGenerateModal && (
 <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
 <div className="bg-white rounded-xl shadow-2xl w-full max-w-md flex flex-col">
 <div className="p-6 border-b flex justify-between items-center">
 <h2 className="text-xl font-bold">Gerador de Curvas Padrão</h2>
 <button onClick={() => setShowGenerateModal(false)} className="text-slate-400 hover:text-slate-600">
 <X className="w-6 h-6" />
 </button>
 </div>
 <div className="p-6 space-y-4">
 <div>
 <label className="block text-sm font-medium text-slate-700 mb-1">Categoria (Tipo)</label>
 <input
 type="text"
 list="curve-types"
 value={generateData.tipo}
 onChange={e => setGenerateData({ ...generateData, tipo: e.target.value })}
 className="ml-input"
 placeholder="Ex: obras, projetos, marketing"
 />
 </div>
 <div>
 <label className="block text-sm font-medium text-slate-700 mb-1">Modelo Matemático</label>
 <select
 value={generateData.modelo}
 onChange={e => setGenerateData({ ...generateData, modelo: e.target.value })}
 className="ml-select"
 >
 <option value="s-curve">Curva S (Obras / Evolução)</option>
 <option value="sino">Curva de Sino (Lançamentos / Vendas)</option>
 <option value="linear">Distribuição Linear (Igual por mês)</option>
 </select>
 </div>
 <div>
 <label className="block text-sm font-medium text-slate-700 mb-1">Período (Meses)</label>
 <input
 type="number"
 min="1"
 max="120"
 value={generateData.meses}
 onChange={e => setGenerateData({ ...generateData, meses: parseInt(e.target.value) || 1 })}
 className="ml-input"
 />
 </div>
 </div>
 <div className="p-6 border-t bg-slate-50 flex justify-end gap-3 rounded-b-xl">
 <Button variant="outline" onClick={() => setShowGenerateModal(false)}>Cancelar</Button>
 <Button onClick={handleGenerateSubmit}>
 <Settings2 className="w-4 h-4 mr-2" /> Gerar Curva
 </Button>
 </div>
 </div>
 </div>
 )}
 </div>
 );
}

