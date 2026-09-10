"""Compara o banco da API com tests/baselines/dados_locais.json.

Ativado com ERP_ML_COMPARAR_DADOS=1 para não falhar o CI só porque o SQLite local mudou.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.baseline_numeros import DADOS_FILE, _diff, capturar_dados_locais


@pytest.mark.skipif(
    os.environ.get("ERP_ML_COMPARAR_DADOS") != "1",
    reason="Defina ERP_ML_COMPARAR_DADOS=1 para cruzar o banco local com a baseline",
)
@pytest.mark.skipif(not DADOS_FILE.exists(), reason="Baseline de dados ainda não capturada")
def test_dados_locais_iguais_a_baseline():
    gravado = json.loads(DADOS_FILE.read_text(encoding="utf-8"))
    atual = capturar_dados_locais()
    skip = {"capturado_em"}
    diffs = _diff(
        {k: v for k, v in gravado.items() if k not in skip},
        {k: v for k, v in atual.items() if k not in skip},
    )
    assert diffs == [], "Dados locais divergiram da baseline:\n" + "\n".join(diffs[:80])
