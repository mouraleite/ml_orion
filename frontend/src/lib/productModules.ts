/**
 * Catálogo de telas placeholder (produto futuro).
 * Não alteram zonas congeladas — apenas informam o usuário.
 */

export interface RelatedModuleLink {
  label: string;
  href: string;
}

export interface ProductModulePlaceholder {
  path: string;
  title: string;
  message: string;
  module: string;
  relatedLinks?: RelatedModuleLink[];
}

const ORCAMENTO_SAFE =
  "Não altera orçamento de despesas, receitas, vendas nem orçado × realizado.";

const GENERIC_SAFE =
  "Não altera números já validados em outros módulos.";

const orcamentoLinks: RelatedModuleLink[] = [
  { label: "Despesas", href: "/dashboard/orcamento/despesas" },
  { label: "Orçado × realizado", href: "/dashboard/orcamento/realizado" },
];

export const PRODUCT_PLACEHOLDERS: ProductModulePlaceholder[] = [
  {
    path: "/dashboard/reports",
    module: "Rentabilidade de Produtos",
    title: "Relatórios de viabilidades",
    message:
      "Este módulo ainda não foi construído. Viabilidades e acompanhamento de empreendimentos continuam iguais.",
    relatedLinks: [
      { label: "Viabilidades", href: "/dashboard/viabilities" },
      { label: "Acompanhamento", href: "/dashboard/tracking" },
    ],
  },
  {
    path: "/dashboard/orcamento/relatorios",
    module: "Orçamento",
    title: "Relatórios de orçamento",
    message: `Módulo ainda não construído. As telas de despesas, receitas, vendas e orçado × realizado continuam iguais.`,
    relatedLinks: orcamentoLinks,
  },
  {
    path: "/dashboard/holding/painel",
    module: "Consolidação",
    title: "Painel corporativo",
    message:
      "A consolidação da holding ainda não foi construída. Não altera viabilidades, orçamento nem forecast.",
    relatedLinks: [{ label: "Visão global", href: "/dashboard/visao-global" }],
  },
  {
    path: "/dashboard/holding/base-historica",
    module: "Consolidação",
    title: "Base histórica",
    message: `Esta tela ainda não foi construída. ${GENERIC_SAFE}`,
    relatedLinks: [{ label: "Visão global", href: "/dashboard/visao-global" }],
  },
  {
    path: "/dashboard/holding/apresentacoes",
    module: "Consolidação",
    title: "Apresentações (curta / longa)",
    message: `Esta tela ainda não foi construída. ${GENERIC_SAFE}`,
    relatedLinks: [{ label: "Visão global", href: "/dashboard/visao-global" }],
  },
  {
    path: "/dashboard/holding/relatorios",
    module: "Consolidação",
    title: "Relatórios de consolidação",
    message: `Esta tela ainda não foi construída. ${GENERIC_SAFE}`,
    relatedLinks: [{ label: "Visão global", href: "/dashboard/visao-global" }],
  },
  {
    path: "/dashboard/governance/workflow",
    module: "Governança e Índices",
    title: "Aprovações (workflow)",
    message:
      "O fluxo de aprovações ainda não foi construído. Não altera a tabela de índices nem os módulos já validados.",
    relatedLinks: [{ label: "Tabela de índices", href: "/dashboard/governance" }],
  },
  {
    path: "/dashboard/governance/relatorios",
    module: "Governança e Índices",
    title: "Relatórios de governança",
    message: `Esta tela ainda não foi construída. ${GENERIC_SAFE}`,
    relatedLinks: [{ label: "Tabela de índices", href: "/dashboard/governance" }],
  },
  {
    path: "/dashboard/seguranca/relatorios",
    module: "Segurança",
    title: "Relatórios de segurança",
    message:
      "Esta tela ainda não foi construída. Usuários, perfis e logs continuam iguais.",
    relatedLinks: [
      { label: "Usuários", href: "/dashboard/seguranca/usuarios" },
      { label: "Perfis", href: "/dashboard/seguranca/perfis" },
    ],
  },
];

export const PLACEHOLDER_PATHS = new Set(
  PRODUCT_PLACEHOLDERS.map((entry) => entry.path),
);

export function getPlaceholderByPath(
  path: string,
): ProductModulePlaceholder | undefined {
  return PRODUCT_PLACEHOLDERS.find((entry) => entry.path === path);
}

export function isPlaceholderPath(path: string): boolean {
  return PLACEHOLDER_PATHS.has(path);
}

export function isPlaceholderHref(href: string): boolean {
  if (!href || href === "#") return false;
  return isPlaceholderPath(href.split("?")[0]);
}
