import json

from app.core.config import settings
from app.services.sienge_client import api_v1_base_url, get_default_client

SIENGE_API_URL = api_v1_base_url()
SIENGE_USER = settings.SIENGE_USER
SIENGE_PASS = settings.SIENGE_PASS


def get_auth_header():
    return get_default_client().auth_headers()


def _fetch_paginated_api(url: str):
    """Auxiliar para buscar todas as páginas de um endpoint da API v1 (com limit e offset)."""
    return get_default_client().paginate_v1_collect(url)


def get_colaboradores():
    """Busca credores marcados como funcionários no Sienge e retorna campos essenciais."""
    url = f"{SIENGE_API_URL}/creditors?employee=true"
    creditors = _fetch_paginated_api(url)

    colaboradores = []
    for c in creditors:
        if c.get("employee") != "S":
            continue

        phones = c.get("phones", [])
        ddd = None
        number = None
        if phones:
            main_phone = next((p for p in phones if p.get("main")), phones[0])
            ddd = main_phone.get("ddd")
            number = main_phone.get("number")

        address = c.get("address", {})
        contacts = c.get("contacts", [])
        email = next((ct.get("email") for ct in contacts if ct.get("email")), None)

        colaboradores.append(
            {
                "sienge_id": c.get("id"),
                "name": c.get("name"),
                "trade_name": c.get("tradeName"),
                "cpf": c.get("cpf"),
                "phone_ddd": ddd,
                "phone_number": number,
                "address_json": json.dumps(address) if address else None,
                "email": email,
            }
        )

    return colaboradores


def get_departamentos():
    """Busca departamentos no Sienge e retorna campos essenciais."""
    url = f"{SIENGE_API_URL}/departments"
    deps = _fetch_paginated_api(url)

    departamentos = []
    for d in deps:
        departamentos.append({"id": d.get("departmentId"), "name": d.get("departmentName")})

    return departamentos
