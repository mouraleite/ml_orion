"""
Arquiva a cópia duplicada de orçamento genérico 'Orçamento' quando existe
'Carga Inicial Sienge 2026' com o mesmo total (despesas/receitas).

NÃO apaga linhas — só marca status='Substituído' (já excluído das listas de
visualização/comparativo).

Uso (sempre dry-run primeiro):
  cd backend
  python -m scripts.arquivar_orcamento_duplicado_carga_sienge
  python -m scripts.arquivar_orcamento_duplicado_carga_sienge --apply

Zona sensível (Orçamento): só rode --apply após conferir o dry-run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Garante imports do app quando rodado como script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func

from app.db.database import SessionLocal
from app.models.orcamento import Orcamento, OrcamentoItem
from app.models.forecast import Forecast
from app.models.user import User  # noqa: F401 — necessário para mapper Orcamento

CARGA = "Carga Inicial Sienge 2026"
COPIA = "Orçamento"
TIPOS = ("DESPESAS", "RECEITAS")
EPS = 0.02  # centavos


def _soma_itens(db, orcamento_id: int) -> float:
    total = (
        db.query(func.coalesce(func.sum(OrcamentoItem.total_anual), 0.0))
        .filter(OrcamentoItem.orcamento_id == orcamento_id)
        .scalar()
    )
    return float(total or 0.0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persiste status=Substituído. Sem esta flag, só lista o que faria.",
    )
    parser.add_argument("--ano", type=int, default=2026)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        candidatas = (
            db.query(Orcamento)
            .filter(
                Orcamento.ano == args.ano,
                Orcamento.tipo.in_(TIPOS),
                Orcamento.descricao == COPIA,
                Orcamento.status != "Substituído",
            )
            .order_by(Orcamento.tipo, Orcamento.id)
            .all()
        )
        if not candidatas:
            print(f"Nenhuma cópia '{COPIA}' ativa em {args.ano}. Nada a fazer.")
            return 0

        to_archive: list[Orcamento] = []
        skipped: list[str] = []

        for copia in candidatas:
            carga = (
                db.query(Orcamento)
                .filter(
                    Orcamento.ano == copia.ano,
                    Orcamento.tipo == copia.tipo,
                    Orcamento.departamento_id == copia.departamento_id,
                    Orcamento.descricao == CARGA,
                    Orcamento.status != "Substituído",
                )
                .order_by(Orcamento.id.desc())
                .first()
            )
            if not carga:
                skipped.append(f"id={copia.id} {copia.tipo}: sem {CARGA} no mesmo dept — mantém")
                continue

            soma_c = _soma_itens(db, copia.id)
            soma_k = _soma_itens(db, carga.id)
            if abs(soma_c - soma_k) > EPS:
                skipped.append(
                    f"id={copia.id} {copia.tipo}: totais diferem "
                    f"(Orçamento={soma_c:.2f} vs Carga={soma_k:.2f}) — mantém"
                )
                continue

            refs = (
                db.query(Forecast)
                .filter(Forecast.versao_base_orcamento_id == copia.id)
                .count()
            )
            if refs:
                skipped.append(
                    f"id={copia.id} {copia.tipo}: {refs} forecast(s) apontam como base — mantém"
                )
                continue

            to_archive.append(copia)
            print(
                f"OK arquivar id={copia.id} {copia.tipo} dept={copia.departamento_id} "
                f"soma={soma_c:.2f} (igual à carga id={carga.id})"
            )

        for msg in skipped:
            print(f"SKIP {msg}")

        if not to_archive:
            print("Nenhum registro elegível para arquivar.")
            return 0

        if not args.apply:
            print(f"\nDry-run: {len(to_archive)} registro(s). Reexecute com --apply para gravar.")
            return 0

        for copia in to_archive:
            copia.status = "Substituído"
        db.commit()
        print(f"\nAplicado: {len(to_archive)} orçamento(s) marcados como Substituído.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
