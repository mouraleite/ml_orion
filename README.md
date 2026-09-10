# Portal de Orçamento, Forecast e Acompanhamento Financeiro (ERP ML)

Projeto para gestão e controle do processo orçamentário (Planejamento, Replanejamento, Execução e Análise), incluindo integração com o Sienge e gestão de permissões.

## Arquitetura e Stack Tecnológica

- **Frontend:** Next.js 16 (React 19), TypeScript, TailwindCSS 4.
- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic.
- **Banco de Dados:** SQLite (padrão) com suporte a PostgreSQL para produção/concorrência.

O projeto é dividido em camadas (Interface, API, Negócio, Banco e Auditoria), garantindo que **todas as regras de negócio críticas residam exclusivamente no Backend**.

## Estrutura do Repositório

- `frontend/` - Aplicação Next.js (Interface e Componentes).
- `backend/` - API FastAPI e scripts de manutenção de dados.

## Instruções de Execução Local

### 1. Backend (API)

Requisitos: Python 3.10+

Abra um terminal na pasta `backend/`:

```bash
# 1. Crie e ative um ambiente virtual (se ainda não existir)
python -m venv .venv
# No Windows:
.venv\Scripts\activate

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Execute o servidor de desenvolvimento
fastapi dev app/main.py
```
O backend ficará disponível em `http://localhost:8000`.

Migrações (Alembic): o banco atual foi marcado como baseline (`alembic stamp head`). **Não rode `alembic upgrade` com revisão gerada automaticamente sem revisar o SQL** — isso pode alterar tabelas já validadas. Novas colunas no futuro devem ir em uma revisão explícita, depois de backup (`ERP_ML_ultimo.zip`).

```bash
alembic current
alembic stamp head
```

### 2. Frontend (Interface)

Requisitos: Node.js 20+

Abra um novo terminal na pasta `frontend/`:

```bash
# 1. Instale as dependências
npm install

# 2. Execute o servidor de desenvolvimento
npm run dev
```
O frontend ficará disponível em `http://localhost:3000`.

## Rodando via Docker (Opcional - Serviços Auxiliares)
Se for utilizar o PostgreSQL ou Redis (ver `backend/docker-compose.yml`), na pasta `backend`:
```bash
docker-compose up -d
```

## Postgres (Onda 3 — dev / migração)

O SQLite validado (`viabilidades.db`) **permanece o padrão**. Postgres é opcional para testar concorrência ou preparar produção.

```bash
cd backend
docker-compose up -d db
# Ajuste DATABASE_URL (veja .env.postgres.example) no .env
python scripts/postgres_init.py
python scripts/sqlite_para_postgres.py --confirm
python scripts/postgres_comparar.py
python scripts/baseline_numeros.py comparar
```

Regras:
- **Nunca** `alembic revision --autogenerate` cego — revisões futuras são escritas à mão.
- Baseline Alembic `20260828_baseline` é vazia (só marca o schema existente).
- Em `production`, a API **não** roda `create_all`; use `alembic upgrade head` após backup (`ERP_ML_ultimo.zip`).

Para voltar ao SQLite: restaure `DATABASE_URL=sqlite:///./viabilidades.db` no `.env`.

## Serviço compartilhado (Onda 4)

`backend/app/services/budget_shared.py` concentra helpers **estruturais** usados por `orcamentos.py` e `forecasts.py` (catálogo permitido, serialização de linhas, trava pessimista, agrupamento de vendas, cópia base→forecast).

Regras de negócio **não** foram unificadas: orçamento despesas grava `total_anual` do payload; forecast recalcula e respeita meses fechados. A gate suite (`test_characterization_api.py` + `test_budget_shared.py`) prova equivalência.

## Cliente Sienge (Onda 5)

`backend/app/services/sienge_client.py` centraliza **auth Basic**, URLs v1/bulk-data e paginação HTTP. Consumidores:

- `sienge_sync.py` — sync principal (`/sync/sienge`)
- `sienge_api.py` — colaboradores e departamentos
- `sienge_api_service.py` — bills/income (via `ErpIntegrationService`)

Credenciais via `.env`: `SIENGE_SUBDOMAIN`, `SIENGE_USER`, `SIENGE_PASS`.

**Não unificado** (de propósito): mapeamento `source_id`, pipelines `integracao_sienge` vs `sienge_sync`, parsers Excel SharePoint.

## Grades React (Onda 6)

Helpers em `frontend/src/lib/`:

- `parseCentroNome.ts` — parse de nome de centro de custo
- `months.ts` — chaves mensais e `MESES_VENDAS`
- `gridFilters.ts` — opções de filtro, `filterLinhasMensais`, `groupByProductId`
- `gridDiff.ts` — classes CSS de diff vs `itens_base`

