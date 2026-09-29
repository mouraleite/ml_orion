"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import {
  siengeConsumoService,
  type ConsumoSiengeMes,
  type FamiliaConsumoSienge,
} from "@/services/siengeConsumo";

function mesAtualSaoPaulo(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(new Date());
  const year = parts.find((part) => part.type === "year")?.value ?? "2026";
  const month = parts.find((part) => part.type === "month")?.value ?? "01";
  return `${year}-${month}`;
}

const fmt = (value: number | null | undefined) =>
  value == null ? "—" : value.toLocaleString("pt-BR");

const fmtDia = (iso: string | null) => {
  if (!iso) return "—";
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
};

function caminhoCurto(path: string): string {
  const markers = ["/bulk-data/v1", "/api/v1"];
  for (const marker of markers) {
    const index = path.indexOf(marker);
    if (index >= 0) return path.slice(index + marker.length) || "/";
  }
  return path;
}

function FamiliaBloco({ familia }: { familia: FamiliaConsumoSienge }) {
  const chart = familia.dias.map((dia) => ({
    dia: dia.data.slice(8),
    total: dia.medido ? dia.total ?? 0 : null,
    acima: dia.acima_do_limite,
  }));
  const temMedicao = familia.dias.some((dia) => dia.medido);

  return (
    <section className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 bg-slate-50 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-bold text-slate-800">{familia.familia}</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Teto do pacote: {fmt(familia.limite_diario)} requisições/dia
            {" · "}
            segurança {fmt(familia.limite_por_minuto)}/min (informativo)
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 p-5">
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Total do mês</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{fmt(familia.total)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Média diária</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{fmt(familia.media_diaria)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Maior dia</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{fmt(familia.maior_dia_total)}</p>
          <p className="text-xs text-slate-400 mt-1">{fmtDia(familia.maior_dia)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">HTTP 429</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{fmt(familia.total == null ? null : familia.http_429)}</p>
          <p className="text-xs text-slate-400 mt-1">
            Fora da cota: 401 {fmt(familia.total == null ? null : familia.http_401)} · 5xx{" "}
            {fmt(familia.total == null ? null : familia.http_5xx)}
          </p>
        </div>
      </div>

      {temMedicao ? (
        <div className="px-5 pb-2 h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart} margin={{ top: 16, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="dia" tick={{ fontSize: 11, fill: "#64748b" }} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} allowDecimals={false} />
              <Tooltip
                formatter={(value) => [fmt(typeof value === "number" ? value : null), "Requisições"]}
                labelFormatter={(label) => `Dia ${label}`}
              />
              <ReferenceLine
                y={familia.limite_diario}
                stroke="#d97706"
                strokeDasharray="4 4"
                label={{ value: "Limite", fill: "#b45309", fontSize: 11, position: "insideTopRight" }}
              />
              <Bar dataKey="total" name="Requisições" radius={[3, 3, 0, 0]}>
                {chart.map((entry) => (
                  <Cell key={entry.dia} fill={entry.acima ? "#d97706" : "#0f766e"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="px-5 pb-5 text-sm text-slate-500">Nenhum dia deste mês foi medido.</p>
      )}

      {temMedicao && (
      <div className="px-5 pb-5 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate-500 border-b border-slate-100">
              <th className="py-2 pr-3 font-medium">Dia</th>
              <th className="py-2 pr-3 font-medium">Requisições</th>
              <th className="py-2 font-medium">Limite diário</th>
            </tr>
          </thead>
          <tbody>
            {familia.dias.map((dia) => (
              <tr
                key={dia.data}
                className={
                  dia.acima_do_limite
                    ? "bg-amber-50 text-amber-900 border-b border-amber-100"
                    : "border-b border-slate-50 text-slate-700"
                }
              >
                <td className="py-1.5 pr-3">{fmtDia(dia.data)}</td>
                <td className="py-1.5 pr-3 tabular-nums">{dia.medido ? fmt(dia.total) : "—"}</td>
                <td className="py-1.5 tabular-nums text-slate-500">{fmt(familia.limite_diario)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}
    </section>
  );
}

export default function ConsumoApisSiengePage() {
  const [mes, setMes] = useState(mesAtualSaoPaulo);
  const [dados, setDados] = useState<ConsumoSiengeMes | null>(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (valor: string) => {
    const [anoTexto, mesTexto] = valor.split("-");
    const ano = Number(anoTexto);
    const mesNumero = Number(mesTexto);
    if (!ano || !mesNumero) return;
    setLoading(true);
    setErro(null);
    try {
      const resposta = await siengeConsumoService.getMes(ano, mesNumero);
      setDados(resposta);
    } catch (error) {
      console.error(error);
      setDados(null);
      setErro("Não foi possível carregar o consumo das APIs Sienge.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregar(mes);
  }, [mes, carregar]);

  return (
    <div className="p-6 md:p-8 max-w-[1400px] mx-auto space-y-6 animate-in fade-in duration-300">
      <div className="flex justify-between items-start gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Activity className="w-6 h-6 text-brand-orange" />
            Consumo APIs Sienge
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Conta somente as chamadas feitas por este ERP. Outros integradores da mesma base Sienge não aparecem aqui.
          </p>
        </div>
        <label className="text-xs font-medium text-slate-500">
          Mês
          <input
            type="month"
            value={mes}
            onChange={(event) => setMes(event.target.value)}
            className="mt-1 block rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
          />
        </label>
      </div>

      {loading && <AppLoadingState title="Carregando consumo…" />}

      {!loading && erro && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl px-4 py-3 text-sm">{erro}</div>
      )}

      {!loading && dados && (
        <>
          <p className="text-xs text-slate-500">
            Pacote {dados.pacote} (aditivo 8, 2022). O total da cota ignora HTTP 401 e 5xx; HTTP 429 conta como estouro.
            Fuso {dados.fuso}.
          </p>

          {dados.historico_vazio && (
            <div className="bg-white rounded-xl border border-slate-200 px-5 py-8 text-center">
              <p className="text-sm font-semibold text-slate-800">Ainda não há histórico de chamadas.</p>
              <p className="text-sm text-slate-500 mt-2 max-w-xl mx-auto">
                O registro começa vazio e só passa a contar as chamadas deste ERP a partir de quando o log estiver gravando.
                Dias anteriores não foram medidos.
              </p>
            </div>
          )}

          <div className="space-y-6">
            {dados.familias.map((familia) => (
              <FamiliaBloco key={familia.familia} familia={familia} />
            ))}
          </div>

          <section className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 bg-slate-50">
              <h2 className="text-base font-bold text-slate-800">Top endpoints do mês</h2>
              <p className="text-xs text-slate-500 mt-0.5">Até 15 caminhos, pela quantidade que entra na cota.</p>
            </div>
            {dados.endpoints.length === 0 ? (
              <p className="px-5 py-6 text-sm text-slate-500">Nenhum endpoint neste mês.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-500 border-b border-slate-100">
                      <th className="px-5 py-2 font-medium">Caminho</th>
                      <th className="px-3 py-2 font-medium">Família</th>
                      <th className="px-5 py-2 font-medium text-right">Quantidade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dados.endpoints.map((item) => (
                      <tr key={`${item.familia}-${item.caminho}`} className="border-b border-slate-50 text-slate-700">
                        <td className="px-5 py-2 font-mono text-xs">{caminhoCurto(item.caminho)}</td>
                        <td className="px-3 py-2">{item.familia}</td>
                        <td className="px-5 py-2 text-right tabular-nums">{fmt(item.quantidade)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
