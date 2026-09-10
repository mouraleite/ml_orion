"""
Valida orçado (carga inicial) e forecast importados do SharePoint vs planilhas fonte.
Compara totais por centro de custo e geral, separando DESPESAS e RECEITAS.
Somente leitura — não altera dados.
"""
from __future__ import annotations

import glob
import os
import sys
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main  # noqa: F401 — inicializa mappers SQLAlchemy

from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.models.forecast import Forecast, ForecastItem
from app.models.migration import MigrationMapping
from app.models.orcamento import Orcamento, OrcamentoItem
from app.services.carga_forecast_sharepoint import (
    FORECAST_BASE_DIR,
    parse_sienge_forecast_report,
)
from app.services.carga_inicial_sharepoint import (
    SHAREPOINT_BASE_DIR,
    parse_sienge_report,
)

TOL = 0.01


def _meses_sum(item) -> float:
    cols = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
    return sum(float(getattr(item, c) or 0) for c in cols)


def _build_maps(db):
    cc_by_id = {c.id: c for c in db.query(CostCenter).all()}
    fp_map = {fp.id: str(fp.db_id or "") for fp in db.query(FinancialPlan).all()}

    cc_map: Dict[str, int] = {}
    fp_map_name: Dict[str, int] = {}
    for m in db.query(MigrationMapping).filter(MigrationMapping.status == "MAPPED").all():
        if m.tipo == "CENTRO_CUSTO" and m.id_destino:
            cc_map[m.nome_origem] = m.id_destino
        elif m.tipo == "PLANO_FINANCEIRO" and m.id_destino:
            fp_map_name[m.nome_origem] = m.id_destino

    db_cc_by_sienge = {str(c.id_sienge): c.id for c in cc_by_id.values() if c.id_sienge}
    db_cc_by_nome = {c.nome.lower(): c.id for c in cc_by_id.values()}
    db_fp_by_nome = {f.name.lower(): f.id for f in db.query(FinancialPlan).all()}

    return cc_by_id, fp_map, cc_map, fp_map_name, db_cc_by_sienge, db_cc_by_nome, db_fp_by_nome


def _resolve_row(
    row: Dict[str, Any],
    cc_map,
    fp_map_name,
    db_cc_by_sienge,
    db_cc_by_nome,
    db_fp_by_nome,
) -> Tuple[int | None, int | None]:
    cc_id_sienge = row.get("cc_id_sienge")
    cc_nome = row.get("cc_nome", "")
    conta_nome = row.get("conta_nome", "")

    cc_cache_key = cc_id_sienge if cc_id_sienge else cc_nome
    cc_id = cc_map.get(cc_cache_key)
    if not cc_id and cc_id_sienge:
        cc_id = db_cc_by_sienge.get(str(cc_id_sienge))
    if not cc_id:
        cc_id = db_cc_by_nome.get(cc_nome.lower())

    fp_id = fp_map_name.get(conta_nome)
    if not fp_id:
        fp_id = db_fp_by_nome.get(conta_nome.lower())

    return cc_id, fp_id


def _tipo_from_fp(fp_id: int | None, fp_map: Dict[int, str]) -> str | None:
    if not fp_id:
        return None
    db_id = fp_map.get(fp_id, "")
    if not db_id:
        return None
    return "RECEITAS" if db_id.startswith("1") else "DESPESAS"


def _aggregate_rows(
    rows: Iterable[Dict[str, Any]],
    db,
    *,
    value_key: str = "orcado",
    ano_filter: int | None = None,
) -> Tuple[Dict[Tuple[str, int], float], int, int]:
    cc_by_id, fp_map, cc_map, fp_map_name, db_cc_by_sienge, db_cc_by_nome, db_fp_by_nome = _build_maps(db)
    totals: Dict[Tuple[str, int], float] = defaultdict(float)
    skipped_no_map = 0
    skipped_no_tipo = 0

    for row in rows:
        if ano_filter is not None and row.get("ano") != ano_filter:
            continue
        cc_id, fp_id = _resolve_row(row, cc_map, fp_map_name, db_cc_by_sienge, db_cc_by_nome, db_fp_by_nome)
        if not cc_id or not fp_id:
            skipped_no_map += 1
            continue
        tipo = _tipo_from_fp(fp_id, fp_map)
        if not tipo:
            skipped_no_tipo += 1
            continue
        val = float(row.get(value_key) or 0)
        if val == 0:
            continue
        totals[(tipo, cc_id)] += val

    return totals, skipped_no_map, skipped_no_tipo


