import sys
import re

with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/ViabilityReport.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace MIX DE VENDAS
content = content.replace('MIX DE VENDAS', 'VENDAS E PLANOS')

# Remove VELOCIDADE DE VENDAS block
pattern = re.compile(r'\s*\{\/\*\s*VELOCIDADE DE VENDAS\s*\*\/\}.*?<tr className="bg-slate-100 font-bold border-b border-slate-200">', re.DOTALL)
replacement = '\n\n                        {/* TAXA DE JUROS */}\n                        <tr className="bg-slate-100 font-bold border-b border-slate-200">'

if pattern.search(content):
    content = pattern.sub(replacement, content)
    with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/ViabilityReport.tsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Sucesso!")
else:
    print("Bloco VELOCIDADE DE VENDAS nao encontrado")
