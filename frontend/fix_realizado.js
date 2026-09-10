const fs = require('fs');
const FILE = 'c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/app/dashboard/orcamento/realizado/page.tsx';
let c = fs.readFileSync(FILE, 'utf8');

// 1. Fix Imports and add parseCentroNome
const importsOld = `import {
  BarChart2, TrendingUp, TrendingDown, DollarSign, GitCompare,
  Eye, RefreshCw, Download, ChevronDown, ChevronRight, AlertCircle, CheckCircle2,
  PlusCircle, MinusCircle, ArrowRightLeft, Building2, Filter,
  ArrowUpDown, ArrowUp, ArrowDown, Calendar, Search, Check, LineChart
} from "lucide-react";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/Table";`;

const importsNew = `import {
  BarChart2, TrendingUp, TrendingDown, DollarSign, GitCompare,
  Eye, RefreshCw, Download, ChevronDown, ChevronRight, AlertCircle, CheckCircle2,
  PlusCircle, MinusCircle, ArrowRightLeft, Building2, Filter,
  ArrowUpDown, ArrowUp, ArrowDown, Calendar, Search, Check, LineChart, Eraser
} from "lucide-react";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/Table";
import { MultiSelect } from "@/components/ui/MultiSelect";

function parseCentroNome(nome: string): { cidade: string; produto: string } {
    if (!nome) return { cidade: "", produto: "" };
    if (nome.toUpperCase().includes("AUTOMÓVEL") || nome.toUpperCase().includes("AUTOMOVEL")) {
      return { cidade: "FROTA", produto: "FROTA" };
    }
    const partes = nome.split(" -").map((p) => p.trim());
    if (partes.length >= 2) {
      const cidade = partes[0];
      const sufixos = ["INATIVO", "ATIVO", "ENCERRADO", "SUSPENSO"];
      const ultimaParte = partes[partes.length - 1].toUpperCase();
      const temSufixo = sufixos.includes(ultimaParte);
      
      let produto = partes.slice(1).join(" - ");
      if (temSufixo && partes.length >= 3) {
        produto = partes.slice(1, -1).join(" - ");
      } else if (temSufixo && partes.length === 2) {
        produto = partes[0];
      }
      return { cidade, produto };
    }
    return { cidade: nome, produto: nome };
}`;
c = c.replace(importsOld, importsNew);


// 2. Fix TabDespesasReceitas filters
const tdrFilterOld = `  const itens = (data.itens || []).filter((item: any) => {
    const prodInfo = data.opcoes_produtos?.find((p: any) => p.id === item.produto_id) || {};
    const planoInfo = data.opcoes_planos?.find((p: any) => p.id === item.plano_financeiro_id) || {};
    
    if (filtros?.busca) {
      const prodName = prodInfo.nome || item.produto_nome || "";
      if (!prodName.toLowerCase().includes(filtros.busca.toLowerCase())) return false;
    }
    
    if (filtros?.idCentroCusto && filtros.idCentroCusto !== "Todos" && item.produto_id && item.produto_id?.toString() !== filtros.idCentroCusto.toString()) return false;
    
    if (filtros?.produtoFiltro && filtros.produtoFiltro !== "Todos" && item.produto_id && item.produto_id?.toString() !== filtros.produtoFiltro.toString()) return false;
    
    if (filtros?.planoFinanceiro && filtros.planoFinanceiro !== "Todos" && item.plano_financeiro_id && item.plano_financeiro_id?.toString() !== filtros.planoFinanceiro.toString()) return false;
    
    const empresaId = String(prodInfo.id_empresa || "");
    if (filtros?.idEmpresa && filtros.idEmpresa !== "Todos" && empresaId !== filtros.idEmpresa) return false;
    if (filtros?.empresaFiltro && filtros.empresaFiltro !== "Todas" && empresaId !== filtros.empresaFiltro) return false;
    
    return true;
  }).sort((a: any, b: any) => {
    const pA = (getProdNome(a.produto_id) || "").toString();
    const pB = (getProdNome(b.produto_id) || "").toString();
    if (!sortConfig) return pA.localeCompare(pB);
    if (pA < pB) return sortConfig.direction === 'asc' ? -1 : 1;
    if (pA > pB) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });`;

const tdrFilterNew = `  const rawItens = useMemo(() => {
    return (data.itens || []).filter((item: any) => {
      const prodInfo = data.opcoes_produtos?.find((p: any) => p.id === item.produto_id) || {};
      const planoInfo = data.opcoes_planos?.find((p: any) => p.id === item.plano_financeiro_id) || {};
      const baseCC: any[] = filtros?.centrosCustoBase || [];
      const baseInfo = baseCC.find((cc: any) => cc.db_id === item.produto_id || cc.id === item.produto_id) || {};
      const idSienge = baseInfo.id ? String(baseInfo.id) : (prodInfo.id_sienge || String(prodInfo.id) || "");
      const nomeEmpresa = baseInfo.nome_empresa || prodInfo.nome_empresa || "";
      if (filtros?.busca) {
        const prodName = prodInfo.nome || baseInfo.nome || "";
        if (!prodName.toLowerCase().includes(filtros.busca.toLowerCase())) return false;
      }
      if (filtros?.idCentroCusto?.length > 0 && !filtros.idCentroCusto.includes(idSienge)) return false;
      if (filtros?.produtoFiltro?.length > 0 && !filtros.produtoFiltro.includes(parseCentroNome(prodInfo.nome || "").produto)) return false;
      if (filtros?.planoFinanceiro?.length > 0 && !filtros.planoFinanceiro.includes(planoInfo.nome || "")) return false;
      if (filtros?.idEmpresa?.length > 0 && !filtros.idEmpresa.includes(String(baseInfo.id_empresa || prodInfo.id_empresa || ""))) return false;
      if (filtros?.empresaFiltro?.length > 0 && !filtros.empresaFiltro.includes(nomeEmpresa)) return false;
      return true;
    });
  }, [data.itens, data.opcoes_produtos, data.opcoes_planos, filtros]);

  const customSortFn = useCallback((a: any, b: any, config: any) => {
    const pA = (getProdNome(a.produto_id) || "").toString();
    const pB = (getProdNome(b.produto_id) || "").toString();
    const plA = (getPlanoNome(a.plano_financeiro_id) || "").toString();
    const plB = (getPlanoNome(b.plano_financeiro_id) || "").toString();
    
    const valA = config.key === 'produto_nome' ? pA : plA;
    const valB = config.key === 'produto_nome' ? pB : plB;
    
    if (valA < valB) return config.direction === 'asc' ? -1 : 1;
    if (valA > valB) return config.direction === 'asc' ? 1 : -1;
    return 0;
  }, [data.opcoes_produtos, data.opcoes_planos]);

  const sortedData = useMemo(() => {
    let sortableItems = [...rawItens];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => customSortFn(a, b, sortConfig));
    }
    return sortableItems;
  }, [rawItens, sortConfig, customSortFn]);

  const itens = sortedData;`;

