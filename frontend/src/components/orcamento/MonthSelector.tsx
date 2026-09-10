import React from 'react';
import { Check, Calendar } from 'lucide-react';

export interface MonthSelectorProps {
  selectedMonths: number[];
  onChange: (months: number[]) => void;
}

const MESES = [
  { id: 1, label: "Jan" }, { id: 2, label: "Fev" }, { id: 3, label: "Mar" },
  { id: 4, label: "Abr" }, { id: 5, label: "Mai" }, { id: 6, label: "Jun" },
  { id: 7, label: "Jul" }, { id: 8, label: "Ago" }, { id: 9, label: "Set" },
  { id: 10, label: "Out" }, { id: 11, label: "Nov" }, { id: 12, label: "Dez" }
];

export const MonthSelector: React.FC<MonthSelectorProps> = ({ selectedMonths, onChange }) => {
  const isAllSelected = selectedMonths.length === 12;

  const toggleMonth = (id: number) => {
    if (selectedMonths.includes(id)) {
      const newSelection = selectedMonths.filter(m => m !== id);
      if (newSelection.length === 0) {
        onChange(MESES.map(m => m.id));
      } else {
        onChange(newSelection);
      }
    } else {
      onChange([...selectedMonths, id].sort((a, b) => a - b));
    }
  };

  const toggleAll = () => {
    onChange(MESES.map(m => m.id));
  };

  return (
    <div className="flex flex-wrap items-center gap-2 mb-4 p-3 bg-white border border-slate-200 rounded-xl shadow-sm">
      <div className="flex items-center text-slate-500 mr-2 text-sm font-medium">
        <Calendar size={16} className="mr-2" />
        Filtro de Meses
      </div>
      <button
        onClick={toggleAll}
        className={`px-3 py-1.5 text-xs font-semibold rounded-full transition-all ${
          isAllSelected
            ? 'bg-brand-600 text-white shadow-sm'
            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
        }`}
      >
        Todos
      </button>
      <div className="h-4 w-px bg-slate-300 mx-1"></div>
      {MESES.map(mes => {
        const isSelected = selectedMonths.includes(mes.id);
        return (
          <button
            key={mes.id}
            onClick={() => {
                // Se clicar em um mês e "Todos" estava marcado, deixa só aquele mês
                if (isAllSelected) {
                    onChange([mes.id]);
                } else {
                    toggleMonth(mes.id);
                }
            }}
            className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all flex items-center ${
              isSelected
                ? 'bg-brand-100 text-brand-700 ring-1 ring-brand-500/50'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300'
            }`}
          >
            {isSelected && <Check size={12} className="mr-1" />}
            {mes.label}
          </button>
        );
      })}
    </div>
  );
};
