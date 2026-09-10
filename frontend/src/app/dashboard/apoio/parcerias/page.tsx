"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { apoioService } from "@/services/apoio";
import { Search, Plus, Pencil, Trash2, X, Users } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

export default function ParceriasPage() {
  const [configs, setConfigs] = useState<any[]>([]);
  const [costCenters, setCostCenters] = useState<any[]>([]);
  const [planosFinanceiros, setPlanosFinanceiros] = useState<any[]>([]);
  const [visionTree, setVisionTree] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Form State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formName, setFormName] = useState("");
  const [formPrefix, setFormPrefix] = useState("");
  const [formRules, setFormRules] = useState<Record<string, boolean>>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [resConfigs, resCC, resPlanos, resVisoes] = await Promise.all([
        api.get("/partnership"),
        apoioService.getCentrosCusto(),
        apoioService.getPlanosFinanceiros(),
        apoioService.listVisoes()
      ]);
      setConfigs(resConfigs.data);
      setCostCenters(resCC);
      setPlanosFinanceiros(resPlanos);
      
      const defaultVision = resVisoes.find((v: any) => v.is_padrao) || resVisoes[0];
      if (defaultVision) {
        const tree = await apoioService.getArvoreVisao(defaultVision.id);
        setVisionTree(tree);
      }
    } catch (e) {
      console.error(e);
      alert("Erro ao carregar dados.");
    } finally {
      setIsLoading(false);
    }
  };

  const getPrefixes = () => {
    const map = new Map<string, string>();
    costCenters.forEach(cc => {
      if (cc.id_sienge) {
        const prefix = String(cc.id_sienge).substring(0, 3);
        if (!map.has(prefix) && cc.nome) {
          map.set(prefix, cc.nome.split(" - ")[0]); // Pega a primeira parte do nome
        }
      }
    });
    return Array.from(map.entries()).map(([prefix, name]) => ({ prefix, name }));
  };

  const openModal = (config?: any) => {
    if (config) {
      setEditingId(config.id);
      setFormName(config.name);
      setFormPrefix(config.sienge_prefix || "");
      setFormRules(config.rules || {});
    } else {
      setEditingId(null);
      setFormName("");
      setFormPrefix("");
      setFormRules({});
    }
    setIsModalOpen(true);
  };

  const toggleRule = (planoNome: string) => {
    setFormRules(prev => ({
      ...prev,
      [planoNome]: !prev[planoNome]
    }));
  };

  const handleSave = async () => {
    if (!formName) {
      alert("Preencha o nome da regra.");
      return;
    }

    try {
      if (editingId) {
        await api.put(`/partnership/${editingId}`, {
          name: formName,
          sienge_prefix: formPrefix,
          rules: formRules
        });
      } else {
        await api.post("/partnership", {
          name: formName,
          sienge_prefix: formPrefix,
          rules: formRules
        });
      }
      setIsModalOpen(false);
      loadData();
    } catch (e: any) {
      alert(e.response?.data?.detail || "Erro ao salvar.");
    }
  };

  const handleDelete = async (id: number) => {
    if (!(await confirmDialog("Tem certeza que deseja excluir esta regra de parceria?", { variant: "danger" }))) return;
    try {
      await api.delete(`/partnership/${id}`);
      loadData();
    } catch (e) {
      alert("Erro ao excluir.");
    }
  };

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Users className="w-6 h-6 text-[#F5883A]" />
            Regras de Parceria
          </h1>
          <p className="text-slate-500 mt-1">Configure o rateio de parceria por agrupamento Sienge.</p>
        </div>
        <Button onClick={() => openModal()} className="bg-[#F5883A] hover:bg-[#d97732] text-white">
          <Plus className="w-4 h-4 mr-2" /> Nova Regra
        </Button>
      </div>

      {isLoading ? (
        <AppLoadingState />
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
              <tr>
                <th className="px-6 py-4">Nome da Regra</th>
                <th className="px-6 py-4">Linhas Rateadas</th>
                <th className="px-6 py-4 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {configs.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-6 py-8 text-center text-slate-500">
                    Nenhuma regra de parceria cadastrada.
                  </td>
                </tr>
              ) : (
                configs.map((config) => (
                  <tr key={config.id} className="hover:bg-slate-50/50">
                    <td className="px-6 py-4 font-medium text-slate-800">{config.name}</td>
                    <td className="px-6 py-4 text-slate-600">
                      {Object.keys(config.rules || {}).filter(k => config.rules[k]).length} selecionadas
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button onClick={() => openModal(config)} className="text-slate-400 hover:text-[#F5883A] p-1">
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleDelete(config.id)} className="text-slate-400 hover:text-red-500 p-1">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
              <h2 className="text-lg font-bold text-slate-800">
                {editingId ? "Editar Regra" : "Nova Regra"}
              </h2>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 space-y-6 overflow-y-auto">
              <div className="grid grid-cols-1 gap-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700 block">Nome da Regra</label>
                  <input
                    type="text"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#F5883A]/40 focus:border-[#F5883A]"
                    placeholder="Ex: Regra Padrão"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-semibold text-slate-700 block">
                    Linhas Financeiras Sujeitas a Rateio
                  </label>
                  <span className="text-xs text-slate-500 italic">
                    O percentual será lido do campo "Participação" do Centro de Custo.
                  </span>
                </div>
                
                <div className="border border-slate-200 rounded-lg overflow-hidden bg-slate-50">
                  <div className="p-4 max-h-96 overflow-y-auto space-y-4">
                    {visionTree.map((node: any) => (
                      <div key={node.id} className="bg-white p-3 rounded border border-slate-200">
                        <h4 className="text-sm font-semibold text-slate-800 mb-2">{node.codigo} - {node.descricao}</h4>
                        <div className="pl-2 grid grid-cols-1 md:grid-cols-2 gap-1">
                          {node.planos_financeiros && node.planos_financeiros.length > 0 ? (
                            node.planos_financeiros.map((plano: any) => (
                              <label key={plano.id} className="flex items-center gap-2 text-sm p-1 rounded hover:bg-slate-50 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={formRules[plano.name] || false}
                                  onChange={() => toggleRule(plano.name)}
                                  className="w-4 h-4 text-[#F5883A] rounded border-slate-300 focus:ring-[#F5883A]"
                                />
                                <span className="truncate flex-1">{plano.name}</span>
                              </label>
                            ))
                          ) : (
                            <span className="text-xs text-slate-400 italic">Nenhum plano financeiro vinculado a este nível.</span>
                          )}
                        </div>
                      </div>
                    ))}
                    {visionTree.length === 0 && (
                      <p className="text-sm text-slate-500">Nenhuma árvore de visão encontrada.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
            
            <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-3">
              <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
              <Button onClick={handleSave} className="bg-[#F5883A] hover:bg-[#d97732] text-white">
                Salvar Regra
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
