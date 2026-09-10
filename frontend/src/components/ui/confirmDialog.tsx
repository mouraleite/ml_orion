"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, HelpCircle } from "lucide-react";
import { Button } from "./Button";

export type ConfirmVariant = "default" | "danger";

export type ConfirmOptions = {
  title?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmVariant;
};

type Pending = ConfirmOptions & {
  message: string;
  resolve: (ok: boolean) => void;
};

const queue: Pending[] = [];
let current: Pending | null = null;
const listeners = new Set<(pending: Pending | null) => void>();

function publish(pending: Pending | null) {
  current = pending;
  listeners.forEach((listener) => listener(pending));
}

function dequeue() {
  publish(queue.shift() ?? null);
}

function finish(ok: boolean) {
  const pending = current;
  if (!pending) return;
  current = null;
  pending.resolve(ok);
  dequeue();
}

export function confirmDialog(message: string, options: ConfirmOptions = {}): Promise<boolean> {
  return new Promise((resolve) => {
    const pending: Pending = { message, ...options, resolve };
    if (current) {
      queue.push(pending);
      return;
    }
    publish(pending);
  });
}

export function ConfirmHost() {
  const [pending, setPending] = useState<Pending | null>(current);
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    listeners.add(setPending);
    return () => {
      listeners.delete(setPending);
    };
  }, []);

  useEffect(() => {
    if (!pending) return;
    const focusTimer = window.setTimeout(() => confirmRef.current?.focus(), 40);
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        finish(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(focusTimer);
      window.removeEventListener("keydown", onKey);
    };
  }, [pending]);

  if (!pending) return null;

  const isDanger = pending.variant === "danger";
  const title = pending.title || (isDanger ? "Confirmar exclusão" : "Confirmar");
  const confirmLabel = pending.confirmLabel || (isDanger ? "Excluir" : "Confirmar");
  const cancelLabel = pending.cancelLabel || "Cancelar";

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={() => finish(false)} />
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="ml-confirm-title"
        aria-describedby="ml-confirm-message"
        className="relative z-[81] w-full max-w-md rounded-xl bg-white shadow-xl border border-slate-200 p-6"
      >
        <div className="flex items-start gap-3">
          <div
            className={`w-10 h-10 rounded-lg shrink-0 flex items-center justify-center ${
              isDanger
                ? "bg-red-50 border border-red-100 text-red-600"
                : "bg-emerald-50 border border-emerald-100 text-emerald-600"
            }`}
          >
            {isDanger ? <AlertTriangle size={20} /> : <HelpCircle size={20} />}
          </div>
          <div className="min-w-0">
            <h2 id="ml-confirm-title" className="text-lg font-bold text-slate-900">
              {title}
            </h2>
            <p id="ml-confirm-message" className="text-sm text-slate-600 mt-1 whitespace-pre-line">
              {pending.message}
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <Button type="button" variant="secondary" onClick={() => finish(false)}>
            {cancelLabel}
          </Button>
          <Button
            ref={confirmRef}
            type="button"
            variant={isDanger ? "danger" : "primary"}
            onClick={() => finish(true)}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
