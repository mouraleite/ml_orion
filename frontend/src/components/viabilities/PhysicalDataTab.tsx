"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { useUnsavedChanges } from "@/contexts/UnsavedChangesContext";
import { apoioService } from "@/services/apoio";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

interface PhasePhysicalData {
  codigo_projeto: string;
  tipo_projeto: string;
  cenario: string;
  area_total: number;
  area_lotes_residenciais: number;
  area_lotes_comerciais: number;
  area_lotes_mistos: number;
  area_sistema_viario: number;
  area_institucional: number;
  area_verde: number;
  sistema_lazer: number;
  area_associacao: number;
  qtde_lotes_residenciais: number;
  qtde_lotes_comerciais: number;
  qtde_lotes_mistos: number;
  valor_venda_residencial_m2: number;
  valor_venda_comercial_m2: number;
  valor_venda_misto_m2: number;
}



const AreaInput = ({ 
  label, 
  value, 
  onChange, 
  totalArea, 
  disabled,
  isInformative
}: { 
  label: string; 
  value: number; 
  onChange: (val: number) => void; 
  totalArea?: number; 
  disabled?: boolean;
  isInformative?: boolean;
}) => {
  const [displayValue, setDisplayValue] = useState(value ? value.toLocaleString("pt-BR") : "");

  useEffect(() => {
    // Only update if the actual numeric value changed and the input is not actively being edited
    if (value !== parseFloat(displayValue.replace(/\./g, "").replace(",", "."))) {
      setDisplayValue(value ? value.toLocaleString("pt-BR") : "");
    }
  }, [value]);

  const handleBlur = () => {
    const parsed = parseFloat(displayValue.replace(/\./g, "").replace(",", ".")) || 0;
    onChange(parsed);
    setDisplayValue(parsed ? parsed.toLocaleString("pt-BR") : "");
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/[^\d.,]/g, '');
    setDisplayValue(val);
  };

  const percentage = (totalArea && value) ? ((value / totalArea) * 100).toFixed(1) + "%" : null;

  return (
    <div className={isInformative ? "p-2 bg-orange-50/50 rounded-lg border border-orange-100/50" : ""}>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <div className="relative">
        <input
          type="text"
          value={displayValue}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={disabled}
          className={`ml-input ${percentage ? 'pr-16' : ''}`}
        />
        {percentage && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
            {percentage}
          </div>
        )}
      </div>
    </div>
  );
};

