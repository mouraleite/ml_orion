"""
Captura e compara uma fotografia dos números atuais (banco local + fórmulas do motor).

Uso (na pasta backend, venv ativo):

  python scripts/baseline_numeros.py capturar
  python scripts/baseline_numeros.py comparar

Não altera dados. Serve para cruzar depois se totais, hashes e indicadores ainda batem.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text

BASELINES_DIR = Path(__file__).resolve().parents[1] / "tests" / "baselines"
MOTOR_FILE = BASELINES_DIR / "motor_formulas.json"
DADOS_FILE = BASELINES_DIR / "dados_locais.json"

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _canon(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _hash(obj) -> str:
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


def _round_num(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return str(v)
        return round(v, 8)
    return v


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return _round_num(obj) if isinstance(obj, (int, float)) else obj


def motor_payload():
    from app.services.math_engine import _apply_offset, _extract_curve
    from app.api.routes.tracking import _calculate_financial_indicators
    from app.services.excel_validator import _to_float, _to_int
    from app.services.calculations import (
        calculo_variacao_rs,
        calculo_variacao_perc,
        calculo_saldo_despesas,
        sumarizar_serie_mensal,
    )

    meses_curve, inicio = _extract_curve({"meses": [1.0, 1.0], "mes_inicio": 1})
    cf_ok = _calculate_financial_indicators({"2024-01": -100.0, "2024-02": 110.0})
    cf_none = _calculate_financial_indicators({"2024-01": 10.0, "2024-02": 10.0})
    cf_gap = _calculate_financial_indicators({"2024-01": -50.0, "2024-03": 50.0})

    itens = [
        {
            "orcado": {**{m: 0.0 for m in MESES}, "jan": 500.0, "total": 6000.0},
            "forecast": {**{m: 0.0 for m in MESES}, "total": 0.0},
            "realizado": {**{m: 0.0 for m in MESES}, "jan": 450.0, "total": 5400.0},
        },
        {
            "orcado": {**{m: 0.0 for m in MESES}, "jan": 300.0, "total": 3600.0},
            "forecast": {**{m: 0.0 for m in MESES}, "total": 0.0},
            "realizado": {**{m: 0.0 for m in MESES}, "jan": 320.0, "total": 3840.0},
        },
    ]

    payload = {
        "curvas": {
            "vazio": _extract_curve(None),
            "soma_100": list(_extract_curve({"meses": [40.0, 60.0], "mes_inicio": 3})),
            "normaliza": [meses_curve, inicio],
            "offset_m1": _apply_offset([10.0, 20.0], 1, 4),
            "offset_m3": _apply_offset([100.0], 3, 5),
            "offset_corte": _apply_offset([1.0, 2.0, 3.0], 5, 5),
        },
        "indicadores_acompanhamento": {
            "fluxo_dois_meses": cf_ok,
            "sem_troca_sinal": cf_none,
            "meses_faltantes": cf_gap,
        },
        "excel": {
            "float_10_virgula": _to_float("10,5"),
            "float_10_ponto": _to_float("10.5"),
            "float_vazio": _to_float(""),
            "int_3": _to_int("3"),
        },
        "variacoes": {
            "rs": calculo_variacao_rs(150.0, 100.0),
            "perc": calculo_variacao_perc(120.0, 100.0),
            "saldo": calculo_saldo_despesas(1000.0, 800.0),
            "serie_jan_orcado": sumarizar_serie_mensal(itens, "orcado")["orcado"]["jan"],
            "serie_total_realizado": sumarizar_serie_mensal(itens, "orcado")["realizado"]["total"],
        },
    }
    payload = _sanitize(payload)
    payload["fingerprint"] = _hash({k: v for k, v in payload.items() if k != "fingerprint"})
    return payload


def _has_table(engine, name: str) -> bool:
    return inspect(engine).has_table(name)


def _scalar(conn, sql: str, default=0):
    row = conn.execute(text(sql)).first()
    if not row:
        return default
    v = row[0]
    return default if v is None else v


def _sum_map(conn, table: str, cols: list[str]) -> dict:
    parts = [f'COALESCE(SUM("{c}"), 0) AS "{c}"' for c in cols]
    row = conn.execute(text(f'SELECT {", ".join(parts)} FROM "{table}"')).mappings().first()
    return {c: _round_num(float(row[c])) for c in cols} if row else {c: 0.0 for c in cols}


def _pluck_indicators(data):
    if not isinstance(data, dict):
        return None
    ind = data.get("indicators")
    if not isinstance(ind, dict):
        return None
    keep = {}
    for key in (
        "tir_anual",
        "tir_mensal",
        "mtir_anual",
        "vpl",
        "payback",
        "exposicao_maxima",
        "periodo_exposicao",
        "vgv",
        "lucro",
        "margem",
    ):
        if key in ind:
            keep[key] = _round_num(ind[key]) if isinstance(ind[key], (int, float)) else ind[key]
    return keep or None


def capturar_dados_locais():
    from app.db.database import engine
    from app.core.config import settings

    url = settings.DATABASE_URL
    fonte = url.split("@")[-1] if "@" in url else url

    with engine.connect() as conn:
        contagens = {}
        somas = {}
        for table, cols in (
            ("orcamento_itens", MESES + ["total_anual"]),
            ("orcamento_venda_itens", ["ticket_medio", "numero_vendas", "vgv"]),
            ("forecast_itens", MESES + ["total_anual"]),
            ("forecast_venda_itens", ["ticket_medio", "numero_vendas", "vgv"]),
            ("actual_transactions", ["value"]),
            ("phase_actuals", ["valor_realizado"]),
            ("viability_revenues", ["vgv_total", "taxa_juros_vendas"]),
            ("viability_constructions", ["custo_obras", "custo_projetos", "aquisicao_area", "adm_obras"]),
            ("viability_expenses", ["marketing_valor", "comercial_valor", "comissao_corretagem_valor", "adm_valor"]),
            ("phase_taxes", ["aliquota_pis", "aliquota_cofins", "aliquota_irpj", "aliquota_csll", "aliquota_outros", "aliquota_total"]),
        ):
            if _has_table(engine, table):
                contagens[table] = int(_scalar(conn, f"SELECT COUNT(*) FROM {table}"))
                somas[table] = _sum_map(conn, table, cols)

        viabilidades = []
        if _has_table(engine, "viabilities"):
            rows = conn.execute(text(
                """
                SELECT id, project_name, city, status,
                       tem_multiplas_fases, aplicar_ipca_receitas, ipca_projetado_valor,
                       aplicar_ipca_despesas, aplicar_incc_obras, incc_projetado_valor,
                       taxa_desconto_vpl
                FROM viabilities
                ORDER BY id
                """
            )).mappings().all()
            for v in rows:
                item = {k: _round_num(val) if isinstance(val, float) else val for k, val in dict(v).items()}
                fases = []
                if _has_table(engine, "phases"):
                    fases = [
                        dict(r)
                        for r in conn.execute(
                            text("SELECT id, name FROM phases WHERE viability_id = :id ORDER BY id"),
                            {"id": v["id"]},
                        ).mappings().all()
                    ]
                item["fases"] = fases
                viabilidades.append(item)

        orcamentos = []
        if _has_table(engine, "orcamentos"):
            sql = """
                SELECT o.id, o.ano, o.tipo, o.status, o.versao_numero, o.departamento_id, o.produto_id,
                       o.descricao,
                       COALESCE((SELECT SUM(i.total_anual) FROM orcamento_itens i WHERE i.orcamento_id = o.id), 0) AS soma_itens,
                       COALESCE((SELECT SUM(v.vgv) FROM orcamento_venda_itens v WHERE v.orcamento_id = o.id), 0) AS soma_vgv
                FROM orcamentos o
                ORDER BY o.id
            """
            for r in conn.execute(text(sql)).mappings().all():
                d = dict(r)
                d["soma_itens"] = _round_num(float(d["soma_itens"]))
                d["soma_vgv"] = _round_num(float(d["soma_vgv"]))
                orcamentos.append(d)

        forecasts = []
        if _has_table(engine, "forecasts"):
            sql = """
                SELECT f.id, f.ano, f.tipo, f.status, f.versao_numero, f.departamento_id, f.produto_id,
                       f.descricao, f.versao_base_orcamento_id, f.versao_base_forecast_id,
                       COALESCE((SELECT SUM(i.total_anual) FROM forecast_itens i WHERE i.forecast_id = f.id), 0) AS soma_itens,
                       COALESCE((SELECT SUM(v.vgv) FROM forecast_venda_itens v WHERE v.forecast_id = f.id), 0) AS soma_vgv
                FROM forecasts f
                ORDER BY f.id
            """
            for r in conn.execute(text(sql)).mappings().all():
                d = dict(r)
                d["soma_itens"] = _round_num(float(d["soma_itens"]))
                d["soma_vgv"] = _round_num(float(d["soma_vgv"]))
                forecasts.append(d)

        snapshots = []
        if _has_table(engine, "phase_snapshots"):
            for r in conn.execute(text(
                "SELECT id, phase_id, version_number, is_baseline, snapshot_data FROM phase_snapshots ORDER BY id"
            )).mappings().all():
                data = r["snapshot_data"]
                snapshots.append({
                    "id": r["id"],
                    "phase_id": r["phase_id"],
                    "version_number": r["version_number"],
                    "is_baseline": bool(r["is_baseline"]),
                    "hash_snapshot": _hash(data),
                    "indicators": _pluck_indicators(data),
                })

        perfis = []
        if _has_table(engine, "access_profiles"):
            for r in conn.execute(text(
                "SELECT id, name, is_active, permissions FROM access_profiles ORDER BY id"
            )).mappings().all():
                perfis.append({
                    "id": r["id"],
                    "name": r["name"],
                    "is_active": bool(r["is_active"]),
                    "hash_permissions": _hash(r["permissions"]),
                })

        indicadores = []
        if _has_table(engine, "economic_indicators"):
            for r in conn.execute(text(
                "SELECT id, nome, competencia, valor, tipo_unidade, index_type FROM economic_indicators ORDER BY id"
            )).mappings().all():
                d = dict(r)
                if isinstance(d.get("valor"), float):
                    d["valor"] = _round_num(d["valor"])
                indicadores.append(d)

    corpo = _sanitize({
        "fonte": fonte,
        "contagens": contagens,
        "somas": somas,
        "viabilidades": viabilidades,
        "orcamentos": orcamentos,
        "forecasts": forecasts,
        "phase_snapshots": snapshots,
        "perfis_acesso": perfis,
        "indicadores_economicos": indicadores,
    })
    return {
        "capturado_em": datetime.now(timezone.utc).isoformat(),
        **corpo,
        "fingerprint": _hash(corpo),
    }


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_capturar():
    motor = motor_payload()
    dados = capturar_dados_locais()
    _write(MOTOR_FILE, motor)
    _write(DADOS_FILE, dados)
    print(f"Motor: {MOTOR_FILE}")
    print(f"  fingerprint {motor['fingerprint']}")
    print(f"Dados locais: {DADOS_FILE}")
    print(f"  fingerprint {dados['fingerprint']}")
    print(f"  viabilidades={len(dados.get('viabilidades') or [])} "
          f"orcamentos={len(dados.get('orcamentos') or [])} "
          f"forecasts={len(dados.get('forecasts') or [])} "
          f"snapshots={len(dados.get('phase_snapshots') or [])}")


def _diff(esperado, atual, caminho="$"):
    diffs = []
    if type(esperado) != type(atual) and not (
        isinstance(esperado, (int, float)) and isinstance(atual, (int, float))
    ):
        diffs.append(f"{caminho}: tipo {type(esperado).__name__} vs {type(atual).__name__}")
        return diffs
    if isinstance(esperado, dict):
        keys = set(esperado) | set(atual if isinstance(atual, dict) else [])
        for k in sorted(keys):
            if k not in esperado:
                diffs.append(f"{caminho}.{k}: só no atual")
            elif k not in atual:
                diffs.append(f"{caminho}.{k}: só no gravado")
            else:
                diffs.extend(_diff(esperado[k], atual[k], f"{caminho}.{k}"))
        return diffs
    if isinstance(esperado, list):
        if not isinstance(atual, list) or len(esperado) != len(atual):
            diffs.append(f"{caminho}: len {len(esperado) if isinstance(esperado, list) else '?'} vs {len(atual) if isinstance(atual, list) else '?'}")
            return diffs
        for i, (a, b) in enumerate(zip(esperado, atual)):
            diffs.extend(_diff(a, b, f"{caminho}[{i}]"))
        return diffs
    if isinstance(esperado, float) and isinstance(atual, (int, float)):
        if abs(float(esperado) - float(atual)) > 1e-6:
            diffs.append(f"{caminho}: {esperado} vs {atual}")
        return diffs
    if esperado != atual:
        diffs.append(f"{caminho}: {esperado!r} vs {atual!r}")
    return diffs


def cmd_comparar():
    if not MOTOR_FILE.exists() or not DADOS_FILE.exists():
        print("Não há baseline. Rode: python scripts/baseline_numeros.py capturar")
        sys.exit(2)

    gravado_motor = json.loads(MOTOR_FILE.read_text(encoding="utf-8"))
    atual_motor = motor_payload()
    d_motor = _diff(
        {k: v for k, v in gravado_motor.items() if k != "capturado_em"},
        {k: v for k, v in atual_motor.items() if k != "capturado_em"},
    )

    gravado_dados = json.loads(DADOS_FILE.read_text(encoding="utf-8"))
    atual_dados = capturar_dados_locais()
    skip = {"capturado_em"}
    d_dados = _diff(
        {k: v for k, v in gravado_dados.items() if k not in skip},
        {k: v for k, v in atual_dados.items() if k not in skip},
    )

    ok = True
    if d_motor:
        ok = False
        print("DIFERENÇAS no motor de fórmulas:")
        for line in d_motor[:50]:
            print(" ", line)
        if len(d_motor) > 50:
            print(f"  ... +{len(d_motor) - 50}")
    else:
        print("Motor de fórmulas: igual à baseline.")

    if d_dados:
        ok = False
        print("DIFERENÇAS nos dados locais:")
        for line in d_dados[:80]:
            print(" ", line)
        if len(d_dados) > 80:
            print(f"  ... +{len(d_dados) - 80}")
    else:
        print("Dados locais: iguais à baseline.")

    sys.exit(0 if ok else 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("comando", choices=["capturar", "comparar"])
    args = parser.parse_args()
    os.chdir(Path(__file__).resolve().parents[1])
    if args.comando == "capturar":
        cmd_capturar()
    else:
        cmd_comparar()


if __name__ == "__main__":
    main()
