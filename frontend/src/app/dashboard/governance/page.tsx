"use client";
import { useEffect, useState } from"react";
import { api } from"@/lib/api";
import { useAuth } from"@/contexts/AuthContext";
import { isAdminUser } from "@/lib/roles";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from"@/components/ui/Card";
import { Button } from"@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { Plus, Edit2, Trash2 } from"lucide-react";
import { IndexModal } from"@/components/governance/IndexModal";

interface EconomicIndex {
 id: number;
 name: string;
 symbol: string;
 current_value: number;
 projected_value: number;
 updated_at: string;
}

export default function GovernancePage() {
 const { user } = useAuth();
 const isAdminUserFlag = isAdminUser(user);
 
 const [indices, setIndices] = useState<EconomicIndex[]>([]);
 const [isLoading, setIsLoading] = useState(true);
 const [isModalOpen, setIsModalOpen] = useState(false);
 const [editingIndex, setEditingIndex] = useState<EconomicIndex | null>(null);

 const fetchIndices = async () => {
 try {
 setIsLoading(true);
 const { data } = await api.get("/governance/indices");
 setIndices(data);
 } catch (error) {
 console.error("Erro ao buscar índices", error);
 } finally {
 setIsLoading(false);
 }
 };

 useEffect(() => {
 fetchIndices();
 }, []);

 const handleDelete = async (id: number) => {
 if (!(await confirmDialog("Tem certeza que deseja remover este índice?", { variant: "danger", confirmLabel: "Remover" }))) return;
 try {
 await api.delete(`/governance/indices/${id}`);
 fetchIndices();
 } catch (error) {
 alert("Erro ao excluir. Verifique suas permissões.");
 }
 };

 const openNewModal = () => {
 setEditingIndex(null);
 setIsModalOpen(true);
 };

 const openEditModal = (idx: EconomicIndex) => {
 setEditingIndex(idx);
 setIsModalOpen(true);
 };

 return (
 <div className="space-y-6">
 <div className="flex justify-between items-center">
 <div>
 <h1 className="text-3xl font-bold tracking-tight text-slate-900">Governança</h1>
 <p className="text-slate-500 mt-1">Gerencie os índices macroeconômicos usados nos cálculos.</p>
 </div>
 {isAdminUserFlag && (
 <Button onClick={openNewModal} className="bg-blue-600 hover:bg-blue-700 text-white shadow-sm flex items-center gap-2">
 <Plus className="w-4 h-4" />
 Novo Índice
 </Button>
 )}
 </div>

 <Card className="border-0 shadow-sm">
 <div className="overflow-x-auto">
 <table className="w-full text-sm text-left">
 <thead className="bg-slate-50 text-slate-600 border-b border-slate-100">
 <tr>
 <th className="px-6 py-4 font-semibold">Nome do Índice</th>
 <th className="px-6 py-4 font-semibold text-right">Valor Atual</th>
 <th className="px-6 py-4 font-semibold text-right">Valor Projetado</th>
 <th className="px-6 py-4 font-semibold text-right">Última Atualização</th>
 {isAdminUserFlag && <th className="px-6 py-4 font-semibold text-right">Ações</th>}
 </tr>
 </thead>
 <tbody className="divide-y divide-slate-100">
 {isLoading ? (
 <tr>
 <td colSpan={5}>
 <AppLoadingState />
 </td>
 </tr>
 ) : indices.length === 0 ? (
 <tr>
 <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
 Nenhum índice cadastrado.
 </td>
 </tr>
 ) : (
 indices.map((idx) => (
 <tr key={idx.id} className="hover:bg-slate-50/50 transition-colors">
 <td className="px-6 py-4 font-medium text-slate-900">
 {idx.name}
 </td>
 <td className="px-6 py-4 text-right">
 {idx.current_value.toFixed(2)} <span className="text-slate-400">{idx.symbol}</span>
 </td>
 <td className="px-6 py-4 text-right text-blue-600 font-medium">
 {idx.projected_value.toFixed(2)} <span className="opacity-70">{idx.symbol}</span>
 </td>
 <td className="px-6 py-4 text-right text-slate-500">
 {new Date(idx.updated_at).toLocaleDateString('pt-BR')}
 </td>
 {isAdminUserFlag && (
 <td className="px-6 py-4 text-right">
 <div className="flex items-center justify-end gap-2">
 <button 
 onClick={() => openEditModal(idx)}
 className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
 >
 <Edit2 className="w-4 h-4" />
 </button>
 <button 
 onClick={() => handleDelete(idx.id)}
 className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
 >
 <Trash2 className="w-4 h-4" />
 </button>
 </div>
 </td>
 )}
 </tr>
 ))
 )}
 </tbody>
 </table>
 </div>
 </Card>

 <IndexModal 
 isOpen={isModalOpen} 
 onClose={() => setIsModalOpen(false)} 
 onSuccess={fetchIndices}
 initialData={editingIndex}
 />
 </div>
 );
}
