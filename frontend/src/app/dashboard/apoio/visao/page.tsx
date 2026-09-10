"use client";

import React, { useState, useEffect } from"react";
import { useRouter } from"next/navigation";
import { Eye, Plus, Edit2, Trash2, Copy, Star, LayoutGrid, ArrowRight } from"lucide-react";
import { Button } from"@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { apoioService } from"@/services/apoio";

interface Visao {
 id: number;
 nome: string;
 descricao: string | null;
 is_padrao: boolean;
 criado_em: string | null;
 total_categorias: number;
 total_planos: number;
}

export default function VisoesPage() {
 const router = useRouter();
 const [visoes, setVisoes] = useState<Visao[]>([]);
 const [isLoading, setIsLoading] = useState(true);
 const [isModalOpen, setIsModalOpen] = useState(false);
 const [formData, setFormData] = useState({ nome:"", descricao:"", copiar_de_id: null as number | null });
 const [createMode, setCreateMode] = useState<"vazia" |"copia">("vazia");

 const fetchVisoes = async () => {
 setIsLoading(true);
 const data = await apoioService.listVisoes();
 setVisoes(data);
 setIsLoading(false);
 };

 useEffect(() => { fetchVisoes(); }, []);

 const handleCreate = async () => {
 if (!formData.nome.trim()) return;
 try {
 const payload = {
 nome: formData.nome,
 descricao: formData.descricao || undefined,
 copiar_de_id: createMode ==="copia" ? formData.copiar_de_id : null
 };
 const created = await apoioService.createVisao(payload);
 setIsModalOpen(false);
 setFormData({ nome:"", descricao:"", copiar_de_id: null });
 // Navegar direto para o editor da nova visão
 router.push(`/dashboard/apoio/visao/${created.id}`);
 } catch (e) {
 alert("Erro ao criar visão.");
 }
 };

 const handleDelete = async (id: number) => {
 if (await confirmDialog("Tem certeza que deseja excluir esta visão? Todos os mapeamentos dela serão perdidos.", { variant: "danger" })) {
 try {
 await apoioService.deleteVisao(id);
 fetchVisoes();
 } catch (e: any) {
 alert(e?.response?.data?.detail ||"Erro ao excluir visão.");
 }
 }
 };

 const formatDate = (iso: string | null) => {
 if (!iso) return"-";
 return new Date(iso).toLocaleDateString("pt-BR");
 };

 return (
 <div className="space-y-6">
 {/* Header */}
 <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
 <div>
 <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
 <Eye className="w-6 h-6 text-ml-green" />
 Gestão de Visões
 </h1>
 <p className="text-slate-500 mt-1">
 Crie e gerencie diferentes cenários de estrutura DRE.
 </p>
 </div>
 <Button onClick={() => setIsModalOpen(true)}>
 <Plus className="w-4 h-4 mr-2" />
 Nova Visão
 </Button>
 </div>

 {/* Cards de Visões */}
 {isLoading ? (
 <AppLoadingState />
 ) : (
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {visoes.map(visao => (
 <div
 key={visao.id}
 className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5 group flex flex-col"
 >
 <div className="p-5 flex-1">
 <div className="flex items-start justify-between mb-3">
 <div className="flex items-center gap-2">
 {/* Badge removido conforme solicitação */}
 </div>
 <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
 {!visao.is_padrao && (
 <button
 onClick={() => handleDelete(visao.id)}
 className="p-1.5 text-slate-400 hover:text-red-600 rounded hover:bg-red-50 transition-colors"
 title="Excluir visão"
 >
 <Trash2 className="w-3.5 h-3.5" />
 </button>
 )}
 </div>
 </div>

 <h3 className="font-bold text-slate-800 text-lg leading-tight">{visao.nome}</h3>
 {visao.descricao && (
 <p className="text-sm text-slate-500 mt-1 line-clamp-2">{visao.descricao}</p>
 )}

 <div className="flex items-center gap-4 mt-4">
 <div className="text-center">
 <p className="text-xl font-bold text-slate-700">{visao.total_categorias}</p>
 <p className="text-xs text-slate-400">categorias</p>
 </div>
 <div className="w-px h-8 bg-slate-100" />
 <div className="text-center">
 <p className="text-xl font-bold text-slate-700">{visao.total_planos}</p>
 <p className="text-xs text-slate-400">planos mapeados</p>
 </div>
 <div className="w-px h-8 bg-slate-100" />
 <div className="text-center">
 <p className="text-xs text-slate-500">{formatDate(visao.criado_em)}</p>
 <p className="text-xs text-slate-400">criado em</p>
 </div>
 </div>
 </div>

 <div className="px-5 pb-4 flex gap-2">
 <Button
 variant="outline"
 className="flex-1"
 onClick={() => router.push(`/dashboard/apoio/visao/${visao.id}/visualizar`)}
 >
 <Eye className="w-4 h-4 mr-2" />
 Visualizar
 </Button>
 <Button
 className="flex-1"
 onClick={() => router.push(`/dashboard/apoio/visao/${visao.id}`)}
 >
 <Edit2 className="w-4 h-4 mr-2" />
 Editar
 </Button>
 </div>
 </div>
 ))}
 </div>
 )}

 {/* Modal de Nova Visão */}
 {isModalOpen && (
 <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4">
 <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
 <div className="p-5 border-b border-slate-100">
 <h3 className="font-bold text-lg text-slate-800">Nova Visão</h3>
 <p className="text-sm text-slate-500 mt-1">Crie uma nova estrutura de cenário DRE.</p>
 </div>
 <div className="p-5 space-y-4">
 {/* Tipo de criação */}
 <div className="grid grid-cols-2 gap-2">
 <button
 onClick={() => { setCreateMode("vazia"); setFormData(f => ({ ...f, copiar_de_id: null })); }}
 className={`p-3 rounded-lg border-2 text-sm font-medium transition-colors text-left ${createMode ==="vazia" ?"border-ml-green bg-emerald-50 text-ml-green" :"border-slate-200 text-slate-600 hover:border-slate-300"}`}
 >
 <Plus className="w-4 h-4 mb-1" />
 Começar do zero
 </button>
 <button
 onClick={() => setCreateMode("copia")}
 className={`p-3 rounded-lg border-2 text-sm font-medium transition-colors text-left ${createMode ==="copia" ?"border-ml-green bg-emerald-50 text-ml-green" :"border-slate-200 text-slate-600 hover:border-slate-300"}`}
 >
 <Copy className="w-4 h-4 mb-1" />
 Copiar de uma existente
 </button>
 </div>

 {createMode ==="copia" && (
 <div>
 <label className="block text-sm font-medium text-slate-700 mb-1">Copiar de qual visão?</label>
 <select
 className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-ml-green outline-none text-sm"
 value={formData.copiar_de_id ??""}
 onChange={e => setFormData(f => ({ ...f, copiar_de_id: Number(e.target.value) || null }))}
 >
 <option value="">Selecione...</option>
 {visoes.map(v => (
 <option key={v.id} value={v.id}>{v.nome}</option>
 ))}
 </select>
 </div>
 )}

 <div>
 <label className="block text-sm font-medium text-slate-700 mb-1">Nome da Visão *</label>
 <input
 type="text"
 placeholder="Ex: Visão 2025, Simulação de Redução de Custos..."
 className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-ml-green outline-none text-sm"
 value={formData.nome}
 onChange={e => setFormData(f => ({ ...f, nome: e.target.value }))}
 autoFocus
 />
 </div>
 <div>
 <label className="block text-sm font-medium text-slate-700 mb-1">Descrição (opcional)</label>
 <textarea
 rows={2}
 placeholder="Descreva o objetivo desta visão..."
 className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-ml-green outline-none text-sm resize-none"
 value={formData.descricao}
 onChange={e => setFormData(f => ({ ...f, descricao: e.target.value }))}
 />
 </div>
 </div>
 <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-2">
 <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
 <Button onClick={handleCreate} disabled={!formData.nome.trim()}>Criar Visão</Button>
 </div>
 </div>
 </div>
 )}
 </div>
 );
}
