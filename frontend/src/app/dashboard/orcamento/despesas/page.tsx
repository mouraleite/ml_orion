"use client";

import { apoioService } from "@/services/apoio";

import React, { useEffect, useState, useMemo } from "react";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { orcamentoService, OrcamentoDespesasResponse, OrcamentoItemData } from "@/services/orcamento";
import { Save, Copy, Plus, Trash2, ChevronDown, ChevronRight, FileSpreadsheet } from "lucide-react";
import { VersionHeader } from "@/components/orcamento/VersionHeader";
import { useAuth } from "@/contexts/AuthContext";
import { BudgetPageToolbar } from "@/components/shared/BudgetPageToolbar";
import {
  BudgetMatrixShell,
  BudgetMatrixScrollArea,
  BUDGET_MATRIX_TABLE_CLASS,
} from "@/components/shared/BudgetMatrixShell";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import {
  MonthlyGridFilterPanel,
  type MonthlyGridFilterValues,
} from "@/components/shared/MonthlyGridFilterPanel";
import { YearSelect } from "@/components/shared/YearSelect";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId } from "@/lib/useActiveDepartmentId";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { ExcelImportModal } from "@/components/orcamento/ExcelImportModal";
import { CriarOrcamentoModal } from "@/components/orcamento/CriarOrcamentoModal";
import { MonthSelector } from "@/components/orcamento/MonthSelector";
import { TableHead } from "@/components/ui/Table";
import { useTableSort, SortConfig } from "@/hooks/useTableSort";
import { MESES_KEYS } from "@/lib/months";
import { buildGridFilterOptions, filterLinhasMensais, groupByProductId } from "@/lib/gridFilters";
import { getMonthlyDiffClass, matchProdutoPlano } from "@/lib/gridDiff";

import toast from 'react-hot-toast';

const MESES = [...MESES_KEYS];

