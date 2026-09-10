const fs = require('fs');
const FILE = 'c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/frontend/src/app/dashboard/orcamento/realizado/page.tsx';
let c = fs.readFileSync(FILE, 'utf8');

const start = c.indexOf('{isExpanded && secoes.map((secao) => {');
const end = c.indexOf('</Fragment>\n                        );\n                      })}');

const badCode = c.substring(start, end + 63);

c = c.replace(badCode, '"use client";\nimport React, { useSta');

fs.writeFileSync(FILE, c, 'utf8');
console.log('Reversed! Check file now!');
