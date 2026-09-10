"use client";

import { useAuth } from "@/contexts/AuthContext";
import { isDepartmentContextId } from "./departmentContext";

export { isDepartmentContextId } from "./departmentContext";

/** ID do departamento ativo (header X-Department-Id + escopo do usuário). */
export function useActiveDepartmentId(): number {
  const { activeDepartamentoId, user } = useAuth();
  if (isDepartmentContextId(activeDepartamentoId)) return activeDepartamentoId;
  if (isDepartmentContextId(user?.departamento_id)) return user!.departamento_id;
  if (user?.departamentos?.length) return user.departamentos[0].id;
  return 1;
}
