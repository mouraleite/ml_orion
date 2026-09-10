const fs = require('fs');

let content = fs.readFileSync('page.tsx', 'utf8');

content = content.replace(/if \(filtros\?\.([a-zA-Z0-9_]+)\?\.length > 0 && !filtros\.\1\.includes/g, (match, prop) => {
    return `if (filtros?.${prop} && filtros?.${prop} !== "Todos" && !filtros.${prop}.includes`;
});

const originalRows = `const rows: {label: string, fn: (m: string) => any, raw?: boolean, isPerc?: boolean, cls?: string}[] = [
                { label: \`\${ref === "orcado" ? "ORC." : "FCST."} Unid.\`, fn: (m: string) => (item[ref]?.[m]?.unidades || 0) },
                { label: "Real. Unid.", fn: (m: string) => (item.realizado?.[m]?.unidades || 0) },
                { label: \`\${ref === "orcado" ? "ORC." : "FCST."} VGV\`, fn: (m: string) => formatMoeda(item[ref]?.[m]?.vgv || 0), raw: true },
                { label: "Real. VGV", fn: (m: string) => formatMoeda(item.realizado?.[m]?.vgv || 0), raw: true },
                { label: "Desvio %", fn: (m: string) => item[\`desvio_\${modo}\`]?.[m] || 0, isPerc: true, cls: "bg-slate-100 font-medium" },
              ];`;

const replacementRows = `const rows: {label: string, fn: (m: string) => any, raw?: boolean, isPerc?: boolean, cls?: string}[] = [
                { label: \`\${ref === "orcado" ? "ORC." : "FCST."} Unid.\`, fn: (m: string) => (item.vendas?.[ref]?.[m]?.unidades || 0) },
                { label: "Real. Unid.", fn: (m: string) => (item.vendas?.realizado?.[m]?.unidades || 0) },
                { label: \`\${ref === "orcado" ? "ORC." : "FCST."} VGV\`, fn: (m: string) => formatMoeda(item.vendas?.[ref]?.[m]?.vgv || 0), raw: true },
                { label: "Real. VGV", fn: (m: string) => formatMoeda(item.vendas?.realizado?.[m]?.vgv || 0), raw: true },
                { label: "Desvio %", fn: (m: string) => item.vendas?.[\`desvio_\${modo}\`]?.[m] || 0, isPerc: true, cls: "bg-slate-100 font-medium" },
              ];`;

content = content.replace(originalRows, replacementRows);

fs.writeFileSync('page.tsx', content, 'utf8');
