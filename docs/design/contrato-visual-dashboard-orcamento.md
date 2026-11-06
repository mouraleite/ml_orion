# Contrato visual — Dashboard de Orçamento e Orçado × Realizado

**Status:** aceito e implementado (chrome). Logos, analítica e drill não mudam.

**Data:** 2026-09-03

**Pedido:** estudar Dribbble + FP&A de mercado (linha Pigment) para melhorar o visual do dashboard de orçamentos e do chrome do Orçado × Realizado, **sem mexer no drill-down** (fornecedor, documento, parcela).

---

## 1. Escopo

### Entra (só chrome / leitura)

| Tela | O que pode mudar depois, se aprovado |
|------|--------------------------------------|
| `/dashboard/orcamento/resumo-geral` | Faixa de filtros, cards de KPI, leitura executiva, gráficos de apoio |
| `/dashboard/orcamento/realizado` | Toolbar, chips de mês, painel de filtro, abas, faixa Ref / Δ / Realizado, narrativa, layout da visão executiva |

### Não entra

- **Logos atuais** (Moura Leite, ML Órion, marca no menu, login e home): não trocar, não redesenhar, não “modernizar”. Os mocks inventaram uma estrela — isso não vale.
- Tabela de drill-down de despesas (`RealizadoDespesasDrillTable` e `/dashboard/orcamento/realizado-despesas`): credor, documento, número, parcela, valor.
- Qualquer fórmula, agregação, arredondamento, filtro que mude número, persistência ou sync.
- Grades editáveis (despesas, receitas, vendas, forecast).
- Home `/dashboard` — outro assunto.

Zona congelada de números continua valendo. Este arquivo é visual, não numérico.

---

## 2. O que o chrome faz hoje

O produto já tem a lógica certa. O problema é **empilhamento e igualdade visual**.

**Resumo geral**

- Seis cards iguais, cada um com ícone colorido (vermelho, verde, laranja, cinza).
- Resultado, despesas, receitas, VGV, unidades e ticket competem no mesmo peso.
- Filtros (holding, meses, ano, vs Orçado/Forecast, versão) ocupam uma faixa solta acima dos cards.

**Orçado × Realizado**

- Chrome em camadas: toolbar → chips de mês → painel de filtro → abas → só então o conteúdo.
- A visão executiva já tem o que o mercado usa: Ref | Variação | Realizado, veredito, blocos Resultado/Receitas/Despesas/Vendas, desvio por mês, drivers.
- Esse miolo fica escondido abaixo do chrome. O diretor não lê em 30 segundos.

**O que já está bom e deve permanecer**

- Faixa Ref / Δ / Realizado.
- Texto de leitura executiva (`DesvioExecStrip`).
- Toggle Executiva / Analítica.
- Toggle Orçado vs Forecast.
- Abas Consolidado / Despesas / Receitas / Vendas.
- **Telas analíticas (grade DRE, expansão por produto, comparativo, visualização):** permanecem. Só cabe ajuste de chrome (barra, espaçamento, hierarquia). Não substituir por cards.
- Drill-down de fornecedor/documento (intocado).
- Logos e marca que já estão no produto.

---

## 3. Cinco referências

Critério: produto de **planejamento financeiro**, não dashboard genérico de fintech (saldo, fatura, cartão). A maior parte do Dribbble é o segundo tipo — útil para densidade, perigoso para copiar.

