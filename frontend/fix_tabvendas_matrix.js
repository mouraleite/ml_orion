const fs = require('fs');
const FILE = 'c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/app/dashboard/orcamento/realizado/page.tsx';
let c = fs.readFileSync(FILE, 'utf8');

// 1. Add expandedSections state to TabVendas
c = c.replace(
  `const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({});`,
  `const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({});\n    const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});`
);

// 2. Add toggleSection
c = c.replace(
  `    const toggleRow = (idx: number) => {\n      setExpandedRows(prev => ({ ...prev, [idx]: !prev[idx] }));\n    };`,
  `    const toggleRow = (idx: number) => {\n      setExpandedRows(prev => ({ ...prev, [idx]: !prev[idx] }));\n    };\n\n    const toggleSection = (idx: number, key: string) => {\n      const sKey = \`\${idx}-\${key}\`;\n      setExpandedSections(prev => ({ ...prev, [sKey]: !prev[sKey] }));\n    };`
);

// 3. Update secoes definition
const oldSecoesStart = c.indexOf('const secoes: { key: string; label: string; headerCls: string; rows: RowDef[] }[] = [');
const oldSecoesEnd = c.indexOf('];', oldSecoesStart) + 2;
const oldSecoes = c.substring(oldSecoesStart, oldSecoesEnd);

const newSecoes = `const secoes: { key: string; label: string; headerCls: string; headerValueLabel: string; headerFn: (m: string) => any; rows: RowDef[] }[] = [
                    {
                      key: "vendas",
                      label: "🟢 VENDAS BRUTAS",
                      headerCls: "bg-emerald-50 text-emerald-800 border-b border-emerald-200 cursor-pointer hover:opacity-90",
                      headerValueLabel: "Real. VGV",
                      headerFn: (m: string) => formatMoeda(item.vendas?.realizado?.[m]?.vgv ?? 0),
                      rows: [
                        { label: ref === "orcado" ? "ORC. Unid." : "FCST. Unid.", fn: (m: string) => (item.vendas?.[ref]?.[m]?.unidades ?? 0) },
                        { label: "Real. Unid.", fn: (m: string) => (item.vendas?.realizado?.[m]?.unidades ?? 0) },
                        { label: "Desvio % Unid.", fn: (m: string) => item["desvio_" + modo + "_vendas_unid"]?.[m] ?? 0, isPerc: true, inverted: false },
                        { label: ref === "orcado" ? "ORC. VGV" : "FCST. VGV", fn: (m: string) => formatMoeda(item.vendas?.[ref]?.[m]?.vgv ?? 0), raw: true },
                        { label: "Real. VGV", fn: (m: string) => formatMoeda(item.vendas?.realizado?.[m]?.vgv ?? 0), raw: true },
                        { label: "Desvio % VGV", fn: (m: string) => item["desvio_" + modo + "_vendas"]?.[m] ?? 0, isPerc: true, cls: "bg-emerald-50/30 font-medium", inverted: false },
                      ],
                    },
                    {
                      key: "distratos",
                      label: "🔴 DISTRATOS",
                      headerCls: "bg-red-50 text-red-800 border-b border-red-200 cursor-pointer hover:opacity-90",
                      headerValueLabel: "Real. VGV",
                      headerFn: (m: string) => formatMoeda(item.distratos?.realizado?.[m]?.vgv ?? 0),
                      rows: [
                        { label: ref === "orcado" ? "ORC. Unid." : "FCST. Unid.", fn: (m: string) => (item.distratos?.[ref]?.[m]?.unidades ?? 0) },
                        { label: "Real. Unid.", fn: (m: string) => (item.distratos?.realizado?.[m]?.unidades ?? 0) },
                        { label: "Desvio % Unid.", fn: (m: string) => item["desvio_" + modo + "_distratos_unid"]?.[m] ?? 0, isPerc: true, inverted: true },
                        { label: ref === "orcado" ? "ORC. VGV" : "FCST. VGV", fn: (m: string) => formatMoeda(item.distratos?.[ref]?.[m]?.vgv ?? 0), raw: true },
                        { label: "Real. VGV", fn: (m: string) => formatMoeda(item.distratos?.realizado?.[m]?.vgv ?? 0), raw: true },
                        { label: "Desvio % VGV", fn: (m: string) => item["desvio_" + modo + "_distratos"]?.[m] ?? 0, isPerc: true, cls: "bg-red-50/30 font-medium", inverted: true },
                      ],
                    },
                    {
                      key: "liquido",
                      label: "🟡 VGV LÍQUIDO",
                      headerCls: "bg-amber-50 text-amber-800 border-b border-amber-200 cursor-pointer hover:opacity-90",
                      headerValueLabel: "Real. VGV Líq.",
                      headerFn: (m: string) => formatMoeda((item.vendas?.realizado?.[m]?.vgv ?? 0) - (item.distratos?.realizado?.[m]?.vgv ?? 0)),
                      rows: [
                        { label: ref === "orcado" ? "ORC. VGV Líq." : "FCST. VGV Líq.", fn: (m: string) => formatMoeda((item.vendas?.[ref]?.[m]?.vgv ?? 0) - (item.distratos?.[ref]?.[m]?.vgv ?? 0)), raw: true },
                        { label: "Real. VGV Líq.", fn: (m: string) => formatMoeda((item.vendas?.realizado?.[m]?.vgv ?? 0) - (item.distratos?.realizado?.[m]?.vgv ?? 0)), raw: true },
                        {
                          label: "Desvio % Líq.",
                          fn: (m: string) => {
                            const refLiq = (item.vendas?.[ref]?.[m]?.vgv ?? 0) - (item.distratos?.[ref]?.[m]?.vgv ?? 0);
                            const realLiq = (item.vendas?.realizado?.[m]?.vgv ?? 0) - (item.distratos?.realizado?.[m]?.vgv ?? 0);
                            return refLiq !== 0 ? (realLiq - refLiq) / Math.abs(refLiq) : 0;
                          },
                          isPerc: true,
                          cls: "bg-amber-50/30 font-medium",
                          inverted: false
                        },
                      ],
                    },
                  ];`;

