const fs = require('fs');
const FILE = 'c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/app/dashboard/orcamento/realizado/page.tsx';
let c = fs.readFileSync(FILE, 'utf8');

// Replace TabDespesasReceitas logic
const startTDR = c.indexOf('  const rawItens = useMemo(() => {');
const endTDR = c.indexOf('  const handleSort = (key: \'produto_nome\' | \'plano_financeiro_nome\') => {');
if (startTDR > -1 && endTDR > -1) {
    const oldTDR = c.substring(startTDR, endTDR);
    const newTDR = `  const itens = (data.itens || []).filter((item: any) => {
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
  }).sort((a: any, b: any) => {
    const pA = (getProdNome(a.produto_id) || "").toString();
    const pB = (getProdNome(b.produto_id) || "").toString();
    const plA = (getPlanoNome(a.plano_financeiro_id) || "").toString();
    const plB = (getPlanoNome(b.plano_financeiro_id) || "").toString();
    
    if (!sortConfig) {
      const compProd = pA.localeCompare(pB);
      if (compProd !== 0) return compProd;
      return plA.localeCompare(plB);
    }
    
    const valA = sortConfig.key === 'produto_nome' ? pA : plA;
    const valB = sortConfig.key === 'produto_nome' ? pB : plB;
    
    if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
    if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

`;
    c = c.replace(oldTDR, newTDR);
    console.log("Replaced TabDespesasReceitas logic");
} else {
    console.log("Could not find TabDespesasReceitas logic: startTDR=", startTDR, "endTDR=", endTDR);
    // let's try finding the alternative start
    const altStartTDR = c.indexOf('  const itens = (data.itens || []).filter((item: any) => {');
    if (altStartTDR > -1 && endTDR > -1) {
        const oldTDR = c.substring(altStartTDR, endTDR);
        const newTDR = `  const itens = (data.itens || []).filter((item: any) => {
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
  }).sort((a: any, b: any) => {
    const pA = (getProdNome(a.produto_id) || "").toString();
    const pB = (getProdNome(b.produto_id) || "").toString();
    const plA = (getPlanoNome(a.plano_financeiro_id) || "").toString();
    const plB = (getPlanoNome(b.plano_financeiro_id) || "").toString();
    
    if (!sortConfig) {
      const compProd = pA.localeCompare(pB);
      if (compProd !== 0) return compProd;
      return plA.localeCompare(plB);
    }
    
    const valA = sortConfig.key === 'produto_nome' ? pA : plA;
    const valB = sortConfig.key === 'produto_nome' ? pB : plB;
    
    if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
    if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

`;
        c = c.replace(oldTDR, newTDR);
        console.log("Replaced TabDespesasReceitas logic (alt)");
    }
}

// Replace TabVendas logic
const startTV = c.lastIndexOf('  const rawItens = useMemo(() => {');
const endTV = c.indexOf('  const handleSort = (key: \'produto_nome\') => {');
if (startTV > -1 && endTV > -1) {
    const oldTV = c.substring(startTV, endTV);
    const newTV = `  const itens = (data.itens || []).filter((item: any) => {
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
  }).sort((a: any, b: any) => {
    const pA = (getProdNome(a.produto_id) || "").toString();
    const pB = (getProdNome(b.produto_id) || "").toString();
    if (!sortConfig) return pA.localeCompare(pB);
    if (pA < pB) return sortConfig.direction === 'asc' ? -1 : 1;
    if (pA > pB) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

`;
    c = c.replace(oldTV, newTV);
    console.log("Replaced TabVendas logic");
} else {
    console.log("Could not find TabVendas logic: startTV=", startTV, "endTV=", endTV);
}

fs.writeFileSync(FILE, c, 'utf8');
console.log("Fixed hooks successfully.");
