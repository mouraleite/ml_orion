const fs = require('fs');

const content = fs.readFileSync('C:\\Users\\Usuario\\.gemini\\antigravity-ide\\brain\\08c9334b-5163-41f4-88a5-6304d7897d44\\scratch\\restore_ast.js', 'utf8');
const lines = content.split('\n');

const sDR = lines.findIndex(l => l.includes('const TAB_DESPESAS_RECEITAS_CODE = `'));
const eDR = lines.findIndex(l => l.includes('const TAB_VENDAS_CODE = `'));
const sTV = eDR;
const eTV = lines.findIndex(l => l.includes('const updatedFileContent = '));

let drLines = lines.slice(sDR, eDR);
// Line 0 is: const TAB_DESPESAS_RECEITAS_CODE = `\nfunction TabDespesasReceitas...
drLines[0] = drLines[0].replace('const TAB_DESPESAS_RECEITAS_CODE = `\\n', '');
// The last line before TAB_VENDAS_CODE should be }\n`;
for(let i=drLines.length-1; i>=0; i--) {
   if (drLines[i].includes('}\\n`;')) {
      drLines[i] = drLines[i].replace('}\\n`;', '}\\n');
      break;
   }
}

let tvLines = lines.slice(sTV, eTV);
// Line 0 is: const TAB_VENDAS_CODE = `\n}\n\nfunction TabVendas...
tvLines[0] = tvLines[0].replace('const TAB_VENDAS_CODE = `\\n}\\n\\n', '');
// The last line before the end should be }\n`;
for(let i=tvLines.length-1; i>=0; i--) {
   if (tvLines[i].includes('}\\n`;')) {
      tvLines[i] = tvLines[i].replace('}\\n`;', '}\\n');
      break;
   }
}

// Unescape
let drStr = drLines.join('\n').split('\\`').join('`').split('\\$').join('$');
let tvStr = tvLines.join('\n').split('\\`').join('`').split('\\$').join('$');

// Read the original page.tsx
let pageLines = fs.readFileSync('frontend/src/app/dashboard/orcamento/realizado/page.tsx', 'utf8').split('\n');
const sDR_page = pageLines.findIndex(l => l.includes('function TabDespesasReceitas'));
const eTV_page = pageLines.findIndex(l => l.includes('function TabComparativo'));

const before = pageLines.slice(0, sDR_page).join('\n');
const after = pageLines.slice(eTV_page).join('\n');

const finalPage = before + '\n' + drStr + '\n' + tvStr + '\n' + after;
fs.writeFileSync('frontend/src/app/dashboard/orcamento/realizado/page.tsx', finalPage, 'utf8');
console.log('Reconstructed page.tsx flawlessly!');