export default function PhysicalDataTab({
  phaseId,
  isReadonly,
  projectId,
  initialProjectName,
  initialCity,
  onProjectUpdate
}: {
  phaseId: number | null;
  isReadonly?: boolean;
  projectId?: number;
  initialProjectName?: string;
  initialCity?: string;
  onProjectUpdate?: (data: any) => void;
}) {
  const [data, setData] = useState<PhasePhysicalData | null>(null);
  const { setHasUnsavedChanges } = useUnsavedChanges();
  const [initialData, setInitialData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [scenarios, setScenarios] = useState<any[]>([]);

  const [projectName, setProjectName] = useState(initialProjectName || "");
  const [city, setCity] = useState(initialCity || "");

  useEffect(() => {
    if (initialProjectName) setProjectName(initialProjectName);
    if (initialCity) setCity(initialCity);
  }, [initialProjectName, initialCity]);

  const loadScenarios = async () => {
    try {
      const data = await apoioService.getCenarios();
      setScenarios(data);
    } catch (error) {
      console.error("Erro ao carregar cenários", error);
    }
  };

  useEffect(() => {
    if (phaseId) {
      loadData();
    }
    loadScenarios();
  }, [phaseId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/viabilities/phases/${phaseId}/physical_data`);
      setData(response.data);
      setInitialData(response.data);
    } catch (error) {
      console.error("Erro ao carregar dados físicos", error);
    } finally {
      setLoading(false);
    }
  };



  const handleChange = (field: keyof PhasePhysicalData, value: any) => {
    if (!data || isReadonly) return;
    setData({ ...data, [field]: value });
  };

  
  useEffect(() => {
    if (initialData && data) {
      const isDirty = JSON.stringify(initialData) !== JSON.stringify(data) || projectName !== initialProjectName || city !== initialCity;
      setHasUnsavedChanges(isDirty);
    }
  }, [data, initialData, projectName, city, initialProjectName, initialCity, setHasUnsavedChanges]);

  const handleSave = async () => {
    if (!phaseId || !data) return;
    try {
      setSaving(true);
      await api.put(`/viabilities/phases/${phaseId}/physical_data`, data);
      
      // Update Viability project name and city
      if (projectId && (projectName !== initialProjectName || city !== initialCity)) {
        await api.put(`/viabilities/${projectId}`, { project_name: projectName, city: city });
        if (onProjectUpdate) {
          onProjectUpdate({ project_name: projectName, city: city });
        }
      }

      setInitialData(data);
      setHasUnsavedChanges(false);
      alert("Dados físicos salvos com sucesso!");
    } catch (error) {
      console.error("Erro ao salvar dados físicos", error);
      alert("Erro ao salvar.");
    } finally {
      setSaving(false);
    }
  };

  if (loading || !data) return <AppLoadingState />;

  const sumAreas = (data.area_lotes_residenciais || 0) +
    (data.area_lotes_comerciais || 0) +
    (data.area_lotes_mistos || 0) +
    (data.area_sistema_viario || 0) +
    (data.area_institucional || 0) +
    (data.area_verde || 0) +
    (data.sistema_lazer || 0) +
    (data.area_associacao || 0);
  
  const diffAreas = (data.area_total || 0) - sumAreas;
  const isAreasBalanced = Math.abs(diffAreas) < 0.1;

  return (
    <div className="p-6 space-y-8">
      {/* 1. CONFIGURAÇÕES GERAIS */}
      <section>
        <h3 className="text-lg font-semibold text-slate-800 mb-4 border-b pb-2">Configurações Gerais</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-slate-700 mb-1">Nome do Empreendimento</label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              disabled={isReadonly}
              className="ml-input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Cidade</label>
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              disabled={isReadonly}
              className="ml-input"
            />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Código do Projeto</label>
            <input
              type="text"
              value={data.codigo_projeto}
              onChange={(e) => handleChange("codigo_projeto", e.target.value)}
              disabled={isReadonly}
              className="ml-input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo de Projeto</label>
            <select
              value={data.tipo_projeto || ""}
              onChange={(e) => {
                if (e.target.value === "NOVO") {
                  const novo = window.prompt("Digite o novo tipo de projeto:");
                  if (novo && novo.trim() !== "") {
                    handleChange("tipo_projeto", novo.trim());
                  }
                } else {
                  handleChange("tipo_projeto", e.target.value);
                }
              }}
              disabled={isReadonly}
              className="ml-select"
            >
              <option value="">Selecione...</option>
              <option value="Aberto">Aberto</option>
              <option value="Aberto Popular">Aberto Popular</option>
              <option value="Loteamento Fechado">Loteamento Fechado</option>
              {data.tipo_projeto && !["Aberto", "Aberto Popular", "Loteamento Fechado", ""].includes(data.tipo_projeto) && (
                <option value={data.tipo_projeto}>{data.tipo_projeto}</option>
              )}
              <option value="NOVO">+ Adicionar Novo Tipo...</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Cenário</label>
            <select
              value={data.cenario || "Neutro"}
              onChange={async (e) => {
                if (e.target.value === "NOVO") {
                  const novo = window.prompt("Digite o novo cenário:");
                  if (novo && novo.trim() !== "") {
                    try {
                      await apoioService.createCenario({ nome: novo.trim() });
                      await loadScenarios();
                    } catch (err) {
                      console.error("Erro ao criar cenário global", err);
                    }
                    handleChange("cenario", novo.trim());
                  }
                } else {
                  handleChange("cenario", e.target.value);
                }
              }}
              disabled={isReadonly}
              className="ml-select"
            >
              {scenarios.map((s, idx) => (
                <option key={idx} value={s.nome}>{s.nome}</option>
              ))}
              {data.cenario && !scenarios.find(s => s.nome === data.cenario) && (
                <option value={data.cenario}>{data.cenario}</option>
              )}
              <option value="NOVO">+ Adicionar Novo Cenário...</option>
            </select>
          </div>
        </div>
      </section>

      {/* 2. PROJETO URBANÍSTICO */}
      <section>
        <h3 className="text-lg font-semibold text-slate-800 mb-4 border-b pb-2">Projeto Urbanístico (m²)</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <AreaInput
            label="Área Total (m²)"
            value={data.area_total}
            onChange={(val) => handleChange("area_total", val)}
            disabled={isReadonly}
          />
          <AreaInput
            label="Lotes Residenciais (m²)"
            value={data.area_lotes_residenciais}
            onChange={(val) => handleChange("area_lotes_residenciais", val)}
            totalArea={data.area_total}
            disabled={isReadonly}
          />
          <AreaInput
            label="Lotes Comerciais (m²)"
            value={data.area_lotes_comerciais || 0}
            onChange={(val) => handleChange("area_lotes_comerciais", val)}
            totalArea={data.area_total}
            disabled={isReadonly}
          />
          <AreaInput
            label="Lotes Mistos (m²)"
            value={data.area_lotes_mistos || 0}
            onChange={(val) => handleChange("area_lotes_mistos", val)}
            totalArea={data.area_total}
            disabled={isReadonly}
          />
          <AreaInput
            label="Sistema Viário (m²)"
            value={data.area_sistema_viario || 0}
            onChange={(val) => handleChange("area_sistema_viario", val)}
            totalArea={data.area_total}
            disabled={isReadonly}
            isInformative={true}
          />
          <AreaInput
            label="Área Institucional (m²)"
            value={data.area_institucional || 0}
            onChange={(val) => handleChange("area_institucional", val)}
            totalArea={data.area_total}
            disabled={isReadonly}
            isInformative={true}
          />
          <AreaInput
            label="Área Verde / APP (m²)"
            value={data.area_verde || 0}
            onChange={(val) => handleChange("area_verde", val)}
            totalArea={data.area_total}
            disabled={isReadonly}
            isInformative={true}
          />
          <AreaInput
            label="Sistema de Lazer (m²)"
            value={data.sistema_lazer || 0}
            onChange={(val) => handleChange("sistema_lazer", val)}
            totalArea={data.area_total}
            disabled={isReadonly}
            isInformative={true}
          />
          <AreaInput
            label="Associação / Não Vendável (m²)"
            value={data.area_associacao || 0}
            onChange={(val) => handleChange("area_associacao", val)}
            totalArea={data.area_total}
            disabled={isReadonly}
            isInformative={true}
          />
        </div>
        <p className="text-xs text-slate-500 mt-2">* Áreas em laranja são apenas informativas e não entram no cálculo do VGV.</p>

        {/* Validação de Áreas */}
        <div className={`mt-4 p-4 rounded-lg border ${isAreasBalanced ? 'bg-emerald-50/50 border-emerald-200' : 'bg-amber-50/50 border-amber-200'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-sm font-semibold ${isAreasBalanced ? 'text-emerald-700' : 'text-amber-700'}`}>
              Validação do Projeto Urbanístico
            </span>
            <span className={`text-sm font-bold flex items-center gap-1 ${isAreasBalanced ? 'text-emerald-600' : 'text-amber-600'}`}>
              {isAreasBalanced ? (
                <>✓ Áreas distribuídas corretamente</>
              ) : (
                <>⚠️ Atenção na distribuição</>
              )}
            </span>
          </div>
          
          <div className="flex justify-between items-end">
            <div className="flex gap-8 text-sm">
              <div>
                <span className="text-slate-500 block text-xs uppercase tracking-wider mb-0.5">Área Total</span>
                <span className="font-semibold text-slate-700">{(data.area_total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m²</span>
              </div>
              <div>
                <span className="text-slate-500 block text-xs uppercase tracking-wider mb-0.5">Soma Distribuída</span>
                <span className="font-semibold text-slate-700">{sumAreas.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m²</span>
              </div>
            </div>
            {!isAreasBalanced && (
              <div className="text-right">
                <span className="text-amber-600/80 block text-xs uppercase tracking-wider mb-0.5">Diferença</span>
                <span className="font-bold text-amber-600">{Math.abs(diffAreas).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m² {diffAreas > 0 ? 'Faltando' : 'Sobrando'}</span>
              </div>
            )}
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* 3. DADOS FÍSICOS (UNIDADES) */}
        <section>
          <h3 className="text-lg font-semibold text-slate-800 mb-4 border-b pb-2">Dados Físicos (Unidades)</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Número de Lotes Residenciais</label>
              <input
                type="number"
                value={data.qtde_lotes_residenciais || ""}
                onChange={(e) => handleChange("qtde_lotes_residenciais", parseInt(e.target.value) || 0)}
                disabled={isReadonly}
                className="ml-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Número de Lotes Comerciais</label>
              <input
                type="number"
                value={data.qtde_lotes_comerciais || ""}
                onChange={(e) => handleChange("qtde_lotes_comerciais", parseInt(e.target.value) || 0)}
                disabled={isReadonly}
                className="ml-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Número de Lotes Mistos</label>
              <input
                type="number"
                value={data.qtde_lotes_mistos || ""}
                onChange={(e) => handleChange("qtde_lotes_mistos", parseInt(e.target.value) || 0)}
                disabled={isReadonly}
                className="ml-input"
              />
            </div>
            <div className="bg-ml-green/10 p-3 rounded-lg border border-ml-green/20 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-700">Total de Lotes:</span>
                <span className="font-semibold text-ml-green">{(data.qtde_lotes_residenciais || 0) + (data.qtde_lotes_comerciais || 0) + (data.qtde_lotes_mistos || 0)}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-2 border-t border-ml-green/10">
                <div className="space-y-1">
                  <span className="text-xs font-semibold text-slate-500 uppercase block mb-1">Área Média</span>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-600">Residencial:</span>
                    <span className="font-semibold">{data.qtde_lotes_residenciais > 0 ? ((data.area_lotes_residenciais || 0) / data.qtde_lotes_residenciais).toFixed(2) : 0} m²</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-600">Comercial:</span>
                    <span className="font-semibold">{data.qtde_lotes_comerciais > 0 ? ((data.area_lotes_comerciais || 0) / data.qtde_lotes_comerciais).toFixed(2) : 0} m²</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-600">Misto:</span>
                    <span className="font-semibold">{data.qtde_lotes_mistos > 0 ? ((data.area_lotes_mistos || 0) / data.qtde_lotes_mistos).toFixed(2) : 0} m²</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <span className="text-xs font-semibold text-slate-500 uppercase block mb-1">Ticket Médio</span>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-600">Residencial:</span>
                    <span className="font-semibold">{new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(data.qtde_lotes_residenciais > 0 ? ((data.area_lotes_residenciais || 0) * (data.valor_venda_residencial_m2 || 0)) / data.qtde_lotes_residenciais : 0)}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-600">Comercial:</span>
                    <span className="font-semibold">{new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(data.qtde_lotes_comerciais > 0 ? ((data.area_lotes_comerciais || 0) * (data.valor_venda_comercial_m2 || 0)) / data.qtde_lotes_comerciais : 0)}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-600">Misto:</span>
                    <span className="font-semibold">{new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(data.qtde_lotes_mistos > 0 ? ((data.area_lotes_mistos || 0) * (data.valor_venda_misto_m2 || 0)) / data.qtde_lotes_mistos : 0)}</span>
                  </div>
                </div>
              </div>
              <div className="flex justify-between text-sm font-bold pt-2 border-t border-ml-green/20">
                <span className="text-slate-800">Ticket Médio Geral:</span>
                <span className="text-ml-green">
                  {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(
                    ((data.qtde_lotes_residenciais || 0) + (data.qtde_lotes_comerciais || 0) + (data.qtde_lotes_mistos || 0)) > 0 
                      ? (((data.area_lotes_residenciais || 0) * (data.valor_venda_residencial_m2 || 0)) + 
                         ((data.area_lotes_comerciais || 0) * (data.valor_venda_comercial_m2 || 0)) + 
                         ((data.area_lotes_mistos || 0) * (data.valor_venda_misto_m2 || 0))) / 
                        ((data.qtde_lotes_residenciais || 0) + (data.qtde_lotes_comerciais || 0) + (data.qtde_lotes_mistos || 0))
                      : 0
                  )}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* 4. DADOS FINANCEIROS (PREMISSAS BASE) */}
        <section>
          <h3 className="text-lg font-semibold text-slate-800 mb-4 border-b pb-2">Dados Financeiros (Premissas)</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Valor Venda Residencial (R$/m²)</label>
              <input
                type="number"
                value={data.valor_venda_residencial_m2 || ""}
                onChange={(e) => handleChange("valor_venda_residencial_m2", parseFloat(e.target.value) || 0)}
                disabled={isReadonly}
                className="ml-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Valor Venda Comercial (R$/m²)</label>
              <input
                type="number"
                value={data.valor_venda_comercial_m2 || ""}
                onChange={(e) => handleChange("valor_venda_comercial_m2", parseFloat(e.target.value) || 0)}
                disabled={isReadonly}
                className="ml-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Valor Venda Misto (R$/m²)</label>
              <input
                type="number"
                value={data.valor_venda_misto_m2 || ""}
                onChange={(e) => handleChange("valor_venda_misto_m2", parseFloat(e.target.value) || 0)}
                disabled={isReadonly}
                className="ml-input"
              />
            </div>
            <div className="bg-ml-green/10 p-3 rounded border border-ml-green/30">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-700">VGV Residencial Base:</span>
                <span className="font-semibold text-ml-green">
                  {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
                    .format((data.area_lotes_residenciais || 0) * (data.valor_venda_residencial_m2 || 0))}
                </span>
              </div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-700">VGV Comercial Base:</span>
                <span className="font-semibold text-ml-green">
                  {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
                    .format((data.area_lotes_comerciais || 0) * (data.valor_venda_comercial_m2 || 0))}
                </span>
              </div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-700">VGV Misto Base:</span>
                <span className="font-semibold text-ml-green">
                  {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
                    .format((data.area_lotes_mistos || 0) * (data.valor_venda_misto_m2 || 0))}
                </span>
              </div>
              <div className="flex justify-between text-base font-bold mt-2 pt-2 border-t border-ml-green/20">
                <span className="text-slate-800">VGV Total Base:</span>
                <span className="text-ml-green">
                  {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
                    .format(((data.area_lotes_residenciais || 0) * (data.valor_venda_residencial_m2 || 0)) + 
                            ((data.area_lotes_comerciais || 0) * (data.valor_venda_comercial_m2 || 0)) +
                            ((data.area_lotes_mistos || 0) * (data.valor_venda_misto_m2 || 0)))}
                </span>
              </div>
            </div>
          </div>
        </section>
      </div>

      {!isReadonly && (
        <div className="flex justify-end pt-4 border-t mt-6">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2.5 bg-brand-green text-white font-semibold rounded-md hover:bg-brand-dark-green disabled:opacity-50 transition-colors"
          >
            {saving ? "Salvando..." : "Salvar Dados Físicos"}
          </button>
        </div>
      )}
    </div>
  );
}