c = c.replace(tdrFilterOld, tdrFilterNew);

// 3. Fix TabVendas filters
const tvFilterOld = `  const itens = (data.itens || []).filter((item: any) => {
    const prodInfo = data.opcoes_produtos?.find((p: any) => p.id === item.produto_id) || {};
    const planoIdField = item.plano_venda_id;
    
    if (filtros?.busca) {
      const prodName = prodInfo.nome || item.produto_nome || "";
      if (!prodName.toLowerCase().includes(filtros.busca.toLowerCase())) return false;
    }
    
    if (filtros?.idCentroCusto && filtros.idCentroCusto !== "Todos" && item.produto_id && item.produto_id?.toString() !== filtros.idCentroCusto.toString()) return false;
    
    if (filtros?.produtoFiltro && filtros.produtoFiltro !== "Todos" && item.produto_id && item.produto_id?.toString() !== filtros.produtoFiltro.toString()) return false;
    
    if (filtros?.planoFinanceiro && filtros.planoFinanceiro !== "Todos" && planoIdField && planoIdField?.toString() !== filtros.planoFinanceiro.toString()) return false;
    
    const empresaId = String(prodInfo.id_empresa || "");
    if (filtros?.idEmpresa && filtros.idEmpresa !== "Todos" && empresaId !== filtros.idEmpresa) return false;
    if (filtros?.empresaFiltro && filtros.empresaFiltro !== "Todas" && empresaId !== filtros.empresaFiltro) return false;
    
    return true;
  }).sort((a: any, b: any) => {
    const pA = (getProdNome(a.produto_id) || "").toString();
    const pB = (getProdNome(b.produto_id) || "").toString();
    if (!sortConfig) return pA.localeCompare(pB);
    if (pA < pB) return sortConfig.direction === 'asc' ? -1 : 1;
    if (pA > pB) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });`;

const tvFilterNew = `  const rawItens = useMemo(() => {
    return (data.itens || []).filter((item: any) => {
      const prodInfo = data.opcoes_produtos?.find((p: any) => p.id === item.produto_id) || {};
      const planoInfo = data.opcoes_planos?.find((p: any) => p.id === item.plano_venda_id) || {};
      const baseCC: any[] = filtros?.centrosCustoBase || [];
      const baseInfo = baseCC.find((cc: any) => cc.db_id === item.produto_id || cc.id === item.produto_id) || {};
      const idSienge = baseInfo.id ? String(baseInfo.id) : (prodInfo.id_sienge || String(prodInfo.id) || "");
      const nomeEmpresa = baseInfo.nome_empresa || prodInfo.nome_empresa || "";
      if (filtros?.busca) {
        const prodName = prodInfo.nome || baseInfo.nome || "";
        if (!prodName.toLowerCase().includes(filtros.busca.toLowerCase())) return false;
      }
      if (filtros?.idCentroCusto?.length > 0 && !filtros.idCentroCusto.includes(idSienge)) return false;
      if (filtros?.produtoFiltro?.length > 0 && !filtros.produtoFiltro.includes(parseCentroNome(prodInfo.nome || "").produto)) return false;
      if (filtros?.planoFinanceiro?.length > 0 && !filtros.planoFinanceiro.includes(planoInfo.nome || "")) return false;
      if (filtros?.idEmpresa?.length > 0 && !filtros.idEmpresa.includes(String(baseInfo.id_empresa || prodInfo.id_empresa || ""))) return false;
      if (filtros?.empresaFiltro?.length > 0 && !filtros.empresaFiltro.includes(nomeEmpresa)) return false;
      return true;
    });
  }, [data.itens, data.opcoes_produtos, data.opcoes_planos, filtros]);

  const customSortFn = useCallback((a: any, b: any, config: any) => {
    const pA = (getProdNome(a.produto_id) || "").toString();
    const pB = (getProdNome(b.produto_id) || "").toString();
    if (pA < pB) return config.direction === 'asc' ? -1 : 1;
    if (pA > pB) return config.direction === 'asc' ? 1 : -1;
    return 0;
  }, [data.opcoes_produtos]);

  const sortedData = useMemo(() => {
    let sortableItems = [...rawItens];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => customSortFn(a, b, sortConfig));
    }
    return sortableItems;
  }, [rawItens, sortConfig, customSortFn]);

  const itens = sortedData;`;

c = c.replace(tvFilterOld, tvFilterNew);

fs.writeFileSync(FILE, c, 'utf8');
console.log("Done part 1.");
