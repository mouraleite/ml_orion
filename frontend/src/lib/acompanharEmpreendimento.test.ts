import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  centroEhSateliteDeProduto,
  mostraFlagAcompanharEmpreendimento,
  podeAcompanharEmpreendimento,
  tipoEfetivoCentro,
} from "./acompanharEmpreendimento";

describe("podeAcompanharEmpreendimento", () => {
  it("mostra no cabeçalho Somente Obra e Obra e Centro de Custo", () => {
    assert.equal(podeAcompanharEmpreendimento("Somente Obra", "TAGUAI - JARDIM DOS IPÊS III"), true);
    assert.equal(podeAcompanharEmpreendimento("Obra e Centro de Custo", "AVARÉ - CENTRAL PARQUE II"), true);
    assert.equal(
      podeAcompanharEmpreendimento("Obra e Centro de Custo", "ARAÇARIGUAMA - RESERVA DO ARAÇARI - MLDU"),
      true,
    );
  });

  it("esconde em Somente Centro de Custo", () => {
    assert.equal(podeAcompanharEmpreendimento("Somente Centro de Custo", "FROTA"), false);
  });

  it("esconde associado satélite (obras, marketing, parceria)", () => {
    assert.equal(
      podeAcompanharEmpreendimento("Centro de Custo associado à Obra", "TAGUAI - JARDIM DOS IPÊS III - OBRAS"),
      false,
    );
    assert.equal(
      podeAcompanharEmpreendimento("Centro de Custo associado à Obra", "AVARÉ - CENTRAL PARQUE II - MARKETING"),
      false,
    );
    assert.equal(
      podeAcompanharEmpreendimento("Centro de Custo associado à Obra", "AVARÉ - CENTRAL PARQUE - PARCERIA"),
      false,
    );
    assert.equal(
      podeAcompanharEmpreendimento("Centro de Custo associado à Obra", "ITATINGA - NOVO HORIZONTE - PARCERIA"),
      false,
    );
  });

  it("mostra associado que é o produto (Morada, Reserva, Novo Horizonte, comercial sem sufixo)", () => {
    assert.equal(
      podeAcompanharEmpreendimento("Centro de Custo associado à Obra", "BOITUVA - MORADA DOS IPÊS II"),
      true,
    );
    assert.equal(
      podeAcompanharEmpreendimento("Centro de Custo associado à Obra", "BOITUVA - RESERVA DOS IPÊS"),
      true,
    );
    assert.equal(
      podeAcompanharEmpreendimento("Centro de Custo associado à Obra", "ITATINGA - NOVO HORIZONTE"),
      true,
    );
    assert.equal(
      podeAcompanharEmpreendimento("Centro de Custo associado à Obra", "TAGUAI - JARDIM DOS IPÊS III"),
      true,
    );
  });
});

describe("mostraFlagAcompanharEmpreendimento", () => {
  it("ainda mostra satélite já marcado para dar para desmarcar", () => {
    assert.equal(
      mostraFlagAcompanharEmpreendimento({
        tipo: "Centro de Custo associado à Obra",
        nome: "AVARÉ - CENTRAL PARQUE - PARCERIA",
        jaAcompanhado: true,
      }),
      true,
    );
    assert.equal(
      mostraFlagAcompanharEmpreendimento({
        tipo: "Centro de Custo associado à Obra",
        nome: "AVARÉ - CENTRAL PARQUE - PARCERIA",
        jaAcompanhado: false,
      }),
      false,
    );
  });
});

describe("helpers", () => {
  it("tipo efetivo prefere override manual", () => {
    assert.equal(
      tipoEfetivoCentro({
        tipo_sienge: "Centro de Custo associado à Obra",
        custom_data: { __tipo_override: "Somente Obra" },
      }),
      "Somente Obra",
    );
  });

  it("reconhece satélite MLDU e gestão", () => {
    assert.equal(centroEhSateliteDeProduto("BOITUVA - RESERVA DOS IPÊS - MLDU (ELLENCO & MLDU)"), true);
    assert.equal(centroEhSateliteDeProduto("ITATINGA - NOVO HORIZONTE - GESTÃO DE CARTEIRA E ESTOQUE"), true);
    assert.equal(centroEhSateliteDeProduto("BOITUVA - MORADA DOS IPÊS II"), false);
  });
});
