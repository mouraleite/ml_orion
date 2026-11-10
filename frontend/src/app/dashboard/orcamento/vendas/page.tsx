"use client";

import React, { useEffect, useState, useMemo } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { 
  orcamentoService, 
  OrcamentoVendasResponse, 
  OrcamentoVendaLinha,
} from "@/services/orcamento";
import { Save, Copy, Plus, Trash2, ChevronDown, ChevronRight, Lock, FileSpreadsheet } from "lucide-react";
import { CriarOrcamentoModal } from "@/components/orcamento/CriarOrcamentoModal";
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
import { buildEmpresaLinkedOptions } from "@/lib/gridFilters";
import { idPublicoSienge, idsPublicosCentro } from "@/lib/idSienge";
import { YearSelect } from "@/components/shared/YearSelect";
import { HoldingMlduBanner } from "@/components/shared/HoldingMlduBanner";
import { useHoldingMldu } from "@/hooks/useHoldingMldu";
import { useActiveDepartmentId } from "@/lib/useActiveDepartmentId";
import { VersionHeader } from "@/components/orcamento/VersionHeader";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { ExcelImportModal } from "@/components/orcamento/ExcelImportModal";
import { IpcaCascataModal } from "@/components/orcamento/IpcaCascataModal";
import { MonthSelector } from "@/components/orcamento/MonthSelector";
import { CurrencyInput } from "@/components/ui/CurrencyInput";
import toast from 'react-hot-toast';
import { useTableSort } from "@/hooks/useTableSort";
import { TableHead } from "@/components/ui/Table";
import { MESES_VENDAS } from "@/lib/months";
import { parseCentroNome } from "@/lib/parseCentroNome";

const MESES = [...MESES_VENDAS];

