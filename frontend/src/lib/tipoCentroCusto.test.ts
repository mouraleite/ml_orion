import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { rotuloTipoSienge } from "./tipoCentroCusto.ts";

describe("rotuloTipoSienge", () => {
  it("mapeia códigos 1 a 4", () => {
    assert.equal(rotuloTipoSienge("1"), "Obra e Centro de Custo");
    assert.equal(rotuloTipoSienge(2), "Somente Obra");
    assert.equal(rotuloTipoSienge("4"), "Centro de Custo associado à Obra");
  });

  it("preserva rótulo já traduzido", () => {
    assert.equal(rotuloTipoSienge("Somente Obra"), "Somente Obra");
  });

  it("usa o id do objeto Sienge e ignora icone/src", () => {
    assert.equal(
      rotuloTipoSienge({
        id: 2,
        description: "Building",
        icon: "https://cdn.sienge.com.br/icons/building.png",
        src: "/file.svg",
      }),
      "Somente Obra",
    );
  });

  it("não devolve HTML nem URL de imagem", () => {
    assert.equal(rotuloTipoSienge('<img src="https://x/a.png">'), "");
    assert.equal(rotuloTipoSienge("https://cdn.sienge.com.br/type/2.png"), "Desconhecido");
    assert.equal(rotuloTipoSienge("/window.svg"), "Desconhecido");
    assert.ok(!rotuloTipoSienge("<img src=x>").includes("<"));
  });

  it("vazio fica vazio para a célula mostrar traço", () => {
    assert.equal(rotuloTipoSienge(null), "");
    assert.equal(rotuloTipoSienge(""), "");
  });
});
