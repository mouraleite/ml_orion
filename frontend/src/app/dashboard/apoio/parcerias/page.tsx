"use client";

import { useState, useEffect, useMemo } from "react";
import { api } from "@/lib/api";
import { apoioService } from "@/services/apoio";
import { Plus, Pencil, Trash2, X, Users, Search } from "lucide-react";
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
  const [formSearch, setFormSearch] = useState("");

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
    setFormSearch("");
    setIsModalOpen(true);
  };

  const toggleRule = (planoNome: string) => {
    setFormRules(prev => ({
      ...prev,
      [planoNome]: !prev[planoNome]
    }));
  };

  const setCategoryRules = (planos: any[], checked: boolean) => {
    setFormRules(prev => {
      const next = { ...prev };
      planos.forEach((plano: any) => {
        next[plano.name] = checked;
      });
      return next;
    });
  };

  const selectedCount = Object.keys(formRules).filter(k => formRules[k]).length;

  const filteredTree = useMemo(() => {
    const term = formSearch.trim().toLowerCase();
    if (!term) return visionTree;

    return visionTree
      .map((node: any) => {
        const planos = (node.planos_financeiros || []).filter((plano: any) =>
          String(plano.name || "").toLowerCase().includes(term)
        );
        const nodeMatches =
          String(node.codigo || "").toLowerCase().includes(term) ||
          String(node.descricao || "").toLowerCase().includes(term);

        if (!nodeMatches && planos.length === 0) return null;
        return {
          ...node,
          planos_financeiros: nodeMatches ? (node.planos_financeiros || []) : planos,
        };
      })
      .filter(Boolean);
  }, [visionTree, formSearch]);

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

  const totalLinhasSelecionadas = configs.reduce((acc, config) => {
    return acc + Object.keys(config.rules || {}).filter(k => config.rules[k]).length;
  }, 0);

  return (
    <div className="p-6 md:p-8 max-w-[1400px] mx-auto space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Users className="w-6 h-6 text-brand-orange" />
            Regras de Parceria
          </h1>
          <p className="text-slate-500 text-sm mt-1">Configure o rateio de parceria por agrupamento Sienge.</p>
        </div>
        <Button onClick={() => openModal()} className="gap-2 shrink-0">
          <Plus className="w-4 h-4" /> Nova Regra
        </Button>
      </div>

      {isLoading ? (
        <AppLoadingState />
      ) : configs.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-10 text-center space-y-3">
          <div className="mx-auto w-12 h-12 rounded-full bg-slate-50 border border-dashed border-slate-200 flex items-center justify-center">
            <Users className="w-5 h-5 text-slate-400" />
          </div>
          <p className="text-sm text-slate-600 font-medium">Nenhuma regra de parceria cadastrada</p>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">Crie a primeira regra para definir quais linhas financeiras entram no rateio de parceria.</p>
          <Button onClick={() => openModal()} className="gap-2 mt-2">
            <Plus className="w-4 h-4" /> Nova Regra
          </Button>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Regras</p>
              <p className="text-2xl font-bold text-slate-800 mt-1">{configs.length}</p>
              <p className="text-xs text-slate-400 mt-1">cadastradas no sistema</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Linhas rateadas</p>
              <p className="text-2xl font-bold text-slate-800 mt-1">{totalLinhasSelecionadas}</p>
              <p className="text-xs text-slate-400 mt-1">soma das seleções nas regras</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Como funciona</p>
              <p className="text-sm text-slate-700 mt-2 leading-relaxed">
                O % de rateio vem do campo <span className="font-semibold">&quot;Participação&quot;</span> do Centro de Custo.
              </p>
            </div>
          </div>

          <div className="bg-emerald-50/60 border border-brand-green/20 rounded-xl px-4 py-3 text-sm text-slate-700">
            Edite uma regra para marcar ou desmarcar as linhas financeiras sujeitas ao rateio de parceria.
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {configs.map((config) => {
              const selectedNames = Object.keys(config.rules || {}).filter(k => config.rules[k]);
              const count = selectedNames.length;
              const preview = selectedNames.slice(0, 4);
              const remaining = Math.max(0, count - preview.length);

              return (
                <div
                  key={config.id}
                  className="bg-white rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-colors flex flex-col"
                >
                  <div className="p-5 flex-1 space-y-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="text-lg font-bold text-slate-800 truncate" title={config.name}>
                          {config.name}
                        </h3>
                        <p className="text-xs text-slate-500 mt-1">
                          Regra usada para definir quais linhas entram no rateio.
                        </p>
                      </div>
                      <span className="shrink-0 text-xs font-semibold text-brand-green bg-brand-green/10 border border-brand-green/20 px-2.5 py-1 rounded-full">
                        {count} linhas
                      </span>
                    </div>

                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 mb-2">
                        Exemplos de linhas selecionadas
                      </p>
                      {preview.length === 0 ? (
                        <p className="text-sm text-slate-400 italic">Nenhuma linha marcada nesta regra.</p>
                      ) : (
                        <ul className="space-y-1.5">
                          {preview.map((name) => (
                            <li key={name} className="text-sm text-slate-700 flex items-start gap-2">
                              <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-brand-green shrink-0" />
                              <span className="leading-snug break-words">{name}</span>
                            </li>
                          ))}
                          {remaining > 0 && (
                            <li className="text-xs text-slate-500 pl-3.5">
                              +{remaining} outras linhas
                            </li>
                          )}
                        </ul>
                      )}
                    </div>
                  </div>

                  <div className="px-5 py-4 border-t border-slate-100 bg-slate-50 flex gap-2">
                    <Button
                      variant="outline"
                      className="flex-1 gap-2"
                      onClick={() => openModal(config)}
                    >
                      <Pencil className="w-4 h-4" />
                      Editar regra
                    </Button>
                    <Button
                      variant="ghost"
                      className="gap-2 text-red-500 hover:text-red-600 hover:bg-red-50"
                      onClick={() => handleDelete(config.id)}
                      title="Excluir"
                    >
                      <Trash2 className="w-4 h-4" />
                      Excluir
                    </Button>
                  </div>
                </div>
              );
            })}

            <button
              type="button"
              onClick={() => openModal()}
              className="min-h-[220px] rounded-xl border-2 border-dashed border-slate-300 bg-slate-50/70 hover:bg-slate-100 hover:border-brand-green/40 transition-colors flex flex-col items-center justify-center gap-2 text-slate-500 hover:text-brand-green"
            >
              <Plus className="w-8 h-8" />
              <span className="text-sm font-semibold">Adicionar nova regra</span>
            </button>
          </div>
        </div>
      )}

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl overflow-hidden max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
              <div>
                <h2 className="text-lg font-bold text-slate-800">
                  {editingId ? "Editar Regra" : "Nova Regra"}
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">Marque as linhas financeiras sujeitas ao rateio.</p>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600 p-1 rounded hover:bg-slate-200/60">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 space-y-5 overflow-y-auto">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700 block">Nome da Regra</label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="ml-input"
                  placeholder="Ex: Regra Padrão"
                />
              </div>

              <div className="space-y-3">
                <div className="flex flex-col gap-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <label className="text-sm font-semibold text-slate-700">
                      Linhas Financeiras Sujeitas a Rateio
                    </label>
                    <span className="text-xs font-medium text-brand-green bg-brand-green/10 px-2.5 py-1 rounded-full">
                      {selectedCount} selecionadas
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    O percentual de rateio é lido do campo <span className="font-medium text-slate-600">&quot;Participação&quot;</span> do Centro de Custo.
                  </p>
                </div>

                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="search"
                    value={formSearch}
                    onChange={(e) => setFormSearch(e.target.value)}
                    className="ml-input pl-9"
                    placeholder="Buscar linha financeira ou categoria..."
                  />
                </div>
                
                <div className="border border-slate-200 rounded-lg overflow-hidden bg-slate-50">
                  <div className="p-3 max-h-[28rem] overflow-y-auto space-y-2">
                    {filteredTree.map((node: any) => {
                      const planos = node.planos_financeiros || [];
                      const hasPlanos = planos.length > 0;
                      const selectedInNode = planos.filter((p: any) => formRules[p.name]).length;
                      const allSelected = hasPlanos && selectedInNode === planos.length;

                      if (!hasPlanos) {
                        return (
                          <div key={node.id} className="px-3 py-2 rounded-lg border border-dashed border-slate-200 bg-white/70">
                            <div className="flex items-center justify-between gap-3">
                              <p className="text-xs font-semibold text-slate-500">
                                {node.codigo} — {node.descricao}
                              </p>
                              <span className="text-[11px] text-slate-400 shrink-0">Sem planos neste nível</span>
                            </div>
                          </div>
                        );
                      }

                      return (
                        <div key={node.id} className="bg-white rounded-lg border border-slate-200 overflow-hidden">
                          <div className="px-3 py-2.5 bg-slate-50 border-b border-slate-100 flex flex-wrap items-center justify-between gap-2">
                            <div className="min-w-0">
                              <h4 className="text-sm font-semibold text-slate-800">
                                {node.codigo} — {node.descricao}
                              </h4>
                              <p className="text-[11px] text-slate-500 mt-0.5">
                                {selectedInNode}/{planos.length} selecionadas nesta categoria
                              </p>
                            </div>
                            <div className="flex items-center gap-1 shrink-0">
                              <button
                                type="button"
                                onClick={() => setCategoryRules(planos, true)}
                                className={`text-xs font-medium px-2 py-1 rounded-md transition-colors ${
                                  allSelected
                                    ? "text-brand-green bg-brand-green/10"
                                    : "text-slate-600 hover:text-brand-green hover:bg-emerald-50"
                                }`}
                              >
                                Selecionar todos
                              </button>
                              <button
                                type="button"
                                onClick={() => setCategoryRules(planos, false)}
                                disabled={selectedInNode === 0}
                                className="text-xs font-medium px-2 py-1 rounded-md text-slate-500 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:pointer-events-none"
                              >
                                Limpar
                              </button>
                            </div>
                          </div>
                          <div className="p-2 grid grid-cols-1 gap-0.5">
                            {planos.map((plano: any) => (
                              <label
                                key={plano.id}
                                className="flex items-start gap-2.5 text-sm p-2 rounded-md hover:bg-slate-50 cursor-pointer"
                              >
                                <input
                                  type="checkbox"
                                  checked={formRules[plano.name] || false}
                                  onChange={() => toggleRule(plano.name)}
                                  className="ml-checkbox mt-0.5 shrink-0"
                                />
                                <span className="text-slate-700 leading-snug break-words" title={plano.name}>
                                  {plano.name}
                                </span>
                              </label>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                    {visionTree.length === 0 && (
                      <div className="p-4 text-center text-sm text-slate-400 bg-white rounded-lg border border-dashed border-slate-200">
                        Nenhuma árvore de visão encontrada.
                      </div>
                    )}
                    {visionTree.length > 0 && filteredTree.length === 0 && (
                      <div className="p-4 text-center text-sm text-slate-400 bg-white rounded-lg border border-dashed border-slate-200">
                        Nenhum resultado para &quot;{formSearch.trim()}&quot;.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
            
            <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-3">
              <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
              <Button onClick={handleSave} className="gap-2">
                Salvar Regra
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
