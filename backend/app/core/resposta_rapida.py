"""Respostas JSON mais rápidas para o sistema todo (11/11/2026).

O FastAPI converte cada resposta campo a campo (jsonable_encoder) antes de
gerar o JSON. Nas telas grandes isso era quase metade do tempo da requisição
(ex.: Realizado de despesas, ~25 MB). Aqui:

* rotas sem response_model que devolvem dict/list pulam essa conversão;
* o JSON é gerado direto pelo json.dumps; datas, Decimal, UUID, Enum, sets,
  modelos pydantic e dataclasses passam pela conversão do FastAPI só no ponto
  em que aparecem (mesmo resultado);
* qualquer outro tipo (objeto ORM, gerador, chave que não é texto...) faz a
  resposta inteira voltar ao caminho antigo, idêntico ao de antes.

O JSON gerado é byte a byte igual ao do FastAPI (mesmos separadores, acentos
sem escape, NaN recusado).
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import enum
import json
import uuid
from decimal import Decimal
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

_TIPOS_SEGUROS = (
    _dt.date, _dt.datetime, _dt.time, _dt.timedelta, Decimal, uuid.UUID,
    enum.Enum, set, frozenset, BaseModel, bytes,
)


class _VoltarAoCaminhoAntigo(Exception):
    pass


def _padrao(obj: Any) -> Any:
    if isinstance(obj, _TIPOS_SEGUROS) or (dataclasses.is_dataclass(obj) and not isinstance(obj, type)):
        return jsonable_encoder(obj)
    raise _VoltarAoCaminhoAntigo


def _dumps(content: Any, default=None) -> bytes:
    return json.dumps(
        content,
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
        default=default,
    ).encode("utf-8")


def gerar_json(content: Any) -> bytes:
    try:
        return _dumps(content, _padrao)
    except (_VoltarAoCaminhoAntigo, TypeError):
        return _dumps(jsonable_encoder(content))


class RespostaJSON(JSONResponse):
    def render(self, content: Any) -> bytes:
        return gerar_json(content)


_instalado = False


def instalar() -> None:
    """Liga o caminho rápido para todas as rotas (idempotente)."""
    global _instalado
    if _instalado:
        return
    import fastapi.routing as rotas
    from starlette.responses import JSONResponse as _JSONStarlette

    original = rotas.serialize_response

    async def serializar(*, field=None, response_content, include=None, exclude=None, **kw):
        if field is None and include is None and exclude is None and isinstance(response_content, (dict, list)):
            return response_content
        return await original(field=field, response_content=response_content, include=include, exclude=exclude, **kw)

    rotas.serialize_response = serializar
    _JSONStarlette.render = lambda self, content: gerar_json(content)
    _instalado = True
