import re

with open('page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's replace {itens.length === 0 ? ( with a safe debug banner, for all tabs!
debug_banner = '{itens.length === 0 ? (\n        <div className="text-center py-16 text-slate-400">\n          <div className="bg-red-100 text-red-800 p-2 text-xs mb-4 border border-red-200">DEBUG API: {data?.itens?.length || 0} itens brutos | {itens.length} itens após filtro | Busca: "{filtros?.busca}"</div>'

# Only replace the exact empty state start
content = content.replace('{itens.length === 0 ? (\n        <div className="text-center py-16 text-slate-400">', debug_banner)

with open('page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
