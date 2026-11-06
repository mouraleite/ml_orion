import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { ACCESS_MODULES, MENU_MODULES } from "./menuCatalog";
import {
  filterMenuModules,
  hydratePermissions,
  isPathAllowed,
  isScreenPermitted,
  matchMenuPath,
  persistPermissions,
  ensureWriteFlags,
  isModuleWriteEnabled,
  setModuleWrite,
  WRITE_KEY,
} from "./accessMatrix";

describe("accessMatrix", () => {
  it("aceita chave antiga Despesas como Orçamento de Despesas", () => {
    const perms = { Orçamento: { Despesas: true } };
    assert.equal(isScreenPermitted(perms, "Orçamento", "Orçamento de Despesas"), true);
    assert.equal(isScreenPermitted(perms, "Orçamento", "Resumo Geral"), false);
  });

  it("aceita tela do dashboard pelo nome do menu", () => {
    const perms = { Orçamento: { "Resumo Geral": true } };
    assert.equal(isScreenPermitted(perms, "Orçamento", "Resumo Geral"), true);
  });

  it("mapeia Comparativo de Versões e Realizado para Orçado x Realizado", () => {
    const perms = { Orçamento: { "Comparativo de Versões": true } };
    assert.equal(isScreenPermitted(perms, "Orçamento", "Orçado x Realizado"), true);
  });

  it("filtra o menu sem mutar o catálogo original", () => {
    const originalCount = MENU_MODULES.find((m) => m.id === "orcamento")?.items[0].subItems?.length;
    const filtered = filterMenuModules(MENU_MODULES, {
      Orçamento: { "Resumo Geral": true, "Orçamento de Despesas": true },
    });
    const orc = filtered.find((m) => m.id === "orcamento");
    assert.ok(orc);
    assert.equal(orc.items.length, 2);
    assert.equal(orc.items[0].name, "Dashboard de Orçamento");
    assert.deepEqual(
      orc.items[0].subItems?.map((s) => s.name),
      ["Resumo Geral"],
    );
    assert.equal(
      MENU_MODULES.find((m) => m.id === "orcamento")?.items[0].subItems?.length,
      originalCount,
    );
  });

  it("coloca DFC de Empreendimentos abaixo do acompanhamento e acima dos relatórios", () => {
    const rent = MENU_MODULES.find((m) => m.id === "viabilidades");
    const names = rent?.items.map((i) => i.name) || [];
    assert.deepEqual(
      names.slice(names.indexOf("Acompanhamento de Empreendimentos"), names.indexOf("Relatórios") + 1),
      ["Acompanhamento de Empreendimentos", "DFC de Empreendimentos", "Relatórios"],
    );
    assert.equal(matchMenuPath("/dashboard/tracking/dfc")?.permKey, "DFC de Empreendimentos");
    assert.equal(matchMenuPath("/dashboard/tracking")?.permKey, "Acompanhamento de Empreendimentos");
    assert.equal(
      isPathAllowed(
        { "Rentabilidade de Produtos": { "Acompanhamento de Empreendimentos": true } },
        "/dashboard/tracking/dfc",
      ),
      true,
    );
    assert.equal(isPathAllowed({}, "/dashboard/tracking/dfc"), false);
  });

  it("mapeia a tela DFC como item do Orçamento, fora do dashboard", () => {
    const orc = MENU_MODULES.find((m) => m.id === "orcamento");
    assert.ok(orc?.items.some((i) => i.name === "DFC" && i.href === "/dashboard/orcamento/dfc"));
    assert.equal(
      orc?.items[0].subItems?.some((s) => s.name === "DFC"),
      false,
    );
    assert.equal(matchMenuPath("/dashboard/orcamento/dfc")?.permKey, "DFC");
    assert.equal(isPathAllowed({}, "/dashboard/orcamento/dfc"), false);
    assert.equal(isPathAllowed({ Orçamento: { DFC: true } }, "/dashboard/orcamento/dfc"), true);
  });

  it("coloca DFC gerencial abaixo do DFC e acima dos relatórios, com alias da permissão DFC", () => {
    const orc = MENU_MODULES.find((m) => m.id === "orcamento");
    const names = orc?.items.map((i) => i.name) || [];
    assert.deepEqual(
      names.slice(names.indexOf("DFC"), names.indexOf("Relatórios") + 1),
      ["DFC", "DFC gerencial", "Análise de Orçamento", "Relatórios"],
    );
    assert.equal(matchMenuPath("/dashboard/orcamento/dfc-gerencial")?.permKey, "DFC gerencial");
    assert.equal(matchMenuPath("/dashboard/orcamento/dfc")?.permKey, "DFC");
    assert.equal(isPathAllowed({ Orçamento: { DFC: true } }, "/dashboard/orcamento/dfc-gerencial"), true);
    assert.equal(isPathAllowed({}, "/dashboard/orcamento/dfc-gerencial"), false);
    assert.equal(matchMenuPath("/dashboard/orcamento/despesas-empreendimento")?.permKey, "Análise de Orçamento");
    assert.equal(isPathAllowed({ Orçamento: { DFC: true } }, "/dashboard/orcamento/despesas-empreendimento"), true);
    assert.equal(
      isPathAllowed({ Orçamento: { "Despesas por empreendimento": true } }, "/dashboard/orcamento/despesas-empreendimento"),
      true,
    );
    assert.equal(isPathAllowed({}, "/dashboard/orcamento/despesas-empreendimento"), false);
  });

  it("não confunde realizado com realizado-despesas", () => {
    assert.equal(matchMenuPath("/dashboard/orcamento/realizado")?.permKey, "Orçado x Realizado");
    assert.equal(matchMenuPath("/dashboard/orcamento/realizado-despesas")?.permKey, "Realizado CP (detalhe)");
  });

  it("bloqueia URL do dashboard sem permissão e libera com permissão", () => {
    assert.equal(isPathAllowed({}, "/dashboard/orcamento/resumo-geral"), false);
    assert.equal(
      isPathAllowed({ Orçamento: { "Resumo Geral": true } }, "/dashboard/orcamento/resumo-geral"),
      true,
    );
    assert.equal(isPathAllowed({}, "/dashboard"), true);
  });

  it("não mistura cadastro Empresas com relatório Empresas", () => {
    const perms = { Apoio: { Empresas: true } };
    assert.equal(isScreenPermitted(perms, "Apoio", "Empresas"), true);
    assert.equal(isScreenPermitted(perms, "Apoio", "Relatórios · Empresas"), false);
    assert.equal(
      isPathAllowed(perms, "/dashboard/apoio/relatorios", "id=empresas"),
      false,
    );
    assert.equal(isPathAllowed(perms, "/dashboard/apoio/empresas"), true);
  });

  it("matriz do perfil só lista telas, não filtros da tela", () => {
    const kinds = ACCESS_MODULES.flatMap((m) => m.groups.flatMap((g) => g.entries.map((e) => e.kind)));
    assert.ok(kinds.length > 0);
    assert.ok(kinds.every((k) => k === "screen"));
    assert.ok(
      !ACCESS_MODULES.some((m) =>
        m.groups.some((g) => g.entries.some((e) => e.permKey === "Consolidação MLDU")),
      ),
    );
  });

  it("grava criar/alterar por módulo sem misturar com tela", () => {
    const withWrite = ensureWriteFlags({ Orçamento: { "Orçamento de Despesas": true } }, "Diretor");
    assert.equal(isModuleWriteEnabled(withWrite, "Orçamento", "Diretor"), true);
    assert.equal(isScreenPermitted(withWrite, "Orçamento", WRITE_KEY), false);
    const engenharia = ensureWriteFlags({ Orçamento: { "Orçamento de Despesas": true } }, "Engenharia");
    assert.equal(isModuleWriteEnabled(engenharia, "Orçamento", "Engenharia"), false);
    const saved = persistPermissions(setModuleWrite(engenharia, "Orçamento", true));
    assert.equal(saved.Orçamento[WRITE_KEY], true);
    assert.equal(saved.Orçamento["Orçamento de Despesas"], true);
  });

  it("hydrate e persist sincronizam chave nova e alias", () => {
    const hydrated = hydratePermissions({ Orçamento: { Despesas: true } });
    assert.equal(hydrated.Orçamento["Orçamento de Despesas"], true);
    const saved = persistPermissions({ Orçamento: { "Orçamento de Despesas": true } });
    assert.equal(saved.Orçamento.Despesas, true);
    assert.equal(saved.Orçamento["Orçamento de Despesas"], true);
  });
});
