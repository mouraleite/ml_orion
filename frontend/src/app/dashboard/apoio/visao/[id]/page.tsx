"use client";

import React, { useState, useEffect, useCallback } from"react";
import { useParams, useRouter } from"next/navigation";
import { Eye, ChevronDown, ChevronRight, FileText, AlertCircle, Plus, Edit2, Trash2, GripVertical, ArrowLeft, RotateCcw } from"lucide-react";
import { Button } from"@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { apoioService, VisaoNode } from"@/services/apoio";
import { formatPlanId } from"@/lib/formatters";
import {
 DndContext, DragOverlay, closestCenter,
 PointerSensor, useSensor, useSensors,
 DragStartEvent, DragEndEvent,
 useDraggable, useDroppable,
} from"@dnd-kit/core";

// ── Draggable Plan ──────────────────────────────────────────────────────────
function DraggablePlano({ plano, variant ="card" }: { plano: any; variant?:"tree" |"card" }) {
 const { attributes, listeners, setNodeRef, transform } = useDraggable({
 id: `plano-${plano.id}`,
 data: { plano }
 });
 const style = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`, zIndex: 50 } : undefined;

 if (variant ==="tree") {
 return (
 <div ref={setNodeRef} style={style}
 className="group/item flex items-center py-1.5 px-2 -ml-2 rounded hover:bg-emerald-50 transition-colors">
 <div {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing text-slate-300 hover:text-slate-600 mr-2 opacity-0 group-hover/item:opacity-100 transition-opacity">
 <GripVertical className="w-4 h-4" />
 </div>
 <FileText className="w-4 h-4 text-slate-400 shrink-0 mr-3" />
 <span className="text-sm text-slate-700 flex-1 truncate" title={plano.name}>{plano.name}</span>
 <span className="text-sm font-mono text-slate-500 w-32 shrink-0">{formatPlanId(plano.db_id)}</span>
 <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded uppercase w-20 text-center shrink-0">{plano.tp_conta || '-'}</span>
 </div>
 );
 }

 return (
 <div ref={setNodeRef} style={style}
 className="flex items-center gap-3 p-2.5 rounded-lg border bg-white shadow-sm border-slate-200 hover:border-slate-300 transition-colors">
 <div {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing text-slate-400 hover:text-slate-600">
 <GripVertical className="w-4 h-4" />
 </div>
 <FileText className="w-4 h-4 text-slate-400 shrink-0" />
 <div className="flex-1 min-w-0">
 <p className="text-sm font-medium text-slate-700 truncate" title={plano.name}>{plano.name}</p>
 <div className="flex items-center gap-2 mt-0.5">
 <span className="text-xs font-mono text-slate-500">{formatPlanId(plano.db_id)}</span>
 {plano.tp_conta && <span className="text-[10px] uppercase font-semibold text-slate-500 bg-slate-100 px-1.5 rounded">{plano.tp_conta}</span>}
 </div>
 </div>
 </div>
 );
}

// ── Droppable Unmapped Area ──────────────────────────────────────────────────
function DroppableUnmapped({ planos }: { planos: any[] }) {
 const { isOver, setNodeRef } = useDroppable({ id:"unmapped-area" });
 return (
 <div ref={setNodeRef}
 className={`flex-1 flex flex-col gap-2 p-4 min-h-[200px] border-2 border-dashed rounded-xl transition-colors ${isOver ?"border-ml-green bg-emerald-50/50" :"border-slate-200 bg-slate-50"}`}>
 {planos.length === 0 ? (
 <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
 <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
 <p className="text-sm font-medium">Nenhuma conta pendente</p>
 <p className="text-xs text-center mt-1">Todas as contas estão na estrutura.</p>
 </div>
 ) : (
 planos.map(plano => <DraggablePlano key={plano.id} plano={plano} />)
 )}
 </div>
 );
}

// ── Droppable Vision Node ────────────────────────────────────────────────────
function DroppableVisionNode({ node, indentLevel, isExpanded, onToggle, onEdit, onDelete }: {
 node: VisaoNode; indentLevel: number; isExpanded: boolean;
 onToggle: () => void; onEdit: () => void; onDelete: () => void;
}) {
 const { isOver, setNodeRef } = useDroppable({ id: `vision-node-${node.id}`, data: { node } });
 const isMainNode = indentLevel === 0;
 const planosOrdenados = [...(node.planos_financeiros || [])].sort((a, b) => a.name.localeCompare(b.name));

 return (
 <div className="mb-1" ref={setNodeRef}>
 <div className={`flex items-center justify-between py-2.5 px-4 rounded-lg transition-colors border-2 group ${isOver ?"border-ml-green bg-emerald-50" :"border-transparent hover:bg-slate-50"} ${isMainNode ? 'bg-slate-50/50' : ''}`}>
 <div className="flex items-center gap-2" style={{ paddingLeft: `${indentLevel * 24}px` }}>
 <button onClick={onToggle} className="p-1 rounded hover:bg-slate-200 transition-colors">
 {isExpanded ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
 </button>
 <div className="flex items-center gap-2">
 <span className={`text-sm ${isMainNode ? 'font-bold text-slate-800' : 'font-semibold text-slate-700'}`}>{node.codigo}</span>
 <span className={`text-sm ${isMainNode ? 'font-bold text-slate-800' : 'font-medium text-slate-700'}`}>{node.descricao}</span>
 <span className="ml-2 text-xs font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{node.planos_financeiros.length} itens</span>
 </div>
 </div>
 <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
 <button onClick={onEdit} className="p-1.5 text-slate-400 hover:text-ml-green rounded hover:bg-emerald-50"><Edit2 className="w-3.5 h-3.5" /></button>
 <button onClick={onDelete} className="p-1.5 text-slate-400 hover:text-red-600 rounded hover:bg-red-50"><Trash2 className="w-3.5 h-3.5" /></button>
 </div>
 </div>
 {isExpanded && planosOrdenados.length > 0 && (
 <div className="mt-1 mb-2 flex flex-col">
 {planosOrdenados.map(plano => (
 <div key={plano.id} style={{ paddingLeft: `${(indentLevel + 1) * 24 + 48}px`, paddingRight: '16px' }}>
 <DraggablePlano plano={plano} variant="tree" />
 </div>
 ))}
 </div>
 )}
 {isExpanded && planosOrdenados.length === 0 && isOver && (
 <div className="mt-1 mb-2 py-3 text-center text-sm text-ml-green font-medium bg-emerald-50 border border-dashed border-emerald-200 rounded-lg mx-4"
 style={{ marginLeft: `${(indentLevel + 1) * 24 + 48}px` }}>
 Solte aqui para vincular à {node.codigo}
 </div>
 )}
 </div>
 );
}

// ── Main Page ────────────────────────────────────────────────────────────────
export default function EditorVisaoPage() {
 const params = useParams();
 const router = useRouter();
 const visaoId = Number(params.id);

 const [visaoNome, setVisaoNome] = useState("");
 const [nodes, setNodes] = useState<VisaoNode[]>([]);
 const [unmappedPlans, setUnmappedPlans] = useState<any[]>([]);
 const [isLoading, setIsLoading] = useState(true);
 const [expandedNodes, setExpandedNodes] = useState<Record<number, boolean>>({});
 const [activeDragPlano, setActiveDragPlano] = useState<any>(null);
 const [hasChanges, setHasChanges] = useState(false);

 // Snapshot para desfazer alterações
 const [originalNodes, setOriginalNodes] = useState<VisaoNode[]>([]);
 const [originalUnmapped, setOriginalUnmapped] = useState<any[]>([]);

 // Modal de Nova Categoria
 const [isModalOpen, setIsModalOpen] = useState(false);
 const [editingNode, setEditingNode] = useState<VisaoNode | null>(null);
 const [formData, setFormData] = useState({ codigo:"", descricao:"" });

 const fetchData = useCallback(async (saveSnapshot = false) => {
 setIsLoading(true);
 try {
 const [visoesData, unmappedData, allVisoes] = await Promise.all([
 apoioService.getArvoreVisao(visaoId),
 apoioService.getNaoMapeadosVisao(visaoId),
 apoioService.listVisoes()
 ]);
 const visao = allVisoes.find((v: any) => v.id === visaoId);
 if (visao) setVisaoNome(visao.nome);

 setNodes(visoesData);
 setUnmappedPlans(unmappedData);

 if (saveSnapshot) {
 setOriginalNodes(JSON.parse(JSON.stringify(visoesData)));
 setOriginalUnmapped(JSON.parse(JSON.stringify(unmappedData)));
 setHasChanges(false);
 }

 setExpandedNodes(prev => {
 if (Object.keys(prev).length === 0) {
 const initial: Record<number, boolean> = {};
 visoesData.forEach((n: VisaoNode) => { initial[n.id] = true; });
 return initial;
 }
 return prev;
 });
 } catch (e) {
 console.error(e);
 } finally {
 setIsLoading(false);
 }
 }, [visaoId]);

 useEffect(() => { fetchData(true); }, [fetchData]);

 const handleUndoChanges = async () => {
 if (!(await confirmDialog("Desfazer todas as alterações e voltar ao estado original desta sessão?", {
   title: "Desfazer alterações",
   confirmLabel: "Desfazer",
   variant: "danger",
 }))) return;
 setNodes(JSON.parse(JSON.stringify(originalNodes)));
 setUnmappedPlans(JSON.parse(JSON.stringify(originalUnmapped)));
 setHasChanges(false);
 // Reverter no banco também
 fetchData(false);
 };

 const getIndentLevel = (codigo: string) => (codigo.match(/\./g) || []).length;

 const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

 const handleDragStart = (event: DragStartEvent) => {
 setActiveDragPlano(event.active.data.current?.plano);
 };

 const handleDragEnd = async (event: DragEndEvent) => {
 const { active, over } = event;
 setActiveDragPlano(null);
 if (!over) return;

 const planoId = parseInt(String(active.id).replace('plano-', ''), 10);
 const targetId = String(over.id);
 let newVisionNodeId: number | null = null;
 if (targetId.startsWith('vision-node-')) newVisionNodeId = parseInt(targetId.replace('vision-node-', ''), 10);

 try {
 let draggedPlano: any = null;

 setUnmappedPlans(prev => {
 const found = prev.find(p => p.id === planoId);
 if (found) draggedPlano = found;
 return prev.filter(p => p.id !== planoId);
 });
 setNodes(prev => prev.map(node => {
 const found = node.planos_financeiros.find(p => p.id === planoId);
 if (found) draggedPlano = found;
 return { ...node, planos_financeiros: node.planos_financeiros.filter(p => p.id !== planoId) };
 }));

 if (newVisionNodeId === null) {
 if (draggedPlano) setUnmappedPlans(prev => [...prev, draggedPlano].sort((a, b) => a.name.localeCompare(b.name)));
 } else {
 setNodes(prev => prev.map(node => {
 if (node.id === newVisionNodeId && draggedPlano) return { ...node, planos_financeiros: [...node.planos_financeiros, draggedPlano] };
 return node;
 }));
 setExpandedNodes(prev => ({ ...prev, [newVisionNodeId]: true }));
 }

 await apoioService.movePlanoInVisao(visaoId, planoId, newVisionNodeId);
 setHasChanges(true);
 } catch (e) {
 console.error("Erro ao mover plano:", e);
 fetchData(false);
 }
 };

 const handleSaveCategoria = async () => {
 try {
 if (editingNode) {
 await apoioService.updateCategoria(visaoId, editingNode.id, formData);
 } else {
 await apoioService.createCategoria(visaoId, formData);
 }
 setIsModalOpen(false);
 setEditingNode(null);
 fetchData(false);
 } catch (e) {
 alert("Erro ao salvar categoria. Verifique se o código já existe.");
 }
 };

 const handleDeleteCategoria = async (id: number) => {
 if (await confirmDialog("Excluir esta categoria? Os planos dentro dela voltarão para Não Mapeados.", { variant: "danger" })) {
 try {
 await apoioService.deleteCategoria(visaoId, id);
 fetchData(false);
 setHasChanges(true);
 } catch (e) { alert("Erro ao excluir categoria."); }
 }
 };

 if (isLoading && nodes.length === 0) {
 return <AppLoadingState />;
 }

 return (
 <DndContext sensors={sensors} collisionDetection={closestCenter} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
 <div className="space-y-6 h-[calc(100vh-8rem)] flex flex-col">
 {/* Header */}
 <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shrink-0">
 <div className="flex items-center gap-3">
 <button onClick={() => router.push('/dashboard/apoio/visao')} className="p-2 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors">
 <ArrowLeft className="w-5 h-5" />
 </button>
 <div>
 <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
 <Eye className="w-6 h-6 text-ml-green" />
 {visaoNome ||"Visão"}
 </h1>
 <p className="text-slate-500 mt-1 text-sm">Arraste contas para as categorias ou vice-versa.</p>
 </div>
 </div>
 <div className="flex gap-2">
 {hasChanges && (
 <Button variant="outline" onClick={handleUndoChanges}>
 <RotateCcw className="w-4 h-4 mr-2" />
 Desfazer Alterações
 </Button>
 )}
 <Button onClick={() => { setEditingNode(null); setFormData({ codigo:"", descricao:"" }); setIsModalOpen(true); }}>
 <Plus className="w-4 h-4 mr-2" />
 Nova Categoria
 </Button>
 </div>
 </div>

 {/* Layout 2 colunas */}
 <div className="flex gap-6 flex-1 min-h-0">
 {/* Árvore */}
 <div className="flex-[2] bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col min-h-0">
 <div className="p-4 border-b border-slate-200 bg-slate-50 shrink-0">
 <h2 className="font-semibold text-slate-800">Estrutura da Visão</h2>
 </div>
 <div className="flex-1 overflow-y-auto p-4 group">
 {nodes.map(node => (
 <DroppableVisionNode
 key={node.id}
 node={node}
 indentLevel={getIndentLevel(node.codigo)}
 isExpanded={!!expandedNodes[node.id]}
 onToggle={() => setExpandedNodes(prev => ({ ...prev, [node.id]: !prev[node.id] }))}
 onEdit={() => { setEditingNode(node); setFormData({ codigo: node.codigo, descricao: node.descricao }); setIsModalOpen(true); }}
 onDelete={() => handleDeleteCategoria(node.id)}
 />
 ))}
 </div>
 </div>

 {/* Painel de Não Mapeados */}
 <div className="flex-1 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col min-h-0">
 <div className="p-4 border-b border-slate-200 bg-slate-50 shrink-0 flex justify-between items-center">
 <h2 className="font-semibold text-slate-800">Não Mapeados</h2>
 <span className={`font-bold px-2 py-0.5 rounded text-xs ${unmappedPlans.length > 0 ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>
 {unmappedPlans.length} pendentes
 </span>
 </div>
 <div className="flex-1 overflow-y-auto p-4 flex flex-col">
 <p className="text-sm text-slate-500 mb-4">Arraste os cartões abaixo para as categorias à esquerda.</p>
 <DroppableUnmapped planos={unmappedPlans} />
 </div>
 </div>
 </div>
 </div>

 <DragOverlay>
 {activeDragPlano ? (
 <div className="opacity-80 scale-105 shadow-xl rotate-1">
 <DraggablePlano plano={activeDragPlano} />
 </div>
 ) : null}
 </DragOverlay>

 {/* Modal Nova/Editar Categoria */}
 {isModalOpen && (
 <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4">
 <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
 <div className="p-4 border-b border-slate-100">
 <h3 className="font-bold text-lg text-slate-800">{editingNode ?"Editar Categoria" :"Nova Categoria"}</h3>
 </div>
 <div className="p-4 space-y-4">
 <div>
 <label className="block text-sm font-medium text-slate-700 mb-1">Código Hierárquico</label>
 <input type="text" placeholder="Ex: 01.05" className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-ml-green outline-none"
 value={formData.codigo} onChange={e => setFormData({ ...formData, codigo: e.target.value })} />
 </div>
 <div>
 <label className="block text-sm font-medium text-slate-700 mb-1">Descrição</label>
 <input type="text" placeholder="Ex: RECEITAS EXTRAORDINÁRIAS" className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-ml-green outline-none"
 value={formData.descricao} onChange={e => setFormData({ ...formData, descricao: e.target.value })} />
 </div>
 </div>
 <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-2">
 <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
 <Button onClick={handleSaveCategoria}>Salvar</Button>
 </div>
 </div>
 </div>
 )}
 </DndContext>
 );
}
