"""Resposta JSON sem a conversão campo a campo do FastAPI (11/11/2026).

Nas telas grandes (DFC gerencial, despesas por empreendimento) a conversão
padrão (jsonable_encoder) gastava ~40% do tempo da requisição. Aqui o
json.dumps serializa direto; só tipos que ele não conhece (datas, Decimal,
modelos) passam pela conversão do FastAPI.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def _padrao(obj: Any) -> Any:
    return jsonable_encoder(obj)


class RespostaJSON(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            default=_padrao,
        ).encode("utf-8")
