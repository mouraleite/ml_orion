import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { classesPainelSemaforo, estadoSemaforo, tipoSemaforo, varPercDesvio } from "./semaforoDesvio.ts";

describe("semaforoDesvio", () => {
  it("despesa menor que a ref é verde", () => {
    const s = estadoSemaforo(800_000, 1_000_000, "DESPESAS");
    assert.equal(s.titulo, "Favorável");
    assert.equal(s.cor, "bg-emerald-500");
  });

  it("saída de DFC já negativa: mais saída é vermelho", () => {
    const s = estadoSemaforo(-10_000_000, -8_000_000, "RESULTADO");
    assert.equal(s.titulo, "Acima do limite");
    assert.equal(s.cor, "bg-red-500");
  });

  it("saída de DFC já negativa: menos saída é verde", () => {
    const s = estadoSemaforo(-6_000_000, -8_000_000, "RESULTADO");
    assert.equal(s.titulo, "Favorável");
    assert.equal(s.cor, "bg-emerald-500");
  });

  it("líquido menor que o LY é vermelho", () => {
    const s = estadoSemaforo(3_100_000, 11_100_000, "RESULTADO");
    assert.equal(s.cor, "bg-red-500");
  });

  it("desvio abaixo de R$ 5 mil é cinza", () => {
    const s = estadoSemaforo(100_004_000, 100_000_000, "RESULTADO");
    assert.equal(s.titulo, "Imaterial");
    assert.equal(s.cor, "bg-slate-300");
  });

  it("linha nova (tem n, ref zero) é azul", () => {
    const s = estadoSemaforo(20_000, 0, "RECEITAS");
    assert.equal(s.titulo, "Novo");
    assert.equal(s.cor, "bg-sky-500");
  });

  it("entre 5% e 10% desfavorável é âmbar", () => {
    const s = estadoSemaforo(1_070_000, 1_000_000, "DESPESAS");
    assert.equal(s.titulo, "Atenção");
    assert.equal(s.cor, "bg-amber-400");
  });

  it("var % usa o módulo da ref", () => {
    assert.equal(varPercDesvio(-80, -100), 0.2);
  });

  it("CONSOLIDADO e tipos desconhecidos usam RESULTADO", () => {
    assert.equal(tipoSemaforo("CONSOLIDADO"), "RESULTADO");
    assert.equal(tipoSemaforo("DESPESAS"), "DESPESAS");
  });

  it("painel âmbar segue o estado Atenção", () => {
    const s = estadoSemaforo(1_070_000, 1_000_000, "DESPESAS");
    assert.equal(classesPainelSemaforo(s).badge, "bg-amber-100 text-amber-900");
  });
});
