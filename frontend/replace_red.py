import sys

with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/ViabilityReport.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('text-red-600">PRE\u00c7OS', 'text-slate-800 uppercase">PRE\u00c7OS')
content = content.replace('text-red-600 w-1/4">DESPESAS', 'text-slate-800 uppercase w-1/4">DESPESAS')
content = content.replace('text-red-600 w-1/6">BASE', 'text-slate-800 uppercase w-1/6">BASE')
content = content.replace('text-red-600 bg-slate-50 border-b border-slate-200">%', 'text-slate-500 uppercase bg-slate-50 border-b border-slate-200">%')
content = content.replace('text-red-600 bg-slate-50 border-b border-slate-200">Valor em R$', 'text-slate-500 uppercase bg-slate-50 border-b border-slate-200">Valor em R$')

with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/ViabilityReport.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replace finalizado!")
