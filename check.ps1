# Checagem rápida antes/depois de mudanças (Onda 0).
# Uso na raiz do projeto:  .\check.ps1
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Venv não encontrado em backend\.venv. Rode: cd backend; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
}

Push-Location $Backend
try {
    Write-Host "== pytest (gate suite) ==" -ForegroundColor Cyan
    $suite = Get-Content (Join-Path $Backend "tests\gate_suite.txt") | Where-Object { $_ -and -not $_.StartsWith("#") }
    & $Python -m pytest @suite -q --tb=short
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "`n== baseline numeros (comparar) ==" -ForegroundColor Cyan
    & $Python scripts/baseline_numeros.py comparar
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "`nOK: testes e baseline batem." -ForegroundColor Green
}
finally {
    Pop-Location
}
