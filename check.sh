#!/usr/bin/env bash
# Checagem rápida antes/depois de mudanças (Onda 0).
# Uso na raiz do projeto:  ./check.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
PYTHON="$BACKEND/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Venv não encontrado em backend/.venv. Rode: cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

cd "$BACKEND"
echo "== pytest (gate suite) =="
mapfile -t SUITE < <(grep -v '^\s*\(#\|$\)' tests/gate_suite.txt)
"$PYTHON" -m pytest "${SUITE[@]}" -q --tb=short
echo ""
echo "== baseline numeros (comparar) =="
"$PYTHON" scripts/baseline_numeros.py comparar
echo ""
echo "OK: testes e baseline batem."
