import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { valoresCardGeracao, type BlocoGeracaoCaixa } from "./geracaoCaixa.ts";

function bloco(partial: Partial<BlocoGeracaoCaixa>): BlocoGeracaoCaixa {
  return {
    ano: 2026,
    corte: 10,
    ytd: 80,
    ytg: 45,
    geracao: 125,
    abertura: 1000,
    posicao_fim: 1125,
    tem_abertura: true,
    geracao_n1: 40,
    posicao_fim_n1: 1000,
    tem_abertura_n1: true,
    ...partial,
  };
}

describe("valoresCardGeracao", () => {
  it("com abertura mostra posição fim × LY", () => {
    const v = valoresCardGeracao(bloco({}));
    assert.equal(v.n, 1125);
    assert.equal(v.ref, 1000);
    assert.equal(v.usaPosicao, true);
  });

  it("sem abertura não inventa estoque — usa YTD+YTG", () => {
    const v = valoresCardGeracao(
      bloco({ tem_abertura: false, abertura: null, posicao_fim: null, tem_abertura_n1: false, posicao_fim_n1: null }),
    );
    assert.equal(v.n, 125);
    assert.equal(v.ref, 40);
    assert.equal(v.usaPosicao, false);
  });
});
