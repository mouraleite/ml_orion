/** Id 0 = Todos; id negativo = Diretoria (-diretoria_id). Não usar `if (!deptId)`. */
export function isDepartmentContextId(deptId: unknown): deptId is number {
  return typeof deptId === "number" && Number.isFinite(deptId);
}
