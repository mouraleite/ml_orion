from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Motor de Viabilidades"
    API_V1_STR: str = "/api/v1"
    # development: atalho dummy-token-for-dev no login. production: só JWT.
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str
    
    # Redis (filas / cache futuro). No plano free pode ficar local dummy.
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 horas
    # "*" no desenvolvimento. Em production, lista separada por vírgula (nunca "*").
    CORS_ORIGINS: str = "*"

    # Microsoft Entra ID (SSO). Vazio = rota /auth/microsoft desligada.
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""

    # Segredo para disparo externo do sync (cron). Vazio = rota /sync/cron desligada.
    CRON_SECRET: str = ""

    # Sienge API — senha só via ambiente (.env local, painel do Render em produção).
    SIENGE_SUBDOMAIN: str = "mouraleite"
    SIENGE_USER: str = "mouraleite-contas-a-pagar"
    SIENGE_PASS: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()


def cors_allow_origins() -> list[str]:
    raw = (settings.CORS_ORIGINS or "*").strip()
    env = settings.ENVIRONMENT.strip().lower()
    if env in ("production", "prod"):
        if raw in ("", "*"):
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        return [item.strip() for item in raw.split(",") if item.strip()]
    if raw == "*":
        return ["*"]
    parsed = [item.strip() for item in raw.split(",") if item.strip()]
    return parsed or ["*"]

