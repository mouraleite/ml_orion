"""Identidade de colaborador: evita cadastro em duplicata com o Sienge."""

from __future__ import annotations

from typing import Any


def digits_only(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def norm_email(value: str | None) -> str:
    return (value or "").strip().lower()


def norm_name(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def is_sienge_colab_registered(colab: Any, users: list[Any]) -> bool:
    """True se já existe usuário com o mesmo Sienge, CPF, e-mail ou nome."""
    sid = getattr(colab, "sienge_id", None)
    if sid is None and isinstance(colab, dict):
        sid = colab.get("sienge_id") or colab.get("id")
    cpf = digits_only(getattr(colab, "cpf", None) if not isinstance(colab, dict) else colab.get("cpf"))
    email = norm_email(getattr(colab, "email", None) if not isinstance(colab, dict) else colab.get("email"))
    name = norm_name(getattr(colab, "name", None) if not isinstance(colab, dict) else colab.get("name"))
    try:
        sid_int = int(sid) if sid is not None and str(sid).strip() != "" else None
    except (TypeError, ValueError):
        sid_int = None

    for user in users:
        user_sid = getattr(user, "sienge_id", None)
        if sid_int is not None and user_sid is not None and int(user_sid) == sid_int:
            return True
        user_cpf = digits_only(getattr(user, "cpf", None))
        if len(cpf) == 11 and user_cpf == cpf:
            return True
        user_email = norm_email(getattr(user, "email", None))
        if email and user_email == email:
            return True
        if name and norm_name(getattr(user, "full_name", None)) == name:
            return True
    return False
