const fs = require('fs');
let content = fs.readFileSync('page.tsx', 'utf8');

const debugString = '{itens.length === 0 ? (\n        <div className="text-center py-16 text-slate-400">\n          <div className="bg-red-100 text-red-800 p-2 text-xs mb-4">DEBUG: Recebidos da API: {data?.itens?.length || 0} | Após filtro: {itens.length}</div>';

content = content.replace(/\{itens\.length === 0 \? \(/g, debugString);

fs.writeFileSync('page.tsx', content, 'utf8');
