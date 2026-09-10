"""Bloqueia POST/PUT/PATCH/DELETE quando o perfil do módulo é só visualização."""

from __future__ import annotations

from starlette.responses import JSONResponse
from sqlalchemy.orm import joinedload

from app.api.deps import DEV_DUMMY_TOKEN, _dev_dummy_auth_allowed
from app.core.config import settings
from app.core.module_write import (
    WRITE_BLOCK_DETAIL,
    can_write_module,
    module_for_path,
    should_skip_write_check,
)
from app.db.database import SessionLocal
from app.models.user import User
from app.schemas.user import TokenPayload
import jwt
from jwt.exceptions import InvalidTokenError as JWTError


class ModuleWriteMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method") or "GET"
        path = scope.get("path") or ""
        if should_skip_write_check(method, path):
            await self.app(scope, receive, send)
            return

        module = module_for_path(path)
        if not module:
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
        auth = headers.get("authorization") or ""
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        if not token:
            await self.app(scope, receive, send)
            return

        if token == DEV_DUMMY_TOKEN and _dev_dummy_auth_allowed():
            await self.app(scope, receive, send)
            return

        db = SessionLocal()
        try:
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                token_data = TokenPayload(**payload)
                user_id = int(token_data.sub) if token_data.sub else None
            except (JWTError, TypeError, ValueError):
                await self.app(scope, receive, send)
                return
            if not user_id:
                await self.app(scope, receive, send)
                return
            user = (
                db.query(User)
                .options(joinedload(User.perfil), joinedload(User.perfis))
                .filter(User.id == user_id)
                .first()
            )
            if user and not can_write_module(user, module):
                response = JSONResponse(status_code=403, content={"detail": WRITE_BLOCK_DETAIL})
                await response(scope, receive, send)
                return
        finally:
            db.close()

        await self.app(scope, receive, send)
