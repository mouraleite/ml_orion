"""Compara o motor atual com tests/baselines/motor_formulas.json."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.baseline_numeros import MOTOR_FILE, _diff, motor_payload


@pytest.mark.skipif(not MOTOR_FILE.exists(), reason="Baseline do motor ainda não capturada")
def test_motor_igual_a_baseline():
    gravado = json.loads(MOTOR_FILE.read_text(encoding="utf-8"))
    atual = motor_payload()
    diffs = _diff(
        {k: v for k, v in gravado.items() if k != "capturado_em"},
        {k: v for k, v in atual.items() if k != "capturado_em"},
    )
    assert diffs == [], "Motor divergiu da baseline:\n" + "\n".join(diffs[:40])
