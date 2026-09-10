/** Espelha backend/app/core/roles.py + /users/me (capabilities). */

export interface UserCapabilities {
  admin: boolean;
  diretor: boolean;
  gestor: boolean;
  analista: boolean;
}

export type UserAccessLike = {
  role?: string;
  effective_role?: string;
  capabilities?: UserCapabilities;
  full_name?: string;
  perfil?: { permissions?: Record<string, unknown>; name?: string };
  write_modules?: Record<string, boolean>;
} | null;

export function roleNorm(role?: string | null): string {
  return (role ?? "").trim();
}

export function effectiveRole(user: UserAccessLike): string {
  return roleNorm(user?.effective_role ?? user?.role);
}

export function capabilitiesFromUser(user: UserAccessLike): UserCapabilities {
  if (user?.capabilities) return user.capabilities;
  const role = effectiveRole(user);
  return {
    admin: isAdmin(role),
    diretor: isDiretor(role),
    gestor: isGestor(role),
    analista: isAnalista(role),
  };
}

export function isAdmin(role?: string | null): boolean {
  const r = roleNorm(role);
  return r === "ADMIN" || r === "Administrador" || r === "Desenvolvedor";
}

export function isDiretor(role?: string | null): boolean {
  const r = roleNorm(role);
  return isAdmin(role) || r === "DIRETOR" || r === "Diretor";
}

export function isGestor(role?: string | null): boolean {
  const r = roleNorm(role);
  return isDiretor(role) || r === "GESTOR" || r === "Gestor";
}

export function isAnalista(role?: string | null): boolean {
  const r = roleNorm(role);
  return isGestor(role) || r === "ANALISTA" || r === "Analista";
}

export function isAdminUser(user: UserAccessLike): boolean {
  return capabilitiesFromUser(user).admin;
}

export function isDiretorUser(user: UserAccessLike): boolean {
  return capabilitiesFromUser(user).diretor;
}

export function isGestorUser(user: UserAccessLike): boolean {
  return capabilitiesFromUser(user).gestor;
}

export function isAnalistaUser(user: UserAccessLike): boolean {
  return capabilitiesFromUser(user).analista;
}

/** Toggle consolidado nas telas de orçamento/forecast (comportamento atual). */
export function isAdminOrDiretor(role?: string | null): boolean {
  const r = roleNorm(role);
  return isAdmin(role) || r === "DIRETOR" || r === "Diretor";
}

export function isAdminOrDiretorUser(user: UserAccessLike): boolean {
  return isAdminOrDiretor(effectiveRole(user));
}

export function canSeeFullMenu(user: UserAccessLike): boolean {
  if (!user) return false;
  return isAdminUser(user) || user.full_name === "Desenvolvedor";
}

/** Visitante / somente leitura nas viabilidades. */
export function isReadOnlyVisitor(role?: string | null): boolean {
  const r = roleNorm(role);
  return r === "VISITANTE" || r === "READ_ONLY" || r === "Consulta";
}

/** Papel do colaborador (campo Permissão), não o nome do perfil. */
export function isUserViewOnly(user: UserAccessLike): boolean {
  if (!user) return true;
  if (isAdmin(user.role) || user.full_name === "Desenvolvedor") return false;
  return isReadOnlyVisitor(user.role);
}

export function isReadOnlyVisitorUser(user: UserAccessLike): boolean {
  return isUserViewOnly(user);
}

export function canCreateViabilidade(role?: string | null): boolean {
  const r = roleNorm(role);
  return r === "ADMIN" || r === "DIRETOR" || r === "ANALISTA" || isAdmin(role);
}

export function canCreateViabilidadeUser(user: UserAccessLike): boolean {
  return canWriteModule(user, "Rentabilidade de Produtos");
}

/** Admin vê o menu inteiro e pode gravar em qualquer módulo. */
export function canWriteModule(user: UserAccessLike, moduleTitle: string): boolean {
  if (!user) return false;
  if (isAdmin(user.role) || user.full_name === "Desenvolvedor") return true;
  if (isUserViewOnly(user)) return false;
  if (isAdminUser(user)) return true;
  const fromApi = (user as { write_modules?: Record<string, boolean> }).write_modules;
  if (fromApi && typeof fromApi[moduleTitle] === "boolean") return fromApi[moduleTitle];
  const perms = user.perfil?.permissions as Record<string, Record<string, boolean>> | undefined;
  const bucket = perms?.[moduleTitle];
  if (bucket && typeof bucket._write === "boolean") return bucket._write;
  return isAnalistaUser(user);
}
