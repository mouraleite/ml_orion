import React, { useState, useRef, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Check, Search, X } from 'lucide-react';

type MultiSelectOption = string | { value: string; label: string };

interface MultiSelectProps {
  options: MultiSelectOption[];
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  className?: string;
  label?: string;
  showSelectAll?: boolean;
}

function getOptionValue(opt: MultiSelectOption): string {
  return typeof opt === 'string' ? opt : opt.value;
}

function getOptionLabel(opt: MultiSelectOption): string {
  return typeof opt === 'string' ? opt : opt.label;
}

export function MultiSelect({ options, value, onChange, placeholder = "Todos", className = "", label, showSelectAll = true }: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [rect, setRect] = useState<DOMRect | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const updateRect = () => {
    if (containerRef.current) {
      setRect(containerRef.current.getBoundingClientRect());
    }
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        containerRef.current && !containerRef.current.contains(target) &&
        (!menuRef.current || !menuRef.current.contains(target))
      ) {
        setIsOpen(false);
      }
    };

    const handleScrollOrResize = (e: Event) => {
      if (!isOpen) return;
      if (e.type === 'scroll' && menuRef.current && e.target instanceof Node && menuRef.current.contains(e.target)) {
        return;
      }
      setIsOpen(false);
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      window.addEventListener("scroll", handleScrollOrResize, true);
      window.addEventListener("resize", handleScrollOrResize);
      updateRect();
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("scroll", handleScrollOrResize, true);
      window.removeEventListener("resize", handleScrollOrResize);
    };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    } else if (!isOpen) {
      setSearchTerm("");
    }
  }, [isOpen]);

  const toggleOption = (optionValue: string) => {
    if (value.includes(optionValue)) {
      onChange(value.filter(v => v !== optionValue));
    } else {
      onChange([...value, optionValue]);
    }
  };

  const hasValue = value.length > 0;

  const getSelectedLabel = () => {
    if (value.length === 0) return placeholder;
    if (value.length === options.length && options.length > 1) {
      return "Todos";
    }
    if (value.length === 1) {
      const found = options.find(o => getOptionValue(o) === value[0]);
      return found ? getOptionLabel(found) : value[0];
    }
    return `${value.length} selecionados`;
  };

  const filteredOptions = useMemo(() => {
    if (!searchTerm) return options;
    return options.filter(opt => 
      getOptionLabel(opt).toLowerCase().includes(searchTerm.toLowerCase()) || 
      getOptionValue(opt).toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [options, searchTerm]);

  const allFilteredValues = filteredOptions.map(getOptionValue);
  const allSelected = allFilteredValues.length > 0 && allFilteredValues.every(v => value.includes(v));

  const handleSelectAll = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (allFilteredValues.length === 0) return;
    onChange(allFilteredValues);
  };

  const handleClearAll = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (allFilteredValues.length === 0) {
      onChange([]);
      return;
    }
    onChange(value.filter((v) => !allFilteredValues.includes(v)));
  };

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      {label && (
        <div className="flex items-center mb-1.5 h-4">
          <label className="block text-xs font-semibold text-slate-600 leading-none m-0">{label}</label>
        </div>
      )}
      <div
        className={`w-full py-2 px-3 text-sm border rounded-lg flex items-center justify-between cursor-pointer transition-colors ${
          hasValue ? "border-[#F5883A] bg-orange-50 text-[#d97732] font-medium" : "border-slate-200 text-slate-800 bg-white hover:border-slate-300"
        } ${isOpen ? "ring-2 ring-[#F5883A]/40 border-[#F5883A]" : ""}`}
        onClick={() => {
          if (!isOpen) {
            updateRect();
          }
          setIsOpen(!isOpen);
        }}
      >
        <div className="flex-1 truncate">
          {hasValue ? getSelectedLabel() : placeholder}
        </div>
        <div className="flex items-center gap-1 ml-2">
          {hasValue && (
            <button
              onClick={(e) => { e.stopPropagation(); onChange([]); }}
              className="text-[#F5883A]/70 hover:text-[#F5883A] transition-colors p-0.5 rounded hover:bg-orange-100"
              title="Limpar seleção"
              type="button"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          <ChevronDown className={`w-4 h-4 transition-transform text-slate-400 ${isOpen ? "rotate-180" : ""}`} />
        </div>
      </div>

      {isOpen && typeof window !== 'undefined' && rect && createPortal(
        <div
          ref={menuRef}
          className="fixed z-[9999] mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-80 flex flex-col"
          style={{
            top: rect.bottom,
            left: rect.left,
            width: rect.width,
          }}
        >
          {options.length > 0 && showSelectAll && (
            <div className="px-2 py-1.5 border-b border-slate-100 flex items-center gap-2 shrink-0 bg-slate-50 rounded-t-lg">
              <button
                type="button"
                onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); }}
                onClick={handleSelectAll}
                disabled={allFilteredValues.length === 0 || allSelected}
                className="text-xs font-semibold text-slate-600 hover:text-[#F5883A] px-2 py-1 rounded hover:bg-orange-50 disabled:opacity-40 disabled:pointer-events-none"
              >
                Marcar todos
              </button>
              <button
                type="button"
                onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); }}
                onClick={handleClearAll}
                disabled={allFilteredValues.length === 0 || !allFilteredValues.some((v) => value.includes(v))}
                className="text-xs font-semibold text-slate-600 hover:text-red-600 px-2 py-1 rounded hover:bg-red-50 disabled:opacity-40 disabled:pointer-events-none"
              >
                Desmarcar todos
              </button>
            </div>
          )}
          {options.length > 5 && (
            <div className="p-2 border-b border-slate-100 flex items-center bg-slate-50">
              <Search className="w-4 h-4 text-slate-400 mr-2 flex-shrink-0" />
              <input
                ref={inputRef}
                type="text"
                className="w-full bg-transparent text-sm border-none focus:outline-none focus:ring-0 text-slate-700 placeholder-slate-400"
                placeholder="Pesquisar..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          )}

          <div className="overflow-y-auto flex-1 max-h-60 p-1">
            {filteredOptions.length === 0 ? (
              <div className="p-3 text-sm text-slate-500 text-center">Nenhuma opção encontrada</div>
            ) : (
              filteredOptions.map((option) => {
                const optValue = getOptionValue(option);
                const optLabel = getOptionLabel(option);
                const isSelected = value.includes(optValue);
                return (
                  <div
                    key={optValue}
                    onClick={() => toggleOption(optValue)}
                    className={`flex items-center px-3 py-2 text-sm cursor-pointer rounded-md transition-colors ${
                      isSelected ? "bg-orange-50/50 text-[#F5883A] font-medium" : "text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <div className={`w-4 h-4 rounded border mr-2 flex items-center justify-center transition-colors flex-shrink-0 ${
                      isSelected ? "bg-[#F5883A] border-[#F5883A]" : "border-slate-300"
                    }`}>
                      {isSelected && <Check className="w-3 h-3 text-white" />}
                    </div>
                    <span className="truncate" title={optLabel}>{optLabel}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}

