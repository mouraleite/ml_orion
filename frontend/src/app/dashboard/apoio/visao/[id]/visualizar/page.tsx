"use client";

import React, { useState, useEffect, useCallback } from"react";
import { useParams, useRouter } from"next/navigation";
import { Eye, ChevronDown, ChevronRight, FileText, ArrowLeft, ArrowRight, Printer } from"lucide-react";
import { Button } from"@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { apoioService, VisaoNode } from"@/services/apoio";
import { formatPlanId } from"@/lib/formatters";

// ── Read-only Plan ──────────────────────────────────────────────────────────
function ReadOnlyPlano({ plano }: { plano: any }) {
 return (
 <div className="flex items-center py-1.5 px-2 -ml-2 rounded hover:bg-slate-50 transition-colors border-b border-slate-50 last:border-0">
 <div className="w-4 h-4 mr-2" /> {/* Placeholder para o grip icon do editor para manter alinhamento */}
 <FileText className="w-4 h-4 text-slate-400 shrink-0 mr-3" />
 <span className="text-sm text-slate-700 flex-1 truncate" title={plano.name}>{plano.name}</span>
 <span className="text-sm font-mono text-slate-500 w-32 shrink-0">{formatPlanId(plano.db_id)}</span>
 <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded uppercase w-20 text-center shrink-0">{plano.tp_conta || '-'}</span>
 </div>
 );
}

// ── Read-only Vision Node ────────────────────────────────────────────────────
function ReadOnlyVisionNode({ node, indentLevel, isExpanded, onToggle }: {
 node: VisaoNode; indentLevel: number; isExpanded: boolean; onToggle: () => void;
}) {
 const isMainNode = indentLevel === 0;
 const planosOrdenados = [...(node.planos_financeiros || [])].sort((a, b) => a.name.localeCompare(b.name));

 return (
 <div className="mb-1">
 <div className={`flex items-center justify-between py-2 px-4 rounded-lg transition-colors hover:bg-slate-50 ${isMainNode ? 'bg-slate-50/50' : ''}`}>
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
 </div>
 {isExpanded && planosOrdenados.length > 0 && (
 <div className="mt-1 mb-2 flex flex-col">
 {planosOrdenados.map(plano => (
 <div key={plano.id} style={{ paddingLeft: `${(indentLevel + 1) * 24 + 48}px`, paddingRight: '16px' }}>
 <ReadOnlyPlano plano={plano} />
 </div>
 ))}
 </div>
 )}
 </div>
 );
}

// ── Main Page ────────────────────────────────────────────────────────────────
export default function VisualizarVisaoPage() {
 const params = useParams();
 const router = useRouter();
 const visaoId = Number(params.id);

 const [visaoNome, setVisaoNome] = useState("");
 const [nodes, setNodes] = useState<VisaoNode[]>([]);
 const [isLoading, setIsLoading] = useState(true);
 const [expandedNodes, setExpandedNodes] = useState<Record<number, boolean>>({});

 const fetchData = useCallback(async () => {
 setIsLoading(true);
 try {
 const [visoesData, allVisoes] = await Promise.all([
 apoioService.getArvoreVisao(visaoId),
 apoioService.listVisoes()
 ]);
 const visao = allVisoes.find((v: any) => v.id === visaoId);
 if (visao) setVisaoNome(visao.nome);

 setNodes(visoesData);

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

 useEffect(() => { fetchData(); }, [fetchData]);

 const getIndentLevel = (codigo: string) => (codigo.match(/\./g) || []).length;

 const expandirTodos = () => {
 const todos: Record<number, boolean> = {};
 nodes.forEach(n => todos[n.id] = true);
 setExpandedNodes(todos);
 };

 const recolherTodos = () => {
 setExpandedNodes({});
 };

 if (isLoading && nodes.length === 0) {
 return <AppLoadingState />;
 }

 return (
 <div className="p-8 space-y-6 flex flex-col h-full animate-in fade-in duration-300">
 {/* Header */}
 <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shrink-0">
 <div className="flex items-center gap-3">
 <button onClick={() => router.push('/dashboard/apoio/visao')} className="p-2 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors">
 <ArrowLeft className="w-5 h-5" />
 </button>
 <div>
 <div className="flex items-center gap-2 flex-wrap">
 <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
 <Eye className="w-6 h-6 text-brand-green" />
 {visaoNome ||"Visão"}
 </h1>
 <span className="bg-slate-100 text-slate-600 text-xs px-2 py-0.5 rounded font-medium">Modo Visualização</span>
 </div>
 <p className="text-slate-500 mt-1 text-sm">Visualize a estrutura de categorias e contas da DRE.</p>
 </div>
 </div>
 <div className="flex gap-2 flex-wrap">
 <Button variant="outline" onClick={expandirTodos}>Expandir Tudo</Button>
 <Button variant="outline" onClick={recolherTodos}>Recolher Tudo</Button>
 <Button onClick={() => router.push(`/dashboard/apoio/visao/${visaoId}`)} className="gap-2">
 Editar Estrutura
 <ArrowRight className="w-4 h-4" />
 </Button>
 </div>
 </div>

 {/* Árvore */}
 <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col flex-1">
 <div className="p-4 border-b border-slate-200 bg-slate-50 shrink-0 flex justify-between items-center">
 <h2 className="font-semibold text-slate-800">Estrutura Consolidada</h2>
 <div className="flex gap-2">
 <button className="p-2 text-slate-500 hover:text-brand-green hover:bg-emerald-50 rounded-lg transition-colors" title="Imprimir" onClick={() => window.print()}>
 <Printer className="w-4 h-4" />
 </button>
 </div>
 </div>
 <div className="overflow-y-auto p-4 group">
 {nodes.length === 0 ? (
 <div className="py-12 text-center text-sm text-slate-400 border border-dashed border-slate-200 rounded-lg bg-slate-50">
 Nenhuma categoria nesta visão.
 </div>
 ) : (
 <>
 <div className="flex items-center px-4 pb-2 mb-2 border-b border-slate-100 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
 <span className="flex-1">Categoria / Conta</span>
 <span className="w-32 shrink-0">Código</span>
 <span className="w-20 text-center shrink-0">Tipo</span>
 </div>
 {nodes.map(node => (
 <ReadOnlyVisionNode
 key={node.id}
 node={node}
 indentLevel={getIndentLevel(node.codigo)}
 isExpanded={!!expandedNodes[node.id]}
 onToggle={() => setExpandedNodes(prev => ({ ...prev, [node.id]: !prev[node.id] }))}
 />
 ))}
 </>
 )}
 </div>
 </div>
 </div>
 );
}
