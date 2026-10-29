"""Horários do sync Sienge (09:00 e 14:00 em Brasília). Sem I/O nem API."""
from datetime import datetime
from zoneinfo import ZoneInfo

TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")
HORAS_SYNC = (9, 14)


def na_janela_do_sync(agora: datetime | None = None, tolerancia_min: int = 120) -> bool:
    """True se estamos até `tolerancia_min` depois das 09:00 ou 14:00 de Brasília."""
    agora = agora or datetime.now(TZ_BRASILIA)
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=TZ_BRASILIA)
    else:
        agora = agora.astimezone(TZ_BRASILIA)
    minutos = agora.hour * 60 + agora.minute
    return any(0 <= (minutos - alvo * 60) < tolerancia_min for alvo in HORAS_SYNC)
