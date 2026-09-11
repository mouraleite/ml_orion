# Caminho free — Vercel + Neon + Render

## 1) Neon (Postgres free)

1. Crie conta em https://console.neon.tech (GitHub login é o mais rápido).
2. Crie projeto `erp-ml` (região: São Paulo se existir, senão US East).
3. Em **Connection Details**, copie a connection string **URI** e troque o prefixo:
   - de: `postgresql://...`
   - para: `postgresql+psycopg2://...`
4. Cole aqui no chat como `DATABASE_URL=...` (ou cole só a URI).

## 2) Migrar SQLite → Neon (local, uma vez)

No PC, com o SQLite intacto (`backend/viabilidades.db`):

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg2://USER:PASS@HOST/neondb?sslmode=require"
python scripts/postgres_init.py
python scripts/sqlite_para_postgres.py --confirm
python scripts/postgres_comparar.py
```

Não apaga o SQLite.

## 3) Render (API free)

1. Conta em https://dashboard.render.com (login GitHub).
2. **New → Blueprint** → repo `marceloantonioalves1-collab/ERP-ML` → `render.yaml`.
3. Preencha as env `sync: false`:
   - `DATABASE_URL` (mesma do Neon, com `+psycopg2`)
   - `SIENGE_*`
   - `AZURE_*` (quando tiver)
4. Após o deploy: URL tipo `https://erp-ml-api.onrender.com`

Nota: plano free **dorme** após ~15 min sem uso (primeiro request demora ~30–60s).

## 4) Vercel (front já no ar)

Em https://vercel.com → projeto `erp-ml` → Settings → Environment Variables:

- `NEXT_PUBLIC_API_URL` = `https://SEU-SERVICO.onrender.com/api/v1`
- `NEXT_PUBLIC_AZURE_TENANT_ID` / `NEXT_PUBLIC_AZURE_CLIENT_ID` (quando SSO)

Redeploy o front.

Confirme no Render: `CORS_ORIGINS=https://mlorion.vercel.app,https://erp-ml-six.vercel.app,http://localhost:3000`

## 5) Smoke test

1. `GET https://SEU-API.onrender.com/health`
2. Login no front (senha ou Microsoft)
3. Abrir uma tela de Orçamento
