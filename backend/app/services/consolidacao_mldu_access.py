"""Consolidação MLDU — filtro de tela, sem liberação no perfil."""

from __future__ import annotations

from typing import Any

MODULO_ORCAMENTO = "Orçamento"
MODULO_FORECAST = "Forecast"
PERMISSAO_TELA = "Consolidação MLDU"


def pode_consolidacao_mldu(user: Any, _modulo: str) -> bool:
    return user is not None


def consolidacao_mldu_flags(user: Any) -> dict[str, bool]:
    return {
        "pode_consolidacao_mldu_orcamento": pode_consolidacao_mldu(user, MODULO_ORCAMENTO),
        "pode_consolidacao_mldu_forecast": pode_consolidacao_mldu(user, MODULO_FORECAST),
    }
