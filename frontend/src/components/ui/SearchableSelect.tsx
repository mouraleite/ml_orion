import React, { useState, useRef, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Check, Search, X } from 'lucide-react';

function foldSearch(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[.\-/]/g, "");
}

export interface Option {
  id: string | number;
  label: string;
}

interface SearchableSelectProps {
  options: Option[];
  value: string | number | "";
  onChange: (value: string | number | "") => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  clearable?: boolean;
}

export function SearchableSelect({ options, value, onChange, placeholder = "Selecione...", className = "", disabled = false, clearable = true }: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [rect, setRect] = useState<DOMRect | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

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
      if (isOpen) {
        if (e.type === 'scroll' && menuRef.current && e.target instanceof Node && menuRef.current.contains(e.target)) {
          return;
        }
        setIsOpen(false);
      }
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

  const selectedOption = options.find((opt) => String(opt.id) === String(value));
  const hasValue = value !== "" && value !== null && value !== undefined;

  const filteredOptions = useMemo(() => {
    if (!searchTerm) return options;
    const needle = foldSearch(searchTerm);
    return options.filter((opt) => foldSearch(String(opt.label)).includes(needle) || foldSearch(String(opt.id)).includes(needle));
  }, [options, searchTerm]);

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      <div
        className={`w-full py-2 px-3 text-sm border rounded bg-white flex items-center justify-between transition-colors shadow-sm focus-within:ring-1 focus-within:ring-brand-500 focus-within:border-brand-500 ${
          disabled ? "bg-slate-50 opacity-75 cursor-not-allowed border-slate-200" : "cursor-pointer border-slate-300 hover:border-slate-400"
        } ${isOpen && !disabled ? "ring-1 ring-brand-500 border-brand-500" : ""} ${hasValue && !disabled ? "border-brand-400 bg-brand-50/10" : ""}`}
        onClick={() => {
          if (disabled) return;
          if (!isOpen) {
            updateRect();
            setSearchTerm("");
          }
          setIsOpen(!isOpen);
        }}
      >
        <div className="flex-1 truncate text-slate-800 font-medium">
          {selectedOption ? selectedOption.label : <span className="text-slate-400 font-normal">{placeholder}</span>}
        </div>
        <div className="flex items-center gap-1 ml-2">
          {hasValue && clearable && !disabled && (
            <button
              onClick={(e) => { e.stopPropagation(); onChange(""); setIsOpen(false); }}
              className="text-slate-400 hover:text-red-500 transition-colors p-0.5 rounded hover:bg-red-50"
              title="Limpar seleção"
              type="button"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <ChevronDown className={`w-4 h-4 transition-transform text-slate-400 ${isOpen ? "rotate-180" : ""}`} />
        </div>
      </div>

      {isOpen && !disabled && typeof window !== 'undefined' && rect && createPortal(
        <div 
          ref={menuRef}
          className="fixed z-[9999] mt-1 bg-white border border-slate-200 rounded-lg shadow-lg overflow-hidden flex flex-col"
          style={{ 
            top: rect.bottom, 
            left: rect.left, 
            width: rect.width,
            maxHeight: '300px'
          }}
        >
          <div className="p-2 border-b border-slate-100 flex items-center shrink-0">
             <Search className="w-4 h-4 text-slate-400 mr-2" />
             <input
               type="text"
               autoFocus
               className="w-full text-sm outline-none bg-transparent text-slate-700"
               placeholder="Digite para buscar..."
               value={searchTerm}
               onChange={(e) => setSearchTerm(e.target.value)}
             />
          </div>
          <div className="overflow-y-auto flex-1">
            {filteredOptions.length === 0 ? (
              <div className="p-3 text-sm text-slate-500 text-center">Nenhum resultado encontrado</div>
            ) : (
              <div className="p-1">
                {filteredOptions.map((option) => {
                  const isSelected = String(value) === String(option.id);
                  return (
                    <div
                      key={option.id}
                      onClick={() => {
                        onChange(option.id);
                        setIsOpen(false);
                      }}
                      className={`flex items-center px-3 py-2 text-sm cursor-pointer rounded-md transition-colors ${
                        isSelected ? "bg-brand-50 text-brand-700 font-medium" : "text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <span className="flex-1 truncate">{option.label}</span>
                      {isSelected && <Check className="w-4 h-4 ml-2 flex-shrink-0" />}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
