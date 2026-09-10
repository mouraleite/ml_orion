# Baseline numérica (3 set 2026)

Fotografia para cruzar depois se os valores ainda batem.

Recapturada em 3 set 2026, depois da reconciliação do realizado contra o SP-MIG
(ver `docs/conferencia-realizado-sp-mig.md`). A fotografia anterior, de 28 ago 2026,
está preservada em `anterior-2026-08-28/` — as diferenças entre as duas foram
conferidas uma a uma antes de recapturar e nenhuma era erro.

## Arquivos

- `motor_formulas.json` — saídas fixas das fórmulas (curvas, TIR/payback de exemplo, Excel, variações). O pytest `test_baseline_motor.py` compara sempre.
- `dados_locais.json` — totais, listas e hashes do SQLite que a API usa (`DATABASE_URL`). Inclui viabilidades, orçamentos, forecasts, snapshots de fase (hash + indicadores) e hash das permissões dos perfis.
- `anterior-2026-08-28/` — fotografia anterior, só para consulta. Nenhum teste lê esta pasta.

## Como usar

Na pasta `backend/`:

```bash
python scripts/baseline_numeros.py capturar
python scripts/baseline_numeros.py comparar
```

Para o pytest cruzar o banco (além do motor):

```bash
set ERP_ML_COMPARAR_DADOS=1
pytest tests/test_baseline_motor.py tests/test_baseline_dados.py -q
```

Se `comparar` ou o teste falhar, algum número ou estrutura mudou em relação a esta fotografia — revalidar na tela antes de gravar uma baseline nova.
