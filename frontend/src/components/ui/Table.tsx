import React from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

export function Table({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="relative w-full overflow-auto rounded-lg border border-slate-200 bg-white shadow-sm">
      <table
        className={`w-full caption-bottom text-sm ${className}`}
        {...props}
      />
    </div>
  );
}

export function TableHeader({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={`border-b border-slate-200 bg-slate-50 ${className}`}
      {...props}
    />
  );
}

export function TableBody({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tbody
      className={`[&_tr:last-child]:border-0 ${className}`}
      {...props}
    />
  );
}

export function TableRow({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={`border-b border-slate-100 transition-colors hover:bg-slate-50 data-[state=selected]:bg-brand-green/5 ${className}`}
      {...props}
    />
  );
}

interface TableHeadProps extends React.ThHTMLAttributes<HTMLTableCellElement> {
  sortable?: boolean;
  sortDirection?: "asc" | "desc" | false;
  onSort?: () => void;
}

export function TableHead({
  className = "",
  sortable,
  sortDirection,
  onSort,
  children,
  ...props
}: TableHeadProps) {
  if (sortable) {
    return (
      <th
        className={`h-11 px-4 text-left align-middle font-semibold text-slate-600 text-xs uppercase tracking-wider cursor-pointer hover:text-slate-900 hover:bg-slate-100 transition-colors select-none ${className}`}
        onClick={onSort}
        {...props}
      >
        <div className="flex items-center gap-1">
          {children}
          <span className="text-brand-orange flex-shrink-0">
            {sortDirection === "asc" && <ArrowUp className="h-3.5 w-3.5" />}
            {sortDirection === "desc" && <ArrowDown className="h-3.5 w-3.5" />}
            {sortDirection === false && <ArrowUpDown className="h-3.5 w-3.5 opacity-30 text-slate-400" />}
          </span>
        </div>
      </th>
    );
  }

  return (
    <th
      className={`h-11 px-4 text-left align-middle font-semibold text-slate-600 text-xs uppercase tracking-wider ${className}`}
      {...props}
    >
      {children}
    </th>
  );
}

export function TableCell({
  className = "",
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={`px-4 py-3 align-middle text-slate-800 ${className}`}
      {...props}
    />
  );
}