`components/shared/ExcelImportModal.tsx` unifica orçamento e forecast (`apiBase`). Wrappers em `components/orcamento/` e `components/forecast/` mantêm imports existentes.

Regras de totais, IPCA, meses fechados e payloads de save **permanecem nas páginas** (zonas congeladas). Vendas e `realizado` usam só utils; despesas/receitas usam filtros compartilhados.

## Módulos placeholder (Onda 7)

Catálogo central em `frontend/src/lib/productModules.ts` — 16 rotas de produto futuro (relatórios, holding, orçamento extra, governança, etc.).

- `PlaceholderPage` + `UnderConstruction` padronizados (título, módulo, links para telas já validadas)
- Badge **Em breve** no sidebar para hrefs do catálogo (inclui flyout do dashboard de orçamento)
- Rota `/dashboard/orcamento/analitico-gastos-2` criada (antes 404 no menu)

**Não implementa funcionalidade** — só informa o usuário sem tocar em números ou zonas congeladas.

## Escopo por perfil (Onda A)

- **Diretor/admin:** vê todos os departamentos ativos; **filtro de departamento** nas telas de orçamento/forecast.
- **Gerente:** N departamentos via `user_departamentos` (cadastro em Segurança → Usuários).
- **`/users/me`:** retorna `pode_ver_todos_departamentos` e lista completa de departamentos acessíveis.
- **Removido:** botão legado “Visão Consolidada” (= todos os dept.). **Consolidação MLDU** vem na Onda D.
- Backend ignora `consolidado=true` antigo; escopo só pelo departamento ativo (`X-Department-Id`).

## Estrutura societária MLDU (Onda B)

- **Tela:** Consolidação → Estrutura societária MLDU (`/dashboard/holding/estrutura-societaria`).
- **Modelo:** `company_ownership_links` (pai → filha, % participação) + campos em `Company` (`participacao_mldu_efetiva`, override manual opcional).
- **Cálculo:** % efetivo = produto ao longo do caminho ML → … → empresa (ex.: Ellenco 50% → Vercellino 55,498% = **27,75%**).
- **MLES:** 33% (organograma; seed de referência usa este valor).
- **Modal Sócios** (Apoio → Empresas): inalterado — cap table da SPE.
- **API:** `/api/v1/holding/estrutura-mldu`, CRUD de vínculos, seed organograma, recalcular.

## Motor Consolidação MLDU (Onda C)

- **Serviço:** `holding_consolidation.py` — centro → `__id_empresa` → % efetivo → `valor × fator`.
- **Somente leitura:** parâmetro `holding_mldu=true` nas rotas GET; não grava no banco.
- **Rotas:** orçamento (despesas/receitas/vendas/visualização), forecast (despesas/vendas), acompanhamento (despesas/receitas/vendas/consolidado).
- **Resposta:** `holding_mldu`, `holding_avisos`, `holding_fator_mldu` por linha (quando aplicável).
- **Debug:** `GET /api/v1/holding/fatores` — mapa empresa/centro × fator.

## Consolidação MLDU na UI (Onda D)

- **Checkbox:** **Consolidação MLDU** na barra de escopo (`BudgetScopeBar`) — orçamento e forecast.
- **Permissão:** perfil em Segurança → **Consolidação MLDU** (módulos Orçamento / Forecast); fallback admin/diretor.
- **`/users/me`:** `pode_consolidacao_mldu_orcamento`, `pode_consolidacao_mldu_forecast`.
- **Estado:** persistido em `localStorage` por escopo (`holding_mldu_orcamento` / `holding_mldu_forecast`).
- **Somente leitura:** edição/salvamento bloqueados quando ativo; banner explica a visão.
- **Telas:** despesas, receitas, vendas, realizado (abas consolidado/despesas/receitas/vendas/visualização), resumo geral, analítico gastos 1, forecast despesas/vendas.

## Validação e regras (Onda E)

### Validação vs organograma

- **Serviço:** `mldu_organograma_validacao.py` — compara % efetivo e vínculos com referência oficial (MLES **33%**, não SharePoint 66%).
- **API:** `GET /api/v1/holding/validacao-organograma`
- **Script CLI:** `python scripts/validar_organograma_mldu.py` (pasta `backend`, venv ativo)
- **UI:** painel na tela Estrutura societária MLDU (verde = ok, âmbar = divergências)
- **Testes:** `test_mldu_organograma_validacao.py` (árvore completa + detecção de divergência)

### Regras de negócio — Consolidação MLDU

