# Orçamento: endpoints que o frontend chama e o backend não tem

Levantado em **3 set 2026**, cruzando as 137 chamadas do frontend com as 156 rotas
registradas no backend em execução. Todas casam, menos as sete abaixo — todas em
`frontend/src/services/orcamento.ts`.

| Ação do usuário | Endpoint chamado | Onde | Hoje |
|--|--|--|--|
| Criar orçamento de Despesas | `POST /orcamentos` | `orcamento/despesas/page.tsx:144` | 404 |
| Criar orçamento de Vendas | `POST /orcamentos` | `orcamento/vendas/page.tsx:147` | 404 |
| Salvar orçamento de Vendas | `POST /orcamentos/vendas/{ano}/salvar` | `orcamento/vendas/page.tsx:332` | 404 |
| Enviar p/ aprovação, aprovar, fechar | `POST /orcamentos/{id}/status` | `VersionHeader.tsx:39` | 404 |
| Solicitar reabertura | `POST /orcamentos/{id}/solicitar-reabertura` | `VersionHeader.tsx:53` | 404 |
| Aprovar reabertura | `POST /orcamentos/{id}/aprovar-reabertura` | `VersionHeader.tsx:67` | 404 |
| Destravar | `POST /orcamentos/{id}/destravar` | `VersionHeader.tsx:81` | 404 |

Mais dois casos relacionados:

- **Criar orçamento de Receitas** (`orcamento/receitas/page.tsx:123`) chama
  `POST /orcamentos/criar`, que existe, mas envia só `{ano, tipo}`. O backend exige
  `produto_id` e devolve **400**. Quebrado também, por outro motivo.
- `travarOrcamento` existe em `orcamento.ts` mas nenhuma tela chama: código morto.

## Situação real do módulo

O Orçamento hoje funciona para **ler** e para **salvar linhas** de Despesas e Receitas.
Criar, versionar e todo o fluxo de aprovação nunca existiram no backend.

Evidências que batem com isso: os dois orçamentos de VENDAS no banco estão com zero
itens; todos os orçamentos existentes foram criados pelos scripts de carga do
SharePoint; e nenhum ponto do backend grava os status `Em aprovação`, `Reaberto`
ou `Substituído` — só `Aprovado`, vindo da carga.

Os testes em `tests/test_acceptance.py` marcados com `xfail(strict=True)` cobrem
parte disso. Quando o endpoint for implementado, o pytest acusa `XPASS(strict)`
para lembrar de rever o teste e tirar a marcação.

## Por que isso é delicado

A tela de acompanhamento escolhe qual orçamento ler filtrando por status e agrupando
por descrição (`acompanhamento.py`, linhas 90-100). Versionamento mexe em
`versao_numero`, `versao_base_id` e `Substituído` — ou seja, **mexe em quais números
aparecem na tela**, os mesmos validados e travados na baseline em 3 set 2026.

Ver `docs/conferencia-realizado-sp-mig.md`.

## Fatiamento

Rodar a baseline (`scripts/baseline_numeros.py comparar`) antes e depois de cada fase.

### Fase 1 — criar, salvar Vendas e travar meses fechados

**Concluída em 3 set 2026.** Baseline comparada antes e depois: motor de fórmulas e
dados locais iguais. Suíte em 141 passando, 2 xfail (ambos de reabertura, Fase 3).

**1.1 Unificar a criação (só frontend).** `orcamento.ts` tem duas funções para a
mesma coisa: `criar` chama `POST /orcamentos`, que não existe, e `criarOrcamento`
chama `/orcamentos/criar`, que existe. As três telas passam a usar a que funciona,
enviando `produto_id`. Remover a função morta. **Sem mudança no backend.**

Decidido: a tela de Receitas passa a pedir o empreendimento no modal de criação,
como Despesas e Vendas já fazem. Hoje ela só pergunta o ano, e por isso o backend
recusa com 400.

**1.2 Salvar Vendas (backend).** `POST /orcamentos/vendas/{ano}/salvar`, espelhando
`salvar_forecast_vendas` em `forecasts.py:657` — mesma estrutura de agrupar por
descrição, mapear por produto e bloquear se Aprovado/Fechado/Em aprovação.

**1.3 Trava de meses fechados (backend + frontend).** Hoje o salvar de Orçamento
não verifica `ClosedMonth`: dá para gravar valor em mês fechado. O critério 8 dos
testes de aceitação cobre isso e está como stub vazio.

Atenção à diferença em relação ao Forecast: lá a regra é "mês fechado tem de bater
com a **base**" (`forecasts.py:344`), porque o forecast tem `versao_base_orcamento_id`.
O orçamento não tem base — ele *é* a base. A regra equivalente é: **mês fechado não
pode diferir do valor já gravado no próprio orçamento.**

Parte de frontend: o GET do orçamento não devolve `meses_fechados` (o do forecast
devolve, `forecasts.py:271`). Sem isso a tela não tem como desabilitar os campos, e
o usuário só descobriria o bloqueio ao tomar 403 no salvar.

