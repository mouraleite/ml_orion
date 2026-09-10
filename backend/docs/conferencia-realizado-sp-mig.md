# Conferência do realizado: SP-MIG × Sienge

Estado da reconciliação em **3 set 2026**, período jan–ago/2026.
Script de conferência: `backend/scripts/_chk_ancoras.py`.

**Números dados como validados em 3 set 2026**, com a baseline numérica recapturada
na mesma data (`tests/baselines/`) para travar esta fotografia.

Escopo do que foi validado: realizado de jan–ago/2026, despesas e receitas, no
consolidado e centro a centro, contra o SP-MIG. Fora do escopo:

- **Setembro em diante não tem como ser validado**: o SP-MIG só tem dados até
  agosto (o total dele é idêntico em jan–ago e no ano cheio). O que existe no
  sistema de set/2026 em diante são pagamentos que o Sienge já registrou com
  data futura.
- A conferência foi feita por consulta ao banco e à camada de agregação, não
  abrindo as telas.

## Onde estamos

| | SP-MIG | Sistema | Diferença | % |
|--|--:|--:|--:|--:|
| Despesas | 77.800.056,23 | 77.737.238,89 | −62.817,34 | −0,081% |
| Receitas | 78.806.060,64 | 78.847.110,49 | +41.049,85 | +0,052% |

Receitas já excluindo AFAC, que fica fora do realizado de receitas por definição
(o SP trata como transferência/despesa). Ver `realizado_sienge.py`.

Âncoras em zero: CC 72801, AFAC (todas as categorias), Serviços de Terceiros (Obra),
Distratos, Distratos Permuta/Quitação, IPTU/ITR, ISS, Documentos/Multas e Seguros
de Veículos, Materiais de Limpeza e Copa.

## Dispersão por centro de custo

Importa para quem analisa um empreendimento isolado: o gap líquido da empresa
poderia estar escondendo desvios grandes que se compensam. Não está.

Receitas: dos 85 centros com movimento, **83 fecham exato**. Os R$ 41.050 estão
todos no 70100 (Rendimentos de Aplicações). Nenhum empreendimento diverge.

Despesas, 172 centros com movimento:

| | Com adiantamentos | Sem adiantamentos |
|--|--:|--:|
| Soma dos gaps em módulo | 279.452,18 | 35.786,88 |
| Sobre a base do SP | 0,359% | 0,046% |
| Centros que fecham exato | 79 | 89 |
| Gap abaixo de R$ 100 | 45 | 45 |
| Gap de R$ 100 a R$ 1.000 | 28 | 30 |
| Gap de R$ 1.000 a R$ 10.000 | 14 | 7 |
| Gap acima de R$ 10.000 | 6 | 1 |

Os seis acima de R$ 10.000 são 14000, 13700, 13800, 13900, 15313 e 13200 — todos
por conta de adiantamento (ver nota abaixo), nenhum por despesa operacional.

Excluindo os adiantamentos sobra um único centro acima de R$ 10.000, e não é
empreendimento: 70100 (CORPORATIVO - MLDU), −R$ 13.997,30. Composição: R$ 9.299
de retenções de Cofins/PIS e IR (classificação, se anula contra a receita),
R$ 4.356 de Despesas Bancárias e o resto abaixo de R$ 500.

## Nota técnica: as contas de adiantamento não são despesa

Vale para **Adiantamento a Parceiros** e **Adiantamentos a Fornecedores**.
Elas respondem por R$ 46.635 dos R$ 62.817 de diferença e por praticamente todo
o descasamento por centro de custo. **Não são erro e não devem ser "corrigidas".**

No SP essas duas linhas registram a *variação do saldo* de uma conta rotativa, não
o caixa pago. A prova é que têm lançamentos negativos, coisa que uma despesa de
caixa nunca tem:

- Adiantamento a Parceiros: −R$ 249.453,60 em lançamentos negativos no SP
- Adiantamentos a Fornecedores: −R$ 59.120,36, espalhados por 39 centros de custo

No sistema, o realizado é caixa efetivamente pago (Contas a Pagar). Por isso os
dois números não podem coincidir por construção.

### Onde há caixa de verdade, o sistema bate exato

Adiantamento a Parceiros, por centro de custo:

