"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useTableSort } from "@/hooks/useTableSort";
import { Card } from "@/components/ui/Card";
import { TableHead } from "@/components/ui/Table";
import { Modal }
from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { forecastService, ForecastDespesasResponse } from "@/services/forecast";
import { OrcamentoItemData } from "@/services/orcamento";
import { Save, Copy, Plus, Trash2, ChevronDown, ChevronRight, FileSpreadsheet } from "lucide-react";
import { ForecastVersionHeader } from "@/components/forecast/ForecastVersionHeader";
import { useAuth } from "@/contexts/AuthContext";
import { BudgetPageToolbar } from "@/components/shared/BudgetPageToolbar";
import { YearSelect } from "@/components/shared/YearSelect";
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
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId } from "@/lib/useActiveDepartmentId";
import { isAdminOrDiretorUser } from "@/lib/roles";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { ExcelImportModal } from "@/components/forecast/ExcelImportModal";
import { MonthSelector } from "@/components/orcamento/MonthSelector";

import toast from 'react-hot-toast';
import { MESES_KEYS } from "@/lib/months";
import { buildGridFilterOptions, filterLinhasMensais, groupByProductId } from "@/lib/gridFilters";
import { getMonthlyDiffClass, matchProdutoPlano } from "@/lib/gridDiff";

const MESES = [...MESES_KEYS];

