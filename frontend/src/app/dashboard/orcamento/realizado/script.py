import json
import requests

res = requests.get('http://localhost:8000/api/v1/acompanhamento/vendas?ano=2026&consolidado=true&dept_id=1', headers={'Department-Id': '1'})
data = res.json()

with open('debug_vendas.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved {len(data.get('itens', []))} items to debug_vendas.json")
