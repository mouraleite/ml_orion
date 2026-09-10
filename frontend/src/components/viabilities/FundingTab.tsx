"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useUnsavedChanges } from "@/contexts/UnsavedChangesContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Save, Info } from "lucide-react";

interface FundingTabProps {
  phaseId: number;
  isReadonly?: boolean;
}

export function FundingTab({ phaseId, isReadonly }: FundingTabProps) {
  const [data, setData] = useState<any>({
    tipo_funding: "Plano Empresarial (Banco)",
    percentual_obra_financiado: 0.0,
    modo_volume: "percentual",
    volume_fixo: 0.0,
    taxa_juros: 0.0,
    indexador: "CDI",
    prazo_meses: 36,
    securitizadora: "Opea",
    estrutura_cri: "Guarda-Chuva",
    icvm: "ICVM 400",
    gross_up: 9.65,
    taxa_estruturacao: 0.0,
    diluir_custos: false,
    sistema_amortizacao_banco: "SAC",
  });
  
  const { setHasUnsavedChanges } = useUnsavedChanges();
  const [initialData, setInitialData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [securitizadorasDisponiveis, setSecuritizadorasDisponiveis] = useState<string[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [res, settingsRes] = await Promise.all([
          api.get(`/viabilities/phases/${phaseId}/funding`),
          api.get(`/apoio/system-settings/funding_rates`).catch(() => ({ data: { value: {} } }))
        ]);
        
        const result = res.data || {};
        const rates = settingsRes.data?.value || {};
        const secKeys = Object.keys(rates.Securitizadoras || {
          "Opea": {}, 
          "Vórtx (Não Guarda-Chuva)": {}, 
          "Vórtx (Guarda-Chuva)": {}, 
          "Oliveira Trust (Guarda-Chuva)": {}
        });
        setSecuritizadorasDisponiveis(secKeys);

        const mergedData = {
          tipo_funding: result.tipo_funding || "Plano Empresarial (Banco)",
          percentual_obra_financiado: result.percentual_obra_financiado || 0.0,
          modo_volume: result.modo_volume || "percentual",
          volume_fixo: result.volume_fixo || 0.0,
          taxa_juros: result.taxa_juros || 0.0,
          indexador: result.indexador || "CDI",
          prazo_meses: result.prazo_meses || 36,
          securitizadora: result.securitizadora || "Opea",
          estrutura_cri: result.estrutura_cri || "Guarda-Chuva",
          icvm: result.icvm || "ICVM 400",
          gross_up: result.gross_up || 9.65,
          taxa_estruturacao: result.taxa_estruturacao || 0.0,
          diluir_custos: result.diluir_custos || false,
          sistema_amortizacao_banco: result.sistema_amortizacao_banco || "SAC",
        };
        setData(mergedData);
        setInitialData(mergedData);
      } catch (e) {
        console.error(e);
      }
    };
    fetchData();
  }, [phaseId]);

  useEffect(() => {
    if (initialData && data) {
      const isDirty = JSON.stringify(initialData) !== JSON.stringify(data);
      setHasUnsavedChanges(isDirty);
    }
  }, [data, initialData, setHasUnsavedChanges]);

  const handleSave = async () => {
    setIsLoading(true);
    setMessage("");
    try {
      await api.put(`/viabilities/phases/${phaseId}/funding`, data);
      setMessage("Funding salvo com sucesso!");
      setInitialData(data);
      setHasUnsavedChanges(false);
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      alert("Erro ao salvar funding.");
    } finally {
      setIsLoading(false);
    }
  };

  const hasFunding = data.tipo_funding !== "Nenhum";
  const isCriCra = data.tipo_funding === "CRI";

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-300">
      
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Funding / Plano Empresarial</h2>
          <p className="text-sm text-slate-500">Defina as condições de captação e estruturação para viabilizar a obra.</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-lg border border-slate-200 shadow-sm mr-4">
            <span className="text-sm font-bold text-slate-700">Possui Captação/Funding?</span>
            <button 
              onClick={() => {
                if (isReadonly) return;
                if (hasFunding) {
                  setData({...data, tipo_funding: "Nenhum", percentual_obra_financiado: 0, volume_fixo: 0});
                } else {
                  setData({...data, tipo_funding: "Plano Empresarial (Banco)"});
                }
              }}
              className={`w-12 h-6 rounded-full transition-colors relative ${hasFunding ? "bg-ml-green" : "bg-slate-300"}`}
            >
              <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${hasFunding ? "translate-x-7" : "translate-x-1"}`} />
            </button>
          </div>

          {message && <span className="text-sm text-green-600 font-medium">{message}</span>}
          <Button onClick={handleSave} disabled={isLoading || isReadonly} className="bg-ml-green hover:bg-ml-dark text-white flex items-center gap-2">
            <Save className="w-4 h-4" />
            {isLoading ? "Salvando..." : "Salvar Funding"}
          </Button>
        </div>
      </div>

      {hasFunding ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 animate-in slide-in-from-bottom-4">
        
        {/* LADO ESQUERDO: PARAMETROS PRINCIPAIS */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
            <h3 className="text-base font-bold text-slate-900 border-b pb-2">Tipo de Captação</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Modalidade de Funding</label>
                <select 
                  className="ml-select"
                  value={data.tipo_funding}
                  disabled={isReadonly}
                  onChange={(e) => setData({ ...data, tipo_funding: e.target.value })}
                >
                  <option value="Plano Empresarial (Banco)">Plano Empresarial (Banco)</option>
                  <option value="CRI">CRI</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Modo de Cálculo do Volume</label>
                <div className="flex items-center bg-slate-100 p-1 rounded-lg">
                  <button 
                    onClick={() => !isReadonly && setData({...data, modo_volume: "percentual"})}
                    className={`flex-1 text-xs py-2 px-3 rounded-md font-medium transition-colors ${data.modo_volume === "percentual" ? "bg-white text-slate-900 shadow" : "text-slate-500 hover:text-slate-700"}`}
                  >
                    % da Obra
                  </button>
                  <button 
                    onClick={() => !isReadonly && setData({...data, modo_volume: "fixo"})}
                    className={`flex-1 text-xs py-2 px-3 rounded-md font-medium transition-colors ${data.modo_volume === "fixo" ? "bg-white text-slate-900 shadow" : "text-slate-500 hover:text-slate-700"}`}
                  >
                    Valor Fixo
                  </button>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              {data.modo_volume === "percentual" ? (
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-700">Percentual da Obra (%)</label>
                  <div className="relative">
                    <span className="absolute right-3 top-2.5 text-slate-500 font-medium">%</span>
                    <Input 
                      type="number" step="0.1"
                      className="font-medium pr-8"
                      value={data.percentual_obra_financiado}
                      disabled={isReadonly}
                      onChange={(e) => setData({ ...data, percentual_obra_financiado: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-700">Volume (R$)</label>
                  <div className="relative">
                    <span className="absolute left-3 top-2.5 text-slate-500 font-medium">R$</span>
                    <Input 
                      type="number" step="1000"
                      className="font-medium pl-8"
                      value={data.volume_fixo}
                      disabled={isReadonly}
                      onChange={(e) => setData({ ...data, volume_fixo: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                </div>
              )}

              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Taxa de Juros (% a.a.)</label>
                <div className="relative">
                  <span className="absolute right-3 top-2.5 text-slate-500 font-medium">%</span>
                  <Input 
                    type="number" step="0.01"
                    className="font-medium pr-8"
                    value={data.taxa_juros}
                    disabled={isReadonly}
                    onChange={(e) => setData({ ...data, taxa_juros: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>
              
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Indexador</label>
                <select 
                  className="ml-select"
                  value={data.indexador}
                  disabled={isReadonly}
                  onChange={(e) => setData({ ...data, indexador: e.target.value })}
                >
                  <option value="CDI">CDI</option>
                  <option value="TR">TR</option>
                  <option value="IPCA">IPCA</option>
                  <option value="Nenhum">Pré-Fixado (Nenhum)</option>
                </select>
              </div>

              {!isCriCra && (
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-700">Sistema de Amortização</label>
                  <select 
                    className="ml-select"
                    value={data.sistema_amortizacao_banco}
                    disabled={isReadonly}
                    onChange={(e) => setData({ ...data, sistema_amortizacao_banco: e.target.value })}
                  >
                    <option value="SAC">SAC</option>
                    <option value="Price">Price</option>
                    <option value="Bullet">Bullet (Final)</option>
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* SESSÃO CRI/CRA ESPECÍFICA */}
          {isCriCra && (
            <div className="bg-slate-50 p-6 rounded-xl border border-slate-200 shadow-sm space-y-6 animate-in slide-in-from-top-4">
              <h3 className="text-base font-bold text-slate-900 border-b pb-2 flex items-center justify-between">
                <span>Estruturação do {data.tipo_funding}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-normal">Diluir custos nas Obras?</span>
                  <button 
                    onClick={() => !isReadonly && setData({...data, diluir_custos: !data.diluir_custos})}
                    className={`w-11 h-6 rounded-full transition-colors relative ${data.diluir_custos ? "bg-ml-green" : "bg-slate-300"}`}
                  >
                    <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${data.diluir_custos ? "translate-x-6" : "translate-x-1"}`} />
                  </button>
                </div>
              </h3>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="space-y-2 col-span-2">
                  <label className="text-sm font-medium text-slate-700">Securitizadora</label>
                  <select 
                    className="ml-select"
                    value={data.securitizadora}
                    disabled={isReadonly}
                    onChange={(e) => setData({ ...data, securitizadora: e.target.value })}
                  >
                    {securitizadorasDisponiveis.map(sec => (
                      <option key={sec} value={sec}>{sec}</option>
                    ))}
                  </select>
                </div>
                
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Instrução CVM</label>
                  <select 
                    className="ml-select"
                    value={data.icvm}
                    disabled={isReadonly}
                    onChange={(e) => setData({ ...data, icvm: e.target.value })}
                  >
                    <option value="ICVM 400">ICVM 400</option>
                    <option value="ICVM 476">ICVM 476</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Prazo (Meses)</label>
                  <Input 
                    type="number"
                    value={data.prazo_meses}
                    disabled={isReadonly}
                    onChange={(e) => setData({ ...data, prazo_meses: parseInt(e.target.value) || 36 })}
                  />
                </div>

                <div className="space-y-2 col-span-2">
                  <label className="text-sm font-medium text-slate-700 flex items-center gap-1">
                    Taxa Estruturação Extra (%) <Info className="w-3 h-3 text-slate-400" />
                  </label>
                  <div className="relative">
                    <span className="absolute right-3 top-2.5 text-slate-500 font-medium">%</span>
                    <Input 
                      type="number" step="0.01"
                      className="pr-8"
                      value={data.taxa_estruturacao}
                      disabled={isReadonly}
                      onChange={(e) => setData({ ...data, taxa_estruturacao: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                </div>

                <div className="space-y-2 col-span-2">
                  <label className="text-sm font-medium text-slate-700">Gross Up Prestador (%)</label>
                  <div className="relative">
                    <span className="absolute right-3 top-2.5 text-slate-500 font-medium">%</span>
                    <Input 
                      type="number" step="0.01"
                      className="pr-8"
                      value={data.gross_up}
                      disabled={isReadonly}
                      onChange={(e) => setData({ ...data, gross_up: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                </div>

              </div>
            </div>
          )}
        </div>

        {/* LADO DIREITO: CARD DE RESUMO */}
        <div className="space-y-6">
          <div className="bg-slate-900 text-white rounded-xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute -right-10 -top-10 w-40 h-40 bg-white/10 rounded-full blur-2xl pointer-events-none" />
            
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 mb-6">
              Simulador de {data.tipo_funding}
            </h3>

            {isCriCra ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center text-sm border-b border-slate-700 pb-2">
                  <span className="text-slate-400">Taxa CVM</span>
                  <span className="font-medium text-slate-200">Auto (Tabela)</span>
                </div>
                <div className="flex justify-between items-center text-sm border-b border-slate-700 pb-2">
                  <span className="text-slate-400">Taxa ANBIMA</span>
                  <span className="font-medium text-slate-200">Auto (Tabela)</span>
                </div>
                <div className="flex justify-between items-center text-sm border-b border-slate-700 pb-2">
                  <span className="text-slate-400">Registro B3</span>
                  <span className="font-medium text-slate-200">Auto (Escalonada)</span>
                </div>
                <div className="flex justify-between items-center text-sm border-b border-slate-700 pb-2">
                  <span className="text-slate-400">Agente Fiduciário</span>
                  <span className="font-medium text-slate-200">Auto ({data.securitizadora})</span>
                </div>
                
                <div className="pt-4 space-y-2">
                  <div className="p-3 bg-slate-800 rounded-lg flex items-start gap-3">
                    <Info className="w-5 h-5 text-ml-green shrink-0 mt-0.5" />
                    <p className="text-xs text-slate-300 leading-relaxed">
                      O motor matemático lerá automaticamente as tabelas de taxas cadastradas em <strong className="text-white">Apoio &gt; Taxas de Funding</strong>. Todos os custos fixos (upfront) e recorrentes (mensais/anuais) entrarão na DRE conforme sua parametrização.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-slate-400">
                  Operação bancária tradicional baseada em juros compostos da taxa de {data.taxa_juros}% a.a + {data.indexador}.
                </p>
                <div className="pt-4 border-t border-slate-700 mt-4">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-400">Taxa Equivalente Mensal</span>
                    <span className="font-medium text-slate-200">
                      {(((1 + data.taxa_juros / 100) ** (1/12) - 1) * 100).toFixed(2)}% a.m.
                    </span>
                  </div>
                </div>
              </div>
            )}
            
          </div>
        </div>

        </div>
      ) : (
        <div className="flex flex-col items-center justify-center p-12 bg-slate-50 border border-slate-200 border-dashed rounded-xl space-y-4">
          <div className="w-16 h-16 bg-slate-200 rounded-full flex items-center justify-center mb-2">
            <span className="text-2xl">🏦</span>
          </div>
          <h3 className="text-lg font-bold text-slate-700">Operação 100% com Capital Próprio</h3>
          <p className="text-slate-500 text-center max-w-md">
            Esta viabilidade não utilizará Funding ou Plano Empresarial. Todo o custo da obra será suportado pelo fluxo de caixa do projeto e/ou capital dos sócios.
          </p>
        </div>
      )}
    </div>
  );
}
