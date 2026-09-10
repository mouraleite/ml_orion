import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { canWriteModule } from "./roles";

describe("canWriteModule", () => {
  it("mesmo perfil: um só vê, o outro altera", () => {
    const perms = { Orçamento: { _write: true, "Orçamento de Despesas": true } };
    const soVe = { role: "READ_ONLY", perfil: { name: "Engenharia", permissions: perms } };
    const altera = { role: "Usuario", perfil: { name: "Engenharia", permissions: perms } };
    assert.equal(canWriteModule(soVe, "Orçamento"), false);
    assert.equal(canWriteModule(altera, "Orçamento"), true);
  });

  it("somente visualização vence perfil Diretor e write_modules da API", () => {
    const u = {
      role: "READ_ONLY",
      effective_role: "Diretor",
      capabilities: { admin: false, diretor: true, gestor: true, analista: true },
      write_modules: { Orçamento: true },
      perfil: { name: "Diretor", permissions: { Orçamento: { _write: true } } },
    };
    assert.equal(canWriteModule(u, "Orçamento"), false);
  });

  it("administrador no colaborador sempre altera", () => {
    const u = {
      role: "ADMIN",
      perfil: { name: "Engenharia", permissions: { Orçamento: { _write: false } } },
    };
    assert.equal(canWriteModule(u, "Orçamento"), true);
  });
});
