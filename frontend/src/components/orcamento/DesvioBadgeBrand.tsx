"use client";

import { TrendingDown, TrendingUp } from "lucide-react";

export function DesvioBadgeBrand({
  value,
  inverted = false,
}: {
  value: number;
  inverted?: boolean;
}) {
  if (value === 0) return <span className="text-slate-400 font-medium">-</span>;
  const isPositive = value > 0;
  const good = inverted ? !isPositive : isPositive;
  return (
    <div
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold ${
        good ? "text-emerald-800 bg-emerald-50" : "text-red-800 bg-red-50"
      }`}
    >
      {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {Math.abs(value * 100).toFixed(1)}%
    </div>
  );
}
