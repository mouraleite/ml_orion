from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.core.resposta_rapida import instalar as instalar_resposta_rapida
from app.core.cache_respostas import CacheRespostas
from app.core.config import settings, cors_allow_origins
from app.api.routes import auth, users, governance, viabilities, curves, snapshots, actuals, documents, dashboard, orcamento_dfc_gerencial, orcamento_despesas_empreendimento, apoio, analysis, market_indices, tracking, tracking_dfc, sync, partnership, system, matriz_permissoes, tax_regimes, orcamentos, fechamento, forecasts, auditoria, integracao, migration, acompanhamento, sienge, access_profiles, holding
from app.api.module_write_middleware import ModuleWriteMiddleware
from app.db.database import engine, init_db, load_models
from app.db.schema_patches import ensure_phase_funding_periodicidade, ensure_sienge_account_balances

# Em desenvolvimento: create_all só cria tabelas faltantes (SQLite ou Postgres vazio).
# Em production: schema via Alembic; a tabela do card de caixa é criada se ainda não existir.
if settings.ENVIRONMENT.strip().lower() not in ("production", "prod"):
    init_db()
else:
    load_models()
    ensure_sienge_account_balances(engine)
    ensure_phase_funding_periodicidade(engine)

from app.core.scheduler import start_scheduler, stop_scheduler
from app.db.audit_listener import setup_audit_listener

# Setup listener for database auditing
setup_audit_listener()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()

app = FastAPI(
    title="ERP ML - API",
    description="API do ERP ML (Moura Leite)",
    version="1.0.0",
    lifespan=lifespan,
)

_cors_origins = cors_allow_origins()
instalar_resposta_rapida()  # JSON direto, sem conversão campo a campo (11/11/2026)
# Respostas grandes (DFC ~2,8 MB) vão comprimidas; nível 5 poupa CPU no plano free.
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
# Telas pesadas: resposta pronta reaproveitada enquanto o banco não mudar (11/11/2026).
app.add_middleware(CacheRespostas)
app.add_middleware(ModuleWriteMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["login"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(governance.router, prefix=f"{settings.API_V1_STR}/governance", tags=["governance"])
app.include_router(viabilities.router, prefix=f"{settings.API_V1_STR}/viabilities", tags=["viabilities"])
app.include_router(analysis.router, prefix=f"{settings.API_V1_STR}/viabilities", tags=["analysis"])
app.include_router(curves.router, prefix=f"{settings.API_V1_STR}/curves", tags=["curves"])
app.include_router(snapshots.router, prefix=f"{settings.API_V1_STR}/viabilities", tags=["snapshots"])
app.include_router(actuals.router, prefix=f"{settings.API_V1_STR}/viabilities", tags=["actuals"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}/viabilities", tags=["documents"])

app.include_router(apoio.router, prefix="/api/v1/apoio", tags=["apoio"])
app.include_router(holding.router, prefix="/api/v1/holding", tags=["holding"])
app.include_router(tax_regimes.router, prefix=f"{settings.API_V1_STR}/apoio/impostos", tags=["tax-regimes"])
app.include_router(analysis.router, prefix=f"{settings.API_V1_STR}/analysis", tags=["Analysis"])
app.include_router(market_indices.router, prefix=f"{settings.API_V1_STR}/market-indices", tags=["Market Indices"])
app.include_router(tracking_dfc.router, prefix=f"{settings.API_V1_STR}/tracking", tags=["Tracking"])
app.include_router(tracking.router, prefix=f"{settings.API_V1_STR}/tracking", tags=["Tracking"])
app.include_router(sync.router, prefix=f"{settings.API_V1_STR}/sync", tags=["sync"])
app.include_router(partnership.router, prefix=f"{settings.API_V1_STR}/partnership", tags=["partnership"])
app.include_router(system.router, prefix=f"{settings.API_V1_STR}/system", tags=["system"])
app.include_router(matriz_permissoes.router, prefix=f"{settings.API_V1_STR}/matriz-permissoes", tags=["matriz-permissoes"])
app.include_router(orcamentos.router, prefix=f"{settings.API_V1_STR}/orcamentos", tags=["orcamentos"])
app.include_router(fechamento.router, prefix=f"{settings.API_V1_STR}/fechamento", tags=["fechamento"])
app.include_router(forecasts.router, prefix=f"{settings.API_V1_STR}/forecasts", tags=["forecasts"])
app.include_router(acompanhamento.router, prefix=f"{settings.API_V1_STR}/acompanhamento", tags=["acompanhamento"])
app.include_router(auditoria.router, prefix=f"{settings.API_V1_STR}/auditoria", tags=["auditoria"])
app.include_router(integracao.router, prefix=f"{settings.API_V1_STR}/integracao", tags=["integracao"])
app.include_router(migration.router, prefix=f"{settings.API_V1_STR}/migration", tags=["migration"])
app.include_router(access_profiles.router, prefix=f"{settings.API_V1_STR}/perfis-acesso", tags=["perfis-acesso"])

app.include_router(orcamento_dfc_gerencial.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(orcamento_despesas_empreendimento.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(sienge.router, prefix=f"{settings.API_V1_STR}/sienge", tags=["sienge"])
@app.get("/")
def read_root():
    return {"message": "Motor de Viabilidades Moura Leite operante."}

@app.get("/health")
def health_check():
    return {"status": "ok"}