def _db_orcamento_totals(db, orcamento: Orcamento) -> Dict[Tuple[str, int], float]:
    totals: Dict[Tuple[str, int], float] = defaultdict(float)
    items = db.query(OrcamentoItem).filter_by(orcamento_id=orcamento.id).all()
    tipo = orcamento.tipo
    for item in items:
        totals[(tipo, item.produto_id)] += _meses_sum(item)
    return totals


def _db_forecast_totals(db, forecast: Forecast) -> Dict[Tuple[str, int], float]:
    totals: Dict[Tuple[str, int], float] = defaultdict(float)
    items = db.query(ForecastItem).filter_by(forecast_id=forecast.id).all()
    tipo = forecast.tipo
    for item in items:
        totals[(tipo, item.produto_id)] += _meses_sum(item)
    return totals


def _compare_totals(
    label: str,
    sp_totals: Dict[Tuple[str, int], float],
    db_totals: Dict[Tuple[str, int], float],
    cc_by_id: Dict[int, CostCenter],
) -> bool:
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    all_keys = set(sp_totals) | set(db_totals)
    divergencias = []
    ok_count = 0

    for key in sorted(all_keys, key=lambda k: (k[0], cc_by_id.get(k[1], CostCenter(id=0, nome="")).nome or "")):
        tipo, cc_id = key
        sp_val = sp_totals.get(key, 0.0)
        db_val = db_totals.get(key, 0.0)
        diff = abs(sp_val - db_val)
        if diff > TOL and (sp_val != 0 or db_val != 0):
            cc = cc_by_id.get(cc_id)
            nome = cc.nome if cc else f"CC#{cc_id}"
            sienge = cc.id_sienge if cc else "?"
            divergencias.append((tipo, cc_id, sienge, nome, sp_val, db_val, diff))
        elif sp_val != 0 or db_val != 0:
            ok_count += 1

    for tipo in ("DESPESAS", "RECEITAS"):
        sp_g = sum(v for (t, _), v in sp_totals.items() if t == tipo)
        db_g = sum(v for (t, _), v in db_totals.items() if t == tipo)
        diff_g = abs(sp_g - db_g)
        status = "OK" if diff_g <= TOL else "DIVERGÊNCIA"
        print(f"\n[{tipo}] GERAL")
        print(f"  SharePoint: R$ {sp_g:,.2f}")
        print(f"  Banco:      R$ {db_g:,.2f}")
        print(f"  Diferença:  R$ {diff_g:,.2f}  -> {status}")

    if divergencias:
        print(f"\n--- Divergências por CC ({len(divergencias)}) ---")
        for tipo, cc_id, sienge, nome, sp_val, db_val, diff in divergencias[:30]:
            print(
                f"  [{tipo}] {sienge} {nome[:40]:<40} | SP: {sp_val:>14,.2f} | DB: {db_val:>14,.2f} | Δ: {diff:>10,.2f}"
            )
        if len(divergencias) > 30:
            print(f"  ... +{len(divergencias) - 30} divergências")
    else:
        print(f"\n>>> Todos os {ok_count} centros de custo com valor batem (tolerância R$ {TOL:.2f})")

    return len(divergencias) == 0


def _find_orcamento(db, tipo: str) -> Orcamento | None:
    """Orçamento V1 2026 do consolidado Sienge (carga SharePoint)."""
    o = (
        db.query(Orcamento)
        .filter_by(ano=2026, tipo=tipo, versao_numero=1)
        .order_by(Orcamento.id)
        .first()
    )
    return o


def _find_forecast(db, folder_name: str, tipo: str) -> Forecast | None:
    return (
        db.query(Forecast)
        .filter_by(descricao=folder_name, tipo=tipo, ano=2026)
        .order_by(Forecast.id.desc())
        .first()
    )


