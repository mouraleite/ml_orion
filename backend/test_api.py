from fastapi.testclient import TestClient
from app.main import app
import warnings
warnings.filterwarnings('ignore')

client = TestClient(app)
response = client.get("/api/viabilities/6")
data = response.json()

cf = data.get('monthly_cashflow', [])
for m in range(40, 50):
    if m < len(cf):
        row = cf[m]
        saidas = row['Obras'] + row['Despesas'] + row['Impostos']
        mov = row['Fluxo_de_Caixa']
        acum = row['Caixa_Acumulado']
        print(f"Mes {m+1}: Entradas={row['Receitas']:.0f}, Saidas={saidas:.0f}, Mov={mov:.0f}, Acum={acum:.0f}")

exposicao = min([r['Caixa_Acumulado'] for r in cf]) if cf else 0
idx = [r['Caixa_Acumulado'] for r in cf].index(exposicao) + 1 if cf else 0
print(f"Exposicao Maxima: {exposicao:.0f} no Mes {idx}")
