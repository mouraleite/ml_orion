import sys

with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/ViabilityReport.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

vendas_e_planos = """
            {/* VENDAS E PLANOS */}
            <div className="page-break p-12 print:py-6 relative">
                <div className="flex justify-between items-center border-b-2 border-ml-green pb-4 mb-8">
                   <img src="/logo-moura-leite.png" alt="Logo" className="h-10 w-auto" />
                   <div className="text-right">
                     <p className="font-bold text-ml-dark">VENDAS E PLANOS</p>
                     <p className="text-sm text-slate-500">Condições de Pagamento</p>
                   </div>
                </div>

                <div className="bg-white rounded-xl border border-slate-200 overflow-hidden print:break-inside-avoid">
                   <table className="w-full text-sm">
                      <thead>
                        <tr>
                          <th className="p-4 bg-slate-50 text-left border-b border-slate-200 w-1/3"></th>
                          {renamedColumns.map(col => (
                             <th key={`vp-head-${col.id}`} className="p-4 text-center bg-slate-50 border-b border-slate-200 font-bold uppercase text-xs">{col.title}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {/* MIX DE VENDAS */}
                        <tr className="bg-slate-50 font-bold border-b border-slate-200">
                          <td className="p-3 pl-4 text-slate-800">MIX DE VENDAS</td>
                          {renamedColumns.map(col => <td key={`mix-${col.id}`}></td>)}
                        </tr>
                        {Array.from(new Set(renamedColumns.flatMap(col => {
                            let conds = col.rawData?.phase?.revenue?.condicoes_pagamento_json;
                            if (typeof conds === 'string') {
                                try { conds = JSON.parse(conds); } catch (e) { conds = []; }
                            }
                            if (!Array.isArray(conds)) conds = [];
                            let flatConds = [];
                            for (const item of conds) {
                                if (item.condicoes && Array.isArray(item.condicoes)) {
                                    flatConds.push(...item.condicoes);
                                } else {
                                    flatConds.push(item);
                                }
                            }
                            return flatConds.map((c: any) => c.nome || '').filter(Boolean);
                        }))).sort((a, b) => {
                            if (a.toUpperCase().includes('VISTA')) return -1;
                            if (b.toUpperCase().includes('VISTA')) return 1;
                            const numA = parseInt(a.replace(/\\D/g, '')) || 999;
                            const numB = parseInt(b.replace(/\\D/g, '')) || 999;
                            return numA - numB;
                        }).map((condName, i) => (
                          <tr key={`cond-${i}`} className="border-b border-slate-100">
                            <td className="p-2 pl-8 text-slate-600 uppercase">{condName}</td>
                            {renamedColumns.map(col => {
                                let conds = col.rawData?.phase?.revenue?.condicoes_pagamento_json;
                                if (typeof conds === 'string') {
                                    try { conds = JSON.parse(conds); } catch (e) { conds = []; }
                                }
                                if (!Array.isArray(conds)) conds = [];
                                let flatConds = [];
                                for (const item of conds) {
                                    if (item.condicoes && Array.isArray(item.condicoes)) {
                                        flatConds.push(...item.condicoes);
                                    } else {
                                        flatConds.push(item);
                                    }
                                }
                                const cond = flatConds.find((c: any) => c.nome === condName);
                                const val = cond ? `${cond.perc}%` : '-';
                                return <td key={`cond-val-${col.id}`} className="p-2 text-center text-slate-600">{val}</td>
                            })}
                          </tr>
                        ))}

                        {/* VELOCIDADE DE VENDAS */}
                        <tr className="bg-slate-50 font-bold border-b border-slate-200">
                          <td className="p-3 pl-4 text-slate-800">VELOCIDADE DE VENDAS</td>
                          {renamedColumns.map(col => <td key={`vel-${col.id}`}></td>)}
                        </tr>
                        <tr className="border-b border-slate-100">
                            <td className="p-2 pl-8 text-slate-600">Curva (% por ano)</td>
                            {renamedColumns.map(col => {
                                let vel = col.rawData?.phase?.revenue?.velocidade_vendas_json;
                                if (typeof vel === 'string') {
                                    try { vel = JSON.parse(vel); } catch (e) { vel = []; }
                                }
                                if (!Array.isArray(vel)) vel = [];
                                let curveStr = vel.map((v: any) => v.perc).join(' / ');
                                if (!curveStr) curveStr = '-';
                                return <td key={`curve-${col.id}`} className="p-2 text-center font-bold text-slate-700">{curveStr}</td>
                            })}
                        </tr>

                        {/* TAXA DE JUROS */}
                        <tr className="bg-slate-100 font-bold border-b border-slate-200">
                          <td className="p-3 pl-4 text-slate-800">TAXA DE JUROS a.m.</td>
                          {renamedColumns.map(col => <td key={`jur-head-${col.id}`} className="bg-slate-100"></td>)}
                        </tr>
                        {Array.from(new Set(renamedColumns.flatMap(col => {
                            let conds = col.rawData?.phase?.revenue?.condicoes_pagamento_json;
                            if (typeof conds === 'string') {
                                try { conds = JSON.parse(conds); } catch (e) { conds = []; }
                            }
                            if (!Array.isArray(conds)) conds = [];
                            let flatConds = [];
                            for (const item of conds) {
                                if (item.condicoes && Array.isArray(item.condicoes)) {
                                    flatConds.push(...item.condicoes);
                                } else {
                                    flatConds.push(item);
                                }
                            }
                            return flatConds.filter((c: any) => c.aplica_juros).map((c: any) => c.nome || '').filter(Boolean);
                        }))).sort((a, b) => {
                            if (a.toUpperCase().includes('VISTA')) return -1;
                            if (b.toUpperCase().includes('VISTA')) return 1;
                            const numA = parseInt(a.replace(/\\D/g, '')) || 999;
                            const numB = parseInt(b.replace(/\\D/g, '')) || 999;
                            return numA - numB;
                        }).map((condName, i) => (
                          <tr key={`juros-${i}`} className="border-b border-slate-100 bg-slate-50">
                            <td className="p-2 pl-8 text-slate-600 uppercase">{condName}</td>
                            {renamedColumns.map(col => {
                                let conds = col.rawData?.phase?.revenue?.condicoes_pagamento_json;
                                if (typeof conds === 'string') {
                                    try { conds = JSON.parse(conds); } catch (e) { conds = []; }
                                }
                                if (!Array.isArray(conds)) conds = [];
                                let flatConds = [];
                                for (const item of conds) {
                                    if (item.condicoes && Array.isArray(item.condicoes)) {
                                        flatConds.push(...item.condicoes);
                                    } else {
                                        flatConds.push(item);
                                    }
                                }
                                const cond = flatConds.find((c: any) => c.nome === condName);
                                let val = '-';
                                if (cond && cond.aplica_juros) {
                                    const jurosAnual = parseFloat(col.rawData?.phase?.revenue?.taxa_juros_vendas || '0');
                                    const jurosMensal = (Math.pow(1 + (jurosAnual / 100), 1/12) - 1) * 100;
                                    val = jurosMensal.toLocaleString('pt-BR', {minimumFractionDigits: 3, maximumFractionDigits: 4}) + '%';
                                }
                                return <td key={`jur-val-${col.id}`} className="p-2 text-center font-bold text-slate-700">{val}</td>
                            })}
                          </tr>
                        ))}
                      </tbody>
                   </table>
                </div>
            </div>

"""

if "{/* 5. DRE NEGÓCIO (COMPARATIVO) */}" in content:
    new_content = content.replace("{/* 5. DRE NEGÓCIO (COMPARATIVO) */}", vendas_e_planos + "            {/* 5. DRE NEGÓCIO (COMPARATIVO) */}")
    with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/components/viabilities/ViabilityReport.tsx', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Sucesso!")
else:
    print("Nao encontrou a tag")
