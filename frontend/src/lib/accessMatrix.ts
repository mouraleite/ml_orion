import {
  ACCESS_MODULES,
  MENU_MODULES,
  flattenAccessEntries,
  flattenScreenEntries,
  type AccessModuleDef,
  type MenuModuleDef,
  type MenuSubItem,
} from "./menuCatalog";

export type PermissionsMap = Record<string, Record<string, boolean>>;

/** Flag de criar/alterar no bucket do módulo — não é tela. */
export const WRITE_KEY = "_write";

/** Perfis cujo nome, sem `_write` gravado, já podia alterar (papel legado). */
export const WRITE_DEFAULT_PROFILE_NAMES = new Set([
  "administrador",
  "diretor",
  "controladoria",
  "gestor",
  "gestor financeiro",
  "marketing",
  "analista",
]);

export function isReservedPermKey(key: string): boolean {
  return key.startsWith("_");
}

export function defaultModuleWrite(profileName?: string | null): boolean {
  return WRITE_DEFAULT_PROFILE_NAMES.has((profileName ?? "").trim().toLowerCase());
}

export function isModuleWriteEnabled(
  perms: PermissionsMap | undefined,
  moduleTitle: string,
  profileName?: string | null,
): boolean {
  const bucket = moduleBucket(perms, moduleTitle);
  if (typeof bucket[WRITE_KEY] === "boolean") return bucket[WRITE_KEY];
  return defaultModuleWrite(profileName);
}

export function setModuleWrite(
  perms: PermissionsMap,
  moduleTitle: string,
  value: boolean,
): PermissionsMap {
  const next = clonePerms(perms);
  if (!next[moduleTitle]) next[moduleTitle] = {};
  next[moduleTitle][WRITE_KEY] = value;
  return next;
}

export function ensureWriteFlags(perms: PermissionsMap, profileName: string): PermissionsMap {
  const next = clonePerms(perms || {});
  for (const mod of ACCESS_MODULES) {
    if (!next[mod.title]) next[mod.title] = {};
    if (typeof next[mod.title][WRITE_KEY] !== "boolean") {
      next[mod.title][WRITE_KEY] = defaultModuleWrite(profileName);
    }
  }
  return next;
}

/** Chaves antigas da matriz → nome atual do menu. */
export const PERMISSION_ALIASES: Record<string, Record<string, string[]>> = {
  "Rentabilidade de Produtos": {
    Viabilidades: ["Lista de Produtos"],
    "DFC de Empreendimentos": ["Acompanhamento de Empreendimentos"],
  },
  "Modelagem Financeira": {
    "Modelagem Mestre": ["Modelos"],
  },
  Orçamento: {
    "Orçamento de Despesas": ["Despesas"],
    "Orçamento de Receitas": ["Receitas"],
    "Orçamento de Vendas": ["Vendas"],
    "Orçado x Realizado": ["Realizado", "Comparativo de Versões"],
    "DFC gerencial": ["DFC"],
    "Análise de Orçamento": ["Despesas por empreendimento", "DFC"],
  },
  Forecast: {
    "Forecast de Despesas": ["Despesas"],
    "Forecast de Vendas": ["Vendas"],
  },
  Consolidação: {
    "Visão Global": ["Fluxo de Caixa Consolidado"],
  },
  "Governança e Índices": {
    "Tabela de Índices": ["Índices"],
    "Aprovações (Workflow)": ["Governança"],
  },
  Apoio: {
    "Centro de Custo": ["Centros de Custo"],
    "Curvas Padrão": ["Curvas Base"],
    Impostos: ["Regimes Tributários"],
  },
  Segurança: {
    "Logs de Auditoria": ["Auditoria"],
  },
};

export type SearchLike = { get(name: string): string | null } | string | null | undefined;

function clonePerms(perms: PermissionsMap): PermissionsMap {
  return JSON.parse(JSON.stringify(perms || {})) as PermissionsMap;
}

function moduleBucket(perms: PermissionsMap | undefined, moduleTitle: string): Record<string, boolean> {
  const bucket = perms?.[moduleTitle];
  return bucket && typeof bucket === "object" ? bucket : {};
}

export function isScreenPermitted(
  perms: PermissionsMap | undefined,
  moduleTitle: string,
  permKey: string,
): boolean {
  if (isReservedPermKey(permKey)) return false;
  const bucket = moduleBucket(perms, moduleTitle);
  if (bucket[permKey] === true) return true;
  const aliases = PERMISSION_ALIASES[moduleTitle]?.[permKey] ?? [];
  return aliases.some((alias) => bucket[alias] === true);
}

export function hydratePermissions(saved: PermissionsMap | undefined): PermissionsMap {
  const result = clonePerms(saved || {});
  for (const mod of ACCESS_MODULES) {
    const bucket = { ...(result[mod.title] || {}) };
    for (const entry of flattenAccessEntries(mod)) {
      if (bucket[entry.permKey] === true) continue;
      if (isScreenPermitted({ [mod.title]: bucket }, mod.title, entry.permKey)) {
        bucket[entry.permKey] = true;
      }
    }
    result[mod.title] = bucket;
  }
  return result;
}

