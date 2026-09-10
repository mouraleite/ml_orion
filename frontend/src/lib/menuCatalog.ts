/**
 * Fonte única do menu lateral e da matriz de perfis.
 * Os nomes aqui são as chaves de permissão (exceto Relatórios de Apoio,
 * prefixados para não colidir com o cadastro de mesmo nome).
 */
import {
  Database,
  DollarSign,
  FileBarChart,
  FileText,
  FolderKanban,
  FolderOpen,
  GitBranch,
  LayoutDashboard,
  PieChart,
  RefreshCw,
  Settings,
  Shield,
  Users,
  type LucideIcon,
} from "lucide-react";

export type MenuSubItem = {
  name: string;
  href: string;
  permKey: string;
};

export type MenuItemDef = {
  name: string;
  href: string;
  icon: LucideIcon;
  subItems?: MenuSubItem[];
};

export type MenuModuleDef = {
  id: string;
  title: string;
  icon: LucideIcon;
  items: MenuItemDef[];
};

export type AccessKind = "screen" | "capability";

export type AccessEntry = {
  name: string;
  permKey: string;
  kind: AccessKind;
};

export type AccessGroup = {
  title: string;
  entries: AccessEntry[];
};

export type AccessModuleDef = {
  id: string;
  title: string;
  groups: AccessGroup[];
};

function sub(name: string, href: string, permKey = name): MenuSubItem {
  return { name, href, permKey };
}

function reportSub(name: string, href: string): MenuSubItem {
  return sub(name, href, `Relatórios · ${name}`);
}

