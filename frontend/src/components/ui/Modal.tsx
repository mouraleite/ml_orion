import React, { useEffect } from "react";
import { X } from "lucide-react";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
  size?: string;
}

export function Modal({ isOpen, onClose, title, children, className = "", size }: ModalProps) {
  const sizeMap: Record<string, string> = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
    xl: "max-w-xl",
    "2xl": "max-w-2xl",
    "3xl": "max-w-3xl",
    "4xl": "max-w-4xl",
    "5xl": "max-w-5xl",
    full: "max-w-[90vw]",
  };
  const sizeClass = size ? (sizeMap[size] || size) : "max-w-lg";

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto overscroll-contain">
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Centering + scrollable viewport */}
      <div className="relative z-50 flex min-h-full items-center justify-center p-4">
        <div
          className={`relative flex w-full ${sizeClass} max-h-[calc(100dvh-2rem)] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl ${className}`}
          role="dialog"
          aria-modal="true"
        >
          {title && (
            <div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-6 pb-4 pt-6">
              <h2 className="pr-2 text-lg font-bold text-slate-900">{title}</h2>
              <button
                onClick={onClose}
                className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-orange"
              >
                <X className="h-5 w-5" />
                <span className="sr-only">Fechar</span>
              </button>
            </div>
          )}
          {!title && (
            <button
              onClick={onClose}
              className="absolute right-4 top-4 z-10 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-orange"
            >
              <X className="h-5 w-5" />
              <span className="sr-only">Fechar</span>
            </button>
          )}
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-5 text-slate-800">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
