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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Content */}
      <div
        className={`relative z-50 w-full ${sizeClass} max-h-[90vh] flex flex-col rounded-xl bg-white shadow-xl border border-slate-200 ${className}`}
      >
        {title && (
          <div className="flex items-center justify-between shrink-0 px-6 pt-6 pb-4 border-b border-slate-200">
            <h2 className="text-lg font-bold text-slate-900 pr-2">{title}</h2>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-orange"
            >
              <X className="h-5 w-5" />
              <span className="sr-only">Fechar</span>
            </button>
          </div>
        )}
        {!title && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 z-10 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-orange"
          >
            <X className="h-5 w-5" />
            <span className="sr-only">Fechar</span>
          </button>
        )}
        <div className="text-slate-800 flex-1 min-h-0 overflow-y-auto overscroll-contain px-6 py-5">
          {children}
        </div>
      </div>
    </div>
  );
}
