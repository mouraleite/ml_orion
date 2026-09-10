"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import { Card } from "@/components/ui/Card";
import { Modal }
from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { forecastService, ForecastVendasResponse } from "@/services/forecast";
import { OrcamentoVendaLinha, MesVenda } from "@/services/orcamento";
import { Save, Copy, Plus, Trash2, ChevronDown, ChevronRight, FileSpreadsheet, Lock } from "lucide-react";
import { ForecastVersionHeader } from "@/components/forecast/ForecastVersionHeader";
import { useAuth } from "@/contexts/AuthContext";
import { isAdminOrDiretorUser } from "@/lib/roles";
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
import { buildEmpresaLinkedOptions } from "@/lib/gridFilters";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId } from "@/lib/useActiveDepartmentId";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { ExcelImportModal } from "@/components/forecast/ExcelImportModal";
import { MonthSelector } from "@/components/orcamento/MonthSelector";
import { TableHead } from "@/components/ui/Table";
import { useTableSort, SortConfig } from "@/hooks/useTableSort";
import { CurrencyInput } from "@/components/ui/CurrencyInput";


import toast from 'react-hot-toast';
import { MESES_VENDAS } from "@/lib/months";
import { parseCentroNome } from "@/lib/parseCentroNome";

const MESES = [...MESES_VENDAS];

