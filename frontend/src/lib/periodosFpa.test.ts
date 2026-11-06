import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  GLOSSA_PERIODO,
  PERIODOS_KPI,
  SIGLAS_PERIODO,
  legendaPeriodo,
  hintPeriodo,
  tituloPeriodo,
} from "./periodosFpa.ts";

describe("periodosFpa", () => {
  it("KPI de ano civil é YTD, YTG e FY — sem Ano duplicado e sem LY", () => {
    assert.deepEqual([...PERIODOS_KPI], ["ytd", "ytg", "fy"]);
    assert.equal(tituloPeriodo("ytd"), "YTD");
    assert.equal(tituloPeriodo("ytg"), "YTG");
    assert.equal(tituloPeriodo("fy"), "FY");
    assert.equal(tituloPeriodo("ly"), "LY");
  });

  it("legenda do corte 9 é jan–set / out–dez / YTD + YTG", () => {
    assert.equal(legendaPeriodo("ytd", 9), "jan–set");
    assert.equal(legendaPeriodo("ytg", 9), "out–dez");
    assert.equal(legendaPeriodo("fy", 9), "YTD + YTG");
  });

  it("YTG some quando o corte é dezembro", () => {
    assert.equal(legendaPeriodo("ytd", 12), "jan–dez");
    assert.equal(legendaPeriodo("ytg", 12), "sem meses");
  });

  it("LY só existe no glossário, não na linha de KPI", () => {
    assert.equal(SIGLAS_PERIODO.ly, "LY");
    assert.equal(GLOSSA_PERIODO.ly, "ano anterior");
    assert.equal(PERIODOS_KPI.includes("ly" as (typeof PERIODOS_KPI)[number]), false);
    assert.match(hintPeriodo("ly"), /ano anterior/);
  });
});