| # | Fonte | Link | O que pegar | O que recusar |
|---|--------|------|-------------|---------------|
| 1 | **Pigment — Boards** (mercado) | [Design de boards](https://kb.pigment.com/docs/designing-pigment-boards) · [UX invertida](https://community.pigment.com/technical-tips-182/get-started-in-pigment-ux-design-1725) · [Templates](https://www.pigment.com/platform/templated-applications) | Pirâmide invertida: veredito no topo, detalhe embaixo. Seletores de página (ano, versão, período) numa barra só. Um propósito por tela. Cor só no desvio. | Clonar o produto. Não vamos virar “board builder”. |
| 2 | **Runway — Pages** (mercado) | [Pages](https://docs.runway.com/concepts/pages/pages-basics) · [Charts](https://docs.runway.com/concepts/pages/charts-block) | Um acento só. Número + frase antes do gráfico. Waterfall para “o que moveu o resultado”. | Canvas creme / estética de startup. A paleta é a da Moura Leite. |
| 3 | **Jirav no Dribbble** | [Shot 21731194](https://dribbble.com/shots/21731194-Jirav-Business-Planning-FP-A-and-Forecasting-Software) | Densidade de FP&A: P&L + tendência + contexto no mesmo olhar, sem seis cards de ícone. | Ilustração de marketing. Não copiar layout pixel a pixel. |
| 4 | **Pry no Dribbble** | [Shot 22143869](https://dribbble.com/shots/22143869-Pry-Financial-Planning-and-Analysis-Software) | Indicadores com período e versão visíveis. Pouca decoração. | Dark UI neon, cards idênticos, gráfico arco-íris. |
| 5 | **Bold BI — Budget vs Actual** (mercado) | [Exemplo](https://www.boldbi.com/dashboard-examples/finance/budget-vs-actual-dashboard/) | A página tem **um** trabalho: orçado × realizado (receita, despesa, categoria, tendência). | Widgetite de BI (donut + mapa + gauge no mesmo quadro). |

Leitura extra, se quiser ver o Pigment falando de variação: [variáveis para comparar versões](https://kb.pigment.com/docs/practical-examples-and-best-practices-for-changeable-static-variables).

---

## 4. Contrato (regras para quando formos desenhar)

### Hierarquia

1. Primeiro o **veredito do Resultado** (favorável / requer atenção / neutro) + Δ em R$ e %.
2. Depois composição do desvio (Receitas vs Despesas; em Vendas: líquido / vendas / distratos).
3. Depois tendência por mês (barras que já existem).
4. Por último tabela / ranking / analítica.

Seis KPIs do mesmo tamanho estão **proibidos**. Unidades e ticket médio são apoio, não heróis.

### Seletores de página

Ano, vs Orçado/Forecast, versão de forecast, meses e holding cabem **numa barra**. Não empilhar card de mês + painel de filtro + toolbar como três blocos iguais.

Filtros de produto/plano/empresa continuam no painel colapsável — só não competem com o veredito.

### Cor (paleta já existente)

| Cor | Hex | Uso |
|-----|-----|-----|
| Verde ML | `#2E864D` | No plano / favorável / aba ativa |
| Laranja ML | `#F5883A` | Ação da marca e desvio **material** — nunca enfeite de card |
| Vermelho | `#FF5144` | Desfavorável |
| Slate / branco | — | Superfície, texto, grade |

Proibido: um ícone de cor diferente em cada KPI. Cor só no Δ e no veredito.

### Número

- `tabular-nums`, pt-BR, 0 casas no hero (como hoje no consolidado).
- Label em 10px uppercase tracking.
- Um número hero por bloco. O segundo valor (referência ou realizado) fica menor, ao lado ou abaixo.

### Assinatura (o que a tela deve ser reconhecida)

A faixa **Referência | Variação | Realizado** + a frase de leitura executiva. Não substituir por um grid de cards. Apertar o chrome em volta para essa faixa ficar acima da dobra.

### Gráfico

- Waterfall ou barras de desvio por mês: **um** gráfico de apoio, não três.
- Sem donut de “composição” se a tabela de drivers já diz a mesma coisa.

### Copy

- “Requer atenção”, “Favorável”, “Neutro” — manter.
- “Comparar com: Orçado | Forecast” — manter.
- Recorte de ano civil: **YTD**, **YTG**, **FY**, **LY**. Título = a sigla; meses na legenda. Ver §7.
- Não vender (“Cérebro da Holding”, “insights poderosos”). Frase curta: o que desviou e onde.

---

## 5. Implementação

Chrome entregue nas duas telas do escopo. Sem mudança de cálculo, drill ou logos.

1. **Resumo geral** — hero Ref | Δ | Realizado; despesas/receitas/VGV secundários; unidades/ticket como apoio; uma barra de filtros.
2. **Orçado × Realizado** — departamento, ano e meses na mesma barra; produto/plano/empresa no painel colapsável; assinatura acima da dobra; analítica intacta.

---

## 6. Caixa de árvore (padrão)

Telas com tabela larga e níveis expansíveis (DFC, DFC gerencial, Despesas por empreendimento, DFC de empreendimentos, DFC comparativo) usam `GrowTreeSheet` em `frontend/src/components/shared/GrowTreeSheet.tsx`.

- A caixa **cresce** ao abrir empresa → grupo → plano. A página rola; não travar altura com `flex-1 min-h-0 overflow-hidden`.
- Coluna de nome: 360px, indentação 20px por nível, sem `truncate`.
- Grade editável de orçado × realizado **não** entra neste padrão.

---

## 7. Recortes de período (padrão)

Em tela de ano civil, estas siglas são o vocabulário do produto. Helper: `frontend/src/lib/periodosFpa.ts`.

| Sigla | Significado | Quando |
|---|---|---|
| **YTD** | realizado até o corte | jan → mês de corte |
| **YTG** | restante do ano | depois do corte |
| **FY** | ano cheio = YTD + YTG | mix de 12 meses |
| **LY** | ano anterior | só se a série existir |

```text
❌ Quarto card "Ano" duplicando FY
❌ YTD (jan–set) no título — meses vão na legenda
❌ Chamar de FY o "cheio" (100% vs MLDU)
❌ FY em tracking "vida do projeto" ou DFC mensal filtrado
✅ Linha de KPI: YTD · YTG · FY
✅ Série do ano passado: LY
✅ Tela nova de ano civil reusa periodosFpa.ts
```

---

## 8. Semáforo de desvio (padrão)

Régua única em `frontend/src/lib/semaforoDesvio.ts`. Ponto: `SemaforoDesvio`. Legenda: `DesvioLegend`.

| Cor | Estado | Quando |
|---|---|---|
| Cinza | Imaterial | \|n − ref\| < R$ 5 mil |
| Verde | Favorável / dentro da tolerância | desvio favorável **ou** ≤ 5% |
| Âmbar | Atenção | desfavorável e ≤ 10% |
| Vermelho | Acima do limite | desfavorável e > 10% |
| Azul | Novo | n com valor e ref zero |

`tipo`: `DESPESAS` (menor é melhor) · `RECEITAS` / `VENDAS` / `RESULTADO` (maior é melhor). Saída de DFC já negativa usa `RESULTADO`.

O ponto entra no KPI que compara n × ref e no **total** da coluna de variação. Não entra em cada mês da grade, em cadastro, nem em grade editável.

Tela nova com orçado × realizado reusa `SemaforoDesvio` — não inventa limiar.

---

## 9. Geração de caixa (roll-forward)

Travado em 2026-11-06. Card no DFC e no DFC gerencial. Snapshot 31/12 persiste no sync; o GET do DFC não chama o Sienge.

Não é estoque 31/12 × 31/12 do Sienge, nem o DFC líquido sozinho, nem a página atual Geração de Caixa (receitas − despesas).

1. **Abertura** do ano N = saldo de contas correntes no **último 31/12 fechado** (`GET /v1/accounts-balances`, `amount`, `companyId` = id Sienge, tipos B Bancária + I Investimento + C CAIXA). Persistido; não consultar o Sienge a cada load do DFC.
2. **YTD** = entradas − saídas **realizadas** até o corte (na visão DFC da tela).
3. **YTG** = entradas − saídas **orçadas** do restante do ano.
4. **Posição fim N** = abertura + YTD + YTG. **Geração N** = posição fim − abertura.
5. Enquanto N não fechou, a abertura de N+1 **é essa posição fim projetada** — não um 31/12 do Sienge que ainda não existe.

Em nov/2026: 31/12/2025 + realizado jan–out + orçado nov–dez → projeta 31/12/2026, que abre 2027. No DFC gerencial, cheio e MLDU.
