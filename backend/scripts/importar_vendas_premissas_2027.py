"""Cria o rascunho de Vendas 2027 a partir de PREMISSAS COMERCIAIS - v1.xlsx.

Padrão: simulação. Para gravar: --gravar
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main  # noqa: F401

from app.db.database import SessionLocal
from app.models.user import User
from app.services.carga_orcamento_vendas_premissas_2027 import (
    PREMISSAS_XLSX_DEFAULT,
    importar_vendas_premissas_2027,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gravar", action="store_true", help="Persiste. Sem esta flag só simula.")
    parser.add_argument("--arquivo", default=None, help="Caminho da planilha (opcional).")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        admin = (
            db.query(User)
            .filter(User.role.in_(["Administrador", "ADMIN", "Admin"]))
            .order_by(User.id)
            .first()
        )
        if not admin:
            print("Nenhum usuário administrador encontrado.")
            return 1
        relatorio = importar_vendas_premissas_2027(
            db,
            usuario_id=admin.id,
            gravar=args.gravar,
            path=args.arquivo or PREMISSAS_XLSX_DEFAULT,
        )
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(f"gravar={args.gravar} arquivo={relatorio.get('arquivo')}")
        flag = "OK" if not relatorio.get("total_erros") else "ERRO"
        print(
            f"{flag}\t{relatorio.get('departamento')}\tlinhas={relatorio.get('total_linhas')}\t"
            f"validas={relatorio.get('total_validas')}\terros={relatorio.get('total_erros')}\t"
            f"un={relatorio.get('unidades')}\tvgv={relatorio.get('vgv')}\t"
            f"gravado={relatorio.get('gravado')}\t{relatorio.get('mensagem')}"
        )
        for e in (relatorio.get("erros") or [])[:8]:
            print(f"  L{e.get('linha')} {e.get('codigo')} {e.get('campo')}: {e.get('mensagem')}")
        out = os.path.join(os.environ.get("TEMP", "."), "vendas_premissas_2027_relatorio.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2, default=str)
        print("relatorio", out)
        return 2 if relatorio.get("total_erros") else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