| Regra | Comportamento |
|-------|----------------|
| **Escopo departamento** | Orçamento/forecast continuam por dept.; filtro só recorta o que o perfil já permite |
| **Escopo holding** | Centro de custo → `__id_empresa` (Sienge) → % efetivo MLDU |
| **% efetivo** | Produto dos % ao longo do caminho ML → … → empresa (ex.: 50% × 55,498% = 27,749%) |
| **Raiz** | MLDU (`id_sienge = 1`) = 100% |
| **Override manual** | Opcional por empresa; indicador “manual” vs “calculado” |
| **Modo Consolidação MLDU** | `holding_mldu=true` na leitura; `valor × fator`; **não grava** no banco |
| **Modo normal** | Inalterado — baseline e zonas congeladas preservados |
| **Centro sem empresa** | Valor zerado + aviso em `holding_avisos` |
| **Empresa 0% MLDU** | Valor zerado + aviso |
| **Edição** | Bloqueada nas grades quando Consolidação MLDU ativa |
| **Permissão** | Perfil → Consolidação MLDU (Orçamento / Forecast); fallback admin/diretor |
| **Árvore** | Uma empresa filha = um pai; ciclos proibidos |
| **Modal Sócios** | Cap table da SPE — independente da árvore holding |

### Referência de % efetivo (organograma)

| id Sienge | Empresa (resumo) | % efetivo |
|-----------|------------------|-----------|
| 1 | MLDU | 100% |
| 12 | Ellenco & ML | 50% |
| 13 | Vercellino | 27,749% |
| 6 | Araçari SPE | 50% |
| 16 | Loteadora Ypês IV | 35% |
| 21 | Reserva Ypês IV | 23,8% |
| 28 | Reserva Ramos | 22,575% |
| 32 | Novo Horizonte | 100% |
| 4 | Terras de Itu | 28,0953% |
| 5 | MLES | **33%** |

Empresas fora da árvore ou com 0% não entram na consolidação.

## Ambiente: desenvolvimento vs produção

| Variável | Desenvolvimento (PC local) | Produção / servidor |
|----------|----------------------------|---------------------|
| `ENVIRONMENT` | `development` | `production` |
| Login frontend | `dummy-token-for-dev` (qualquer e-mail) | Form OAuth2 `/login/access-token` |
| `CORS_ORIGINS` | `*` | Domínios explícitos (nunca `*`) |
| `SECRET_KEY` | Valor local | Chave forte (`openssl rand -hex 32`) |
| Banco | SQLite `viabilidades.db` | PostgreSQL recomendado |

Copie os exemplos antes de subir:

```bash
# Backend
copy backend\.env.example backend\.env

# Frontend
copy frontend\.env.example frontend\.env.local
```

**Auth (Onda 1):** rotas `/dashboard/*` exigem cookie `erp_ml_auth` (setado no login junto com o token no `localStorage`). Quem já tinha sessão aberta pode passar uma vez pelo `/login` — o cookie é recriado automaticamente.

**Papéis (Onda 2):** `/users/me` devolve `effective_role` e `capabilities` (perfil AccessProfile + fallback em `User.role`). Prioridade: `permissions._role` → `permissions._capabilities` → nome do perfil → coluna `role`.

## Checagem antes de mudanças (recomendado)

Na **raiz do projeto**, com o venv do backend ativo:

```powershell
# Windows
.\check.ps1
```

```bash
# Linux / macOS
chmod +x check.sh && ./check.sh
```

Isso roda a **gate suite** (`backend/tests/gate_suite.txt`: caracterização, baseline, roles, CORS) e `python scripts/baseline_numeros.py comparar`. Se falhar, algum número ou comportamento divergiu da fotografia validada — veja `backend/tests/baselines/LEIA-ME.md`.

Para rodar todos os testes (inclui legado `test_acceptance.py`, ainda desalinhado): `cd backend && pytest tests/`.

## Plano de melhorias (ondas)

| Onda | Foco | Estado |
|------|------|--------|
| **0** | Script de checagem, `.env.example`, higiene segura | Concluída |
| **1** | Middleware Next, `roles.ts`, `require_admin` nas rotas admin | Concluída |
| **2** | AccessProfile + papel efetivo (`/users/me`) | Concluída |
| **3** | Postgres + scripts de migração/comparação + Alembic | Concluída |
| **4** | Serviço compartilhado orçamento/forecast (`budget_shared.py`) | Concluída |
| **5** | Cliente Sienge unificado (`sienge_client.py`) | Concluída |
| **6** | Grades React compartilhadas (`lib/grid*`, Excel unificado) | Concluída |
| **7** | Módulos UnderConstruction (`productModules.ts`, badges menu) | Concluída |
| **A** | Escopo perfil + filtro departamento (remove consolidado legado) | Concluída |

**Zonas congeladas** (números já validados): viabilidades, acompanhamento, orçamento, forecast, apoio, segurança. Detalhe em `.cursor/rules/zonas-congeladas.mdc`.
