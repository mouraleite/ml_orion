"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/Table";
import { Building2, TrendingUp, PackageCheck, Search, Filter, Clock, Eraser } from "lucide-react";
import { BotaoComoLemos, ComoLemosAcompanhamentoPanel } from "@/components/tracking/ComoLemosAcompanhamentoPanel";
import { fatosDaLista } from "@/lib/comoLemosAcompanhamento";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

const formatCurrency = (val: number) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(val);
const formatCurrencyMi = (val: number) => `R$ ${(val / 1000000).toFixed(1)} Mi`;
const formatPercent = (val: number | null | undefined) => {
  if (val === null || val === undefined) return "N/A";
  return new Intl.NumberFormat("pt-BR", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(val / 100);
};
const formatNumber = (val: number | null | undefined) => {
  if (val === null || val === undefined) return "N/A";
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(val);
};

export default function TrackingPage() {
  const router = useRouter();
  const [data, setData] = useState<any[]>([]);
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);
  const [realizadoCaixa, setRealizadoCaixa] = useState<{ fonte_despesas?: string; fonte_receitas?: string } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  
  const [empreendimentoFilter, setEmpreendimentoFilter] = useState<string[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [painelMetodoAberto, setPainelMetodoAberto] = useState(false);

  const loadData = async () => {
    setIsLoading(true);
    setLoadError(false);
    try {
      const res = await api.get("/tracking/summary", { timeout: 180000 });
      // API returns {items: [...], last_sync_at: "..."} or legacy plain array
      if (Array.isArray(res.data)) {
        setData(res.data);
      } else {
        setData(res.data.items || []);
        setLastSyncAt(res.data.last_sync_at || null);
        setRealizadoCaixa(res.data.realizado_caixa || null);
      }
    } catch (e) {
      console.error(e);
      setLoadError(true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredData = data.filter((row) => {
    if (empreendimentoFilter.length > 0 && !empreendimentoFilter.includes(row.project_name)) return false;
    if (categoryFilter.length > 0 && !categoryFilter.includes(row.category)) return false;
    if (statusFilter.length > 0 && !statusFilter.includes(row.status)) return false;
    return true;
  });

  const empreendimentosUnicos = Array.from(new Set(data.map(d => d.project_name).filter(Boolean))).sort();
  const categoriasUnicas = Array.from(new Set(data.map(d => d.category).filter(Boolean))).sort();
  const statusUnicos = Array.from(new Set(data.map(d => d.status).filter(Boolean))).sort();

  const totalEmpreendimentos = filteredData.length;
  const totalVGV = filteredData.reduce((acc, curr) => acc + (curr.vgv_total || 0), 0);
  const totalVendas = filteredData.reduce((acc, curr) => acc + (curr.vendas_acumuladas || 0), 0);
  const percVendido = totalVGV > 0 ? (totalVendas / totalVGV) * 100 : 0;
  const totalLucro = filteredData.reduce((acc, curr) => acc + (curr.lucro || 0), 0);
  const tirMedia = filteredData.reduce((acc, curr) => acc + (curr.tir_anual || 0), 0) / (filteredData.length || 1);
  const paybackMedio = filteredData.reduce((acc, curr) => acc + (curr.payback_anos || 0), 0) / (filteredData.length || 1);
  const totalExposicao = filteredData.reduce((acc, curr) => acc + (curr.exposicao_max_caixa || 0), 0);

  const fatosLista = filteredData.length === 1 ? fatosDaLista(filteredData[0]) : null;

  return (
    <div className="space-y-6 animate-in fade-in duration-300" translate="no" lang="pt-BR">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">ACOMPANHAMENTO DE EMPREENDIMENTOS</h1>
        <BotaoComoLemos onClick={() => setPainelMetodoAberto(true)} />
      </div>

      {/* TABS */}
      <div className="flex overflow-x-auto border-b border-slate-200 hide-scrollbar mt-4">
        <button className="whitespace-nowrap px-6 py-3 font-medium text-sm border-b-2 border-brand-green text-brand-green transition-colors">
          Visão Geral
        </button>
        <button 
          onClick={() => {
            if (filteredData && filteredData.length > 0) {
              router.push(`/dashboard/tracking/${filteredData[0].id}`);
            }
          }}
          className="whitespace-nowrap px-6 py-3 font-medium text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 transition-colors"
        >
          Empreendimentos
        </button>
      </div>

      {/* TOP KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-4">
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1">Empreendimentos</span>
          <span className="text-xl font-bold text-slate-900">{totalEmpreendimentos}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1">VGV Total</span>
          <span className="text-xl font-bold text-slate-900" translate="no">{formatCurrencyMi(totalVGV)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">Vendas (Acum.)</span>
          <span className="text-xl font-bold text-slate-900" translate="no">{formatCurrencyMi(totalVendas)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">% Vendido (VGV)</span>
          <span className="text-xl font-bold text-brand-green">{formatPercent(percVendido)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">Lucro (Acum.)</span>
          <span className="text-xl font-bold text-slate-900" translate="no">{formatCurrencyMi(totalLucro)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">TIR Média Anual</span>
          <span className="text-xl font-bold text-slate-900">{formatPercent(tirMedia)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">Payback Médio</span>
          <span className="text-xl font-bold text-slate-900">{formatNumber(paybackMedio)}</span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center bg-white shadow-sm border border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-semibold mb-1 text-center">Exp. Máx Caixa</span>
          <span className="text-xl font-bold text-red-600" translate="no">{formatCurrencyMi(totalExposicao)}</span>
        </Card>
      </div>

      {/* DATA TABLE */}
      <Card className="p-0 border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex flex-col md:flex-row items-start md:items-center justify-between bg-white gap-4 w-full">
          <div className="flex flex-col md:flex-row items-start md:items-center gap-4 w-full">
            <div className="w-full md:w-72">
              <MultiSelect
                options={empreendimentosUnicos}
                value={empreendimentoFilter}
                onChange={setEmpreendimentoFilter}
                placeholder="Selecionar Empreendimentos"
                className="bg-white"
              />
            </div>
            <div className="w-full md:w-56">
              <MultiSelect
                options={categoriasUnicas}
                value={categoryFilter}
                onChange={setCategoryFilter}
                placeholder="Todas Categorias"
                className="bg-white"
              />
            </div>
            <div className="w-full md:w-56">
              <MultiSelect
                options={statusUnicos}
                value={statusFilter}
                onChange={setStatusFilter}
                placeholder="Todos Status"
                className="bg-white"
              />
            </div>


          </div>

            <div className="flex flex-wrap items-center gap-2 justify-end">
             {realizadoCaixa?.fonte_despesas && realizadoCaixa?.fonte_receitas && (
               <div
                 className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs text-slate-600"
                 title="Mesmo recorte de caixa efetivo do orçamento: contas a pagar (OP1/OP8/OP10/RET) e contas a receber (INC/BM)."
               >
                 <span className="whitespace-nowrap">
                   Caixa realizado:{" "}
                   <span className="font-semibold">contas a pagar / receber</span>
                 </span>
               </div>
             )}
             {lastSyncAt && (() => {
               // Formatar: "2026-07-21T08:10:45" → "21/07/2026 às 08:10:45"
               const dt = new Date(lastSyncAt);
               const isValidDate = !isNaN(dt.getTime());
               if (!isValidDate) return null;
               const datePart = dt.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
               const timePart = dt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
               return (
                 <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-md text-xs text-emerald-700" title="Data e horário da última sincronização com as APIs do Sienge">
                   <Clock className="w-3.5 h-3.5 shrink-0" />
                   <span className="whitespace-nowrap">
                     APIs atualizadas:{" "}
                     <span className="font-semibold">
                       {datePart} às {timePart}
                     </span>
                   </span>
                 </div>
               );
             })()}
            </div>
          </div>
        
        {isLoading ? (
          <AppLoadingState />
        ) : loadError ? (
          <div className="p-12 text-center text-slate-500">
            Não foi possível carregar o acompanhamento. Atualize a página.
          </div>
        ) : filteredData.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            Nenhum projeto encontrado.
          </div>
        ) : (
          <div className="overflow-x-auto bg-white">
            <Table className="!w-max table-fixed">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[200px] min-w-[200px] max-w-[200px] sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-20">Indicadores</TableHead>
                  {filteredData.map((row) => (
                    <TableHead key={row.id} className="!text-center w-[250px] min-w-[250px] max-w-[250px] align-top py-4">
                      <div 
                        className="font-bold text-slate-900 cursor-pointer hover:text-brand-green transition-colors line-clamp-2 w-full text-center"
                        title={row.project_name}
                        onClick={() => router.push(`/dashboard/tracking/${row.id}`)}
                      >
                        {row.project_name}
                      </div>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {/* Categoria */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">Categoria</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center">
                      <span className={`px-2 py-1 text-[10px] uppercase font-bold rounded-full ${
                        row.category === 'Land Bank' ? 'bg-amber-100 text-amber-700' :
                        row.category === 'Em Andamento' ? 'bg-blue-100 text-blue-700' :
                        'bg-emerald-100 text-emerald-700'
                      }`}>
                        {row.category}
                      </span>
                    </TableCell>
                  ))}
                </TableRow>
                
                {/* Status */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">Status</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center text-slate-600">
                      {row.status}
                    </TableCell>
                  ))}
                </TableRow>

                {/* Cidade */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">Cidade</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center text-slate-600">
                      {row.city}
                    </TableCell>
                  ))}
                </TableRow>

                {/* VGV Total */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">VGV Total</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center font-medium">
                      {formatCurrency(row.vgv_total)}
                    </TableCell>
                  ))}
                </TableRow>

                {/* Vendas */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">Vendas Acumuladas</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center text-slate-600">
                      {formatCurrency(row.vendas_acumuladas)}
                    </TableCell>
                  ))}
                </TableRow>

                {/* % Vend */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">% Vendido</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center font-bold text-brand-green">
                      {formatPercent(row.perc_vendido)}
                    </TableCell>
                  ))}
                </TableRow>

                {/* Lucro */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">Lucro Operacional</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center font-medium">
                      {formatCurrency(row.lucro)}
                    </TableCell>
                  ))}
                </TableRow>

                {/* TIR aa */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">TIR (a.a.)</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center text-slate-700">
                      {formatPercent(row.tir_anual)}
                    </TableCell>
                  ))}
                </TableRow>

                {/* MTIR aa */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">MTIR (a.a.)</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center text-slate-700">
                      {formatPercent(row.mtir_anual)}
                    </TableCell>
                  ))}
                </TableRow>

                {/* Payback */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">Payback (Meses)</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center text-slate-700">
                      {formatNumber(row.payback_anos)}
                    </TableCell>
                  ))}
                </TableRow>

                {/* Exp Max Caixa */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">Exp. Máx de Caixa</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center font-bold text-slate-900">
                      {formatCurrency(row.exposicao_max_caixa)}
                    </TableCell>
                  ))}
                </TableRow>

                {/* Exp / VGV */}
                <TableRow className="hover:bg-slate-50">
                  <TableCell className="font-semibold text-slate-700 sticky left-0 bg-white shadow-[1px_0_0_0_#e2e8f0] z-10">Exposição / VGV</TableCell>
                  {filteredData.map((row) => (
                    <TableCell key={row.id} className="text-center text-slate-600">
                      {formatPercent(row.exposicao_caixa_vgv)}
                    </TableCell>
                  ))}
                </TableRow>
              </TableBody>
            </Table>
          </div>
        )}
      </Card>
      <ComoLemosAcompanhamentoPanel
        open={painelMetodoAberto}
        onClose={() => setPainelMetodoAberto(false)}
        fatos={fatosLista}
      />
    </div>
  );
}