export function persistPermissions(ui: PermissionsMap): PermissionsMap {
  const result = clonePerms(ui);
  for (const mod of ACCESS_MODULES) {
    const bucket = { ...(result[mod.title] || {}) };
    const writeOn = bucket[WRITE_KEY] === true;
    for (const entry of flattenAccessEntries(mod)) {
      const on = bucket[entry.permKey] === true;
      bucket[entry.permKey] = on;
      for (const alias of PERMISSION_ALIASES[mod.title]?.[entry.permKey] ?? []) {
        bucket[alias] = on;
      }
    }
    bucket[WRITE_KEY] = writeOn;
    result[mod.title] = bucket;
  }
  return result;
}

export function filterMenuModules(
  modules: MenuModuleDef[] = MENU_MODULES,
  perms: PermissionsMap | undefined,
): MenuModuleDef[] {
  if (!perms) return [];
  return modules
    .map((mod) => {
      const items = mod.items.flatMap((item) => {
        if (item.subItems && item.subItems.length > 0) {
          const subItems = item.subItems.filter((sub) =>
            isScreenPermitted(perms, mod.title, sub.permKey),
          );
          if (subItems.length === 0) return [];
          return [{ ...item, subItems }];
        }
        if (isScreenPermitted(perms, mod.title, item.name)) return [item];
        return [];
      });
      return { ...mod, items };
    })
    .filter((mod) => mod.items.length > 0);
}

export type MatchedScreen = {
  moduleTitle: string;
  name: string;
  permKey: string;
  pathname: string;
  queryId?: string;
};

function parseHref(href: string): { pathname: string; queryId?: string } | null {
  if (!href || href === "#") return null;
  const [pathname, query] = href.split("?");
  if (!pathname) return null;
  if (!query) return { pathname };
  const params = new URLSearchParams(query);
  const queryId = params.get("id") ?? undefined;
  return { pathname, queryId };
}

export function allScreenRoutes(modules: MenuModuleDef[] = MENU_MODULES): MatchedScreen[] {
  const routes: MatchedScreen[] = [];
  for (const mod of modules) {
    for (const item of mod.items) {
      if (item.subItems && item.subItems.length > 0) {
        for (const sub of item.subItems) {
          const parsed = parseHref(sub.href);
          if (!parsed) continue;
          routes.push({
            moduleTitle: mod.title,
            name: sub.name,
            permKey: sub.permKey,
            pathname: parsed.pathname,
            queryId: parsed.queryId,
          });
        }
        continue;
      }
      const parsed = parseHref(item.href);
      if (!parsed) continue;
      routes.push({
        moduleTitle: mod.title,
        name: item.name,
        permKey: item.name,
        pathname: parsed.pathname,
        queryId: parsed.queryId,
      });
    }
  }
  return routes;
}

function readQueryId(search: SearchLike): string | null {
  if (!search) return null;
  if (typeof search === "string") {
    const raw = search.startsWith("?") ? search.slice(1) : search;
    return new URLSearchParams(raw).get("id");
  }
  return search.get("id");
}

export function matchMenuPath(
  pathname: string,
  search?: SearchLike,
  modules: MenuModuleDef[] = MENU_MODULES,
): MatchedScreen | null {
  const queryId = readQueryId(search);
  const hits = allScreenRoutes(modules).filter((route) => {
    const pathOk = pathname === route.pathname || pathname.startsWith(`${route.pathname}/`);
    if (!pathOk) return false;
    if (route.queryId) return queryId === route.queryId;
    return true;
  });
  if (hits.length === 0) return null;
  hits.sort((a, b) => b.pathname.length - a.pathname.length);
  return hits[0];
}

const OPEN_PATHS = new Set(["/dashboard", "/dashboard/"]);

export function isPathAllowed(
  perms: PermissionsMap | undefined,
  pathname: string,
  search?: SearchLike,
): boolean {
  if (!pathname || OPEN_PATHS.has(pathname)) return true;
  const hit = matchMenuPath(pathname, search);
  if (!hit) return true;
  return isScreenPermitted(perms, hit.moduleTitle, hit.permKey);
}

export function moduleScreenStats(mod: AccessModuleDef, perms: PermissionsMap): { granted: number; total: number } {
  const screens = flattenScreenEntries(mod);
  const granted = screens.filter((e) => perms[mod.title]?.[e.permKey] === true).length;
  return { granted, total: screens.length };
}

export function setEntry(
  perms: PermissionsMap,
  moduleTitle: string,
  permKey: string,
  value: boolean,
): PermissionsMap {
  const next = clonePerms(perms);
  if (!next[moduleTitle]) next[moduleTitle] = {};
  next[moduleTitle][permKey] = value;
  return next;
}

export function setEntries(
  perms: PermissionsMap,
  moduleTitle: string,
  permKeys: string[],
  value: boolean,
): PermissionsMap {
  const next = clonePerms(perms);
  if (!next[moduleTitle]) next[moduleTitle] = {};
  for (const key of permKeys) next[moduleTitle][key] = value;
  return next;
}

export type { MenuSubItem };
