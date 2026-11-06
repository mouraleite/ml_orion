"use client";

import { DesvioLegend } from "@/components/orcamento/DesvioLegend";
import { PeriodoKpiCard } from "@/components/orcamento/PeriodoKpiCard";
import { fluxoCartoesDfc, legendaMesesDfc, type FluxoCartoes, type NoDfcFluxo } from "@/lib/dfcFluxoCartoes";
import { valoresCardGeracao, type BlocoGeracaoCaixa } from "@/lib/geracaoCaixa";
import { hintPeriodo, tituloPeriodo } from "@/lib/periodosFpa";

export function DfcFluxoCards({
  ano,
  meses,
  linhas,
  liquido,
  liquidoN1,
  totalEntradas,
  liquidoMldu,
  liquidoN1Mldu,
  comMldu = false,
  geracaoCaixa,
}: {
  ano: number;
  meses: string[];
  linhas: NoDfcFluxo[];
  liquido: number;
  liquidoN1: number;
  totalEntradas?: number;
  liquidoMldu?: number;
  liquidoN1Mldu?: number;
  comMldu?: boolean;
  geracaoCaixa?: BlocoGeracaoCaixa | null;
}) {
  const fluxo: FluxoCartoes = fluxoCartoesDfc({
    linhas,
    liquido,
    liquidoN1,
    totalEntradas,
    liquidoMldu,
    liquidoN1Mldu,
  });
  const nLabel = String(ano);
  const refLabel = tituloPeriodo("ly");
  const legenda = legendaMesesDfc(meses);
  const lyHint = hintPeriodo("ly");
  const mlduDe = (n: number, ref: number) => (comMldu ? { n, ref } : undefined);

  return (
    <div className="shrink-0 space-y-2">
      <div className={`grid grid-cols-1 sm:grid-cols-3 gap-3 ${comMldu ? "lg:gap-4" : ""}`}>
        <PeriodoKpiCard
          titulo="Entradas"
          legenda={legenda}
          hint={`Entradas do período × ${lyHint}`}
          n={fluxo.entradas}
          ref={fluxo.entradasN1}
          nLabel={nLabel}
          refLabel={refLabel}
          tipo="RESULTADO"
          mldu={mlduDe(fluxo.entradasMldu, fluxo.entradasN1Mldu)}
        />
        <PeriodoKpiCard
          titulo="Saídas"
          legenda={legenda}
          hint={`Saídas do período × ${lyHint}. Valores negativos.`}
          n={fluxo.saidas}
          ref={fluxo.saidasN1}
          nLabel={nLabel}
          refLabel={refLabel}
          tipo="RESULTADO"
          mldu={mlduDe(fluxo.saidasMldu, fluxo.saidasN1Mldu)}
        />
        <PeriodoKpiCard
          titulo="Líquido"
          legenda={legenda}
          hint={`Caixa líquido da visão × ${lyHint}`}
          n={liquido}
          ref={liquidoN1}
          nLabel={nLabel}
          refLabel={refLabel}
          tipo="RESULTADO"
          mldu={mlduDe(liquidoMldu ?? 0, liquidoN1Mldu ?? 0)}
        />
      </div>
      {geracaoCaixa ? <GeracaoCaixaCard bloco={geracaoCaixa} comMldu={comMldu} /> : null}
      <DesvioLegend />
    </div>
  );
}

function GeracaoCaixaCard({ bloco, comMldu }: { bloco: BlocoGeracaoCaixa; comMldu: boolean }) {
  const valores = valoresCardGeracao(bloco);
  const mlduBloco = comMldu ? bloco.mldu : null;
  const mlduValores = mlduBloco ? valoresCardGeracao(mlduBloco) : null;
  const hint = valores.usaPosicao
    ? `Posição fim = abertura + YTD realizado + YTG orçado × ${hintPeriodo("ly")}`
    : "Sem snapshot 31/12. Mostra só YTD + YTG da visão DFC.";
  return (
    <PeriodoKpiCard
      titulo="Geração de caixa"
      legenda={bloco.legenda}
      hint={hint}
      n={valores.n}
      ref={valores.ref}
      nLabel={valores.nLabel}
      refLabel={valores.refLabel}
      tipo="RESULTADO"
      mldu={mlduValores ? { n: mlduValores.n, ref: mlduValores.ref } : undefined}
    />
  );
}
