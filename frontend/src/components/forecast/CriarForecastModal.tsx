"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { forecastService, ForecastBaseOption, OpcaoPlano, OpcaoProduto } from "@/services/forecast";
import toast from "react-hot-toast";

type TipoForecast = "DESPESAS" | "VENDAS";

export function CriarForecastModal({
  tipo,
  deptId,
  anoInicial,
  onClose,
  onCreated,
}: {
  tipo: TipoForecast;
  deptId: number;
  anoInicial: number;
  onClose: () => void;
  onCreated: (ano: number, produtoId: number) => void;
}) {
  const [ano, setAno] = useState(anoInicial);
  const [produtoId, setProdutoId] = useState<number | 0>(0);
  const [planoId, setPlanoId] = useState<number | 0>(0);
  const [baseKey, setBaseKey] = useState("");
  const [produtos, setProdutos] = useState<OpcaoProduto[]>([]);
  const [planos, setPlanos] = useState<OpcaoPlano[]>([]);
  const [bases, setBases] = useState<ForecastBaseOption[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    forecastService.getCatalogo(tipo, ano, deptId).then((resp) => {
      setProdutos(resp.opcoes_produtos || []);
      setPlanos(resp.opcoes_planos || []);
      setBases(resp.opcoes_base || []);
    }).catch(() => {
      toast.error("Não foi possível carregar empreendimentos, planos e bases.");
    });
  }, [tipo, deptId, ano]);

  const confirmar = async () => {
    if (!produtoId) {
      toast.error("Selecione um empreendimento");
      return;
    }
    if (!planoId) {
      toast.error(tipo === "VENDAS" ? "Selecione um plano de venda" : "Selecione um plano financeiro");
      return;
    }
    setSaving(true);
    try {
      let orcamentoId: number | undefined;
      let forecastId: number | undefined;
      if (baseKey.startsWith("Orcamento:")) {
        orcamentoId = Number(baseKey.split(":")[1]);
      } else if (baseKey.startsWith("Forecast:")) {
        forecastId = Number(baseKey.split(":")[1]);
      }
      await forecastService.criarDeBase(
        ano,
        tipo,
        deptId,
        orcamentoId,
        forecastId,
        produtoId,
        tipo === "VENDAS"
          ? { plano_venda_id: planoId }
          : { plano_financeiro_id: planoId },
      );
      toast.success("Criado!");
      onCreated(ano, produtoId);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao criar.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-lg font-bold text-slate-800 mb-4">Criar Forecast</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Ano</label>
            <input
              type="number"
              className="w-full p-2 border border-slate-300 rounded-md"
              value={ano}
              onChange={(e) => setAno(Number(e.target.value))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Empreendimento</label>
            <SearchableSelect
              options={produtos.map((p) => ({
                id: p.id,
                label: p.id_sienge ? `${p.id_sienge} - ${p.nome}` : p.nome,
              }))}
              value={produtoId}
              onChange={(val) => setProdutoId(Number(val))}
              placeholder="Pesquise ou selecione..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Base</label>
            <select
              className="w-full p-2 border border-slate-300 rounded-md text-sm"
              value={baseKey}
              onChange={(e) => setBaseKey(e.target.value)}
            >
              <option value="">Sem base (linha zerada)</option>
              {bases.map((b) => (
                <option key={`${b.tipo}-${b.id}`} value={`${b.tipo}:${b.id}`}>
                  {b.descricao} ({b.tipo === "Orcamento" ? "Orçamento" : "Forecast"})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {tipo === "VENDAS" ? "Plano de venda" : "Plano financeiro"}
            </label>
            <SearchableSelect
              options={planos.map((p) => ({
                id: p.id,
                label: p.db_id ? `${p.db_id} - ${p.nome}` : p.nome,
              }))}
              value={planoId}
              onChange={(val) => setPlanoId(Number(val))}
              placeholder="Pesquise ou selecione..."
            />
          </div>
          {(!produtos.length || !planos.length) && (
            <p className="text-sm text-brand-orange">
              O departamento não tem empreendimento ou plano vinculado. Confira em Apoio → Departamentos.
            </p>
          )}
        </div>
        <div className="flex justify-end gap-2 pt-5">
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={confirmar} disabled={saving}>{saving ? "Criando..." : "Criar"}</Button>
        </div>
      </div>
    </div>
  );
}
