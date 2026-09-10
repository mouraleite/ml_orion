from typing import Any
from fastapi import APIRouter, HTTPException
import httpx
import time

router = APIRouter()

# ── In-memory cache ────────────────────────────────────────────────────────────
_cache: dict = {}
CACHE_TTL = 3600  # 1 hora

def _get_cached(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL:
        return entry["data"]
    return None

def _set_cache(key: str, data: Any):
    _cache[key] = {"ts": time.time(), "data": data}

# ── BCB SGS Helper ─────────────────────────────────────────────────────────────
BCB_SGS_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
BCB_FOCUS_BASE = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata"

async def _fetch_sgs(codigo: int, ultimos: int = 24) -> list:
    url = BCB_SGS_BASE.format(codigo=codigo)
    params = {"formato": "json", "ultimos": ultimos}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

async def _fetch_focus(indicador: str) -> list:
    url = f"{BCB_FOCUS_BASE}/ExpectativasMercadoAnuais"
    params = {
        "$format": "json",
        "$filter": f"Indicador eq '{indicador}' and baseCalculo eq 0",
        "$orderby": "Data desc",
        "$top": 5,
        "$select": "Indicador,Data,Mediana,Media,DataReferencia"
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json().get("value", [])


def _calcular_acumulado(series: list) -> list:
    """Calcula o acumulado de 12 meses rolling e o acumulado do ano para cada mes."""
    result = []
    for i, item in enumerate(series):
        # Acumulado 12 meses: produto dos ultimos 12 valores mensais
        start = max(0, i - 11)
        window = series[start:i + 1]
        acum_12m = 1.0
        for w in window:
            acum_12m *= (1 + (w["valor"] / 100))
        acum_12m = (acum_12m - 1) * 100

        # Acumulado do ano: meses com mesmo ano
        partes = item["data"].split("/")
        ano = partes[-1] if len(partes) == 3 else item["data"][:4]
        acum_ano = 1.0
        for w in series[max(0, i - 11):i + 1]:
            w_partes = w["data"].split("/")
            w_ano = w_partes[-1] if len(w_partes) == 3 else w["data"][:4]
            if w_ano == ano:
                acum_ano *= (1 + (w["valor"] / 100))
        acum_ano = (acum_ano - 1) * 100

        result.append({
            **item,
            "acumulado_12m": round(acum_12m, 4),
            "acumulado_ano": round(acum_ano, 4),
        })
    return result


@router.get("/ipca")
async def get_ipca() -> Any:
    """
    Retorna os ultimos 24 meses de IPCA mensal (serie 433) com acumulados calculados.
    Cache de 1 hora para nao sobrecarregar o BCB.
    """
    cached = _get_cached("ipca")
    if cached:
        return cached

    try:
        raw = await _fetch_sgs(433, ultimos=24)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar IPCA do BCB: {str(e)}")

    series = [{"data": r["data"], "valor": float(r["valor"])} for r in raw]
    series_with_acum = _calcular_acumulado(series)

    ultimo = series_with_acum[-1] if series_with_acum else None
    resultado = {
        "indicador": "IPCA",
        "fonte": "BCB SGS - Serie 433",
        "ultimo_mes": {
            "data": ultimo["data"] if ultimo else None,
            "mensal": ultimo["valor"] if ultimo else None,
            "acumulado_12m": ultimo["acumulado_12m"] if ultimo else None,
            "acumulado_ano": ultimo["acumulado_ano"] if ultimo else None,
        },
        "historico": series_with_acum,
    }

    _set_cache("ipca", resultado)
    return resultado


@router.get("/incc")
async def get_incc() -> Any:
    """
    Retorna os ultimos 24 meses de INCC-DI mensal (serie 192) com acumulados calculados.
    Cache de 1 hora.
    """
    cached = _get_cached("incc")
    if cached:
        return cached

    try:
        raw = await _fetch_sgs(192, ultimos=24)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar INCC do BCB: {str(e)}")

    series = [{"data": r["data"], "valor": float(r["valor"])} for r in raw]
    series_with_acum = _calcular_acumulado(series)

    ultimo = series_with_acum[-1] if series_with_acum else None
    resultado = {
        "indicador": "INCC-DI",
        "fonte": "BCB SGS - Serie 192 (FGV/INCC-DI)",
        "ultimo_mes": {
            "data": ultimo["data"] if ultimo else None,
            "mensal": ultimo["valor"] if ultimo else None,
            "acumulado_12m": ultimo["acumulado_12m"] if ultimo else None,
            "acumulado_ano": ultimo["acumulado_ano"] if ultimo else None,
        },
        "historico": series_with_acum,
    }

    _set_cache("incc", resultado)
    return resultado


@router.get("/igpm")
async def get_igpm() -> Any:
    """
    Retorna os ultimos 24 meses de IGP-M mensal (serie 189) com acumulados calculados.
    Cache de 1 hora.
    """
    cached = _get_cached("igpm")
    if cached:
        return cached

    try:
        raw = await _fetch_sgs(189, ultimos=24)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar IGP-M do BCB: {str(e)}")

    series = [{"data": r["data"], "valor": float(r["valor"])} for r in raw]
    series_with_acum = _calcular_acumulado(series)

    ultimo = series_with_acum[-1] if series_with_acum else None
    resultado = {
        "indicador": "IGP-M",
        "fonte": "BCB SGS - Serie 189 (FGV/IGP-M)",
        "ultimo_mes": {
            "data": ultimo["data"] if ultimo else None,
            "mensal": ultimo["valor"] if ultimo else None,
            "acumulado_12m": ultimo["acumulado_12m"] if ultimo else None,
            "acumulado_ano": ultimo["acumulado_ano"] if ultimo else None,
        },
        "historico": series_with_acum,
    }

    _set_cache("igpm", resultado)
    return resultado


@router.get("/focus")
async def get_focus() -> Any:
    """
    Retorna as projecoes mais recentes do Boletim Focus (BCB Olinda) para IPCA e IGP-M.
    Cache de 1 hora.
    """
    cached = _get_cached("focus")
    if cached:
        return cached

    try:
        ipca_proj = await _fetch_focus("IPCA")
        igpm_proj = await _fetch_focus("IGP-M")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar Focus do BCB: {str(e)}")

    resultado = {
        "fonte": "BCB Boletim Focus - Expectativas Anuais",
        "IPCA": ipca_proj[:5],
        "IGP-M": igpm_proj[:5],
    }

    _set_cache("focus", resultado)
    return resultado


@router.post("/cache/clear")
async def clear_cache() -> Any:
    """Limpa o cache de indices (forca re-fetch na proxima chamada)."""
    _cache.clear()
    return {"ok": True, "message": "Cache limpo com sucesso."}
