import re

path = 'c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/SummaryTab.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_rows = """                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">EXPOSIÇÃO CAIXA / INVESTIMENTO</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">%</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-900'}`}>
                              {formatPerc(col.ind?.expo_inv)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">EXPOSIÇÃO CAIXA / VGV</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">%</td>
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
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">%</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-900'}`}>
                              {formatPerc(col.ind?.retorno_sem_juros)}
                          </td>
                      ))}
                  </tr>
                  <tr>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-800 font-medium pl-8 text-sm">(INVESTIMENTO/RETORNO) COM JUROS</td>
                      <td className="py-2 px-4 border-b border-slate-100 text-slate-400 font-medium">%</td>
                      {columns.map(col => (
                          <td key={col.id} className={`py-2 px-4 border-b border-slate-100 text-right font-medium ${col.isCurrent ? 'bg-ml-green/10 text-ml-very-dark' : 'text-slate-900'}`}>
                              {formatPerc(col.ind?.retorno_com_juros)}
                          </td>
                      ))}
                  </tr>\n"""

# Let's find EXPOSIÇÃO MÁXIMA CAIXA
parts = content.split('EXPOSIÇÃO MÁXIMA CAIXA')
if len(parts) == 2:
    # Now find the first </tr> after that
    end_tr_idx = parts[1].find('</tr>')
    if end_tr_idx != -1:
        insert_pos = end_tr_idx + 5 # include </tr>
        
        final_content = parts[0] + 'EXPOSIÇÃO MÁXIMA CAIXA' + parts[1][:insert_pos] + '\n' + new_rows + parts[1][insert_pos:]
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print("Success")
    else:
        print("Could not find </tr>")
else:
    print("Could not find EXPOSIÇÃO MÁXIMA CAIXA. len(parts):", len(parts))
