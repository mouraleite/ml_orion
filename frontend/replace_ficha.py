import sys
import re

with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/ViabilityReport.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern for the Ficha Técnica block I just inserted
pattern = re.compile(r'(<h2 className="text-xl font-bold text-ml-dark mb-4 border-b pb-2">Ficha T\u00e9cnica</h2>\s*<table className="w-full text-sm">\s*<tbody>.*?</tbody>\s*</table>)', re.DOTALL)

replacement = """<h2 className="text-xl font-bold text-ml-dark mb-4 border-b pb-2">Ficha T\u00e9cnica</h2>
                    <table className="w-full text-sm">
                      <tbody>
                        <tr className="border-b border-slate-100">
                          <td className="py-2 text-slate-600">\u00c1rea Total</td>
                          <td className="py-2 text-right font-semibold">{formatArea(physicalData?.area_total)} m\u00b2</td>
                        </tr>
                        <tr className="border-b border-slate-100">
                          <td className="py-2 text-slate-600">Total de Lotes</td>
                          <td className="py-2 text-right font-semibold">
                            {(physicalData?.qtde_lotes_residenciais || 0) + (physicalData?.qtde_lotes_comerciais || 0) + (physicalData?.qtde_lotes_mistos || 0)}
                          </td>
                        </tr>
                        <tr className="border-b border-slate-100">
                          <td className="py-2 text-slate-600">Ticket M\u00e9dio</td>
                          <td className="py-2 text-right font-semibold">
                            {(() => {
                               const lotes = (physicalData?.qtde_lotes_residenciais || 0) + (physicalData?.qtde_lotes_comerciais || 0) + (physicalData?.qtde_lotes_mistos || 0);
                               const vgvBase = ((physicalData?.area_lotes_residenciais || 0) * (physicalData?.valor_venda_residencial_m2 || 0)) + 
                                               ((physicalData?.area_lotes_comerciais || 0) * (physicalData?.valor_venda_comercial_m2 || 0)) + 
                                               ((physicalData?.area_lotes_mistos || 0) * (physicalData?.valor_venda_misto_m2 || 0));
                               return lotes > 0 ? formatCurrency(vgvBase / lotes) : formatCurrency(0);
                            })()}
                          </td>
                        </tr>
                        <tr className="border-b border-slate-100">
                          <td className="py-2 text-slate-600">VGV Total Projetado</td>
                          <td className="py-2 text-right font-semibold">
                            {(() => {
                               const vgvBase = ((physicalData?.area_lotes_residenciais || 0) * (physicalData?.valor_venda_residencial_m2 || 0)) + 
                                               ((physicalData?.area_lotes_comerciais || 0) * (physicalData?.valor_venda_comercial_m2 || 0)) + 
                                               ((physicalData?.area_lotes_mistos || 0) * (physicalData?.valor_venda_misto_m2 || 0));
                               return formatCurrency(vgvBase);
                            })()}
                          </td>
                        </tr>
                      </tbody>
                    </table>"""

if pattern.search(content):
    new_content = pattern.sub(replacement, content)
    with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/ViabilityReport.tsx', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Sucesso!")
else:
    print("Pattern nao encontrado")
