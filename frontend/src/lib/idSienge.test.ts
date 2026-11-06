import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  idPublicoSienge,
  idsPublicosCentro,
  mapaNomeSiengePrimeiro,
  siengeOcupadosDe,
} from "./idSienge.ts";

describe("mapaNomeSiengePrimeiro em centro, obra e obra/centro", () => {
  it("Terras de Itu é 4 e Novo Horizonte é 32, iguais ao Sienge", () => {
    const map = mapaNomeSiengePrimeiro([
      { sienge: "32", interno: 4, nome: "NOVO HORIZONTE" },
      { sienge: "4", interno: 32, nome: "TERRAS DE ITU" },
    ]);
    assert.equal(map.get("4"), "TERRAS DE ITU");
    assert.equal(map.get("32"), "NOVO HORIZONTE");
    assert.equal(map.size, 2);
  });

  it("Sienge ganha do PK quando o número cruza os três tipos", () => {
    const map = mapaNomeSiengePrimeiro([
      { sienge: "14100", interno: 70, nome: "ITU - ALTAVISTA II" },
      { sienge: "70", interno: 14100, nome: "FROTA" },
      { sienge: "17700", interno: 4, nome: "TAGUAI - JARDIM DOS IPÊS III" },
      { sienge: "4", interno: 17700, nome: "CORPORATIVO - TERRAS DE ITU" },
    ]);
    assert.equal(map.get("14100"), "ITU - ALTAVISTA II");
    assert.equal(map.get("70"), "FROTA");
    assert.equal(map.get("17700"), "TAGUAI - JARDIM DOS IPÊS III");
    assert.equal(map.get("4"), "CORPORATIVO - TERRAS DE ITU");
  });
});

describe("idPublicoSienge", () => {
  const produtos = [
    { id: 70, id_sienge: "14100" },
    { id: 14100, id_sienge: "70" },
    { id: 4, id_sienge: "17700" },
    { id: 17700, id_sienge: "4" },
  ];
  const ocupados = siengeOcupadosDe(produtos);

  it("usa o Sienge e não o PK cruzado", () => {
    assert.equal(idPublicoSienge(produtos[0], ocupados), "14100");
    assert.equal(idPublicoSienge(produtos[1], ocupados), "70");
    assert.equal(idPublicoSienge(produtos[2], ocupados), "17700");
    assert.equal(idPublicoSienge(produtos[3], ocupados), "4");
  });

  it("lista pública não mistura obra com centro", () => {
    assert.deepEqual(idsPublicosCentro(produtos).sort(), ["14100", "17700", "4", "70"].sort());
  });

  it("ID público é só o Sienge, mesmo sem colisão", () => {
    const isolado = [{ id: 100, id_sienge: "501" }];
    assert.deepEqual(idsPublicosCentro(isolado), ["501"]);
    assert.equal(idPublicoSienge({ id: 100 }, siengeOcupadosDe(isolado)), "");
  });
});