const RAW_MENU: MenuModuleDef[] = [
  {
    id: "viabilidades",
    title: "Rentabilidade de Produtos",
    icon: FolderOpen,
    items: [
      { name: "Viabilidades", icon: FolderKanban, href: "/dashboard/viabilities" },
      { name: "Acompanhamento de Empreendimentos", icon: LayoutDashboard, href: "/dashboard/tracking" },
      { name: "Relatórios", icon: FileBarChart, href: "/dashboard/reports" },
    ],
  },
  {
    id: "modelagem",
    title: "Modelagem Financeira",
    icon: PieChart,
    items: [
      { name: "Modelagem Mestre", icon: FileText, href: "/dashboard/modeling" },
      { name: "Relatórios", icon: FileText, href: "#" },
    ],
  },
  {
    id: "orcamento",
    title: "Orçamento",
    icon: DollarSign,
    items: [
      {
        name: "Dashboard de Orçamento",
        icon: LayoutDashboard,
        href: "#",
        subItems: [
          sub("Resumo Geral", "/dashboard/orcamento/resumo-geral"),
          sub("Analítico de Gastos I", "/dashboard/orcamento/analitico-gastos-1"),
          sub("Realizado CP (detalhe)", "/dashboard/orcamento/realizado-despesas"),
          sub("Analítico dos Gastos II", "/dashboard/orcamento/analitico-gastos-2"),
          sub("Geração de Caixa", "/dashboard/orcamento/geracao-caixa"),
          sub("Indicadores e Metas", "/dashboard/orcamento/indicadores-metas"),
          sub("Investimentos", "/dashboard/orcamento/investimentos"),
          sub("Recebimento por Grupo", "/dashboard/orcamento/recebimento-grupo"),
          sub("Receita de Lotes", "/dashboard/orcamento/receita-lotes"),
        ],
      },
      { name: "Orçamento de Despesas", icon: FileText, href: "/dashboard/orcamento/despesas" },
      { name: "Orçamento de Receitas", icon: FileText, href: "/dashboard/orcamento/receitas" },
      { name: "Orçamento de Vendas", icon: FileText, href: "/dashboard/orcamento/vendas" },
      { name: "Orçado x Realizado", icon: FileText, href: "/dashboard/orcamento/realizado" },
      { name: "DFC", icon: FileText, href: "/dashboard/orcamento/dfc" },
      { name: "Relatórios", icon: FileText, href: "/dashboard/orcamento/relatorios" },
    ],
  },
  {
    id: "forecast",
    title: "Forecast",
    icon: FileText,
    items: [
      { name: "Forecast de Despesas", icon: FileText, href: "/dashboard/forecast/despesas" },
      { name: "Forecast de Vendas", icon: FileText, href: "/dashboard/forecast/vendas" },
    ],
  },
  {
    id: "holding",
    title: "Consolidação",
    icon: LayoutDashboard,
    items: [
      { name: "Visão Global", icon: LayoutDashboard, href: "/dashboard/visao-global" },
      { name: "Estrutura societária MLDU", icon: GitBranch, href: "/dashboard/holding/estrutura-societaria" },
      { name: "Painel Corporativo", icon: LayoutDashboard, href: "/dashboard/holding/painel" },
      { name: "Base Histórica", icon: FileText, href: "/dashboard/holding/base-historica" },
      { name: "Apresentações (Curta/Longa)", icon: FileText, href: "/dashboard/holding/apresentacoes" },
      { name: "Relatórios", icon: FileText, href: "/dashboard/holding/relatorios" },
    ],
  },
  {
    id: "governanca",
    title: "Governança e Índices",
    icon: Settings,
    items: [
      { name: "Tabela de Índices", icon: Settings, href: "/dashboard/governance" },
      { name: "Aprovações (Workflow)", icon: FileText, href: "/dashboard/governance/workflow" },
      { name: "Relatórios", icon: FileText, href: "/dashboard/governance/relatorios" },
    ],
  },
  {
    id: "apoio",
    title: "Apoio",
    icon: Database,
    items: [
      { name: "Cenários", icon: FileText, href: "/dashboard/apoio/cenarios" },
      { name: "Centro de Custo", icon: FileText, href: "/dashboard/apoio/centro-de-custo" },
      { name: "Curvas Padrão", icon: FileText, href: "/dashboard/apoio/curvas" },
      { name: "Departamentos", icon: Users, href: "/dashboard/apoio/departamentos" },
      { name: "Empresas", icon: FileText, href: "/dashboard/apoio/empresas" },
      { name: "Impostos", icon: FileText, href: "/dashboard/apoio/impostos" },
      { name: "Índices Projetados", icon: FileText, href: "/dashboard/apoio/indicadores" },
      { name: "Índices de Mercado", icon: FileText, href: "/dashboard/apoio/indices-mercado" },
      { name: "Integração Sienge", icon: RefreshCw, href: "/dashboard/apoio/integracao" },
      { name: "Carga SharePoint", icon: Database, href: "/dashboard/apoio/migracao" },
      { name: "Planos de Pagamento", icon: FileText, href: "/dashboard/apoio/planos-de-pagamento" },
      { name: "Planos Financeiros", icon: FileText, href: "/dashboard/apoio/planos-financeiros" },
      { name: "Regras de Parceria", icon: Users, href: "/dashboard/apoio/parcerias" },
      { name: "Taxas de Funding", icon: FileText, href: "/dashboard/apoio/taxas-funding" },
      { name: "Visão", icon: FileText, href: "/dashboard/apoio/visao" },
      {
        name: "Relatórios",
        icon: FileText,
        href: "#",
        subItems: [
          reportSub("Centros de Custo", "/dashboard/apoio/relatorios?id=centro_custo"),
          reportSub("Empresas", "/dashboard/apoio/relatorios?id=empresas"),
          reportSub("Planos Financeiros", "/dashboard/apoio/relatorios?id=planos_financeiros"),
          reportSub("Cenários", "/dashboard/apoio/relatorios?id=cenarios"),
          reportSub("Planos de Pagamento", "/dashboard/apoio/relatorios?id=planos_pagamento"),
          reportSub("Indicadores Projetados", "/dashboard/apoio/relatorios?id=indicadores"),
          reportSub("Regimes Tributários", "/dashboard/apoio/relatorios?id=impostos"),
          reportSub("Curvas Padrão", "/dashboard/apoio/relatorios?id=curvas"),
          reportSub("Regras de Parceria", "/dashboard/apoio/relatorios?id=parcerias"),
          reportSub("Árvores de Visão", "/dashboard/apoio/relatorios?id=visao"),
          reportSub("Índices (IPCA)", "/dashboard/apoio/relatorios?id=indices_mercado"),
          reportSub("Taxas de Funding", "/dashboard/apoio/relatorios?id=taxas_funding"),
        ],
      },
    ],
  },
  {
    id: "seguranca",
    title: "Segurança",
    icon: Shield,
    items: [
      { name: "Usuários", icon: Users, href: "/dashboard/seguranca/usuarios" },
      { name: "Perfis de Acesso", icon: Settings, href: "/dashboard/seguranca/perfis" },
      { name: "Logs de Auditoria", icon: Settings, href: "/dashboard/seguranca/logs" },
      { name: "Relatórios", icon: FileText, href: "/dashboard/seguranca/relatorios" },
    ],
  },
];

export const MENU_MODULES: MenuModuleDef[] = RAW_MENU;

export const ACCESS_MODULES: AccessModuleDef[] = MENU_MODULES.map((mod) => {
  const groups: AccessGroup[] = [];
  const loose: AccessEntry[] = [];

  for (const item of mod.items) {
    if (item.subItems && item.subItems.length > 0) {
      groups.push({
        title: item.name,
        entries: item.subItems.map((s) => ({
          name: s.name,
          permKey: s.permKey,
          kind: "screen",
        })),
      });
    } else {
      loose.push({ name: item.name, permKey: item.name, kind: "screen" });
    }
  }

  if (loose.length > 0) {
    groups.push({
      title: "Telas",
      entries: loose,
    });
  }

  return { id: mod.id, title: mod.title, groups };
});

export function flattenAccessEntries(mod: AccessModuleDef): AccessEntry[] {
  return mod.groups.flatMap((g) => g.entries);
}

export function flattenScreenEntries(mod: AccessModuleDef): AccessEntry[] {
  return flattenAccessEntries(mod).filter((e) => e.kind === "screen");
}
