import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  centroEhSateliteDeProduto,
  ehCabecaDeObra,
  mostraFlagAcompanharEmpreendimento,
  opcoesObraAcompanhamento,
  podeAcompanharEmpreendimento,
  rotuloCentroIdNome,
  tipoEfetivoCentro,
} from "./acompanharEmpreendimento.ts";

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

describe("obra no acompanhamento", () => {
  it("só aceita Somente Obra e Obra e Centro de Custo", () => {
    assert.equal(ehCabecaDeObra("Somente Obra"), true);
    assert.equal(ehCabecaDeObra("Obra e Centro de Custo"), true);
    assert.equal(ehCabecaDeObra("Centro de Custo associado à Obra"), false);
    assert.equal(ehCabecaDeObra("Somente Centro de Custo"), false);
  });

  it("rótulo junta ID e nome", () => {
    assert.equal(
      rotuloCentroIdNome(17700, "TAGUAI - JARDIM DOS IPÊS III"),
      "17700 - TAGUAI - JARDIM DOS IPÊS III",
    );
    assert.equal(rotuloCentroIdNome("", "FROTA"), "FROTA");
  });

  it("lista ignora associado, somente CC e frota", () => {
    const opcoes = opcoesObraAcompanhamento([
      { db_id: 1, id: 900, nome: "AUTOMÓVEL FIAT", tipo_sienge: "Somente Centro de Custo" },
      { db_id: 2, id: 17701, nome: "TAGUAI - JARDIM DOS IPÊS III - OBRAS", tipo_sienge: "Centro de Custo associado à Obra" },
      { db_id: 3, id: 17700, nome: "TAGUAI - JARDIM DOS IPÊS III", tipo_sienge: "Somente Obra" },
      { db_id: 4, id: 12800, nome: "AVARÉ - CENTRAL PARQUE II", tipo_sienge: "Obra e Centro de Custo" },
    ]);
    assert.deepEqual(
      opcoes.map((c) => c.id),
      [12800, 17700],
    );
  });
});
