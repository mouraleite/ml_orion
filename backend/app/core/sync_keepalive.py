"""Mantém a API acordada no Render gratuito enquanto um sync roda.

O plano free desliga o serviço após ~15 min sem requisições de fora. O sync
leva perto de 1 hora, então ele morria no meio se ninguém chamasse a API.
Aqui uma thread chama o endereço público da própria API a cada poucos minutos
enquanto o sync estiver em execução. RENDER_EXTERNAL_URL é definido pelo
próprio Render; fora dele (local, testes) nada é feito.
"""
from __future__ import annotations

import logging
import os
import threading
from contextlib import contextmanager

import httpx

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 4 * 60


def url_publica() -> str | None:
    url = (os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
    return url or None


def _pingar(url: str, parar: threading.Event, intervalo: float) -> None:
    while not parar.wait(intervalo):
        try:
            httpx.get(f"{url}/health", timeout=30)
        except Exception as e:  # rede instável não pode derrubar o sync
            logger.warning("Keep-alive do sync falhou: %s", e)


@contextmanager
def manter_acordado(intervalo: float = INTERVALO_SEGUNDOS):
    url = url_publica()
    if not url:
        yield False
        return
    parar = threading.Event()
    t = threading.Thread(
        target=_pingar, args=(url, parar, intervalo), name="sync-keepalive", daemon=True
    )
    t.start()
    logger.info("Keep-alive do sync ligado (%s/health a cada %ss).", url, int(intervalo))
    try:
        yield True
    finally:
        parar.set()
        t.join(timeout=5)
        logger.info("Keep-alive do sync desligado.")