**1.4** `travarOrcamento` em `orcamento.ts` é código morto. Remover, ou implementar
junto com o destravar na Fase 3.

#### O que ficou de fato

- `criar` em `orcamento.ts` passou a apontar para `/orcamentos/criar`; `criarOrcamento`
  e `travarOrcamento` foram removidos. As três telas usam a mesma função.
- Receitas ganhou o seletor de empreendimento no modal de criação.
- `POST /orcamentos/vendas/{ano}/salvar` existe. O teste 10 saiu do `xfail`.
- Os três salvares recusam alteração em mês fechado, com `db.rollback()` antes do 403
  para não deixar o orçamento sem os itens que já haviam sido apagados. Helpers novos
  em `services/periodos.py`: `meses_fechados_do_ano` e `mes_fechado_alterado`.
- Os três GETs devolvem `meses_fechados`. **A tela ainda não usa esse campo** para
  desabilitar as células — falta ligar, e enquanto isso o usuário descobre o bloqueio
  ao tomar 403.
- Critério 8 dos testes de aceitação deixou de ser stub.

#### Achado fora do escopo, não corrigido

`salvar_forecast_vendas` (`forecasts.py:741`) chama `injetar_vendas_em_receitas(forecast, db)`,
mas `forecast` não existe naquele escopo — a variável é `forecast_ref`. Todo salvamento
de Forecast de Vendas estoura `NameError` (500) depois de já ter gravado e commitado os
itens. Zona congelada; não mexi. Vale decidir à parte.

### Fase 2 — fluxo de status

`POST /{id}/status` com transições explícitas e auditoria. Risco médio: muda quais
orçamentos entram no filtro das telas.

#### Decisão (3 set 2026)

Quem aprova: perfil **Gestor / Gerente**, **Diretor** ou **Administrador**
(`is_gestor_user` / `is_diretor_user` / `is_admin_user` — o cargo no cadastro
não conta). Ao aprovar, o orçamento vai direto para **Fechado**. Não fica
parado em Aprovado: nesse código Aprovado e Fechado já bloqueiam igual, e o
acompanhamento já lê os dois.

Cargo e nível continuam etiqueta. A autorização lê o **perfil de acesso**.

**Passo intermediário:** o analista envia (Rascunho / Reaberto → Em aprovação).
Só gerente, diretor ou admin vê Aprovar / Rejeitar. Aprovar grava **Fechado**.
Rejeitar volta para Rascunho. Notificação para o aprovador fica para depois —
nesta fase o status na tela já basta.

**Forecast segue a mesma regra:** mesmo quem aprova, mesmo passo de envio, e
aprovar fecha. Os registros que hoje estão Aprovado continuam Aprovado (o
acompanhamento já lê os dois). O botão "Fechar" some nas duas telas.

**Implementada em 3 set 2026.** Cadastro completo de perfis ficou para depois:
quem já é admin ou tem perfil Diretor/Gestor aprova; os demais só enviam.
O botão "Fechar" saiu das duas telas. `POST /orcamentos/{id}/status` existe.
O do Forecast passou a recusar salto de status e a gravar Fechado na aprovação.

### Fase 3 — reabertura

Solicitar, aprovar, destravar. Semântica já decidida (ver adiante).

## Decisão de desenho da Fase 3 (3 set 2026)

**A reabertura edita o mesmo orçamento. Não cria versão nova "corrente".**

Motivo: os 22 forecasts apontam para o orçamento 10 via `versao_base_orcamento_id`.
Criar um registro novo deixaria esses forecasts amarrados ao registro antigo enquanto
a tela passaria a ler outro — o número mudaria sem ninguém pedir. Editando o mesmo
registro, id e descrição não mudam, os forecasts seguem válidos e a seleção do
acompanhamento fica estável.

**Ao destravar, guardar uma cópia do estado aprovado com status `Substituído`.**

Esse status já é filtrado fora em todo lugar que importa — seleção do acompanhamento,
listagem de versões do comparativo (`budget_shared.py`, `status != "Substituído"`) e
telas de orçamento. A cópia não aparece para o usuário; serve como histórico do que
foi aprovado, para consulta ou restauração.

Sem ela, os valores aprovados seriam sobrescritos sem rastro: a auditoria registra
quem reabriu e por quê, mas não o que era antes.

### Decorrências a tratar junto

- O texto de confirmação em `VersionHeader.tsx` diz "Aprovar a reabertura irá criar
  uma NOVA VERSÃO do orçamento ligada a esta". Precisa mudar, senão promete uma
  coisa e faz outra.
- O comparativo lista versões por **descrição**, não por `versao_numero`
  (`list_visualizacao_versoes_disponiveis`). Com esta decisão, `versao_numero` passa
  a ser só contador interno.

### Ainda em aberto para a Fase 2

Nada. As duas perguntas foram fechadas em 3 set 2026 (passo de envio e
Forecast alinhado). Notificação ao aprovador fica fora desta fase.