def validate_orcado(db) -> bool:
    if not os.path.exists(SHAREPOINT_BASE_DIR):
        print(f"Pasta orçado não encontrada: {SHAREPOINT_BASE_DIR}")
        return False

    files = [
        f
        for f in glob.glob(os.path.join(SHAREPOINT_BASE_DIR, "**", "*.xlsx"), recursive=True)
        if "~$" not in f
    ]
    print(f"\nOrçado: {len(files)} planilhas em {SHAREPOINT_BASE_DIR}")

    raw: List[Dict[str, Any]] = []
    for f in files:
        try:
            raw.extend(parse_sienge_report(f, db))
        except Exception as e:
            print(f"  ERRO lendo {os.path.basename(f)}: {e}")

    sp_totals, skip_map, skip_tipo = _aggregate_rows(raw, db)
    print(f"  Linhas parseadas: {len(raw)} | sem mapeamento: {skip_map} | sem tipo: {skip_tipo}")

    cc_by_id, *_ = _build_maps(db)
    all_ok = True

    for tipo in ("DESPESAS", "RECEITAS"):
        orc = _find_orcamento(db, tipo)
        if not orc:
            print(f"  Orçamento '{tipo}' não encontrado no banco.")
            all_ok = False
            continue
        db_totals = _db_orcamento_totals(db, orc)
        sp_tipo = {k: v for k, v in sp_totals.items() if k[0] == tipo}
        db_tipo = {k: v for k, v in db_totals.items() if k[0] == tipo}
        ok = _compare_totals(f"ORÇADO — {tipo} (V1 2026, id={orc.id})", sp_tipo, db_tipo, cc_by_id)
        all_ok = all_ok and ok

    return all_ok


def validate_forecast(db) -> bool:
    if not os.path.exists(FORECAST_BASE_DIR):
        print(f"Pasta forecast não encontrada: {FORECAST_BASE_DIR}")
        return False

    subdirs = sorted(
        f.path for f in os.scandir(FORECAST_BASE_DIR) if f.is_dir() and "Forecast -" in f.name
    )
    print(f"\nForecast: {len(subdirs)} pastas em {FORECAST_BASE_DIR}")

    cc_by_id, *_ = _build_maps(db)
    all_ok = True

    for folder in subdirs:
        folder_name = os.path.basename(folder)
        files = [
            f
            for f in glob.glob(os.path.join(folder, "**", "*.xlsx"), recursive=True)
            if "~$" not in f
        ]
        if not files:
            continue

        raw: List[Dict[str, Any]] = []
        for f in files:
            try:
                raw.extend(parse_sienge_forecast_report(f, db))
            except Exception as e:
                print(f"  ERRO lendo {os.path.basename(f)}: {e}")

        sp_totals, skip_map, skip_tipo = _aggregate_rows(raw, db, ano_filter=2026)
        print(f"\n  {folder_name}: {len(files)} arquivos, {len(raw)} linhas, skip map={skip_map}")

        for tipo in ("DESPESAS", "RECEITAS"):
            fc = _find_forecast(db, folder_name, tipo)
            if not fc:
                print(f"  Forecast DB '{folder_name}' / {tipo} não encontrado.")
                all_ok = False
                continue
            db_totals = _db_forecast_totals(db, fc)
            sp_tipo = {k: v for k, v in sp_totals.items() if k[0] == tipo}
            db_tipo = {k: v for k, v in db_totals.items() if k[0] == tipo}
            ok = _compare_totals(f"FORECAST — {folder_name} / {tipo}", sp_tipo, db_tipo, cc_by_id)
            all_ok = all_ok and ok

    return all_ok


def main():
    db = SessionLocal()
    try:
        print("Validação SharePoint vs Banco — Orçado e Forecast (DESPESAS + RECEITAS)")
        ok_orc = validate_orcado(db)
        ok_fc = validate_forecast(db)
        print("\n" + "=" * 70)
        if ok_orc and ok_fc:
            print("RESULTADO FINAL: TUDO OK — valores batem com as planilhas SharePoint")
        else:
            print("RESULTADO FINAL: DIVERGÊNCIAS ENCONTRADAS — ver detalhes acima")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()
