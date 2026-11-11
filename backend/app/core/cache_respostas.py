"""Cache das telas pesadas entre uma gravação e outra no banco (11/11/2026).

Os números das telas de leitura (DFC, acompanhamento, realizado, executivo...)
só mudam quando algo é gravado no banco: o sync do Sienge (9h e 14h), um
orçamento/forecast salvo, um fechamento de mês. O servidor guarda a resposta
pronta e a reaproveita enquanto o banco não mudar.

"Não mudou" = a posição do log de gravações do Postgres (pg_current_wal_lsn)
é a mesma de quando a resposta foi calculada. Qualquer gravação, de qualquer
servidor ou script, avança essa posição — então o cache nunca devolve um
número velho. A posição é lida ANTES de calcular: uma gravação no meio do
cálculo invalida o resultado na chamada seguinte.

Segurança: a chave inclui o token do usuário (cada um só recebe o que ele
mesmo já recebeu), o departamento ativo, a data do dia e a URL completa. Num
acerto o token ainda é validado (assinatura e validade).
"""
from __future__ import annotations

import datetime as _dt
import time
from collections import OrderedDict
from typing import Callable, Optional

ROTAS_EM_CACHE = (
    "/api/v1/dashboard/dfc/",
    "/api/v1/dashboard/despesas-empreendimento/",
    "/api/v1/dashboard/realizado-despesas/",
    "/api/v1/dashboard/matriz-detalhada/",
    "/api/v1/dashboard/executivo/",
    "/api/v1/acompanhamento/",
    "/api/v1/tracking/summary",
)
LIMITE_TOTAL = 48 * 1024 * 1024  # bytes guardados (respostas já comprimidas); folga no plano free (512 MB)
LIMITE_ITEM = 8 * 1024 * 1024
VALIDADE_S = 30 * 60


def versao_postgres() -> Optional[str]:
    """Posição atual do log de gravações; None se não der para ler (cache desligado)."""
    from sqlalchemy import text

    from app.db.database import engine, is_postgres_url

    if not is_postgres_url():
        return None
    try:
        with engine.connect() as conn:
            return conn.execute(text("select pg_current_wal_lsn()::text")).scalar()
    except Exception:  # noqa: BLE001
        return None


def token_valido(token: str) -> bool:
    import jwt

    from app.api.deps import DEV_DUMMY_TOKEN, _dev_dummy_auth_allowed
    from app.core.config import settings

    if token == DEV_DUMMY_TOKEN:
        return _dev_dummy_auth_allowed()
    try:
        jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return True
    except Exception:  # noqa: BLE001
        return False


class CacheRespostas:
    def __init__(self, app, versao_dados: Callable[[], Optional[str]] = versao_postgres,
                 validar_token: Callable[[str], bool] = token_valido):
        self.app = app
        self.versao_dados = versao_dados
        self.validar_token = validar_token
        self.itens: "OrderedDict[tuple, dict]" = OrderedDict()
        self.total = 0
        self.acertos = 0
        self.erros = 0

    def _guardar(self, chave, cabecalhos, corpo: bytes):
        if len(corpo) > LIMITE_ITEM:
            return
        antigo = self.itens.pop(chave, None)
        if antigo:
            self.total -= len(antigo["corpo"])
        self.itens[chave] = {"cabecalhos": cabecalhos, "corpo": corpo, "quando": time.monotonic()}
        self.total += len(corpo)
        while self.total > LIMITE_TOTAL and self.itens:
            _k, velho = self.itens.popitem(last=False)
            self.total -= len(velho["corpo"])

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "GET" or not str(scope.get("path", "")).startswith(ROTAS_EM_CACHE):
            await self.app(scope, receive, send)
            return
        h = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
        auth = h.get("authorization", "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        if not token:
            await self.app(scope, receive, send)
            return

        from anyio import to_thread

        versao = await to_thread.run_sync(self.versao_dados)
        if not versao:
            await self.app(scope, receive, send)
            return
        chave = (
            scope.get("path"), scope.get("query_string", b"").decode("latin-1"), token,
            h.get("x-department-id", ""), "gzip" in h.get("accept-encoding", ""), h.get("origin", ""),
            _dt.date.today().isoformat(), versao,
        )
        item = self.itens.get(chave)
        if item and time.monotonic() - item["quando"] < VALIDADE_S and self.validar_token(token):
            self.itens.move_to_end(chave)
            self.acertos += 1
            await send({"type": "http.response.start", "status": 200,
                        "headers": item["cabecalhos"] + [(b"x-cache", b"HIT")]})
            await send({"type": "http.response.body", "body": item["corpo"]})
            return

        self.erros += 1
        inicio: dict = {}
        partes: list = []

        async def enviar(msg):
            if msg["type"] == "http.response.start":
                inicio.update(msg)
                msg = dict(msg, headers=list(msg.get("headers", [])) + [(b"x-cache", b"MISS")])
            elif msg["type"] == "http.response.body":
                partes.append(msg.get("body", b""))
                if not msg.get("more_body", False) and inicio.get("status") == 200:
                    cab = [(k, v) for k, v in inicio.get("headers", []) if k.lower() != b"set-cookie"]
                    if len(cab) == len(inicio.get("headers", [])):
                        self._guardar(chave, cab, b"".join(partes))
            await send(msg)

        await self.app(scope, receive, enviar)
