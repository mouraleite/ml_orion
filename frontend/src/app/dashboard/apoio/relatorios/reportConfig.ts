import { ColumnDef } from "@/lib/exportUtils";

export type FilterConfig = {
  key: string;
  label: string;
  type: "select" | "multi-select" | "text";
  options?: string[];
  placeholder?: string;
};

export type ReportConfig = {
  id: string;
  title: string;
  endpoint: string;
  columns: ColumnDef[];
  filters: FilterConfig[];
  dataExtractor?: (data: any) => any[];
};

export const reportConfigs: ReportConfig[] = [
  {
    id: "centro_custo",
    title: "Relatório de Centros de Custo",
    endpoint: "/apoio/centros-custo",
    filters: [
      {
        key: "search",
        label: "Buscar (Nome ou Sienge)",
        type: "text",
        placeholder: "Ex: Reserva dos Ipês...",
      },
      {
        key: "fase",
        label: "Fase do Empreendimento",
        type: "multi-select",
        options: ["Em Andamento", "Encerrado", "Estudo", "Breve Lançamento"],
      },
      {
        key: "status",
        label: "Status",
        type: "select",
        options: ["Todos", "Ativo", "Inativo"],
      },
    ],
    columns: [
      { header: "Cód. Sienge", accessor: "id" },
      { header: "Nome", accessor: "nome" },
      { header: "Tipo", accessor: "tipo_sienge" },
      { 
        header: "Cidade", 
        accessor: "nome", 
        format: (val) => val ? val.split("-")[0].trim() : "" 
      },
      { 
        header: "Produto", 
        accessor: "nome", 
        format: (val) => {
          if (!val) return "";
          const parts = val.split("-").map((p: string) => p.trim());
          return parts.length > 1 ? parts[1] : "";
        } 
      },
      { header: "ID Empresa", accessor: "id_empresa" },
      { header: "Empresa", accessor: "nome_empresa" },
      { 
        header: "Participação", 
        accessor: "custom_data", 
        format: (val) => val && val["Participação"] ? `${val["Participação"]}%` : "" 
      },
      { header: "Fase", accessor: "project_phase" },
      { header: "Status", accessor: "status" },
      { header: "Custo Terreno Manual", accessor: "manual_land_cost" },
      { header: "Na Dashboard", accessor: "track_in_dashboard", format: (v) => (v ? "Sim" : "Não") },
    ],
  },
  {
    id: "empresas",
    title: "Relatório de Empresas",
    endpoint: "/apoio/empresas",
    filters: [
      {
        key: "search",
        label: "Buscar (Nome ou CNPJ)",
        type: "text",
        placeholder: "Ex: 00.000.000/0001-00...",
      },
      {
        key: "tipo_empresa",
        label: "Tipo de Empresa",
        type: "multi-select",
        options: ["SPE", "SCP", "HOLDING", "CONSTRUTORA", "LOTEADORA", "OUTROS"],
      },
      {
        key: "status",
        label: "Status",
        type: "select",
        options: ["Todos", "Ativo", "Inativo"],
      },
    ],
    columns: [
      { header: "Cód. Sienge", accessor: "id" },
      { header: "CNPJ", accessor: "cnpj" },
      { header: "Razão Social", accessor: "razaoSocial" },
      { header: "Nome Fantasia", accessor: "nomeFantasia" },
      { header: "Tipo", accessor: "tipo_empresa" },
      { header: "Status", accessor: "status" },
    ],
  },
  {
    id: "planos_financeiros",
    title: "Relatório de Planos Financeiros",
    endpoint: "/apoio/planos-financeiros",
    filters: [
      {
        key: "search",
        label: "Buscar (Nome ou Cód)",
        type: "text",
        placeholder: "Ex: Receitas de Vendas...",
      },
      {
        key: "tpConta",
        label: "Tipo de Conta",
        type: "select",
        options: ["Todos", "Sintética", "Analítica"],
      },
      {
        key: "flAtiva",
        label: "Status",
        type: "select",
        options: ["Todos", "Ativa", "Inativa"],
      },
    ],
    columns: [
      { header: "Código", accessor: "db_sienge_id" },
      { header: "Descrição", accessor: "name" },
      { header: "Tipo Conta", accessor: "tpConta", format: (v) => (v === "S" ? "Sintética" : v === "A" ? "Analítica" : String(v)) },
      { header: "Ativa", accessor: "flAtiva", format: (v) => (v ? "Sim" : "Não") },
      { header: "Redutora", accessor: "flRedutora", format: (v) => (v ? "Sim" : "Não") },
      { header: "Adiantamento", accessor: "flAdiantamento", format: (v) => (v ? "Sim" : "Não") },
      { header: "Imposto", accessor: "flImposto", format: (v) => (v ? "Sim" : "Não") },
    ],
  },
  {
    id: "cenarios",
    title: "Relatório de Cenários",
    endpoint: "/apoio/cenarios",
    filters: [
      {
        key: "search",
        label: "Buscar (Nome)",
        type: "text",
        placeholder: "Ex: Cenário Base...",
      },
    ],
    columns: [
      { header: "ID", accessor: "id" },
      { header: "Nome", accessor: "nome" },
      { header: "Mult. VGV", accessor: "vgv_multiplier" },
      { header: "Mult. Custo", accessor: "construction_cost_multiplier" },
      { header: "Mult. Velocidade", accessor: "sales_speed_multiplier" },
    ],
  },
  {
    id: "planos_pagamento",
    title: "Relatório de Planos de Pagamento",
    endpoint: "/apoio/planos-pagamento",
    filters: [
      {
        key: "search",
        label: "Buscar (Nome)",
        type: "text",
        placeholder: "Ex: Plano 30/70...",
      },
    ],
    columns: [
      { header: "ID", accessor: "id" },
      { header: "Nome", accessor: "nome" },
      { header: "Condições Cadastradas", accessor: "condicoes_json", format: (v) => v ? `${v.length} condição(ões)` : "0" },
    ],
  },
  {
    id: "indicadores",
    title: "Relatório de Indicadores Projetados",
    endpoint: "/apoio/indicadores",
    filters: [
      {
        key: "search",
        label: "Buscar (Nome)",
        type: "text",
        placeholder: "Ex: IPCA...",
      },
      {
        key: "index_type",
        label: "Tipo",
        type: "select",
        options: ["Todos", "INFLATION", "COST", "RATE"],
      },
    ],
    columns: [
      { header: "ID", accessor: "id" },
      { header: "Nome", accessor: "nome" },
      { header: "Tipo", accessor: "index_type" },
      { header: "Valor", accessor: "valor" },
      { header: "Unidade", accessor: "tipo_unidade" },
    ],
  },
  {
    id: "impostos",
    title: "Relatório de Regimes Tributários",
    endpoint: "/apoio/impostos/",
    filters: [
      {
        key: "search",
        label: "Buscar (Nome)",
        type: "text",
        placeholder: "Ex: RET...",
      },
    ],
    columns: [
      { header: "ID", accessor: "id" },
      { header: "Nome", accessor: "nome" },
      { header: "Ativo", accessor: "ativo", format: (v) => (v ? "Sim" : "Não") },
      { header: "PIS (%)", accessor: "pis" },
      { header: "COFINS (%)", accessor: "cofins" },
      { header: "IRPJ (%)", accessor: "irpj" },
      { header: "CSLL (%)", accessor: "csll" },
      { header: "Outros (%)", accessor: "outros" },
    ],
  },
  {
    id: "curvas",
    title: "Relatório de Curvas Padrão",
    endpoint: "/curves/",
    filters: [
      { key: "search", label: "Buscar (Nome)", type: "text", placeholder: "Ex: Curva S..." }
    ],
    columns: [
      { header: "ID", accessor: "id" },
      { header: "Nome", accessor: "nome" },
      { header: "Tipo de Curva", accessor: "tipo" },
      { header: "Classificação", accessor: "classificacao" },
    ],
  },
  {
    id: "parcerias",
    title: "Relatório de Regras de Parceria",
    endpoint: "/partnership",
    filters: [
      { key: "search", label: "Buscar (Nome)", type: "text" }
    ],
    columns: [
      { header: "ID", accessor: "id" },
      { header: "Nome da Regra", accessor: "name" },
      { header: "Descrição", accessor: "description" },
    ],
  },
  {
    id: "visao",
    title: "Relatório de Árvores de Visão",
    endpoint: "/apoio/visoes",
    filters: [
      { key: "search", label: "Buscar (Nome)", type: "text" }
    ],
    columns: [
      { header: "ID", accessor: "id" },
      { header: "Nome", accessor: "nome" },
      { header: "Descrição", accessor: "descricao" },
    ],
  },
  {
    id: "indices_mercado",
    title: "Relatório de Índices (IPCA)",
    endpoint: "/market-indices/ipca",
    filters: [
      { key: "search", label: "Filtrar Data", type: "text", placeholder: "MM/YYYY" }
    ],
    columns: [
      { header: "Data", accessor: "data" },
      { header: "Valor (%)", accessor: "valor" },
    ],
  },
  {
    id: "taxas_funding",
    title: "Relatório de Taxas de Funding",
    endpoint: "/apoio/system-settings/funding_rates",
    dataExtractor: (data: any) => {
      // Data might be { value: { CDI: 0.1, TR: 0.2 } }
      if (data && data.value && typeof data.value === 'object') {
        return Object.keys(data.value).map(k => ({ taxa: k, valor: data.value[k] }));
      }
      return [];
    },
    filters: [
      { key: "search", label: "Buscar (Nome)", type: "text" }
    ],
    columns: [
      { header: "Taxa", accessor: "taxa" },
      { header: "Valor (%)", accessor: "valor" },
    ],
  },
];
