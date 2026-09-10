"use client";

import React, { useState, useRef } from "react";

interface CurrencyInputProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

/**
 * Input formatado como moeda (pt-BR) sem símbolo.
 * Exibe: 343.497,86
 * Durante edição: permite digitar normalmente
 * Ao sair (blur): reformata com vírgula decimal
 */
export function CurrencyInput({
  value,
  onChange,
  disabled = false,
  placeholder = "0,00",
  className = "",
}: CurrencyInputProps) {
  const [editing, setEditing] = useState(false);
  const [rawText, setRawText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Formata um número para exibição (ex: 343497.86 → "343.497,86")
  const formatDisplay = (num: number): string => {
    if (!num && num !== 0) return "";
    if (num === 0) return "";
    return num.toLocaleString("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  // Converte texto digitado para número (aceita "," e "." como separadores)
  const parseRaw = (text: string): number => {
    if (!text) return 0;
    // Remove pontos de milhar, substitui vírgula por ponto
    const normalized = text.replace(/\./g, "").replace(",", ".");
    const parsed = parseFloat(normalized);
    return isNaN(parsed) ? 0 : Math.round(parsed * 100) / 100;
  };

  const handleFocus = () => {
    setEditing(true);
    // Ao focar, exibe o valor raw para edição fácil
    setRawText(value !== 0 ? value.toString().replace(".", ",") : "");
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const handleBlur = () => {
    setEditing(false);
    const parsed = parseRaw(rawText);
    onChange(parsed);
    setRawText("");
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Permite apenas números, vírgula e ponto
    const val = e.target.value.replace(/[^0-9,\.]/g, "");
    setRawText(val);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === "Tab") {
      inputRef.current?.blur();
    }
  };

  const baseClass =
    "w-full p-1 text-xs text-right border-0 border-b border-transparent focus:border-brand-500 focus:ring-0 bg-transparent hover:bg-slate-50 transition-colors disabled:bg-transparent disabled:border-transparent outline-none";

  return (
    <input
      ref={inputRef}
      type="text"
      inputMode="decimal"
      className={`${baseClass} ${className}`}
      value={editing ? rawText : formatDisplay(value)}
      onFocus={handleFocus}
      onBlur={handleBlur}
      onChange={handleChange}
      onKeyDown={handleKeyDown}
      disabled={disabled}
      placeholder={placeholder}
    />
  );
}
