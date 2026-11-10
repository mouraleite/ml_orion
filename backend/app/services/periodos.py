"""Meses e totais mensais compartilhados (orçamento, forecast, excel, acompanhamento)."""

MESES_STR = [
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]


def soma_meses_obj(obj) -> float:
    return sum(float(getattr(obj, m, 0.0) or 0.0) for m in MESES_STR)


def skip_linha_total_zero(item_data) -> bool:
    """Regra atual: linha sem total_anual e sem observação não é gravada."""
    total = float(getattr(item_data, "total_anual", 0) or 0)
    obs = getattr(item_data, "observacao", None)
    return total == 0 and not obs


def mudou(novo, base, tolerancia: float = 0.005) -> bool:
    """True se o valor mudou de fato. Ignora diferença de arredondamento (meio centavo)
    e trata vazio como zero: a tela devolve 1234.5600000001 e o banco tem 1234.56."""
    return abs(float(novo or 0.0) - float(base or 0.0)) > tolerancia


def mes_fechado_alterado(item_data, atual, meses_fechados: list[int]) -> str | None:
    """Nome do primeiro mês fechado cujo valor mudou, ou None.

    No orçamento não existe versão-base: a referência é o valor já gravado nele.
    """
    for idx, mes in enumerate(MESES_STR, start=1):
        if idx not in meses_fechados:
            continue
        novo = float(getattr(item_data, mes, 0.0) or 0.0)
        gravado = float(getattr(atual, mes, 0.0) or 0.0) if atual is not None else 0.0
        if abs(novo - gravado) > 0.005:
            return mes
    return None


def meses_fechados_do_ano(db, ano: int) -> list[int]:
    """Meses fechados do ano, como [1, 2, 3...]."""
    from app.models.fechamento import ClosedMonth

    return [
        mf.mes for mf in db.query(ClosedMonth).filter(ClosedMonth.ano == ano).all()
    ]