export default function OrcamentoDespesasPage() {
  const { user, loading: authLoading } = useAuth();
  const deptId = useActiveDepartmentId();
  const { holdingMldu, setHoldingMldu, canUseHoldingMldu } = useHoldingMldu("orcamento");
  const currentYear = new Date().getFullYear();
  const [ano, setAno] = useState<number>(currentYear);
  const [anosDisponiveis, setAnosDisponiveis] = useState<number[]>([]);
  const [showCriarModal, setShowCriarModal] = useState(false);
  const [data, setData] = useState<OrcamentoDespesasResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [linhas, setLinhas] = useState<OrcamentoItemData[]>([]);
  const [novoProdutoId, setNovoProdutoId] = useState<number | "">("");
  const [novoPlanoId, setNovoPlanoId] = useState<number | "">("");
  const [showExcel, setShowExcel] = useState(false);
  const [expandedProducts, setExpandedProducts] = useState<number[]>([]);

  // Estado de Filtro
  const [busca, setBusca] = useState("");
  const [filtroIdCentro, setFiltroIdCentro] = useState<string[]>([]);
  const [filtroProduto, setFiltroProduto] = useState<string[]>([]);
  const [filtroPlano, setFiltroPlano] = useState<string[]>([]);
  const [selectedMonths, setSelectedMonths] = useState<number[]>([1,2,3,4,5,6,7,8,9,10,11,12]);
  const [filtroEmpresaIds, setFiltroEmpresaIds] = useState<string[]>([]);

  const filtroOpcoes = useMemo(
    () => buildGridFilterOptions(data, true),
    [data],
  );

  const { centrosId: opcoesIdCentro, produtos: opcoesProduto, planos: opcoesPlano, empresasId: opcoesIdEmpresa, empresasNome: opcoesEmpresa } = filtroOpcoes;


  const carregarAnos = async () => {
    try {
      const resp = await orcamentoService.getAnosDisponiveis("DESPESAS", deptId, false);
      setAnosDisponiveis(resp.anos);
      return resp.anos;
    } catch (err) {
      console.error(err);
      return [];
    }
  };

  useEffect(() => {
    if (!user || authLoading) return;
    carregarAnos().then(anos => {
      if (anos.length > 0) {
        setAno(anos[anos.length - 1]);
      }
    });
  }, [deptId, user, authLoading]);

  const carregarDados = async (selectedAno: number) => {
    if (!anosDisponiveis.includes(selectedAno)) {
      setData(null);
      setLinhas([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const resp = await orcamentoService.getDespesas(selectedAno, deptId, false, holdingMldu);
      setData(resp);
      setLinhas(resp.itens || []);
    } catch (err: any) {
      if (err?.response?.status === 404) {
        setData(null);
        setLinhas([]);
      } else {
        const detail = err?.response?.data?.detail;
        toast.error(
          typeof detail === "string" ? detail : "Erro ao carregar orçamento.",
        );
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user || authLoading) return;
    if (anosDisponiveis.includes(ano)) {
      carregarDados(ano);
    } else {
      setData(null);
      setLinhas([]);
      setLoading(false);
    }
  }, [ano, deptId, holdingMldu, anosDisponiveis, user, authLoading]);

  const handleCreated = async (anoCriado: number, produtoId: number) => {
    setShowCriarModal(false);
    const anos = await carregarAnos();
    if (anos.includes(anoCriado)) {
      setAno(anoCriado);
    }
    setExpandedProducts((prev) => prev.includes(produtoId) ? prev : [...prev, produtoId]);
  };
  
  const handleDeleteEmpreendimento = async (produtoId: number) => {
    if(!(await confirmDialog('Tem certeza que deseja excluir os dados deste empreendimento da matriz? A exclusão vale ao clicar em Salvar.', { variant: "danger" }))) return;
    setLinhas(linhas.filter((l) => l.produto_id !== produtoId));
    toast.success("Empreendimento removido da matriz. Clique em Salvar para gravar.");
  };


  const recalcularTotal = (linha: OrcamentoItemData): OrcamentoItemData => {
    linha.total_anual = MESES.reduce((acc, mes) => acc + (Number(linha[mes as keyof OrcamentoItemData]) || 0), 0);
    return linha;
  };

  const handleInputChange = (index: number, campo: keyof OrcamentoItemData, valor: string) => {
    const novasLinhas = [...linhas];
    if (campo === "observacao") {
      novasLinhas[index][campo] = valor;
    } else {
      (novasLinhas[index] as any)[campo] = parseFloat(valor) || 0;
      novasLinhas[index] = recalcularTotal(novasLinhas[index]);
    }
    setLinhas(novasLinhas);
  };

  const adicionarLinhaProduto = (produtoId: number) => {
    const usados = new Set(linhas.filter((l) => l.produto_id === produtoId).map((l) => l.plano_financeiro_id));
    const livre = data?.opcoes_planos?.find((p) => !usados.has(p.id));
    if (!livre) {
      toast.error("Esta combinação empreendimento + plano já está no orçamento.");
      return;
    }
    const novaLinha: any = {
      produto_id: produtoId,
      plano_financeiro_id: livre.id,
      jan: 0, fev: 0, mar: 0, abr: 0, mai: 0, jun: 0, jul: 0, ago: 0, set: 0, out: 0, nov: 0, dez: 0,
      total_anual: 0,
      observacao: "",
    };
    setLinhas([...linhas, novaLinha]);
    if (!expandedProducts.includes(produtoId)) {
      setExpandedProducts([...expandedProducts, produtoId]);
    }
  };

  const adicionarLinhaMatriz = () => {
    if (!novoProdutoId || !novoPlanoId) {
      toast.error("Selecione um empreendimento e um plano financeiro.");
      return;
    }
    if (linhas.some((l) => l.produto_id === novoProdutoId && l.plano_financeiro_id === novoPlanoId)) {
      toast.error("Esta combinação empreendimento + plano já está no orçamento.");
      return;
    }
    const pid = Number(novoProdutoId);
    setLinhas([...linhas, {
      produto_id: pid,
      plano_financeiro_id: Number(novoPlanoId),
      jan: 0, fev: 0, mar: 0, abr: 0, mai: 0, jun: 0, jul: 0, ago: 0, set: 0, out: 0, nov: 0, dez: 0,
      total_anual: 0,
      observacao: "",
    }]);
    if (!expandedProducts.includes(pid)) {
      setExpandedProducts([...expandedProducts, pid]);
    }
  };

  const removerLinha = (index: number) => {
    setLinhas(linhas.filter((_, i) => i !== index));
  };

  const salvar = async () => {
    setSaving(true);
    try {
      const itens = linhas.map((l) => ({
        ...l,
        observacao: l.observacao ?? "",
      }));
      await orcamentoService.salvarDespesas(ano, deptId, itens);
      toast.success("Orçamento salvo com sucesso!");
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail) && detail[0]?.msg
            ? detail[0].msg
            : "Erro ao salvar orçamento. Verifique permissões.";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const replicarValor = async (index: number, mesOrigem: string) => {
    const linha = linhas[index];
    const valorOrigem = Number(linha[mesOrigem as keyof OrcamentoItemData]) || 0;
    
    const mesesRestantes = MESES.slice(MESES.indexOf(mesOrigem) + 1);
    
    let precisaConfirmacao = false;
    for (const mes of mesesRestantes) {
      if ((Number(linha[mes as keyof OrcamentoItemData]) || 0) > 0) {
        precisaConfirmacao = true;
        break;
      }
    }

    if (precisaConfirmacao) {
      const ok = await confirmDialog("Existem valores já preenchidos nos meses seguintes. Deseja sobrescrever?", {
        title: "Sobrescrever valores",
        confirmLabel: "Sobrescrever",
      });
      if (!ok) return;
    }

    const novasLinhas = [...linhas];
    mesesRestantes.forEach((mes) => {
      (novasLinhas[index] as any)[mes] = valorOrigem;
    });
    
    novasLinhas[index] = recalcularTotal(novasLinhas[index]);
    setLinhas(novasLinhas);
    toast.success(`Valor replicado de ${mesOrigem.toUpperCase()} em diante.`);
  };

  const getDiffClass = (linha: OrcamentoItemData, campo: keyof OrcamentoItemData) =>
    getMonthlyDiffClass(linha, campo, data?.itens_base, matchProdutoPlano);

  const calcularTotalGeralColuna = (campo: keyof OrcamentoItemData) => {
    return linhas.reduce((acc, linha) => acc + (Number(linha[campo]) || 0), 0);
  };

  const isBlocked =
    holdingMldu ||
    ["Em aprovação", "Aprovado", "Fechado", "Solicitação Reabertura"].includes(data?.status || "");

  const gridFilters = { busca, filtroIdCentro, filtroProduto, filtroPlano, filtroEmpresaIds };

  const patchGridFilters = (patch: Partial<MonthlyGridFilterValues>) => {
    if (patch.busca !== undefined) setBusca(patch.busca);
    if (patch.filtroIdCentro !== undefined) setFiltroIdCentro(patch.filtroIdCentro);
    if (patch.filtroProduto !== undefined) setFiltroProduto(patch.filtroProduto);
    if (patch.filtroPlano !== undefined) setFiltroPlano(patch.filtroPlano);
    if (patch.filtroEmpresaIds !== undefined) setFiltroEmpresaIds(patch.filtroEmpresaIds);
  };

  const linhasFiltradas = filterLinhasMensais(linhas, data, gridFilters);

  const groupedByProduct = useMemo(
    () => groupByProductId(linhasFiltradas),
    [linhasFiltradas],
  );

  const customSortFn = React.useCallback((a: number, b: number, config: SortConfig<number>) => {
    if (config.key === 'produto') {
      const prodA = data?.opcoes_produtos.find(p => p.id === a);
      const prodB = data?.opcoes_produtos.find(p => p.id === b);
      const nameA = prodA ? `${prodA.id_sienge || ""} - ${prodA.nome}` : "";
      const nameB = prodB ? `${prodB.id_sienge || ""} - ${prodB.nome}` : "";
      return config.direction === 'asc' ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
    }
    
    if (MESES.includes(config.key as string) || config.key === 'total_anual') {
      const sumA = groupedByProduct[a].reduce((acc, l) => acc + (Number(l[config.key as keyof OrcamentoItemData]) || 0), 0);
      const sumB = groupedByProduct[b].reduce((acc, l) => acc + (Number(l[config.key as keyof OrcamentoItemData]) || 0), 0);
      return config.direction === 'asc' ? sumA - sumB : sumB - sumA;
    }
    
    return 0;
  }, [groupedByProduct, data?.opcoes_produtos]);

  const { sortConfig, handleSort, sortedData: sortedProductIds } = useTableSort(
    Object.keys(groupedByProduct).map(Number),
    'produto',
    'asc',
    customSortFn
  );

  const mesesVisiveis = MESES.filter((_, i) => selectedMonths.includes(i + 1));

  const toggleProduct = (prodId: number) => {
    if (expandedProducts.includes(prodId)) {
      setExpandedProducts(expandedProducts.filter(id => id !== prodId));
    } else {
      setExpandedProducts([...expandedProducts, prodId]);
    }
  };

  return (
    <BudgetMatrixShell
      title="Orçamento de Despesas"
      subtitle="Matriz de alocação de despesas por centro de custo."
      toolbar={
        <BudgetPageToolbar
          scope="orcamento"
          holdingMldu={holdingMldu}
          onHoldingMlduChange={setHoldingMldu}
          canUseHoldingMldu={canUseHoldingMldu}
          contextControls={
            <YearSelect value={ano} years={anosDisponiveis} onChange={setAno} />
          }
          actions={
            <>
              <button
                onClick={() => setShowCriarModal(true)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"
              >
                <Plus className="w-4 h-4 text-brand-600" />
                Criar Orçamento
              </button>
              <button
                onClick={() => setShowExcel(true)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"
              >
                <FileSpreadsheet className="w-4 h-4 text-brand-green" />
                Excel
              </button>
              {!isBlocked && (
                <Button variant="primary" onClick={salvar} disabled={saving || loading}>
                  <Save className="mr-2 h-4 w-4" /> {saving ? "Salvando..." : "Salvar Orçamento"}
                </Button>
              )}
            </>
          }
        />
      }
      chrome={
        <>
          {holdingMldu ? <HoldingMlduBanner avisos={data?.holding_avisos} /> : null}
          <VersionHeader orcamento={data} deptId={deptId} onStatusChanged={() => carregarDados(ano)} />
          {data ? (
            <MonthSelector selectedMonths={selectedMonths} onChange={setSelectedMonths} />
          ) : null}
          <MonthlyGridFilterPanel
            values={{ busca, filtroIdCentro, filtroProduto, filtroPlano, filtroEmpresaIds }}
            onChange={patchGridFilters}
            opcoesIdCentro={opcoesIdCentro}
            opcoesProduto={opcoesProduto}
            opcoesPlano={opcoesPlano}
            opcoesEmpresaId={opcoesIdEmpresa}
            opcoesEmpresaNome={opcoesEmpresa}
          />
          {isBlocked ? (
            <div className="bg-brand-orange/10 border border-brand-orange-light text-brand-orange px-3 py-1.5 rounded-md text-xs">
              <strong>Ano de {ano} Travado:</strong> O orçamento base já está aprovado e é imutável pela interface.
            </div>
          ) : null}
        </>
      }
    >
      {!data && !loading && !authLoading && (
        <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-lg bg-slate-50 p-12">
          <div className="bg-white p-4 rounded-full shadow-sm mb-4">
            <Plus className="w-8 h-8 text-slate-400" />
          </div>
          <h2 className="text-lg font-medium text-slate-700 mb-2">Nenhum orçamento encontrado</h2>
          <p className="text-slate-500 text-center max-w-md mb-6">
            Não existem orçamentos para <strong>{user?.departamentos.find((d) => d.id === deptId)?.nome ?? "este departamento"}</strong> em {ano}.
            Importações SharePoint ficam em <strong>Corporativo</strong> — selecione esse departamento no filtro.
            Vincule planos financeiros em Apoio → Departamentos para filtrar por área.
          </p>
          <Button variant="primary" onClick={() => setShowCriarModal(true)}>
            <Plus className="mr-2 h-4 w-4" /> Criar Primeiro Orçamento
          </Button>
        </div>
      )}

      {data && (
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-white rounded-2xl border border-slate-200">
          {loading ? (
          <AppLoadingState />
        ) : (
          <BudgetMatrixScrollArea>
            <table className={BUDGET_MATRIX_TABLE_CLASS}>
              <thead className="text-xs text-slate-700 uppercase bg-slate-100 sticky top-0 z-20">
                <tr>
                  <TableHead className="px-3 py-3 min-w-[300px] bg-slate-100 sticky left-0 z-30 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]" sortable sortDirection={sortConfig?.key === 'produto' ? sortConfig.direction : false} onClick={() => handleSort('produto')}>Produto (C.C.) / Plano Financeiro</TableHead>
                  {mesesVisiveis.map(mes => (
                    <TableHead key={mes} className="px-3 py-3 w-[100px] text-center bg-slate-100 border-l border-slate-200" sortable sortDirection={sortConfig?.key === mes ? sortConfig.direction : false} onClick={() => handleSort(mes)}>{mes.toUpperCase()}</TableHead>
                  ))}
                  <TableHead className="px-3 py-3 w-[120px] text-right font-bold text-brand-700 bg-slate-100 border-l border-slate-200" sortable sortDirection={sortConfig?.key === 'total_anual' ? sortConfig.direction : false} onClick={() => handleSort('total_anual')}>TOTAL (R$)</TableHead>
                  <TableHead className="px-3 py-3 min-w-[200px] bg-slate-100 border-l border-slate-200 text-left">Observação</TableHead>
                  <TableHead className="px-3 py-3 text-center bg-slate-100 border-l border-slate-200">Ações</TableHead>
                </tr>
              </thead>
              <tbody>
                {Object.keys(groupedByProduct).length === 0 ? (
                  <tr>
                    <td colSpan={16} className="px-6 py-8 text-center text-slate-500">
                      Nenhuma linha adicionada. Comece adicionando um centro de custo.
                    </td>
                  </tr>
                ) : (
                  
                  sortedProductIds.map(produtoId => {
                    const groupLinhas = groupedByProduct[produtoId];

                    const isExpanded = expandedProducts.includes(produtoId);
                    const produto = data?.opcoes_produtos.find(p => p.id === produtoId);
                    
                    const totaisProdMes: Record<string, number> = {};
                    let vgvAnualProd = 0;
                    
                    mesesVisiveis.forEach(m => { totaisProdMes[m] = 0; });

                    groupLinhas.forEach(l => {
                      MESES.forEach(m => {
                        totaisProdMes[m] += (Number(l[m as keyof OrcamentoItemData]) || 0);
                        vgvAnualProd += (Number(l[m as keyof OrcamentoItemData]) || 0);
                      });
                    });

                    return (
                      <React.Fragment key={`prod-${produtoId}`}>
                        <tr className="bg-slate-50 border-y hover:bg-slate-100 cursor-pointer transition-colors group" onClick={() => toggleProduct(produtoId)}>
                          <td className="px-3 py-3 font-bold text-slate-800 flex items-center whitespace-nowrap sticky left-0 z-10 bg-slate-50 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] group-hover:bg-slate-100">
                            {isExpanded ? <ChevronDown size={16} className="mr-1 text-brand-600" /> : <ChevronRight size={16} className="mr-1 text-slate-400" />}
                            {produto ? `${produto.id_sienge ? produto.id_sienge + ' - ' : ''}${produto.nome}` : `Produto #${produtoId}`}
                            <div className="ml-4 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              {!isBlocked && (
                                <>
                                  <button onClick={(e) => { e.stopPropagation(); adicionarLinhaProduto(produtoId); }} className="text-brand-600 hover:text-brand-700 p-1 bg-white rounded shadow-sm border border-brand-200" title="Adicionar Linha">
                                    <Plus size={14} />
                                  </button>
                                  <button onClick={(e) => { e.stopPropagation(); handleDeleteEmpreendimento(produtoId); }} className="text-red-500 hover:text-red-600 p-1 bg-white rounded shadow-sm border border-red-200" title="Excluir Empreendimento">
                                    <Trash2 size={14} />
                                  </button>
                                </>
                              )}
                            </div>
                          </td>
                          {mesesVisiveis.map(mes => (
                            <td key={`prod-m-${mes}`} className="px-3 py-2 text-right border-l border-slate-200 bg-slate-50 font-semibold text-brand-700">
                              {totaisProdMes[mes].toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </td>
                          ))}
                          <td className="px-3 py-3 text-right font-bold text-brand-800 border-l border-slate-200 bg-brand-50/50">
                            {vgvAnualProd.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="px-3 py-3 border-l border-slate-200 text-center"></td>
                          <td className="px-3 py-3 border-l border-slate-200 text-center"></td>
                        </tr>

                        {isExpanded && groupLinhas.map((linha) => {
                          const globalIdx = linhas.indexOf(linha);
                          return (
                            <React.Fragment key={`linha-${globalIdx}`}>
                              <tr className="bg-white border-t border-slate-100 hover:bg-slate-50 group">
                                <td className="px-3 py-2 pl-8 font-medium text-slate-700 whitespace-nowrap bg-white border-l-2 border-l-brand-400 sticky left-0 z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] group-hover:bg-slate-50">
                                  <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">PLANO FINANCEIRO</label>
                                  <select
                                    className="w-full p-1 border rounded text-sm bg-slate-50 focus:bg-white disabled:opacity-75"
                                    value={linha.plano_financeiro_id}
                                    disabled={isBlocked}
                                    onChange={(e) => {
                                      const novoPlano = Number(e.target.value);
                                      const duplicada = linhas.some((l, i) => i !== globalIdx && l.produto_id === linha.produto_id && l.plano_financeiro_id === novoPlano);
                                      if (duplicada) {
                                        toast.error("Esta combinação empreendimento + plano já está no orçamento.");
                                        return;
                                      }
                                      const novas = [...linhas];
                                      novas[globalIdx].plano_financeiro_id = novoPlano;
                                      setLinhas(novas);
                                    }}
                                  >
                                    {data?.opcoes_planos.map(p => (
                                      <option key={p.id} value={p.id}>{p.db_id ? `${p.db_id} - ${p.nome}` : p.nome}</option>
                                    ))}
                                  </select>
                                </td>
                                {mesesVisiveis.map((mes) => (
                                  <td key={`${globalIdx}-${mes}`} className={`px-1 py-2 text-center border-l border-slate-100 relative group/cell ${getDiffClass(linha, mes as keyof OrcamentoItemData)}`}>
                                    <div className="flex items-center">
                                      <input
                                        type="number"
                                        className="w-full p-1 text-xs text-right border-0 border-b border-transparent focus:border-brand-500 focus:ring-0 bg-transparent hover:bg-slate-50 transition-colors [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none disabled:bg-transparent disabled:border-transparent"
                                        value={linha[mes as keyof OrcamentoItemData] || ''}
                                        disabled={isBlocked}
                                        onChange={(e) => handleInputChange(globalIdx, mes as keyof OrcamentoItemData, e.target.value)}
                                        placeholder="0.00"
                                      />
                                      {!isBlocked && mes !== 'dez' && (
                                        <button 
                                          onClick={() => replicarValor(globalIdx, mes)}
                                          className="absolute -right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover/cell:opacity-100 p-1 bg-brand-100 text-brand-600 rounded-full hover:bg-brand-200 z-10 transition-opacity"
                                          title="Replicar para a direita"
                                        >
                                          <Copy size={12} />
                                        </button>
                                      )}
                                    </div>
                                  </td>
                                ))}
                                <td className={`px-3 py-2 text-right text-sm font-bold text-slate-700 bg-slate-50/50 border-l border-slate-100 ${getDiffClass(linha, 'total_anual')}`}>
                                  {linha.total_anual.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className={`px-3 py-2 border-l border-slate-100 ${getDiffClass(linha, 'observacao')}`}>
                                  <input
                                    type="text"
                                    className="w-full p-1 text-xs border-0 border-b border-transparent focus:border-brand-500 focus:ring-0 bg-transparent hover:bg-slate-50 disabled:bg-transparent disabled:border-transparent"
                                    value={linha.observacao || ''}
                                    disabled={isBlocked}
                                    onChange={(e) => handleInputChange(globalIdx, 'observacao', e.target.value)}
                                    placeholder="Nota..."
                                  />
                                </td>
                                <td className="px-3 py-2 text-center border-l border-slate-100">
                                  {!isBlocked && (
                                    <button onClick={() => removerLinha(globalIdx)} className="text-brand-red-light hover:text-brand-red transition-colors">
                                      <Trash2 size={16} className="mx-auto" />
                                    </button>
                                  )}
                                </td>
                              </tr>
                            </React.Fragment>
                          );
                        })}
                      </React.Fragment>
                    );
                  })
                )}
              </tbody>
              <tfoot className="bg-slate-100 font-bold sticky bottom-0 z-30">
                <tr>
                  <td className="px-3 py-3 text-right border-r border-slate-200 sticky left-0 z-30 bg-slate-100 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">TOTAIS GERAIS:</td>
                  {mesesVisiveis.map(mes => (
                    <td key={mes} className="px-3 py-3 text-right text-brand-700 border-l border-slate-200">
                      {calcularTotalGeralColuna(mes as keyof OrcamentoItemData).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                  ))}
                  <td className="px-3 py-3 text-right text-brand-700 bg-brand-200/50 text-base border-l border-slate-200">
                    {calcularTotalGeralColuna('total_anual').toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td colSpan={2} className="border-l border-slate-200"></td>
                </tr>
              </tfoot>
            </table>
          </BudgetMatrixScrollArea>
        )}

        {!isBlocked && (
          <div className="p-5 border-t bg-slate-50 flex flex-wrap items-end gap-4">
            <div className="flex-1 min-w-[200px] max-w-sm">
              <label className="block text-xs text-slate-500 font-medium mb-1">Centro de Custo</label>
              <SearchableSelect
                options={data?.opcoes_produtos.map((p) => ({
                  id: p.id,
                  label: p.id_sienge ? `${p.id_sienge} - ${p.nome}` : p.nome,
                })) || []}
                value={novoProdutoId}
                onChange={(val) => setNovoProdutoId(Number(val))}
                placeholder="Pesquise ou selecione..."
              />
            </div>
            <div className="flex-1 min-w-[200px] max-w-sm">
              <label className="block text-xs text-slate-500 font-medium mb-1">Plano financeiro</label>
              <SearchableSelect
                options={data?.opcoes_planos.map((p) => ({
                  id: p.id,
                  label: p.db_id ? `${p.db_id} - ${p.nome}` : p.nome,
                })) || []}
                value={novoPlanoId}
                onChange={(val) => setNovoPlanoId(Number(val))}
                placeholder="Pesquise ou selecione..."
              />
            </div>
            <Button
              variant="outline"
              className="text-brand-700 border-brand-200 bg-white hover:bg-brand-50 min-w-[160px] h-[38px]"
              onClick={adicionarLinhaMatriz}
            >
              <Plus className="mr-2 h-4 w-4" /> Adicionar à Matriz
            </Button>
          </div>
        )}
        
      </div>
      )}
      {showExcel && (
        <ExcelImportModal
          tipo="DESPESAS"
          ano={ano}
          deptId={deptId}
          orcamentoId={data?.orcamento_id}
          onClose={() => setShowExcel(false)}
          onSuccess={() => { setShowExcel(false); carregarDados(ano); }}
        />
      )}

      {showCriarModal && (
        <CriarOrcamentoModal
          tipo="DESPESAS"
          deptId={deptId}
          anoInicial={ano}
          onClose={() => setShowCriarModal(false)}
          onCreated={handleCreated}
        />
      )}
    </BudgetMatrixShell>
  );
}