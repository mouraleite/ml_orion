"use client";

import { RefreshCw } from "lucide-react";

/** Loading padrão do ML Órion (telas, rotas e painéis). */
export function AppLoadingState({
  title = "Carregando informações…",
  hint = "Isso pode levar alguns segundos.",
}: {
  title?: string;
  hint?: string;
}) {
  return (
    <div
      className="flex-1 flex flex-col items-center justify-center min-h-[220px] gap-3 px-6"
      role="status"
      aria-live="polite"
    >
      <RefreshCw className="w-6 h-6 text-ml-green animate-spin" aria-hidden />
      <p className="text-sm font-semibold text-slate-700">{title}</p>
      <p className="text-xs text-slate-500 text-center max-w-sm leading-relaxed">{hint}</p>
    </div>
  );
}

/** Tela cheia (auth, Suspense do layout). Fundo branco como o restante do app. */
export function AppLoadingScreen() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-white">
      <AppLoadingState />
    </div>
  );
}

/** @deprecated Use AppLoadingState — mesmo componente, nome antigo das telas de orçamento. */
export const BudgetLoadingState = AppLoadingState;

export function BudgetRefreshingBanner() {
  return (
    <div className="shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 text-xs text-slate-600">
      <RefreshCw className="w-3.5 h-3.5 animate-spin text-ml-green" aria-hidden />
      Atualizando informações…
    </div>
  );
}

export function BudgetLoadError({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center min-h-[220px] gap-3 px-6 text-center">
      <p className="text-sm font-semibold text-slate-800">Não foi possível carregar</p>
      <p className="text-xs text-slate-500 max-w-sm leading-relaxed">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          Tentar de novo
        </button>
      ) : null}
    </div>
  );
}

export function acompRequestError(err: unknown): string {
  const ax = err as {
    code?: string;
    message?: string;
    response?: { data?: { detail?: unknown } };
  };
  if (ax?.code === "ECONNABORTED") {
    return "O cálculo demorou demais. Tente de novo.";
  }
  const detail = ax?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (!ax?.response) return "Não foi possível conectar ao servidor.";
  return "Não foi possível carregar as informações.";
}