export default function OrcamentoVendasPage() {
  const { user, loading: authLoading } = useAuth();
  const deptId = useActiveDepartmentId();
  const { holdingMldu, setHoldingMldu, canUseHoldingMldu } = useHoldingMldu("orcamento");
  const currentYear = new Date().getFullYear();
  const [ano, setAno] = useState<number>(currentYear);
  const [anosDisponiveis, setAnosDisponiveis] = useState<number[]>([]);
  const [showCriarModal, setShowCriarModal] = useState(false);
  const [data, setData] = useState<OrcamentoVendasResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [linhas, setLinhas] = useState<OrcamentoVendaLinha[]>([]);
  const [showExcel, setShowExcel] = useState(false);
  const [expandedProducts, setExpandedProducts] = useState<number[]>([]);
  const [accessDenied, setAccessDenied] = useState(false);
  const [novoProdutoId, setNovoProdutoId] = useState<number | "">("");
  const [novoPlanoId, setNovoPlanoId] = useState<number | "">("");
  const [selectedMonths, setSelectedMonths] = useState<number[]>(MESES.map(m => m.id));
  const [activeTab, setActiveTab] = useState<'vendas'|'distratos'|'liquidas'>('vendas');

  // Filtros
  const [busca, setBusca] = useState("");
  const [filtroIdCentro, setFiltroIdCentro] = useState<string[]>([]);
  const [filtroProduto, setFiltroProduto] = useState<string[]>([]);
  const [filtroPlano, setFiltroPlano] = useState<string[]>([]);
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
      const resp = await orcamentoService.getAnosDisponiveis("VENDAS", deptId, false);
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
      const resp = await orcamentoService.getVendas(selectedAno, deptId, false, holdingMldu);
      setAccessDenied(false);
      setData(resp);
      setLinhas(resp.itens || []);
    } catch (err: any) {
      if (err?.response?.status === 403) {
        setAccessDenied(true);
        setData(null);
        setLinhas([]);
      } else if (err?.response?.status === 404) {
        setAccessDenied(false);
        setData(null);
        setLinhas([]);
      } else {
        const detail = err?.response?.data?.detail;
        toast.error(typeof detail === "string" ? detail : "Erro ao carregar orçamento.");
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
    if (!(await confirmDialog("Tem certeza que deseja excluir os dados deste empreendimento da matriz? A exclusão vale ao clicar em Salvar.", { variant: "danger" }))) return;
    setLinhas(linhas.filter((l) => l.produto_id !== produtoId));
    toast.success("Empreendimento removido da matriz. Clique em Salvar para gravar.");
  };


  const toggleProduct = (produtoId: number) => {
    setExpandedProducts(prev => 
      prev.includes(produtoId) 
        ? prev.filter(id => id !== produtoId)
        : [...prev, produtoId]
    );
  };

  const isDistratoFn = (l: OrcamentoVendaLinha) => l.observacao?.includes('Distrato') || l.meses.some(m => (m.numero_vendas || 0) < 0) || (data?.opcoes_planos.find(p => p.id === l.plano_venda_id)?.nome || '').includes('Distrato');

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

    // COM-002: Não sobrescreve valor existente sem confirmação
    const mesesRestantes = MESES.filter(m => m.id > mesIdOrigem);
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

  const [ipcaAlvo, setIpcaAlvo] = useState<{ linhaIndex: number; mesIdOrigem: number } | null>(null);

  const aplicarIPCA = (linhaIndex: number, mesIdOrigem: number) => {
    setIpcaAlvo({ linhaIndex, mesIdOrigem });
  };

  const confirmarIPCA = (taxaMensal: number, descricao: string) => {
    if (!ipcaAlvo) return;
    const { linhaIndex, mesIdOrigem } = ipcaAlvo;
    setIpcaAlvo(null);

    const multiplicador = 1 + taxaMensal;
    const novasLinhas = [...linhas];
    const linha = novasLinhas[linhaIndex];
    const mesOrigem = linha.meses.find(m => m.mes === mesIdOrigem);
    
    if (!mesOrigem) return;
    
    let currentTicket = mesOrigem.ticket_medio;
    const mesesRestantes = MESES.filter(m => m.id > mesIdOrigem);

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
    toast.success(`IPCA de ${descricao} aplicado com sucesso!`);
  };

  const getDiffClass = (linha: OrcamentoVendaLinha, mesId: number, campo: "ticket_medio" | "numero_vendas" | "vgv") => {
    if (!data?.itens_base || data.itens_base.length === 0) return "";
    const baseItem = data.itens_base.find(b => b.produto_id === linha.produto_id && b.plano_venda_id === linha.plano_venda_id && b.mes === mesId);
    if (!baseItem) return "bg-brand-green/5"; // Linha nova/plano novo
    
    const currItem = linha.meses.find(m => m.mes === mesId);
    if (!currItem) return "";
    if (currItem[campo] !== baseItem[campo]) return "bg-brand-orange-light/30 border-brand-orange-light text-slate-900"; // Modificado
    return "";
  };

  const handleAdicionarLinhaMatriz = () => {
    if (!novoProdutoId || !novoPlanoId) {
      toast.error("Selecione um empreendimento e um plano de venda.");
      return;
    }
    const isDistratoTab = activeTab === "distratos";
    const duplicada = linhas.some(
      (l) =>
        l.produto_id === novoProdutoId &&
        l.plano_venda_id === novoPlanoId &&
        isDistratoFn(l) === isDistratoTab,
    );
    if (duplicada) {
      toast.error("Esta combinação empreendimento + plano já está no orçamento.");
      return;
    }
    const pid = Number(novoProdutoId);
    const novaLinha: OrcamentoVendaLinha = {
      produto_id: pid,
      plano_venda_id: Number(novoPlanoId),
      meses: MESES.map((m) => ({ mes: m.id, ticket_medio: 0, numero_vendas: 0, vgv: 0 })),
      observacao: isDistratoTab ? "(Distrato)" : "",
    };
    setLinhas([...linhas, novaLinha]);
    if (!expandedProducts.includes(pid)) {
      setExpandedProducts([...expandedProducts, pid]);
    }
  };

  const adicionarLinhaProduto = (produtoId: number) => {
    const isDistratoTab = activeTab === "distratos";
    const usados = new Set(
      linhas
        .filter((l) => l.produto_id === produtoId && isDistratoFn(l) === isDistratoTab)
        .map((l) => l.plano_venda_id),
    );
    const livre = data?.opcoes_planos?.find((p) => !usados.has(p.id));
    if (!livre) {
      toast.error("Esta combinação empreendimento + plano já está no orçamento.");
      return;
    }
    const novaLinha: OrcamentoVendaLinha = {
      produto_id: produtoId,
      plano_venda_id: livre.id,
      meses: MESES.map((m) => ({ mes: m.id, ticket_medio: 0, numero_vendas: 0, vgv: 0 })),
      observacao: isDistratoTab ? "(Distrato)" : "",
    };
    setLinhas([...linhas, novaLinha]);
    if (!expandedProducts.includes(produtoId)) {
      setExpandedProducts([...expandedProducts, produtoId]);
    }
  };

  const salvar = async () => {
    setSaving(true);
    try {
      await orcamentoService.salvarVendas(ano, deptId, linhas);
      toast.success("Orçamento salvo com sucesso!");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao salvar orçamento.");
    } finally {
      setSaving(false);
    }
  };

  const filtroOpcoes = useMemo(() => {
    if (!data) return { centrosId: [], produtos: [], planos: [], empresasId: [], empresasNome: [] };
    const centrosId = idsPublicosCentro(data.opcoes_produtos).sort((a, b) => Number(a) - Number(b));
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
      if (filtroIdCentro.length > 0 && produtoInfo && !filtroIdCentro.includes(idPublicoSienge(produtoInfo))) return false;
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

  const customSortFn = (a: number, b: number, config: any) => {
    if (config.key === 'produto') {
      const prodA = data?.opcoes_produtos.find(p => p.id === a);
      const prodB = data?.opcoes_produtos.find(p => p.id === b);
      const nameA = prodA ? `${prodA.id_sienge || ""} - ${prodA.nome}` : "";
      const nameB = prodB ? `${prodB.id_sienge || ""} - ${prodB.nome}` : "";
      return config.direction === 'asc' ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
    }
    
    const mesIdNum = parseInt(config.key as string);
    if (!isNaN(mesIdNum)) {
      const sumA = groupedByProduct[a]?.reduce((acc, l) => acc + (l.meses.find(m => m.mes === mesIdNum)?.vgv || 0), 0) || 0;
      const sumB = groupedByProduct[b]?.reduce((acc, l) => acc + (l.meses.find(m => m.mes === mesIdNum)?.vgv || 0), 0) || 0;
      return config.direction === 'asc' ? sumA - sumB : sumB - sumA;
    }

    if (config.key === 'total_anual') {
      const sumA = groupedByProduct[a]?.reduce((acc, l) => acc + l.meses.reduce((s, m) => s + (m.vgv || 0), 0), 0) || 0;
      const sumB = groupedByProduct[b]?.reduce((acc, l) => acc + l.meses.reduce((s, m) => s + (m.vgv || 0), 0), 0) || 0;
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

  const mesesVisiveis = MESES.filter(m => selectedMonths.includes(m.id));

  if (accessDenied) {
    return (
      <div className="w-full h-full flex items-center justify-center p-6 bg-slate-50">
        <Card className="max-w-md p-8 text-center space-y-4">
          <div className="w-16 h-16 bg-brand-red-light/30 text-brand-red rounded-full flex items-center justify-center mx-auto">
            <Lock size={32} />
          </div>
          <h2 className="text-xl font-bold text-slate-800">Acesso Restrito</h2>
          <p className="text-slate-600">
            O Orçamento de Vendas é de uso exclusivo do departamento <strong>Vendas</strong> e da Diretoria.
          </p>
          <Button variant="primary" onClick={() => window.history.back()}>
            Voltar
          </Button>
        </Card>
      </div>
    );
  }

  const isBlocked =
    holdingMldu ||
    ["Em aprovação", "Aprovado", "Fechado", "Solicitação Reabertura"].includes(data?.status || "");

  return (
    <BudgetMatrixShell
      title="Orçamento de Vendas"
      subtitle="Matriz de previsão de VGV por produto e plano de pagamento."
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
          {isBlocked ? (
            <div className="bg-brand-orange/10 border border-brand-orange-light text-brand-orange px-3 py-1.5 rounded-md text-xs">
              <strong>Ano de {ano} Travado:</strong> O orçamento base já está aprovado e é imutável pela interface.
            </div>
          ) : null}
          {data ? (
            <MonthSelector selectedMonths={selectedMonths} onChange={setSelectedMonths} />
          ) : null}
          {data ? (
            <div className="flex space-x-6 border-b border-slate-200 px-2">
              <button
                onClick={() => setActiveTab('vendas')}
                className={`pb-2 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'vendas' ? 'border-brand-500 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
              >
                Orçamento de Vendas
              </button>
              <button
                onClick={() => setActiveTab('distratos')}
                className={`pb-2 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'distratos' ? 'border-brand-500 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
              >
                Orçamento de Distratos
              </button>
              <button
                onClick={() => setActiveTab('liquidas')}
                className={`pb-2 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'liquidas' ? 'border-brand-500 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
              >
                Vendas Líquidas
              </button>
            </div>
          ) : null}
          {data ? (
            <MonthlyGridFilterPanel
              values={{ busca, filtroIdCentro, filtroProduto, filtroPlano, filtroEmpresaIds }}
              onChange={patchGridFilters}
              opcoesIdCentro={opcoesIdCentro}
              opcoesProduto={opcoesProduto}
              opcoesPlano={opcoesPlano}
              opcoesEmpresaId={opcoesIdEmpresa}
              opcoesEmpresaNome={opcoesEmpresa}
              planoLabel="Forma de Venda"
              useCompactInput
            />
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
            Não existem orçamentos de vendas para <strong>{user?.departamentos.find((d) => d.id === deptId)?.nome ?? "este departamento"}</strong> em {ano}.
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
              <thead className="text-[10px] text-slate-700 uppercase bg-slate-100 sticky top-0 z-20">
                <tr>
                  <TableHead sortable sortDirection={sortConfig?.key === 'produto' ? sortConfig.direction : false} onSort={() => handleSort('produto')} className="min-w-[300px] bg-slate-100 sticky left-0 z-30 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">
                    {activeTab === 'distratos' ? 'Produto (C.C.)' : 'Produto (C.C.) / Forma de Venda'}
                  </TableHead>
                  {mesesVisiveis.map(mes => (
                    <TableHead sortable sortDirection={sortConfig?.key === String(mes.id) ? sortConfig.direction : false} onSort={() => handleSort(String(mes.id))} key={mes.id} className="w-[120px] text-center bg-slate-100 border-l border-slate-200">{mes.label.toUpperCase()}</TableHead>
                  ))}
                  <TableHead sortable sortDirection={sortConfig?.key === 'total_anual' ? sortConfig.direction : false} onSort={() => handleSort('total_anual')} className="w-[120px] text-right font-bold text-brand-700 bg-slate-100 border-l border-slate-200 hover:bg-brand-50">TOTAL VGV (R$)</TableHead>
                  <TableHead className="text-center bg-slate-100 border-l border-slate-200">Ações</TableHead>
                </tr>
              </thead>
              <tbody>
                {Object.keys(groupedByProduct).length === 0 ? (
                  <tr>
                    <td colSpan={15} className="px-6 py-8 text-center text-slate-500">
                      Nenhuma previsão adicionada. Comece adicionando uma linha.
                    </td>
                  </tr>
                ) : (
                  sortedProductIds.map((produtoId) => {
                    const groupLinhas = groupedByProduct[produtoId];
                    const isExpanded = expandedProducts.includes(produtoId);
                    const prodName = data?.opcoes_produtos.find(p => p.id === produtoId)?.nome || `Produto #${produtoId}`;
                    
                    // Somar totais do produto
                    const totaisProdVGV: Record<number, number> = {};
                    const totaisProdQtd: Record<number, number> = {};
                    let vgvAnualProd = 0;
                    
                    MESES.forEach(m => {
                      totaisProdVGV[m.id] = 0;
                      totaisProdQtd[m.id] = 0;
                    });

                    groupLinhas.forEach(l => {
                      l.meses.forEach(m => {
                        totaisProdVGV[m.mes] += (m.vgv || 0);
                        totaisProdQtd[m.mes] += (m.numero_vendas || 0);
                        vgvAnualProd += (m.vgv || 0);
                      });
                    });

                    return (
                      <React.Fragment key={`prod-${produtoId}`}>
                        {/* Célula Master do Produto */}
                        <tr className="bg-slate-50 border-y hover:bg-slate-100 cursor-pointer transition-colors group" onClick={() => toggleProduct(produtoId)}>
                          <td className="px-3 py-3 font-bold text-slate-800 flex items-center whitespace-nowrap sticky left-0 z-10 bg-slate-50 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] group-hover:bg-slate-100">
                            {isExpanded ? <ChevronDown size={16} className="mr-1 text-brand-600" /> : <ChevronRight size={16} className="mr-1 text-slate-400" />}
                            {data?.opcoes_produtos.find(p => p.id === produtoId)?.id_sienge
                              ? `${data.opcoes_produtos.find(p => p.id === produtoId)!.id_sienge} - ${prodName}`
                              : prodName} {activeTab === 'distratos' ? '- Distratos' : (activeTab === 'liquidas' ? '- Vendas Líquidas' : '- Vendas')}
                            <div className="ml-4 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              {!isBlocked && activeTab !== 'liquidas' && (
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
                          {MESES.filter(m => selectedMonths.includes(m.id)).map(mes => (
                            <td key={`prod-m-${mes.id}`} className="px-3 py-2 text-right border-l border-slate-200 bg-slate-50">
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

                        {/* Linhas filhas (Planos) */}
                        {isExpanded && groupLinhas.map((linha, innerIdx) => {
                          const globalIdx = linhas.indexOf(linha);
                          const totalVGVLinha = linha.meses.reduce((acc, m) => acc + (m.vgv || 0), 0);

                          return (
                            <React.Fragment key={`linha-${globalIdx}`}>
                              {/* Sub Header for the Plan */}
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
                                        const novoPlano = Number(e.target.value);
                                        const duplicada = linhas.some((l, i) => i !== globalIdx && l.produto_id === linha.produto_id && l.plano_venda_id === novoPlano && isDistratoFn(l) === isDistratoFn(linha));
                                        if (duplicada) {
                                          toast.error("Esta combinação empreendimento + plano já está no orçamento.");
                                          return;
                                        }
                                        const novas = [...linhas];
                                        novas[globalIdx].plano_venda_id = novoPlano;
                                        setLinhas(novas);
                                      }}
                                    >
                                      {data?.opcoes_planos.map(p => (
                                        <option key={p.id} value={p.id}>{p.nome}</option>
                                      ))}
                                    </select>
                                  </td>
                                  <td colSpan={selectedMonths.length + 2} className="bg-white border-l border-slate-100"></td>
                                </tr>
                              )}
                              
                              {/* Row: Ticket Médio */}
                              <tr className="bg-white border-none group/row">
                                <td className="px-3 py-1 pl-12 text-xs text-slate-500 whitespace-nowrap bg-white sticky left-0 z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] group-hover/row:bg-slate-50">↳ Ticket Médio (R$)</td>
                                {MESES.filter(m => selectedMonths.includes(m.id)).map(mes => {
                                  const mObj = linha.meses.find(m => m.mes === mes.id);
                                  return (
                                    <td key={`tkt-${mes.id}`} className={`px-1 py-1 border-l border-slate-100 relative group/cell ${getDiffClass(linha, mes.id, 'ticket_medio')}`}>
                                      <div className="flex items-center">
                                        <CurrencyInput
                                          value={mObj?.ticket_medio || 0}
                                          disabled={isBlocked || activeTab === 'liquidas'}
                                          onChange={(val) => handleInputChange(globalIdx, mes.id, 'ticket_medio', val)}
                                          placeholder="0,00"
                                        />
                                        {!isBlocked && activeTab !== 'liquidas' && mes.id !== 12 && (
                                          <div className="absolute right-0 top-0 bottom-0 flex items-center bg-white shadow-sm border rounded px-1 opacity-0 group-hover/cell:opacity-100 z-10 transition-opacity translate-x-1/2 gap-1">
                                            <button onClick={() => replicarValor(globalIdx, mes.id, 'ticket_medio')} className="text-slate-400 hover:text-brand-600" title="Replicar">
                                              <Copy size={12} />
                                            </button>
                                            <button onClick={() => aplicarIPCA(globalIdx, mes.id)} className="text-slate-400 hover:text-brand-green font-bold text-[10px]" title="Aplicar IPCA">
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

                              {/* Row: Quantidade */}
                              <tr className="bg-white border-none group/row">
                                <td className="px-3 py-1 pl-12 text-xs text-slate-500 whitespace-nowrap bg-white sticky left-0 z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] group-hover/row:bg-slate-50">
                                  ↳ {activeTab === 'distratos' ? 'Distrato (Qtd)' : 'Vendas (Qtd)'}
                                </td>
                                {MESES.filter(m => selectedMonths.includes(m.id)).map(mes => {
                                  const mObj = linha.meses.find(m => m.mes === mes.id);
                                  return (
                                    <td key={`qtd-${mes.id}`} className={`px-1 py-1 border-l border-slate-100 relative group/cell ${getDiffClass(linha, mes.id, 'numero_vendas')}`}>
                                      <div className="flex items-center">
                                        <input
                                          type="number"
                                          className="w-full p-1 text-xs text-right font-medium text-slate-700 border-0 border-b border-transparent focus:border-brand-500 focus:ring-0 bg-transparent hover:bg-slate-50 transition-colors [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none disabled:bg-transparent disabled:border-transparent"
                                          value={mObj?.numero_vendas || ''}
                                          disabled={isBlocked || activeTab === 'liquidas'}
                                          onChange={(e) => handleInputChange(globalIdx, mes.id, 'numero_vendas', e.target.value)}
                                          placeholder="0"
                                        />
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

                              {/* Row: Recebimento/VGV (Read-only) */}
                              <tr className="bg-slate-50/50 border-b border-slate-200">
                                <td className="px-3 py-2 pl-12 text-xs font-semibold text-slate-700 whitespace-nowrap bg-slate-50/50 sticky left-0 z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">VGV Mensal (R$)</td>
                                {MESES.filter(m => selectedMonths.includes(m.id)).map(mes => {
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
            </table>
          </BudgetMatrixScrollArea>
        )}

        {!isBlocked && activeTab !== 'liquidas' && (
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
              <label className="block text-xs text-slate-500 font-medium mb-1">Plano de venda</label>
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
              onClick={handleAdicionarLinhaMatriz}
            >
              <Plus className="mr-2 h-4 w-4" /> Adicionar à Matriz
            </Button>
          </div>
        )}
        
      </div>
      )}
      {showExcel && (
        <ExcelImportModal
          tipo="VENDAS"
          ano={ano}
          deptId={deptId}
          orcamentoId={data?.orcamento_id}
          onClose={() => setShowExcel(false)}
          onSuccess={() => { setShowExcel(false); carregarDados(ano); }}
        />
      )}

      {showCriarModal && (
        <CriarOrcamentoModal
          tipo="VENDAS"
          deptId={deptId}
          anoInicial={ano}
          onClose={() => setShowCriarModal(false)}
          onCreated={handleCreated}
        />
      )}
      {ipcaAlvo && (
        <IpcaCascataModal onClose={() => setIpcaAlvo(null)} onConfirm={confirmarIPCA} />
      )}
    </BudgetMatrixShell>
  );
}
