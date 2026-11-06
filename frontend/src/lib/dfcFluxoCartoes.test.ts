import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { fluxoCartoesDfc, legendaMesesDfc } from "./dfcFluxoCartoes.ts";

describe("fluxoCartoesDfc", () => {
  it("entradas vêm dos planos com sentido; saídas = líquido − entradas", () => {
    const fluxo = fluxoCartoesDfc({
      liquido: 110,
      liquidoN1: 80,
      totalEntradas: 150,
      linhas: [
        {
          kind: "categoria",
          total: 150,
          total_n1: 100,
          planos: [{ sentido: "entrada", total: 150, total_n1: 100 }],
        },
        {
          kind: "categoria",
          total: -40,
          total_n1: -20,
          planos: [{ sentido: "saida", total: -40, total_n1: -20 }],
        },
      ],
    });
    assert.equal(fluxo.entradas, 150);
    assert.equal(fluxo.entradasN1, 100);
    assert.equal(fluxo.saidas, -40);
    assert.equal(fluxo.saidasN1, -20);
  });

  it("no gerencial, plano sem sentido e positivo conta como entrada", () => {
    const fluxo = fluxoCartoesDfc({
      liquido: 70,
      liquidoN1: 40,
      liquidoMldu: 35,
      liquidoN1Mldu: 20,
      linhas: [
        {
          kind: "empresa",
          filhos: [
            {
              kind: "plano",
              total_real: 100,
              total_n1: 80,
              total_real_mldu: 50,
              total_n1_mldu: 40,
            },
            {
              kind: "plano",
              total_real: -30,
              total_n1: -40,
              total_real_mldu: -15,
              total_n1_mldu: -20,
            },
          ],
        },
      ],
    });
    assert.equal(fluxo.entradas, 100);
    assert.equal(fluxo.entradasN1, 80);
    assert.equal(fluxo.entradasMldu, 50);
    assert.equal(fluxo.saidas, -30);
    assert.equal(fluxo.saidasMldu, -15);
  });

  it("legenda do filtro de meses", () => {
    assert.equal(legendaMesesDfc([]), "ano completo");
    assert.equal(legendaMesesDfc(["jan", "fev", "mar"]), "jan–mar");
    assert.equal(legendaMesesDfc(["set"]), "set");
  });
});
