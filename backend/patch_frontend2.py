import re

path = 'c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/SummaryTab.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_rows = """                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">EXPOSIÇÃO CAIXA / INVESTIMENTO</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium"></td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-900'}`}>
                              {formatPerc(col.ind?.expo_inv)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">EXPOSIÇÃO CAIXA / VGV</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium"></td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-900'}`}>
                              {formatPerc(col.ind?.expo_vgv)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium mt-2 pt-4">RENTABILIDADE</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium pt-4"></td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium pt-4 ${col.isCurrent ? 'bg-ml-green/10' : ''}`}></td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">(INVESTIMENTO/RETORNO) SEM JUROS</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium"></td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-900'}`}>
                              {formatPerc(col.ind?.retorno_sem_juros)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">(INVESTIMENTO/RETORNO) COM JUROS</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium"></td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-900'}`}>
                              {formatPerc(col.ind?.retorno_com_juros)}
                          </td>
                      ))}
                  </tr>"""

target_string = """                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium">PERODO</td>"""

# Fix for encoding issue in target string (PERÍODO with accent)
# Let's search for "PER" and "ODO" instead using regex or just splitting

blocks = content.split('EXPOSIO MXIMA CAIXA')
if len(blocks) == 2:
    # EXPOSIÇÃO MÁXIMA is at blocks[1]
    blocks2 = blocks[1].split('PERODO')
    if len(blocks2) == 2:
        # We want to insert just before <tr>\\n<td...>PERÍODO
        # First, find the closing </tr> of EXPOSIÇÃO MÁXIMA CAIXA
        tr_end = blocks2[0].find('</tr>') + 5
        
        first_part = blocks[0] + 'EXPOSIO MXIMA CAIXA' + blocks2[0][:tr_end]
        second_part = blocks2[0][tr_end:] + 'PERODO' + blocks2[1]
        
        content = first_part + "\n" + new_rows + second_part

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
