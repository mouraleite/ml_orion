"""Corrige Ipês III 15600→17701 e carrega distratos 2027 no rascunho de Vendas.

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
from app.services.carga_orcamento_distratos_2027 import (
    DISTRATOS_XLSX_DEFAULT,
    importar_distratos_2027,
)
from app.services.carga_orcamento_vendas_premissas_2027 import remap_sienge_rascunho_vendas


def _print(relatorio: dict, titulo: str) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    flag = "OK" if not relatorio.get("total_erros") else "ERRO"
    print(titulo)
    print(
        f"{flag}\tgravado={relatorio.get('gravado')}\t"
        f"itens={relatorio.get('itens', relatorio.get('total_validas'))}\t"
        f"un={relatorio.get('unidades')}\tvgv={relatorio.get('vgv')}\t"
        f"{relatorio.get('mensagem')}"
    )
    for e in (relatorio.get("erros") or [])[:8]:
        print(f"  L{e.get('linha')} {e.get('codigo')} {e.get('campo')}: {e.get('mensagem')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gravar", action="store_true", help="Persiste. Sem esta flag só simula.")
    parser.add_argument("--arquivo", default=None, help="Caminho da planilha de distratos.")
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
        remap = remap_sienge_rascunho_vendas(db, usuario_id=admin.id, gravar=args.gravar)
        _print(remap, "1) Ipês III 15600 → 17701")
        if remap.get("total_erros"):
            return 2
        dist = importar_distratos_2027(
            db,
            usuario_id=admin.id,
            gravar=args.gravar,
            path=args.arquivo or DISTRATOS_XLSX_DEFAULT,
        )
        _print(dist, "2) Distratos 2027")
        out = os.path.join(os.environ.get("TEMP", "."), "distratos_2027_relatorio.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"remap": remap, "distratos": dist}, f, ensure_ascii=False, indent=2, default=str)
        print("relatorio", out)
        return 2 if dist.get("total_erros") else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
