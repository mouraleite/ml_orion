"use client";

import { useEffect } from "react";
import { X } from "lucide-react";
import {
  FatosAcompanhamento,
  TEXTO_CAMADAS,
  TEXTO_DRE,
  TEXTO_FORA,
  TEXTO_SEM_PRODUTO,
  TEXTO_VGV_ESTOQUE,
  TITULO_CRONOGRAMA_OBRA,
  TITULO_PAINEL,
  TITULO_VENDAS_ESTOQUE,
  formatarMi,
  textoTir,
} from "@/lib/comoLemosAcompanhamento";

type Props = {
  open: boolean;
  onClose: () => void;
  fatos: FatosAcompanhamento | null;
};

function Bloco({ titulo, children }: { titulo: string; children: string }) {
  return (
    <section className="border-l-[3px] border-brand-green pl-3">
      <h3 className="text-sm font-bold text-slate-900">{titulo}</h3>
      <p className="mt-1 text-[13px] leading-relaxed text-slate-600">{children}</p>
    </section>
  );
}

export function ComoLemosAcompanhamentoPanel({ open, onClose, fatos }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  const subtitulo = fatos
    ? [fatos.nome, fatos.fase].filter(Boolean).join(" · ")
    : TEXTO_SEM_PRODUTO;

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        aria-label="Fechar"
        className="absolute inset-0 bg-slate-900/40"
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="como-lemos-titulo"
        className="absolute inset-y-0 right-0 flex w-full max-w-md flex-col border-l-[4px] border-brand-green bg-white"
      >
        <header className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-brand-green">Método</p>
            <h2 id="como-lemos-titulo" className="mt-1 text-lg font-bold text-slate-900">
              {TITULO_PAINEL}
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-slate-500">{subtitulo}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <X className="h-5 w-5" />
            <span className="sr-only">Fechar</span>
          </button>
        </header>

        <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
          {fatos ? (
            <div className="grid grid-cols-3 gap-2">
              <Tile rotulo="Pago (obra)" valor={formatarMi(fatos.obrasPagas)} />
              <Tile rotulo="Cronograma de obra" valor={formatarMi(fatos.obrasPrevistas)} />
              <Tile rotulo="Terreno" valor={formatarMi(fatos.terreno)} />
            </div>
          ) : null}

          <div className="overflow-hidden rounded-lg border border-slate-200">
            <Camada cor="bg-amber-500" titulo={TITULO_CRONOGRAMA_OBRA} texto={TEXTO_CAMADAS.obras} />
            <Camada cor="bg-sky-600" titulo={TITULO_VENDAS_ESTOQUE} texto={TEXTO_CAMADAS.estoque} />
            <Camada cor="bg-teal-700" titulo="Comprometido" texto={TEXTO_CAMADAS.comprometido} />
            <Camada cor="bg-brand-dark-green" titulo="Pago" texto={TEXTO_CAMADAS.pago} />
          </div>

          {fatos && fatos.estoqueUnidades > 0 ? (
            <p className="text-xs text-slate-500">
              Estoque neste produto: {fatos.estoqueUnidades} unidades
              {fatos.vgvEstoque > 0 ? ` · ${formatarMi(fatos.vgvEstoque)}` : ""}.
            </p>
          ) : null}

          <Bloco titulo="VGV e estoque">{TEXTO_VGV_ESTOQUE}</Bloco>
          <Bloco titulo="DRE">{TEXTO_DRE}</Bloco>
          <Bloco titulo="TIR e MTIR">
            {fatos
              ? textoTir(fatos)
              : "TIR clássica só existe se o caixa começa com investimento. Se o primeiro mês é entrada, o card pode mostrar 0% e a taxa da vida é a MTIR (TMA 12%). Payback e exposição leem o mesmo fluxo."}
          </Bloco>
          <Bloco titulo="O que não entra">{TEXTO_FORA}</Bloco>
        </div>
      </aside>
    </div>
  );
}

function Tile({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="rounded-md border border-slate-200 px-2 py-2">
      <p className="text-[10px] font-medium uppercase tracking-wide text-slate-500">{rotulo}</p>
      <p className="mt-1 text-sm font-bold text-slate-900">{valor}</p>
    </div>
  );
}

function Camada({ cor, titulo, texto }: { cor: string; titulo: string; texto: string }) {
  return (
    <div className="flex gap-3 border-b border-slate-100 last:border-b-0">
      <div className={`w-2 shrink-0 ${cor}`} />
      <div className="py-3 pr-3">
        <p className="text-sm font-bold text-slate-900">{titulo}</p>
        <p className="mt-0.5 text-[13px] leading-relaxed text-slate-600">{texto}</p>
      </div>
    </div>
  );
}

export function BotaoComoLemos({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2 rounded-md border border-brand-green px-4 py-2 text-sm font-medium text-brand-green hover:bg-brand-green/5"
    >
      {TITULO_PAINEL}
    </button>
  );
}
