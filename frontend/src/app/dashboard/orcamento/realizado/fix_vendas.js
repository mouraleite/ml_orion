const fs = require('fs');

let content = fs.readFileSync('page.tsx', 'utf8');

// Ensure Fragment and ChevronDown/ChevronRight are imported
if (!content.includes('Fragment')) {
    content = content.replace(/import React, \{([^\}]+)\} from "react";/, 'import React, { , Fragment } from "react";');
}
if (!content.includes('ChevronDown')) {
    content = content.replace(/import \{([^}]+)\} from "lucide-react";/, 'import { , ChevronDown, ChevronRight } from "lucide-react";');
}

// 1. Refactor TabVendas
let vendasStart = content.indexOf('function TabVendas');
let vendasBlock = content.substring(vendasStart, content.indexOf('function TabComparativo', vendasStart));

if (!vendasBlock.includes('const [expandedRows, setExpandedRows]')) {
    vendasBlock = vendasBlock.replace('const [sortConfig, setSortConfig] = useState<{ key: string, direction: \'asc\' | \'desc\' } | null>(null);', 'const [sortConfig, setSortConfig] = useState<{ key: string, direction: \'asc\' | \'desc\' } | null>(null);\n  const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({});\n  const toggleRow = (idx: number) => setExpandedRows(prev => ({ ...prev, [idx]: !prev[idx] }));');
}

const oldTbodyVendas =             <tbody>
              {itens.map((item: any, idx: number) => {
                const rows: {label: string, fn: (m: string) => any, raw?: boolean, isPerc?: boolean, cls?: string}[] = [
                { label: \\\\\\ Unid.\\\, fn: (m: string) => (item.vendas?.[ref]?.[m]?.unidades || 0) },
                { label: "Real. Unid.", fn: (m: string) => (item.vendas?.realizado?.[m]?.unidades || 0) },
                { label: \\\\\\ VGV\\\, fn: (m: string) => formatMoeda(item.vendas?.[ref]?.[m]?.vgv || 0), raw: true },
                { label: "Real. VGV", fn: (m: string) => formatMoeda(item.vendas?.realizado?.[m]?.vgv || 0), raw: true },
                { label: "Desvio %", fn: (m: string) => item.vendas?.[\\\desvio_\\\\\\]?.[m] || 0, isPerc: true, cls: "bg-slate-100 font-medium" },
              ];
              return rows.map((row, ri) => (
                <tr key={\\\\\\-\\\\\\} className={\\\group hover:bg-slate-50 transition-colors border-b border-slate-200 \\\\\\}>
                  {ri === 0 && <td rowSpan={5} className="px-3 py-2 font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-20 group-hover:bg-slate-50 transition-colors align-top min-w-[200px]">{getProdNome(item.produto_id)}</td>}
                  <td className={\\\px-3 py-2 text-slate-500 whitespace-nowrap text-xs sticky left-[350px] shadow-[1px_0_0_0_#e2e8f0] z-20 transition-colors min-w-[100px] \\\\\\}>{row.label}</td>
                  {[...MESES_STR, "total"].map(m => (
                    <td key={m} className={\\\px-3 py-2 text-right tabular-nums \\\\\\}>
                      {row.isPerc
                        ? <DesvBadge value={row.fn(m)} />
                        : row.raw
                          ? row.fn(m)
                          : <span className="text-slate-600">{row.fn(m)}</span>
                      }
                    </td>
                  ))}
                </tr>
              ));
            })}
          </tbody>;

const newTbodyVendas =             <tbody>
              {itens.map((item: any, idx: number) => {
                const isExpanded = expandedRows[idx];
                const rows: {label: string, fn: (m: string) => any, raw?: boolean, isPerc?: boolean, cls?: string}[] = [
                { label: \\\\\\ Unid.\\\, fn: (m: string) => (item.vendas?.[ref]?.[m]?.unidades || 0) },
                { label: "Real. Unid.", fn: (m: string) => (item.vendas?.realizado?.[m]?.unidades || 0) },
                { label: \\\\\\ VGV\\\, fn: (m: string) => formatMoeda(item.vendas?.[ref]?.[m]?.vgv || 0), raw: true },
                { label: "Real. VGV", fn: (m: string) => formatMoeda(item.vendas?.realizado?.[m]?.vgv || 0), raw: true },
                { label: "Desvio %", fn: (m: string) => item.vendas?.[\\\desvio_\\\\\\]?.[m] || 0, isPerc: true, cls: "bg-slate-100 font-medium" },
              ];
              
              return (
                <Fragment key={idx}>
                  <tr className="group hover:bg-slate-50 transition-colors border-b border-slate-200 bg-slate-50/50 cursor-pointer" onClick={() => toggleRow(idx)}>
                    <td className="px-3 py-3 font-semibold text-slate-700 sticky left-0 shadow-[1px_0_0_0_#e2e8f0] z-20 group-hover:bg-slate-100 transition-colors align-top min-w-[200px]" colSpan={2}>
                      <div className="flex items-center gap-2">
                        {isExpanded ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
                        {getProdNome(item.produto_id)}
                      </div>
                    </td>
                    {[...MESES_STR, "total"].map((m, i) => <td key={i} className="px-3 py-2 bg-slate-50/50"></td>)}
                  </tr>
                  
                  {isExpanded && rows.map((row, ri) => (
                    <tr key={\\\\\\-\\\\\\} className={\\\group hover:bg-slate-50 transition-colors border-b border-slate-200 bg-white\\\}>
                      <td className="px-3 py-2 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-20 border-r border-slate-200 min-w-[200px]"></td>
                      <td className={\\\px-3 py-2 text-slate-500 whitespace-nowrap text-xs sticky left-[200px] shadow-[1px_0_0_0_#e2e8f0] z-20 transition-colors min-w-[100px] \\\\\\}>{row.label}</td>
                      {[...MESES_STR, "total"].map(m => (
                        <td key={m} className={\\\px-3 py-2 text-right tabular-nums \\\\\\}>
                          {row.isPerc
                            ? <DesvBadge value={row.fn(m)} />
                            : row.raw
                              ? row.fn(m)
                              : <span className="text-slate-600">{row.fn(m)}</span>
                          }
                        </td>
                      ))}
                    </tr>
                  ))}
                </Fragment>
              );
            })}
          </tbody>;

vendasBlock = vendasBlock.replace(new RegExp(oldTbodyVendas.replace(/[.*+?^$|[\\]{}]/g, '\\$&')), newTbodyVendas);
content = content.substring(0, vendasStart) + vendasBlock + content.substring(vendasStart + vendasBlock.length);

fs.writeFileSync('page.tsx', content, 'utf8');
