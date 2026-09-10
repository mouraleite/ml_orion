const http = require('http');
const fs = require('fs');

const options = {
  hostname: 'localhost',
  port: 8000,
  path: '/api/v1/acompanhamento/vendas/2026?consolidado=true&dept_id=1',
  method: 'GET',
  headers: {
    'Department-Id': '1'
  }
};

const req = http.request(options, (res) => {
  let data = '';
  res.on('data', (chunk) => {
    data += chunk;
  });
  res.on('end', () => {
    const json = JSON.parse(data);
    fs.writeFileSync('debug_vendas.json', JSON.stringify(json, null, 2));
    console.log('Saved ' + (json.itens ? json.itens.length : 0) + ' items.');
  });
});
req.end();