export default function ForecastVendasPage() {
  const { user, loading: authLoading } = useAuth();
  const deptId = useActiveDepartmentId();
  const { holdingMldu, setHoldingMldu, canUseHoldingMldu } = useHoldingMldu("forecast");
  const currentYear = new Date().getFullYear();
  const [ano, setAno] = useState<number>(currentYear);
  const [versaoId, setVersaoId] = useState<number | undefined>(undefined);
  const [anosDisponiveis, setAnosDisponiveis] = useState<number[]>([]);
  const [data, setData] = useState<ForecastVendasResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [linhas, setLinhas] = useState<OrcamentoVendaLinha[]>([]);
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
  const [accessDenied, setAccessDenied] = useState(false);

  // Estados de Filtro
  const [busca, setBusca] = useState("");
  const [activeTab, setActiveTab] = useState<'vendas'|'distratos'|'liquidas'>('vendas');
  const [filtroIdCentro, setFiltroIdCentro] = useState<string[]>([]);
  const [filtroProduto, setFiltroProduto] = useState<string[]>([]);
  const [filtroPlano, setFiltroPlano] = useState<string[]>([]);
  const [selectedMonths, setSelectedMonths] = useState<number[]>(MESES.map(m => m.id));
  const [filtroEmpresaIds, setFiltroEmpresaIds] = useState<string[]>([]);

  const patchGridFilters = (patch: Partial<MonthlyGridFilterValues>) => {
    if (patch.busca !== undefined) setBusca(patch.busca);
    if (patch.filtroIdCentro !== undefined) setFiltroIdCentro(patch.filtroIdCentro);
    if (patch.filtroProduto !== undefined) setFiltroProduto(patch.filtroProduto);
    if (patch.filtroPlano !== undefined) setFiltroPlano(patch.filtroPlano);
    if (patch.filtroEmpresaIds !== undefined) setFiltroEmpresaIds(patch.filtroEmpresaIds);
  };

  const carregarAnos = async () => {
    try {
      const resp = await forecastService.getAnosDisponiveis("VENDAS", deptId, false);
      setAnosDisponiveis(resp.anos);
      return resp.anos;
    } catch (err: any) {
      if (err.response?.status === 403) setAccessDenied(true);
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
    setAccessDenied(false);
    try {
      const resp = await forecastService.getVendas(selectedAno, deptId, false, vId, holdingMldu);
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
      if (err.response?.status === 403) {
        setAccessDenied(true);
      } else if (err?.response?.status === 404) {
        setData(null);
        setLinhas([]);
      } else {
        toast.error("Erro ao carregar forecast de vendas.");
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
        "VENDAS", 
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

  const handleGerarLote = async () => {
    if (!(await confirmDialog(`Gerar Forecasts em lote para ${ano}?\n\nO sistema vai varrer todos os Centros de Custo com Orçamento Base aprovado e criar automaticamente os Forecasts que ainda não existirem.`, {
      title: "Gerar forecasts em lote",
      confirmLabel: "Gerar",
    }))) return;
    setGerandoLote(true);
    try {
      const resp = await forecastService.gerarLote(ano, "VENDAS", deptId);
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
  
  const handleDeleteEmpreendimento = async (produtoId: number) => {
    if(!(await confirmDialog('Tem certeza que deseja excluir os dados deste Empreendimento?', { variant: "danger" }))) return;
    try {
        const map_id = data?.mapa_ids?.[produtoId];
        if(!map_id) { toast.error("ID não encontrado"); return; }
        await forecastService.delete(map_id);
        toast.success("Excluído com sucesso.");
        carregarDados(ano);
    } catch(err: any) {
        toast.error(err.response?.data?.detail || "Erro ao excluir.");
    }
  };

  const isDistratoFn = (l: OrcamentoVendaLinha) => l.observacao?.includes('Distrato') || l.meses.some(m => (m.numero_vendas || 0) < 0) || (data?.opcoes_planos.find((p: any) => p.id === l.plano_venda_id)?.nome || '').includes('Distrato');

  const findTicketMedioVenda = (linha: OrcamentoVendaLinha, mesId: number) => {
    const venda = linhas.find(l => 
      l.produto_id === linha.produto_id && 
      l.plano_venda_id === linha.plano_venda_id && 
      !isDistratoFn(l)
    );
    if (venda) {
      const m = venda.meses.find(m => m.mes === mesId);
      if (m && m.ticket_medio > 0) return m.ticket_medio;
      const totalVGV = venda.meses.reduce((acc, mv) => acc + (mv.vgv || 0), 0);
      const totalQtd = venda.meses.reduce((acc, mv) => acc + (mv.numero_vendas || 0), 0);
      if (totalQtd > 0) return totalVGV / totalQtd;
    }
    return 0;
  };

  const handleInputChange = (
    linhaIndex: number, 
    mesId: number, 
    campo: "ticket_medio" | "numero_vendas", 
    valorStr: string | number
  ) => {
    const valorRaw = typeof valorStr === 'number' ? valorStr : parseFloat(String(valorStr).replace(',', '.')) || 0;
    const isDistratoTab = activeTab === 'distratos';
    const multiplicador = (isDistratoTab && campo === 'numero_vendas') ? -1 : 1;
    let valor = campo === 'ticket_medio' ? Math.round(valorRaw * 100) / 100 : valorRaw * multiplicador;
    
    const novasLinhas = [...linhas];
    const linha = novasLinhas[linhaIndex];
    
    let mesObj = linha.meses.find(m => m.mes === mesId);
    if (!mesObj) {
      mesObj = { mes: mesId, ticket_medio: 0, numero_vendas: 0, vgv: 0 };
      linha.meses.push(mesObj);
    }

    if (campo === 'numero_vendas') {
      mesObj.numero_vendas = valor;
      if (isDistratoTab) {
         const tk = findTicketMedioVenda(linha, mesId);
         if (tk > 0) mesObj.ticket_medio = tk;
      }
    } else {
      mesObj.ticket_medio = valor;
    }
    
    mesObj.vgv = Math.round(mesObj.ticket_medio * mesObj.numero_vendas * 100) / 100;

    setLinhas(novasLinhas);
  };

  const replicarValor = async (linhaIndex: number, mesIdOrigem: number, campo: "ticket_medio" | "numero_vendas") => {
    const novasLinhas = [...linhas];
    const linha = novasLinhas[linhaIndex];
    const mesOrigem = linha.meses.find(m => m.mes === mesIdOrigem);
    
    if (!mesOrigem) return;
    const valorOrigem = mesOrigem[campo];

    const mesesRestantes = MESES.filter(m => m.id > mesIdOrigem && !data?.meses_fechados?.includes(m.id));
    let precisaConfirmacao = false;

    for (const m of mesesRestantes) {
      const mesAtual = linha.meses.find(xm => xm.mes === m.id);
      if (mesAtual && mesAtual[campo] > 0) {
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

    mesesRestantes.forEach(m => {
      let mesAlvo = linha.meses.find(xm => xm.mes === m.id);
      if (!mesAlvo) {
        mesAlvo = { mes: m.id, ticket_medio: 0, numero_vendas: 0, vgv: 0 };
        linha.meses.push(mesAlvo);
      }
      mesAlvo[campo] = valorOrigem;
      mesAlvo.vgv = mesAlvo.ticket_medio * mesAlvo.numero_vendas;
    });

    setLinhas(novasLinhas);
    toast.success(`Valor replicado em diante.`);
  };

  const aplicarIPCA = (linhaIndex: number, mesIdOrigem: number) => {
    const percStr = window.prompt("Informe a taxa de IPCA (%) para aplicar em cascata:");
    if (!percStr) return;
    const perc = parseFloat(percStr.replace(',', '.'));
    if (isNaN(perc)) return;

    const multiplicador = 1 + (perc / 100);
    const novasLinhas = [...linhas];
    const linha = novasLinhas[linhaIndex];
    const mesOrigem = linha.meses.find(m => m.mes === mesIdOrigem);
    
    if (!mesOrigem) return;
    
    let currentTicket = mesOrigem.ticket_medio;
    const mesesRestantes = MESES.filter(m => m.id > mesIdOrigem && !data?.meses_fechados?.includes(m.id));

    mesesRestantes.forEach(m => {
      let mesAlvo = linha.meses.find(xm => xm.mes === m.id);
      if (!mesAlvo) {
        mesAlvo = { mes: m.id, ticket_medio: 0, numero_vendas: 0, vgv: 0 };
        linha.meses.push(mesAlvo);
      }
      currentTicket = currentTicket * multiplicador;
      mesAlvo.ticket_medio = currentTicket;
      mesAlvo.vgv = mesAlvo.ticket_medio * mesAlvo.numero_vendas;
    });

    setLinhas(novasLinhas);
    toast.success(`IPCA de ${perc}% aplicado com sucesso!`);
  };

  const adicionarLinhaProduto = (produtoId: number) => {
    const isDistratoTab = activeTab === 'distratos';
    const distratoPlan = data?.opcoes_planos?.find((p: any) => p.nome.includes('Distrato'));
    const defaultPlano = isDistratoTab 
      ? (distratoPlan?.id || data?.opcoes_planos?.[0]?.id || 0) 
      : data?.opcoes_planos?.[0]?.id || 0;
      
    const novaLinha: any = {
      produto_id: produtoId,
      plano_financeiro_id: defaultPlano,
      plano_venda_id: defaultPlano,
      total_anual: 0,
      observacao: isDistratoTab ? "(Distrato)" : "",
      meses: MESES.map(m => ({ mes: m.id, ticket_medio: 0, numero_vendas: 0, vgv: 0 }))
    };
    setLinhas([...linhas, novaLinha]);
    if (!expandedProducts.includes(produtoId)) {
      setExpandedProducts([...expandedProducts, produtoId]);
    }
  };

  const salvar = async () => {
    setSaving(true);
    try {
      await forecastService.salvarVendas(ano, deptId, linhas);
      toast.success("Forecast salvo com sucesso!");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao salvar forecast.");
    } finally {
      setSaving(false);
    }
  };

  const getDiffClass = (linha: OrcamentoVendaLinha, mesId: number, campo: "ticket_medio" | "numero_vendas" | "vgv") => {
    if (!data?.itens_base || data.itens_base.length === 0) return "";
    const baseItem = data.itens_base.find(b => b.produto_id === linha.produto_id && b.plano_venda_id === linha.plano_venda_id && b.mes === mesId);
    if (!baseItem) return "bg-green-50"; 
    
    const currItem = linha.meses.find(m => m.mes === mesId);
    if (!currItem) return "";
    if (currItem[campo] !== baseItem[campo]) return "bg-amber-100 border-amber-300 text-amber-900"; 
    return "";
  };

  const isBlocked =
    holdingMldu ||
    ["Em aprovação", "Aprovado", "Fechado", "Solicitação Reabertura"].includes(data?.status || "");

  const filtroOpcoes = useMemo(() => {
    if (!data) return { centrosId: [], produtos: [], planos: [], empresasId: [], empresasNome: [] };
    const centrosId = Array.from(new Set(data.opcoes_produtos.map(p => p.id_sienge || String(p.id)))).sort((a, b) => Number(a) - Number(b));
    const produtos = Array.from(new Set(data.opcoes_produtos.map(p => parseCentroNome(p.nome).produto)));
    const plans = Array.from(new Set(data.opcoes_planos.map(p => p.nome)));
    const empresas = buildEmpresaLinkedOptions(data.opcoes_produtos);
    
    return {
      centrosId: centrosId.map(id => ({ value: id as string, label: id as string })),
      produtos: produtos.map(p => ({ value: p as string, label: p as string })),
      planos: plans.map(p => ({ value: p as string, label: p as string })),
      empresasId: empresas.empresasId,
      empresasNome: empresas.empresasNome,
    };
  }, [data]);

  const { centrosId: opcoesIdCentro, produtos: opcoesProduto, planos: opcoesPlano, empresasId: opcoesIdEmpresa, empresasNome: opcoesEmpresa } = filtroOpcoes;

  // Filtragem
  const linhasFiltradas = useMemo(() => {
    let baseLinhas = linhas;

    if (activeTab === 'liquidas') {
      const combinadas = new Map<string, OrcamentoVendaLinha>();
      for (const linha of linhas) {
        const key = `${linha.produto_id}-${linha.plano_venda_id}`;
        if (!combinadas.has(key)) {
          combinadas.set(key, JSON.parse(JSON.stringify(linha)));
        } else {
          const exist = combinadas.get(key)!;
          for (const mes of linha.meses) {
            const exMes = exist.meses.find(m => m.mes === mes.mes);
            if (exMes) {
              exMes.numero_vendas = (exMes.numero_vendas || 0) + (mes.numero_vendas || 0);
              exMes.vgv = (exMes.vgv || 0) + (mes.vgv || 0);
              if (exMes.numero_vendas !== 0) {
                exMes.ticket_medio = Math.abs(exMes.vgv / exMes.numero_vendas);
              }
            } else {
              exist.meses.push({ ...mes });
            }
          }
        }
      }
      baseLinhas = Array.from(combinadas.values());
    }

    return baseLinhas.filter(linha => {
      if (activeTab !== 'liquidas') {
        const isDistrato = isDistratoFn(linha);
        if (activeTab === 'vendas' && isDistrato) return false;
        if (activeTab === 'distratos' && !isDistrato) return false;
      }

      const produtoInfo = data?.opcoes_produtos.find(p => p.id === linha.produto_id);
      const planoInfo = data?.opcoes_planos.find(p => p.id === linha.plano_venda_id);
      const nomeCompleto = produtoInfo ? `${produtoInfo.id_sienge || ""} - ${produtoInfo.nome}` : "";
      
      if (busca && !nomeCompleto.toLowerCase().includes(busca.toLowerCase())) return false;
      if (filtroIdCentro.length > 0 && produtoInfo && !filtroIdCentro.includes(produtoInfo.id_sienge || String(produtoInfo.id))) return false;
      if (filtroProduto.length > 0 && produtoInfo && !filtroProduto.includes(parseCentroNome(produtoInfo.nome).produto)) return false;
      if (filtroPlano.length > 0 && planoInfo && !filtroPlano.includes(planoInfo.nome)) return false;
      if (filtroEmpresaIds.length > 0 && produtoInfo && !filtroEmpresaIds.includes(produtoInfo.id_empresa || '')) return false;

      return true;
    });
  }, [linhas, activeTab, busca, filtroIdCentro, filtroProduto, filtroPlano, filtroEmpresaIds, data]);

  const groupedByProduct = useMemo(() => {
    const groups: Record<number, OrcamentoVendaLinha[]> = {};
    linhasFiltradas.forEach((linha) => {
      if (!groups[linha.produto_id]) groups[linha.produto_id] = [];
      groups[linha.produto_id].push(linha);
    });
    return groups;
  }, [linhasFiltradas]);

  const customSortFn = useCallback((a: number, b: number, config: SortConfig<number>) => {
    if (config.key === 'produto') {
      const prodA = data?.opcoes_produtos.find(p => p.id === a);
      const prodB = data?.opcoes_produtos.find(p => p.id === b);
      const nameA = prodA ? `${prodA.id_sienge || ""} - ${prodA.nome}` : "";
      const nameB = prodB ? `${prodB.id_sienge || ""} - ${prodB.nome}` : "";
      return config.direction === 'asc' ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
    }
    
    const mesIdNum = parseInt(config.key as string);
    if (!isNaN(mesIdNum)) {
      const sumA = groupedByProduct[a].reduce((acc, l) => acc + (l.meses.find(m => m.mes === mesIdNum)?.vgv || 0), 0);
      const sumB = groupedByProduct[b].reduce((acc, l) => acc + (l.meses.find(m => m.mes === mesIdNum)?.vgv || 0), 0);
      return config.direction === 'asc' ? sumA - sumB : sumB - sumA;
    }

    if (config.key === 'total_anual') {
      const sumA = groupedByProduct[a].reduce((acc, l) => acc + l.meses.reduce((s, m) => s + (m.vgv || 0), 0), 0);
      const sumB = groupedByProduct[b].reduce((acc, l) => acc + l.meses.reduce((s, m) => s + (m.vgv || 0), 0), 0);
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

  const mesesVisiveis = MESES.filter(m => selectedMonths.includes(m.id));

  const toggleProduct = (prodId: number) => {
    if (expandedProducts.includes(prodId)) {
      setExpandedProducts(expandedProducts.filter(id => id !== prodId));
    } else {
      setExpandedProducts([...expandedProducts, prodId]);
    }
  };

  const calcularTotalGeralColunaQtd = (mesId: number) => {
    return linhas.reduce((acc, l) => acc + (l.meses.find(m => m.mes === mesId)?.numero_vendas || 0), 0);
  };
  const calcularTotalGeralColunaVGV = (mesId: number) => {
    return linhas.reduce((acc, l) => acc + (l.meses.find(m => m.mes === mesId)?.vgv || 0), 0);
  };
  const calcularTotalGeralAnualVGV = () => {
    return linhas.reduce((acc, l) => acc + l.meses.reduce((s, m) => s + (m.vgv || 0), 0), 0);
  };

  if (accessDenied) {
    return (
      <div className="w-full h-full flex items-center justify-center p-6 bg-slate-50">
        <Card className="max-w-md p-8 text-center space-y-4">
          <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto">
            <Lock size={32} />
          </div>
          <h2 className="text-xl font-bold text-slate-800">Acesso Restrito</h2>
          <p className="text-slate-600">
            O Forecast de Vendas é de uso exclusivo do <strong>Departamento Comercial</strong> e da Diretoria.
          </p>
          <Button variant="primary" onClick={() => window.history.back()}>
            Voltar
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <BudgetMatrixShell
      title="Forecast de Vendas"
      subtitle="Matriz de previsão atualizada de VGV por produto e plano de pagamento."
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
          {data && !data.is_empty ? (
            <div className="flex space-x-6 border-b border-slate-200 px-2">
              <button
                onClick={() => setActiveTab('vendas')}
                className={`pb-2 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'vendas' ? 'border-brand-500 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
              >
                Forecast de Vendas
              </button>
              <button
                onClick={() => setActiveTab('distratos')}
                className={`pb-2 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'distratos' ? 'border-brand-500 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
              >
                Forecast de Distratos
              </button>
              <button
                onClick={() => setActiveTab('liquidas')}
                className={`pb-2 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'liquidas' ? 'border-brand-500 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
              >
                Vendas Líquidas
              </button>
            </div>
          ) : null}
          {data && !data.is_empty ? (
            <MonthlyGridFilterPanel
              values={{ busca, filtroIdCentro, filtroProduto, filtroPlano, filtroEmpresaIds }}
              onChange={patchGridFilters}
              opcoesIdCentro={opcoesIdCentro}
              opcoesProduto={opcoesProduto}
              opcoesPlano={opcoesPlano}
              opcoesEmpresaId={opcoesIdEmpresa}
              opcoesEmpresaNome={opcoesEmpresa}
              planoLabel="Forma de Venda"
            />
          ) : null}
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
                  <TableHead className="px-3 py-3 min-w-[300px] bg-slate-100 sticky left-0 z-30 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]" sortable sortDirection={sortConfig?.key === 'produto' ? sortConfig.direction : false} onClick={() => handleSort('produto')}>
                    {activeTab === 'distratos' ? 'Produto (C.C.)' : 'Produto (C.C.) / Forma de Venda'}
                  </TableHead>
                  {mesesVisiveis.map(mes => (
                    <TableHead key={mes.id} className="px-3 py-3 w-[120px] text-center bg-slate-100 border-l border-slate-200" sortable sortDirection={sortConfig?.key === String(mes.id) ? sortConfig.direction : false} onClick={() => handleSort(String(mes.id))}>{mes.label.toUpperCase()}</TableHead>
                  ))}
                  <TableHead className="px-3 py-3 w-[120px] text-right font-bold text-brand-700 bg-slate-100 border-l border-slate-200" sortable sortDirection={sortConfig?.key === 'total_anual' ? sortConfig.direction : false} onClick={() => handleSort('total_anual')}>TOTAL VGV (R$)</TableHead>
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
                    
                    const totaisProdVGV: Record<number, number> = {};
                    const totaisProdQtd: Record<number, number> = {};
                    let vgvAnualProd = 0;
                    
                    mesesVisiveis.forEach(m => { 
                      totaisProdVGV[m.id] = 0; 
                      totaisProdQtd[m.id] = 0;
                    });

                    groupLinhas.forEach(l => {
                      l.meses.forEach(m => {
                        if (totaisProdVGV[m.mes] !== undefined) {
                          totaisProdVGV[m.mes] += (m.vgv || 0);
                          totaisProdQtd[m.mes] += (m.numero_vendas || 0);
                        }
                        vgvAnualProd += (m.vgv || 0);
                      });
                    });

                    return (
                      <React.Fragment key={`prod-${produtoId}`}>
                        {/* Célula Master do Produto */}
                        <tr className="bg-slate-50 border-y hover:bg-slate-100 cursor-pointer transition-colors group" onClick={() => toggleProduct(produtoId)}>
                          <td className="px-3 py-3 font-bold text-slate-800 flex items-center whitespace-nowrap sticky left-0 z-10 bg-slate-50 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] group-hover:bg-slate-100">
                            {isExpanded ? <ChevronDown size={16} className="mr-1 text-brand-600" /> : <ChevronRight size={16} className="mr-1 text-slate-400" />}
                            {produto ? `${produto.id_sienge ? produto.id_sienge + ' - ' : ''}${produto.nome}` : `Produto #${produtoId}`} {activeTab === 'distratos' ? '- Distratos' : (activeTab === 'liquidas' ? '- Vendas Líquidas' : '- Vendas')}
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
                            <td key={`prod-m-${mes.id}`} className={`px-3 py-2 text-right border-l border-slate-200 ${data?.meses_fechados?.includes(mes.id) ? "bg-red-50/50" : "bg-slate-50"}`}>
                              <div className="text-[10px] text-slate-500 uppercase">QTD: {totaisProdQtd[mes.id]}</div>
                              <div className="font-semibold text-brand-700 text-sm mt-0.5">
                                {totaisProdVGV[mes.id].toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                              </div>
                            </td>
                          ))}
                          <td className="px-3 py-3 text-right font-bold text-brand-800 border-l border-slate-200 bg-brand-50/50">
                            {vgvAnualProd.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="px-3 py-3 border-l border-slate-200 text-center"></td>
                        </tr>

                        {isExpanded && groupLinhas.map((linha) => {
                          const globalIdx = linhas.indexOf(linha);
                          const totalVGVLinha = linha.meses.reduce((acc, m) => acc + (m.vgv || 0), 0);

                          return (
                            <React.Fragment key={`linha-${globalIdx}`}>
                              {activeTab !== 'distratos' && (
                                <tr className="bg-white border-t border-slate-100 hover:bg-slate-50 group">
                                  <td className="px-3 py-2 pl-8 font-medium text-slate-700 whitespace-nowrap bg-white border-l-2 border-l-brand-400 sticky left-0 z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] group-hover:bg-slate-50">
                                    <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                                      FORMA DE VENDA
                                    </label>
                                    <select
                                      className="w-full p-1 border rounded text-sm bg-slate-50 focus:bg-white disabled:opacity-75"
                                      value={linha.plano_venda_id}
                                      disabled={isBlocked || activeTab === 'liquidas'}
                                      onChange={(e) => {
                                        const novas = [...linhas];
                                        novas[globalIdx].plano_venda_id = Number(e.target.value);
                                        setLinhas(novas);
                                      }}
                                    >
                                      {data?.opcoes_planos.map(p => (
                                        <option key={p.id} value={p.id}>{p.nome}</option>
                                      ))}
                                    </select>
                                  </td>
                                  <td colSpan={mesesVisiveis.length + 2} className="bg-white border-l border-slate-100"></td>
                                </tr>
                              )}
                              
                              <tr className="bg-white border-none group/row">
                                <td className="px-3 py-1 pl-12 text-xs text-slate-500 whitespace-nowrap bg-white sticky left-0 z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] group-hover/row:bg-slate-50 border-l-2 border-l-brand-400">↳ Ticket Médio (R$)</td>
                                {mesesVisiveis.map(mes => {
                                  const mObj = linha.meses.find(m => m.mes === mes.id);
                                  return (
                                    <td key={`tkt-${mes.id}`} className={`px-1 py-1 border-l border-slate-100 relative group/cell ${getDiffClass(linha, mes.id, 'ticket_medio')}`}>
                                      <div className="flex items-center">
                                        <CurrencyInput
                                          value={mObj?.ticket_medio || 0}
                                          disabled={isBlocked || activeTab === 'liquidas'}
                                          onChange={(val: number) => handleInputChange(globalIdx, mes.id, 'ticket_medio', val)}
                                          placeholder="0,00"
                                        />
                                        {!isBlocked && activeTab !== 'liquidas' && mes.id !== 12 && (
                                          <div className="absolute right-0 top-0 bottom-0 flex items-center bg-white shadow-sm border rounded px-1 opacity-0 group-hover/cell:opacity-100 z-10 transition-opacity translate-x-1/2 gap-1">
                                            <button onClick={() => replicarValor(globalIdx, mes.id, 'ticket_medio')} className="text-slate-400 hover:text-brand-600" title="Replicar">
                                              <Copy size={12} />
                                            </button>
                                            <button onClick={() => aplicarIPCA(globalIdx, mes.id)} className="text-slate-400 hover:text-emerald-600 font-bold text-[10px]" title="Aplicar IPCA">
                                              %
                                            </button>
                                          </div>
                                        )}
                                      </div>
                                    </td>
                                  )
                                })}
                                <td className="border-l border-slate-100"></td>
                                <td rowSpan={3} className="px-3 py-2 text-center border-l border-slate-100 align-middle">
                                  {!isBlocked && activeTab !== 'liquidas' && (
                                    <button 
                                      onClick={() => setLinhas(linhas.filter((_, i) => i !== globalIdx))}
                                      className="text-xs text-brand-red hover:text-brand-red font-semibold"
                                    >
                                      Excluir
                                    </button>
                                  )}
                                </td>
                              </tr>

                              <tr className="bg-white border-none group/row">
                                <td className="px-3 py-1 pl-12 text-xs text-slate-500 whitespace-nowrap bg-white sticky left-0 z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] group-hover/row:bg-slate-50 border-l-2 border-l-brand-400">↳ {activeTab === 'distratos' ? 'Distrato (Qtd)' : 'Vendas (Qtd)'}</td>
                                {mesesVisiveis.map(mes => {
                                  const mObj = linha.meses.find(m => m.mes === mes.id);
                                  return (
                                    <td key={`qtd-${mes.id}`} className={`px-1 py-1 border-l border-slate-100 relative group/cell ${getDiffClass(linha, mes.id, 'numero_vendas')}`}>
                                      <div className="flex items-center">
                                        {data?.meses_fechados?.includes(mes.id) ? (
                                          <div className="w-full text-xs text-right p-1 font-medium text-slate-500 flex items-center justify-end">
                                            {Number(mObj?.numero_vendas || 0)}
                                          </div>
                                        ) : (
                                          <input
                                            type="number"
                                            className="w-full p-1 text-xs text-right font-medium text-slate-700 border-0 border-b border-transparent focus:border-brand-500 focus:ring-0 bg-transparent hover:bg-slate-50 transition-colors [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none disabled:bg-transparent disabled:border-transparent"
                                            value={mObj?.numero_vendas || ''}
                                            disabled={isBlocked || activeTab === 'liquidas'}
                                            onChange={(e) => handleInputChange(globalIdx, mes.id, 'numero_vendas', e.target.value)}
                                            placeholder="0"
                                          />
                                        )}
                                        {!isBlocked && activeTab !== 'liquidas' && mes.id !== 12 && (
                                          <button 
                                            onClick={() => replicarValor(globalIdx, mes.id, 'numero_vendas')}
                                            className="absolute right-0 top-1/2 -translate-y-1/2 opacity-0 group-hover/cell:opacity-100 p-1 bg-white text-brand-600 border shadow-sm rounded-full hover:bg-slate-50 z-10 transition-opacity translate-x-1/2"
                                            title="Replicar"
                                          >
                                            <Copy size={10} />
                                          </button>
                                        )}
                                      </div>
                                      {mObj?.origem_venda && (
                                        <div className="text-[9px] text-center text-slate-400 mt-1 truncate" title={mObj.origem_venda}>
                                          {mObj.origem_venda}
                                        </div>
                                      )}
                                    </td>
                                  )
                                })}
                                <td className="border-l border-slate-100"></td>
                              </tr>

                              <tr className="bg-slate-50/50 border-b border-slate-200">
                                <td className="px-3 py-2 pl-12 text-xs font-semibold text-slate-700 whitespace-nowrap bg-slate-50/50 sticky left-0 z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] border-l-2 border-l-brand-400">VGV Mensal (R$)</td>
                                {mesesVisiveis.map(mes => {
                                  const mObj = linha.meses.find(m => m.mes === mes.id);
                                  return (
                                    <td key={`vgv-${mes.id}`} className={`px-2 py-2 text-right text-xs font-semibold text-brand-700 border-l border-slate-100 ${getDiffClass(linha, mes.id, 'vgv')}`}>
                                      {(mObj?.vgv || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </td>
                                  )
                                })}
                                <td className="px-3 py-2 text-right font-bold text-brand-800 border-l border-slate-200 bg-brand-50/50">
                                  {totalVGVLinha.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
              <tfoot className="bg-slate-100 font-bold sticky bottom-0 z-10">
                <tr>
                  <td className="px-3 py-3 text-right border-r border-slate-200 flex flex-col">
                    <span>TOTAIS GERAIS:</span>
                  </td>
                  {mesesVisiveis.map(mes => (
                    <td key={`tfoot-${mes.id}`} className="px-3 py-3 text-right text-brand-700 border-l border-slate-200">
                      <div className="text-[10px] text-slate-500 uppercase">QTD: {calcularTotalGeralColunaQtd(mes.id)}</div>
                      <div>{calcularTotalGeralColunaVGV(mes.id).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                    </td>
                  ))}
                  <td className="px-3 py-3 text-right text-brand-700 bg-brand-200/50 text-base border-l border-slate-200">
                    {calcularTotalGeralAnualVGV().toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="border-l border-slate-200"></td>
                </tr>
              </tfoot>
            </table>
          </BudgetMatrixScrollArea>
        )}

        
      </div>
      )}

      {showExcel && (
        <ExcelImportModal
          tipo="VENDAS"
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
