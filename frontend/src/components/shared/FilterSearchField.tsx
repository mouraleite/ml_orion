"use client";

import { Search, X } from "lucide-react";

interface FilterSearchFieldProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
}

export function FilterSearchField({
  value,
  onChange,
  placeholder = "Buscar...",
  label = "Buscar",
}: FilterSearchFieldProps) {
  return (
    <div className="flex-1 min-w-[200px]">
      <label className="text-xs text-slate-500 font-medium mb-1 flex items-center">
        <Search className="w-3.5 h-3.5 mr-1" />
        {label}
      </label>
      <div className="relative">
        <input
          type="text"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-2.5 py-1.5 pr-8 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
        {value ? (
          <button
            type="button"
            onClick={() => onChange("")}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            title="Limpar busca"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        ) : null}
      </div>
    </div>
  );
}
