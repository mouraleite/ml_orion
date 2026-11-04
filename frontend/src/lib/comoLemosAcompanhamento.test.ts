import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  TEXTO_CAMADAS,
  TITULO_CRONOGRAMA_OBRA,
  TITULO_VENDAS_ESTOQUE,
  estoqueDaDre,
  fatosDoDetalhe,
  somaFluxo,
  textoTir,
  tirClassicaAusente,
} from "./comoLemosAcompanhamento";

describe("camadas do método", () => {
  it("separa engenharia de vendas de estoque", () => {
    assert.equal(TITULO_CRONOGRAMA_OBRA, "Cronograma de desembolso de obra");
    assert.equal(TITULO_VENDAS_ESTOQUE, "Vendas de lotes em estoque");
    assert.equal(TEXTO_CAMADAS.obras.includes("Estoque"), false);
    assert.match(TEXTO_CAMADAS.obras, /saldo do orçamento da obra/);
    assert.match(TEXTO_CAMADAS.obras, /mês que vem/);
    assert.match(TEXTO_CAMADAS.estoque, /6 meses que tiveram venda/);
    assert.match(TEXTO_CAMADAS.estoque, /média do m²/);
    assert.equal(TEXTO_CAMADAS.estoque.includes("mês que vem"), false);
    assert.match(TEXTO_CAMADAS.pago, /baixas do Sienge/);
    assert.match(TEXTO_CAMADAS.comprometido, /títulos em aberto/);
  });
});

describe("estoqueDaDre", () => {
  it("lê unidades e valor da linha de estoque", () => {
    const out = estoqueDaDre([
      { item: "Receita Bruta", valor: 10 },
      { item: "VGV Estoque Potencial (32 unidades)", valor: 2_200_000 },
    ]);
    assert.equal(out.unidades, 32);
    assert.equal(out.valor, 2_200_000);
  });
});

describe("somaFluxo", () => {
  it("separa obra paga de prevista", () => {
    const out = somaFluxo([
      { Obras: 618_000, Terreno: 0, is_forecast: false },
      { Obras: 5_885_000, Terreno: 0, is_forecast: true },
    ]);
    assert.equal(out.obrasPagas, 618_000);
    assert.equal(out.obrasPrevistas, 5_885_000);
  });
});

describe("tirClassicaAusente", () => {
  it("reconhece 0% com MTIR preenchida", () => {
    assert.equal(tirClassicaAusente(0, 20.7), true);
    assert.equal(tirClassicaAusente(6.7, 9.8), false);
  });
});

describe("textoTir", () => {
  it("não inventa TIR quando o card está 0%", () => {
    const t = textoTir({
      nome: "Jardim dos Ipês III",
      estoqueUnidades: 0,
      vgvEstoque: 0,
      terreno: 0,
      obrasPagas: 0,
      obrasPrevistas: 0,
      tirAnual: 0,
      mtirAnual: 20.7,
      payback: 34,
      exposicao: -2_479_296,
    });
    assert.match(t, /card pode mostrar 0%/);
    assert.match(t, /MTIR 20,7%/);
    assert.match(t, /34 meses/);
  });
});

describe("fatosDoDetalhe", () => {
  it("monta os fatos a partir do payload já na tela", () => {
    const fatos = fatosDoDetalhe({
      nome: "Jardim dos Ipês III",
      fase: "Em Andamento",
      kpis: { tir_anual: 0, mtir_anual: 20.7, payback: 34, exposicao_max_caixa: -2479296 },
      dre: [
        { item: "(-) Custo de Terreno", valor: 0 },
        { item: "VGV Estoque Potencial (12 unidades)", valor: 1_200_000 },
      ],
      fluxoCaixa: [
        { Obras: 100, is_forecast: false, Terreno: 0 },
        { Obras: 900, is_forecast: true, Terreno: 0 },
      ],
    });
    assert.equal(fatos.estoqueUnidades, 12);
    assert.equal(fatos.obrasPrevistas, 900);
    assert.equal(fatos.payback, 34);
  });
});
