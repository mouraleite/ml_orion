import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { isDepartmentContextId } from "./departmentContext";

describe("isDepartmentContextId", () => {
  it("aceita Todos (id 0), diretorias (negativo) e departamentos reais", () => {
    assert.equal(isDepartmentContextId(0), true);
    assert.equal(isDepartmentContextId(-3), true);
    assert.equal(isDepartmentContextId(18), true);
  });

  it("rejeita ausência e valores inválidos", () => {
    assert.equal(isDepartmentContextId(undefined), false);
    assert.equal(isDepartmentContextId(null), false);
    assert.equal(isDepartmentContextId(Number.NaN), false);
    assert.equal(isDepartmentContextId("1"), false);
  });
});
