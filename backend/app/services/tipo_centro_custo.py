"""Rótulo de tipo do centro de custo / obra Sienge.

A API às vezes manda `type` como número, como `{id, description, icon}` ou até HTML.
O cadastro só pode persistir e devolver um dos quatro textos em português.
"""
from __future__ import annotations

import re
from typing import Any

TIPO_POR_CODIGO = {
    "1": "Obra e Centro de Custo",
    "2": "Somente Obra",
    "3": "Somente Centro de Custo",
    "4": "Centro de Custo associado à Obra",
}
ROTULOS_TIPO = frozenset(TIPO_POR_CODIGO.values())

_HTML = re.compile(r"<[^>]*>")
_URL = re.compile(r"^(https?:\/\/|data:image|\/\/)", re.I)
_ARQUIVO_IMAGEM = re.compile(r"\.(png|jpe?g|gif|svg|webp)(\?|$)", re.I)


def _texto(raw: Any) -> str:
    if raw is None or isinstance(raw, bool):
        return ""
    if isinstance(raw, dict):
        for key in ("id", "value", "type", "codigo", "code"):
            val = raw.get(key)
            if val is not None and not isinstance(val, (dict, list)):
                extraido = _texto(val)
                if extraido:
                    return extraido
        for key in ("description", "nome", "name", "label"):
            extraido = _texto(raw.get(key))
            if extraido:
                return extraido
        return ""
    if isinstance(raw, (list, tuple)):
        return _texto(raw[0]) if raw else ""
    if isinstance(raw, float) and raw.is_integer():
        raw = int(raw)
    texto = str(raw).strip()
    texto = _HTML.sub(" ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def codigo_tipo_sienge(raw: Any) -> str:
    texto = _texto(raw)
    if texto in TIPO_POR_CODIGO:
        return texto
    return ""


def rotulo_tipo_sienge(raw: Any, default: str = "Desconhecido") -> str:
    texto = _texto(raw)
    if not texto:
        return default
    if _URL.search(texto) or _ARQUIVO_IMAGEM.search(texto):
        return default
    if texto in TIPO_POR_CODIGO:
        return TIPO_POR_CODIGO[texto]
    if texto in ROTULOS_TIPO:
        return texto
    por_minuscula = {rotulo.lower(): rotulo for rotulo in ROTULOS_TIPO}
    if texto.lower() in por_minuscula:
        return por_minuscula[texto.lower()]
    return default
