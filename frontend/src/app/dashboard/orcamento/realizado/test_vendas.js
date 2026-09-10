const fs = require('fs');
const lines = fs.readFileSync('page.tsx', 'utf8').split('\n');
const start = lines.findIndex(l => l.includes('function TabVendas'));
console.log(lines.slice(start, start + 30).join('\n'));
