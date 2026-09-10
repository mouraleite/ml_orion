"""
Valida árvore MLDU cadastrada vs organograma de referência.

Uso (na pasta backend, venv ativo):

  python scripts/validar_organograma_mldu.py

Exit 0 = sem divergências nas empresas presentes.
Exit 1 = % ou vínculos divergentes do organograma.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.services.mldu_organograma_validacao import validate_organograma


def main() -> int:
    db = SessionLocal()
    try:
        result = validate_organograma(db)
    finally:
        db.close()

    print(f"Validação organograma MLDU — ok={result['ok']} divergências={result['divergencias']}")
    print(f"Referência: {result['referencia']['fonte']} (tol. {result['referencia']['tolerancia_pct']}%)")
    print()

    for row in result["empresas"]:
        if row["status"] == "ausente":
            print(f"  [ausente] id {row['id_sienge']} — esperado {row['expected_pct']}%")
        elif row["status"] == "divergente":
            print(
                f"  [DIVERGENTE] {row.get('nome', '?')} (id {row['id_sienge']}): "
                f"esperado {row['expected_pct']}% · atual {row['actual_pct']}%"
            )
        else:
            print(f"  [ok] {row.get('nome', '?')} (id {row['id_sienge']}): {row['actual_pct']}%")

    bad_links = [v for v in result["vinculos"] if v["status"] not in ("ok", "ausente")]
    if bad_links:
        print()
        for v in bad_links:
            print(
                f"  [vínculo {v['status']}] {v['parent_id_sienge']}→{v['child_id_sienge']}: "
                f"esperado {v['expected_pct']}%"
            )

    if result["avisos"]:
        print()
        for msg in result["avisos"]:
            print(f"  aviso: {msg}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
