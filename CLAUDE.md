# ML Órion (ERP ML) — regras de trabalho

Leia também `.agents/AGENTS.md` e `.cursor/rules/*.mdc` (zonas congeladas, git/deploy, IDs Sienge, períodos). Em conflito, vale o que o Marcelo disser na conversa.

## Fluxo de mudança

1. Plano curto antes de mudar código; esperar aprovação. Se encostar em zona congelada, dizer no plano.
2. Trabalhar sempre numa branch (`correcoes-analise` ou outra combinada). **Nunca** commitar direto na `main`: a `main` publica sozinha na Vercel (front) e no Render (API).
3. Cada correção vem com teste que falha no código antigo e passa no novo.
4. Antes de entregar: suíte completa do backend verde e gate suite verde (`backend/tests/gate_suite.txt`).
5. Commit na branch quando o Marcelo aprovar. Push/merge na `main` só com autorização explícita («pode subir»).

## Testes

- Na pasta `backend`, com o venv: `.venv\Scripts\python -m pytest tests -q`
- Gate suite: `.\check.ps1` na raiz.
- O `tests/conftest.py` define `ERP_ML_DISABLE_SCHEDULER=1`: subir a API nos testes nunca dispara sync real do Sienge. Não remover.
- Testes de reprodução dos erros da análise: `docs/analise_2026-11-09/test_reproducao_erros.py`.

## Dados de produção (Neon)

- Leitura: scripts somente leitura (`set_session(readonly=True)`), rodados pelo Marcelo via `.bat` em `docs/analise_2026-11-09/`.
- Qualquer alteração de dados de produção: antes, criar uma branch de backup no painel do Neon; script testado; Marcelo roda; conferência depois.
- Nunca imprimir senhas de `.env`, `.env.neon`, `.env.backfill`.

## Detalhes técnicos

- Repositório guarda arquivos com fim de linha LF. Ao editar no Windows/VM, manter LF (senão o diff mostra o arquivo inteiro).
- Sienge: credenciais em `backend/.env.backfill` (não em `.env`).
- Realizado: o significado de cada lançamento depende do prefixo de `source_id` (ver `services/realizado_sienge.py` e `.cursor/rules/ids-sienge-amarracoes.mdc`).

## Decisões de negócio já tomadas (09/11/2026)

- Taxa do financiamento bancário: seletor "% a.a." / "% a.m." (padrão a.a.; anual → mensal por (1+i)^(1/12) − 1).
- Parceiros: percentual vale sobre o projeto inteiro; custos rateados divididos pelo percentual; custos não rateados 100% dos empreendedores, repartidos entre eles na proporção de cada um.

## Análise de referência

- `docs/ML_Orion_Analise_Tecnica_e_Financeira.docx` (versão viva no Claude Docs): erros, riscos e plano em fases.
- Backup completo antes das correções: `Backups/Backup_2026-11-09_pre-analise/`.
