"""Carga local de Orçamento Despesas 2027 (Elaboração do Orçamento / fImportacao).

Padrão: simulação. Para gravar: --gravar
Roda na máquina com a pasta do SharePoint. Render não tem esses arquivos.
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
from app.services.carga_orcamento_departamentos_2027 import (
    importar_orcamentos_departamentos_2027,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gravar", action="store_true", help="Persiste. Sem esta flag só simula.")
    parser.add_argument("--base-dir", default=None, help="Pasta Elaboração do Orçamento (opcional).")
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
        relatorio = importar_orcamentos_departamentos_2027(
            db,
            usuario_id=admin.id,
            gravar=args.gravar,
            base_dir=args.base_dir,
        )
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(f"gravar={args.gravar} base={relatorio.get('base_dir')}")
        if relatorio.get("erro_base"):
            print("ERRO", relatorio["erro_base"])
            return 1
        for ign in relatorio.get("ignorados") or []:
            print(f"IGNORADO\t{ign.get('pasta')}\t{ign.get('motivo')}")
        falhou = False
        for d in relatorio.get("departamentos") or []:
            flag = "OK" if not d.get("total_erros") else "ERRO"
            if d.get("total_erros"):
                falhou = True
            print(
                f"{flag}\t{d.get('departamento')}\tlinhas={d.get('total_linhas')}\t"
                f"validas={d.get('total_validas')}\terros={d.get('total_erros')}\t"
                f"gravado={d.get('gravado')}\t{d.get('mensagem')}"
            )
            for e in (d.get("erros") or [])[:5]:
                print(f"  L{e.get('linha')} {e.get('codigo')} {e.get('campo')}: {e.get('mensagem')}")
        out = os.path.join(os.environ.get("TEMP", "."), "orcamento_2027_relatorio.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2, default=str)
        print("relatorio", out)
        return 2 if falhou else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
