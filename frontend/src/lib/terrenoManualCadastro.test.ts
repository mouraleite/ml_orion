import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  formatarMesPt,
  linhasAlertaTerreno,
  mesSugeridoInicio,
  mostraInicioTerreno,
} from "./terrenoManualCadastro";

describe("mostraInicioTerreno", () => {
  it("esconde curva e início quando o valor é zero", () => {
    assert.equal(mostraInicioTerreno(0), false);
  });

  it("mostra início sempre que houver valor", () => {
    assert.equal(mostraInicioTerreno(1), true);
    assert.equal(mostraInicioTerreno(2480000), true);
  });
});

describe("formatarMesPt", () => {
  it("escreve ago/2026", () => {
    assert.equal(formatarMesPt("2026-08"), "ago/2026");
  });

  it("ignora vazio ou inválido", () => {
    assert.equal(formatarMesPt(""), "");
    assert.equal(formatarMesPt(null), "");
    assert.equal(formatarMesPt("2026-13"), "");
  });
});

describe("mesSugeridoInicio", () => {
  it("prefere o primeiro mês de caixa", () => {
    assert.equal(
      mesSugeridoInicio({ primeiroMesCaixa: "2026-08", primeiroMesDesembolso: "2026-12" }),
      "2026-08",
    );
  });

  it("usa a primeira saída se ainda não houver caixa de entrada", () => {
    assert.equal(
      mesSugeridoInicio({ primeiroMesCaixa: null, primeiroMesDesembolso: "2026-12" }),
      "2026-12",
    );
  });
});

describe("linhasAlertaTerreno", () => {
  it("mostra caixa e saída quando são meses diferentes", () => {
    const linhas = linhasAlertaTerreno({
      primeiroMesCaixa: "2026-08",
      primeiroMesDesembolso: "2026-12",
    });
    assert.equal(linhas[0], "O caixa desta obra começa em ago/2026.");
    assert.equal(linhas[1], "A primeira saída é dez/2026.");
  });

  it("não repete o mês quando caixa e saída coincidem", () => {
    const linhas = linhasAlertaTerreno({
      primeiroMesCaixa: "2026-08",
      primeiroMesDesembolso: "2026-08",
    });
    assert.equal(linhas.length, 2);
    assert.equal(linhas[0], "O caixa desta obra começa em ago/2026.");
  });

  it("avisa quando a obra ainda não tem caixa", () => {
    const linhas = linhasAlertaTerreno({ primeiroMesCaixa: null, primeiroMesDesembolso: null });
    assert.match(linhas[0], /Ainda não há movimento de caixa/);
  });
});
