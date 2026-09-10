const fs = require('fs');

let content = fs.readFileSync('page.tsx', 'utf8');

// I need to undo the broken replace
const brokenDebugString = '<div className="text-center py-16 text-slate-400">\\n          <div className="bg-red-100 text-red-800 p-2 text-xs mb-4">DEBUG: Recebidos da API: {data\\?\\.itens\\?\\.length \\|\\| 0} \\| Após filtro: {itens\\.length}</div>';

content = content.replace(new RegExp(brokenDebugString, 'g'), '{itens.length === 0 ? (\n        <div className="text-center py-16 text-slate-400">\n          <div className="bg-red-100 text-red-800 p-2 text-xs mb-4">DEBUG: Recebidos da API: {data?.itens?.length || 0} | Após filtro: {itens.length}</div>');

fs.writeFileSync('page.tsx', content, 'utf8');