c = c.replace(oldSecoes, newSecoes);

// 4. Update the JSX rendering
const oldJsxStart = c.indexOf('{isExpanded && secoes.map((secao) => (');
const oldJsxEnd = c.indexOf('</Fragment>\n                      ))}', oldJsxStart) + 38;
const oldJsx = c.substring(oldJsxStart, oldJsxEnd);

const newJsx = `{isExpanded && secoes.map((secao) => {
                        const sKey = \`\${idx}-\${secao.key}\`;
                        const isSecaoExpanded = expandedSections[sKey];

                        return (
                        <Fragment key={secao.key}>
                          <tr className={secao.headerCls} onClick={() => toggleSection(idx, secao.key)}>
                            <td className="px-3 py-1.5 font-bold text-xs sticky left-0 z-20 shadow-[1px_0_0_0_#e2e8f0] bg-inherit min-w-[200px] pl-10" colSpan={1}>
                              <div className="flex items-center gap-2 w-full text-left focus:outline-none">
                                <span className={\`transform transition-transform \${isSecaoExpanded ? 'rotate-90' : ''}\`}>
                                  <ChevronRight className="w-3 h-3 opacity-70" />
                                </span>
                                {secao.label}
                              </div>
                            </td>
                            <td className="px-3 py-1.5 text-xs font-semibold sticky left-[200px] z-10 shadow-[1px_0_0_0_#e2e8f0] bg-inherit min-w-[130px] opacity-80" colSpan={1}>
                              {secao.headerValueLabel}
                            </td>
                            {months.map((m: string) => (
                              <td key={m} className={\`px-3 py-1.5 text-right tabular-nums text-sm font-semibold opacity-80 \${m === "total" ? "border-l border-emerald-200/50" : ""}\`}>
                                {secao.headerFn(m)}
                              </td>
                            ))}
                          </tr>
                          {isSecaoExpanded && secao.rows.map((row, ri) => (
                            <tr key={\`\${secao.key}-\${ri}\`} className={\`group hover:bg-slate-100/50 transition-colors border-b border-slate-100 \${ri % 2 === 0 ? "bg-white" : "bg-slate-50/30"}\`}>
                              <td className="px-3 py-1.5 sticky left-0 shadow-[1px_0_0_0_#e2e8f0] bg-inherit z-20 min-w-[200px]"></td>
                              <td className={\`px-3 py-1.5 text-slate-500 whitespace-nowrap text-xs sticky left-[200px] shadow-[1px_0_0_0_#e2e8f0] bg-inherit z-10 min-w-[130px] \${row.cls || ""}\`}>
                                {row.label}
                              </td>
                              {months.map((m: string) => (
                                <td key={m} className={\`px-3 py-1.5 text-right tabular-nums text-sm \${m === "total" ? "font-bold border-l border-slate-200" : ""}\`}>
                                  {row.isPerc
                                    ? <DesvBadge value={row.fn(m)} inverted={row.inverted || false} />
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
                      })}`;

c = c.replace(oldJsx, newJsx);

fs.writeFileSync(FILE, c, 'utf8');
console.log('TabVendas matrix updated successfully!');
