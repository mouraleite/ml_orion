"use client";

interface YearSelectProps {
  value: number;
  years: number[];
  onChange: (year: number) => void;
  className?: string;
}

export function YearSelect({ value, years, onChange, className = "" }: YearSelectProps) {
  if (years.length === 0) return null;

  return (
    <div className={`min-w-[100px] ${className}`}>
      <label className="block text-xs font-semibold text-slate-600 mb-1.5">Ano</label>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full py-2 px-3 text-sm border border-slate-200 rounded-lg bg-white text-slate-800 hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#F5883A]/40 focus:border-[#F5883A]"
      >
        {years.map((y) => (
          <option key={y} value={y}>
            {y}
          </option>
        ))}
      </select>
    </div>
  );
}
