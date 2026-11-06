import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { centrosNomePorId, empresasNomePorId } from "./empresasNomePorId.ts";

describe("empresasNomePorId", () => {
  it("id Sienge ganha do PK interno quando o número é o mesmo", () => {
    const map = empresasNomePorId([
      { id: "32", db_id: 4, nomeFantasia: "NOVO HORIZONTE" },
      { id: "4", db_id: 32, nomeFantasia: "TERRAS DE ITU" },
    ]);
    assert.equal(map.get("4"), "TERRAS DE ITU");
    assert.equal(map.get("32"), "NOVO HORIZONTE");
  });

  it("ID público é o Sienge, não o PK do cadastro", () => {
    const map = empresasNomePorId([
      { id: "12", db_id: 100, nomeFantasia: "Ellenco" },
    ]);
    assert.equal(map.get("12"), "Ellenco");
    assert.equal(map.has("100"), false);
  });
});

describe("centrosNomePorId", () => {
  it("Sienge ganha do PK em obra, centro e obra/centro", () => {
    const map = centrosNomePorId([
      { id: "14100", db_id: 70, nome: "ITU - ALTAVISTA II" },
      { id: "70", db_id: 14100, nome: "FROTA" },
      { id: "17700", db_id: 4, nome: "TAGUAI - JARDIM DOS IPÊS III" },
    ]);
    assert.equal(map.get("14100"), "ITU - ALTAVISTA II");
    assert.equal(map.get("70"), "FROTA");
    assert.equal(map.get("17700"), "TAGUAI - JARDIM DOS IPÊS III");
    assert.equal(map.has("4"), false);
  });
});
