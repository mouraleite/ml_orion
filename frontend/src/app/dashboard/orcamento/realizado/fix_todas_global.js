const fs = require('fs');

let content = fs.readFileSync('page.tsx', 'utf8');

content = content.replace(/if \(filtros\?\.empresaFiltro && filtros\?\.empresaFiltro !== "Todos" && !filtros\.empresaFiltro\.includes\(nomeEmpresa\)\) return false;/g, 'if (filtros?.empresaFiltro && (filtros?.empresaFiltro !== "Todos" && filtros?.empresaFiltro !== "Todas") && !filtros.empresaFiltro.includes(nomeEmpresa)) return false;');

fs.writeFileSync('page.tsx', content, 'utf8');