| CC | SP | Sistema | Gap |
|--|--:|--:|--:|
| 70108 | 200.000,00 | 200.000,00 | 0,00 |
| 16103 | 15.000,00 | 15.000,00 | 0,00 |
| 15200 | 10.000,00 | 10.000,00 | 0,00 |
| 13200 | 9.452,50 | 9.452,50 | 0,00 |
| 13700 | −47.584,00 | 0,00 | +47.584,00 |
| 13800 | −31.616,00 | 0,00 | +31.616,00 |
| 13900 | 32.340,00 | 0,00 | −32.340,00 |
| 14000 | 44.660,00 | 0,00 | −44.660,00 |

Os quatro primeiros são adiantamentos reais e fecham na vírgula. Os quatro últimos
são só movimentação de saldo no SP; o líquido deles é −R$ 2.200, exatamente o gap
da categoria na empresa.

### Por que não ajustamos

Fechar isso exigiria importar a concessão do adiantamento como despesa positiva e a
baixa como despesa negativa. Descartado em 3 set 2026 porque:

1. O realizado dessas categorias deixaria de significar caixa pago e passaria a
   significar variação de saldo, confundindo a leitura da tela.
2. Passaríamos a gravar despesa negativa de forma contínua, inclusive para o futuro,
   com efeito não avaliado no orçado × realizado.
3. É zona congelada, e a diferença não é erro: é conceito. O conceito atual do
   sistema (caixa) é o mais defensável dos dois.

**Se este tema voltar, releia esta seção antes de investigar de novo.**

## Demais resíduos conhecidos

Nenhum indica dado faltando.

| Item | Valor | Natureza |
|--|--:|--|
| Despesas Bancárias | −11.799,64 | resíduo pequeno, não investigado a fundo |
| Rendimentos de Aplicações (receita) | +35.623,82 | resíduo pequeno, não investigado a fundo |
| Retenção de Cofins/PIS e de IR | ∓9.299,47 | só classificação: o SP lança como receita negativa, o sistema como despesa negativa. Se anulam entre os dois blocos. |
| Multas | −4.871,12 | resíduo pequeno |
| Depósitos não Identificados (receita) | −3.873,42 | resíduo pequeno |
| IR sobre Aplicação | −93,01 | um movimento de agosto que o SP capturou e o extrato ainda não |
| IOF | −1.024,20 | resíduo pequeno |

## Pontos em aberto (não bloqueiam a validação)

**Orçamentos duplicados no banco.** Existem dois pares de cópias idênticas para
2026: ids 5 e 8 com descrição `'Orçamento'` (843 e 96 itens) e ids 10 e 11 com
`'Carga Inicial Sienge 2026'` (mesmos 843 e 96 itens, mesmos totais).

A tela de acompanhamento **não duplica** hoje: em `acompanhamento.py` ela pega o
maior id com status Aprovado/Fechado e soma todos os orçamentos com a *mesma
descrição*. Como as descrições diferem, seleciona só um por tipo — R$ 184.269.360,34
de despesa orçada e R$ 198.268.420,04 de receita.

O risco é a fragilidade: se alguém alinhar as descrições desses pares, a tela passa
a somar os dois e o orçado dobra silenciosamente.

**8 testes de aceitação falhando** em `tests/test_acceptance.py`, rotas de orçamento
respondendo 404. Anteriores a este trabalho e sem relação com o sync (os 135 demais
testes passam, incluindo os 31 de sync).

## Histórico dos ajustes que fecharam diferença

| Data | Ajuste | Ganho |
|--|--|--:|
| 3 set 2026 | IR sobre Aplicação lido das saídas do Caixa e Bancos (não passa pelo Contas a Pagar) | 62.334 |
| 3 set 2026 | Colisão de `source_id`: pagamentos do mesmo título, dia e categoria se sobrescreviam; desempate pelo id do movimento bancário | 138.329 |
| 3 set 2026 | Adiantamento (op 10) aceito só em "Adiantamento a Parceiros" com rateio integral | — |
| 3 set 2026 | AFAC espelhado de receita para despesa no sync | — |

Baseline recapturada em 3 set 2026 e conferida logo depois: motor de fórmulas e
dados locais iguais à fotografia, `test_baseline_motor.py` e `test_baseline_dados.py`
passando com `ERP_ML_COMPARAR_DADOS=1`.