export default function ForecastDespesasPage() {
  const { user, loading: authLoading } = useAuth();
  const deptId = useActiveDepartmentId();
  const { holdingMldu, setHoldingMldu, canUseHoldingMldu } = useHoldingMldu("forecast");
  const currentYear = new Date().getFullYear();
  const [ano, setAno] = useState<number>(currentYear);
  const [versaoId, setVersaoId] = useState<number | undefined>(undefined);
  const [anosDisponiveis, setAnosDisponiveis] = useState<number[]>([]);
  const [showCriarModal, setShowCriarModal] = useState(false);
  const [novoAno, setNovoAno] = useState<number>(currentYear);
  const [data, setData] = useState<ForecastDespesasResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [linhas, setLinhas] = useState<OrcamentoItemData[]>([]);
  const [novoProdutoId, setNovoProdutoId] = useState<number | "">("");
  const [novoPlanoId, setNovoPlanoId] = useState<number | "">("");
  const [showCriarBaseModal, setShowCriarBaseModal] = useState(false);
  const [baseSelecionada, setBaseSelecionada] = useState<{id: number, tipo: string} | null>(null);
  const [produtoCriacaoId, setProdutoCriacaoId] = useState<number | 0>(0);
  const [produtoModalAdicionarLinha, setProdutoModalAdicionarLinha] = useState<number | 0>(0);
  const [showExcel, setShowExcel] = useState(false);
  const [gerandoLote, setGerandoLote] = useState(false);
  const isAdminOrDiretor = isAdminOrDiretorUser(user);
  const [expandedProducts, setExpandedProducts] = useState<number[]>([]);

  // Estados de Filtro
  const [busca, setBusca] = useState("");
  const [filtroIdCentro, setFiltroIdCentro] = useState<string[]>([]);
  const [filtroProduto, setFiltroProduto] = useState<string[]>([]);
  const [filtroPlano, setFiltroPlano] = useState<string[]>([]);
  const [selectedMonths, setSelectedMonths] = useState<number[]>([1,2,3,4,5,6,7,8,9,10,11,12]);
  const [filtroEmpresaIds, setFiltroEmpresaIds] = useState<string[]>([]);

  // O hook useTableSort foi movido para baixo, depois de groupedByProduct



  const carregarAnos = async () => {
    try {
      const resp = await forecastService.getAnosDisponiveis("DESPESAS", deptId, false);
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

  const carregarDados = async (selectedAno: number, vId?: number) => {
    setLoading(true);
    try {
      const resp = await forecastService.getDespesas(selectedAno, deptId, false, vId, holdingMldu);
      setData(resp);
      setLinhas(resp.itens || []);

      if (!resp.is_locked_by_other && (resp.status === "Rascunho" || resp.status === "Reaberto")) {
        try {
          await forecastService.travarForecast(resp.forecast_id, deptId);
        } catch (e) {
          // Lock might be busy
        }
      }
    } catch (err: any) {
      if (err?.response?.status === 404) {
        setData(null);
        setLinhas([]);
      } else {
        toast.error("Erro ao carregar forecast.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user || authLoading) return;
    if (anosDisponiveis.includes(ano)) {
      setVersaoId(undefined);
      carregarDados(ano, undefined);
    } else {
      setData(null);
      setLinhas([]);
      setLoading(false);
    }
  }, [ano, deptId, holdingMldu, anosDisponiveis, user, authLoading]);

  useEffect(() => {
    if (versaoId !== undefined && anosDisponiveis.includes(ano)) {
      carregarDados(ano, versaoId);
    }
  }, [versaoId, holdingMldu]);

  const handleCriarDeBase = (baseId: number, baseTipo: string) => {
    setBaseSelecionada({id: baseId, tipo: baseTipo});
    setProdutoCriacaoId(0);
    setShowCriarBaseModal(true);
  };

  const handleCriarDeBaseFinal = async (produtoId: number) => {
    if(!baseSelecionada) return;
    const { id: baseId, tipo: baseTipo } = baseSelecionada;
    try {
      const isOrcamento = baseTipo === "Orcamento";
      await forecastService.criarDeBase(
        ano, 
        "DESPESAS",
        deptId,
        isOrcamento && baseId ? baseId : undefined, 
        (!isOrcamento && baseId) ? baseId : undefined,
        produtoId
      );
      toast.success(`Criado!`);
      setShowCriarBaseModal(false);
      carregarDados(ano);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao criar.");
    }
  };
  
  const handleDeleteEmpreendimento = async (produtoId: number) => {
    if(!(await confirmDialog('Tem certeza que deseja excluir os dados deste Empreendimento?', { variant: "danger" }))) return;
    try {
        const map_id = data?.mapa_ids?.[produtoId];
        if(!map_id) { toast.error("ID n\u00e3o encontrado"); return; }
        await forecastService.delete(map_id);
        toast.success("Exclu\u00eddo com sucesso.");
        carregarDados(ano);
    } catch(err: any) {
        toast.error(err.response?.data?.detail || "Erro ao excluir.");
    }
  };

const handleGerarLote = async () => {
    if (!(await confirmDialog(`Gerar Forecasts em lote para ${ano}?\n\nO sistema vai varrer todos os Centros de Custo com Orçamento Base aprovado e criar automaticamente os Forecasts que ainda não existirem.`, {
      title: "Gerar forecasts em lote",
      confirmLabel: "Gerar",
    }))) return;
    setGerandoLote(true);
    try {
      const resp = await forecastService.gerarLote(ano, "DESPESAS", deptId);
      const criados = resp.criados?.length ?? 0;
      const ignorados = resp.ignorados_ja_existentes?.length ?? 0;
      toast.success(`${criados} Forecast(s) criado(s). ${ignorados} já existia(m).`);
      await carregarAnos();
      carregarDados(ano);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao gerar forecasts em lote.");
    } finally {
      setGerandoLote(false);
    }
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
    const defaultPlano = data?.opcoes_planos?.[0]?.id || 0;
    const novaLinha: any = {
      produto_id: produtoId,
      plano_financeiro_id: defaultPlano,
      plano_venda_id: defaultPlano,
      jan: 0, fev: 0, mar: 0, abr: 0, mai: 0, jun: 0, jul: 0, ago: 0, set: 0, out: 0, nov: 0, dez: 0,
      total_anual: 0,
      observacao: "",
      mes: "jan", ticket_medio: 0, numero_vendas: 0, vgv: 0
    };
    setLinhas([...linhas, novaLinha]);
    if (!expandedProducts.includes(produtoId)) {
      setExpandedProducts([...expandedProducts, produtoId]);
    }
  };

  const removerLinha = (index: number) => {
    setLinhas(linhas.filter((_, i) => i !== index));
  };

  const salvar = async () => {
    setSaving(true);
    try {
      await forecastService.salvarDespesas(ano, deptId, linhas);
      toast.success("Forecast salvo com sucesso!");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao salvar forecast. Verifique permissões.");
    } finally {
      setSaving(false);
    }
  };

  const replicarValor = async (index: number, mesOrigem: string) => {
    const linha = linhas[index];
    const valorOrigem = Number(linha[mesOrigem as keyof OrcamentoItemData]) || 0;
    
    const mesesRestantes = MESES.slice(MESES.indexOf(mesOrigem) + 1).filter((_, i) => !data?.meses_fechados?.includes(MESES.indexOf(mesOrigem) + i + 2));
    
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

  const filtroOpcoes = useMemo(() => buildGridFilterOptions(data, false), [data]);

  const { centrosId: opcoesIdCentro, produtos: opcoesProduto, planos: opcoesPlano, empresasId: opcoesIdEmpresa, empresasNome: opcoesEmpresa } = filtroOpcoes;

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

  const customSortFn = (a: number, b: number, config: any) => {
    if (config.key === 'produto') {
      const prodA = data?.opcoes_produtos.find(p => p.id === a);
      const prodB = data?.opcoes_produtos.find(p => p.id === b);
      const nameA = prodA ? `${prodA.id_sienge || ""} - ${prodA.nome}` : "";
      const nameB = prodB ? `${prodB.id_sienge || ""} - ${prodB.nome}` : "";
      return config.direction === 'asc' ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
    }
    
    if (MESES.includes(config.key as string) || config.key === 'total_anual') {
      const sumA = groupedByProduct[a]?.reduce((acc, l) => acc + (Number(l[config.key as keyof OrcamentoItemData]) || 0), 0) || 0;
      const sumB = groupedByProduct[b]?.reduce((acc, l) => acc + (Number(l[config.key as keyof OrcamentoItemData]) || 0), 0) || 0;
      return config.direction === 'asc' ? sumA - sumB : sumB - sumA;
    }
    
    return 0;
  };

  const productIds = useMemo(() => Object.keys(groupedByProduct).map(Number), [groupedByProduct]);

  const { sortConfig, handleSort, sortedData: sortedProductIds } = useTableSort<number>(
    productIds,
    'produto',
    'asc',
    customSortFn
  );



  // Ordenação já feita pelo hook useTableSort

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
      title="Forecast de Despesas"
      subtitle="Acompanhamento e ajuste financeiro de despesas (Forecast)."
      toolbar={
        <BudgetPageToolbar
          scope="forecast"
          holdingMldu={holdingMldu}
          onHoldingMlduChange={setHoldingMldu}
          canUseHoldingMldu={canUseHoldingMldu}
          contextControls={
            <>
              <YearSelect value={ano} years={anosDisponiveis} onChange={setAno} />
              {data && !data.is_empty && data.versoes_disponiveis && data.versoes_disponiveis.length > 0 ? (
                <div className="min-w-[140px]">
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Versão</label>
                  <select
                    value={versaoId || data.forecast_id || ""}
                    onChange={(e) => setVersaoId(Number(e.target.value))}
                    className="w-full py-1.5 px-2.5 text-sm border border-slate-200 rounded-lg bg-white text-slate-800 hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#F5883A]/40 focus:border-[#F5883A]"
                  >
                    {data.versoes_disponiveis.map((v: { id: number; descricao: string }) => (
                      <option key={v.id} value={v.id}>
                        {v.descricao}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}
            </>
          }
          actions={
            <>
              {isAdminOrDiretor ? (
                <button
                  onClick={handleGerarLote}
                  disabled={gerandoLote}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-sm font-medium text-violet-700 bg-violet-50 border border-violet-200 rounded-lg hover:bg-violet-100 transition shadow-sm disabled:opacity-50"
                >
                  {gerandoLote ? (
                    <span className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <span className="text-sm">&#9889;</span>
                  )}
                  Gerar em Lote
                </button>
              ) : null}
              <button
                onClick={() => handleCriarDeBase(0, "Vazio")}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"
              >
                <Plus className="w-4 h-4 text-brand-600" />
                Criar Forecast
              </button>
              <button
                onClick={() => setShowExcel(true)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"
              >
                <FileSpreadsheet className="w-4 h-4 text-brand-green" />
                Excel
              </button>
              {!isBlocked ? (
                <Button variant="primary" onClick={salvar} disabled={saving || loading}>
                  <Save className="mr-2 h-4 w-4" /> {saving ? "Salvando..." : "Salvar Forecast"}
                </Button>
              ) : null}
            </>
          }
        />
      }
      chrome={
        <>
          {holdingMldu ? <HoldingMlduBanner avisos={data?.holding_avisos} /> : null}
          <ForecastVersionHeader forecast={data} deptId={deptId} onStatusChanged={() => carregarDados(ano)} />
          {data && !data.is_empty ? (
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
              <strong>Versão Travada:</strong> Este forecast já está aprovado e é imutável pela interface.
            </div>
          ) : null}
        </>
      }
    >
      {data?.is_empty ? (
        <Card className="flex-1 min-h-0 p-6 flex flex-col items-center justify-center space-y-4 overflow-auto">
          <div className="text-slate-500 text-center">
            <h2 className="text-xl font-bold mb-2">Nenhum Forecast Aberto para {ano}</h2>
            <p>Você pode iniciar um novo forecast a partir de uma base existente.</p>
          </div>
          
          <div className="w-full max-w-md bg-slate-50 p-4 border rounded-md">
            <h3 className="font-semibold text-sm text-slate-700 mb-3">Versões Base Disponíveis:</h3>
            {data.opcoes_base?.length === 0 ? (
              <div className="flex flex-col items-center justify-center space-y-4 py-4">
                <p className="text-sm text-slate-500 text-center">Nenhum orçamento ou forecast aprovado/fechado encontrado para basear.</p>
                <Button size="sm" onClick={() => handleCriarDeBase(0, 'Vazio')}>
                  <Plus className="w-4 h-4 mr-2" />
                  Criar Forecast do Zero
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {data.opcoes_base?.map((opcao: any) => (
                  <div key={`${opcao.tipo}-${opcao.id}`} className="flex justify-between items-center bg-white p-3 border rounded shadow-sm">
                    <div>
                      <span className="font-bold text-slate-700">{opcao.descricao}</span>
                      <span className="ml-2 text-xs text-slate-400">({opcao.tipo})</span>
                    </div>
                    <Button size="sm" onClick={() => handleCriarDeBase(opcao.id, opcao.tipo)}>Usar Base</Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      ) : data && (
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-white rounded-2xl border border-slate-200">
          {loading ? (
          <AppLoadingState />
        ) : (
          <BudgetMatrixScrollArea>
            <table className={BUDGET_MATRIX_TABLE_CLASS}>
              <thead className="text-xs text-slate-700 uppercase bg-slate-100 sticky top-0 z-20">
                <tr>
                  <TableHead sortable sortDirection={sortConfig?.key === 'produto' ? sortConfig.direction : false} onSort={() => handleSort('produto')} className="min-w-[300px] bg-slate-100 sticky left-0 z-30 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">Produto (C.C.) / Plano Financeiro</TableHead>
                  {mesesVisiveis.map(mes => (
                    <TableHead sortable sortDirection={sortConfig?.key === mes ? sortConfig.direction : false} onSort={() => handleSort(mes)} key={mes} className="w-[100px] text-center bg-slate-100 border-l border-slate-200">{mes.toUpperCase()}</TableHead>
                  ))}
                  <TableHead sortable sortDirection={sortConfig?.key === 'total_anual' ? sortConfig.direction : false} onSort={() => handleSort('total_anual')} className="w-[120px] text-right font-bold text-brand-700 bg-slate-100 border-l border-slate-200 hover:bg-brand-50">TOTAL (R$)</TableHead>
                  <TableHead className="min-w-[200px] bg-slate-100 border-l border-slate-200">Observação</TableHead>
                  <TableHead className="text-center bg-slate-100 border-l border-slate-200">Ações</TableHead>
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
                            <td key={`prod-m-${mes}`} className={`px-3 py-2 text-right border-l border-slate-200 font-semibold text-brand-700 ${data?.meses_fechados?.includes(MESES.indexOf(mes) + 1) ? "bg-red-50/50" : "bg-slate-50"}`}>
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
                                      const novas = [...linhas];
                                      novas[globalIdx].plano_financeiro_id = Number(e.target.value);
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
                                      {data?.meses_fechados?.includes(MESES.indexOf(mes) + 1) ? (
                                        <div className="w-full text-xs text-right p-1 text-slate-500 flex items-center justify-end">
                                          <span className="mr-1">🔒</span>
                                          {Number(linha[mes as keyof OrcamentoItemData] || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                        </div>
                                      ) : (
                                        <input
                                          type="number"
                                          className="w-full p-1 text-xs text-right border-0 border-b border-transparent focus:border-brand-500 focus:ring-0 bg-transparent hover:bg-slate-50 transition-colors [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none disabled:bg-transparent disabled:border-transparent"
                                          value={linha[mes as keyof OrcamentoItemData] || ''}
                                          disabled={isBlocked}
                                          onChange={(e) => handleInputChange(globalIdx, mes as keyof OrcamentoItemData, e.target.value)}
                                          placeholder="0.00"
                                        />
                                      )}
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

        
      </div>
      )}

      {showExcel && (
        <ExcelImportModal
          tipo="DESPESAS"
          ano={ano}
          deptId={deptId}
          orcamentoId={data?.forecast_id}
          onClose={() => setShowExcel(false)}
          onSuccess={() => { setShowExcel(false); carregarDados(ano); }}
        />
      )}

    
      {showCriarBaseModal && (
        <Modal isOpen={showCriarBaseModal} onClose={() => setShowCriarBaseModal(false)} title="Selecione o Empreendimento">
          <div className="space-y-4">
            <p className="text-sm text-slate-500">Selecione o Centro de Custo para criar.</p>
            <SearchableSelect
              options={data?.opcoes_produtos?.map((p: any) => ({
                id: p.id,
                label: p.id_sienge ? `${p.id_sienge} - ${p.nome}` : p.nome
              })) || []}
              value={produtoCriacaoId}
              onChange={(val) => setProdutoCriacaoId(Number(val))}
              placeholder="Pesquise ou selecione..."
            />
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setShowCriarBaseModal(false)}>Cancelar</Button>
              <Button onClick={() => {
                if(!produtoCriacaoId) { toast.error("Selecione um empreendimento"); return; }
                handleCriarDeBaseFinal(produtoCriacaoId);
              }}>Criar</Button>
            </div>
          </div>
        </Modal>
      )}
    </BudgetMatrixShell>
  );
}
