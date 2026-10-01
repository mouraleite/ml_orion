"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { forecastService, BaseForecastResponse } from "@/services/forecast";
import { GitCommit, Clock, FileText, CheckCircle, Lock, AlertCircle, RefreshCw, Trash2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { isAdminUser, isGestorUser, canWriteModule } from "@/lib/roles";

const statusColors: Record<string, string> = {
  "Rascunho": "bg-slate-100 text-slate-700 border-slate-200",
  "Em aprovação": "bg-yellow-100 text-yellow-700 border-yellow-200",
  "Aprovado": "bg-green-100 text-green-700 border-green-200",
  "Fechado": "bg-blue-100 text-blue-700 border-blue-200",
  "Reaberto": "bg-purple-100 text-purple-700 border-purple-200",
  "Solicitação Reabertura": "bg-orange-100 text-orange-700 border-orange-200",
};

interface ForecastVersionHeaderProps {
  forecast: BaseForecastResponse | null;
  deptId: number;
  onStatusChanged: () => void;
}

export function ForecastVersionHeader({ forecast, deptId, onStatusChanged }: ForecastVersionHeaderProps) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  
  if (!forecast) return null;
  if (forecast.is_empty) return null; // Não mostra o header se não há forecast criado (apenas opções base)

  const isAdminUserFlag = isAdminUser(user);
  const podeAprovar = isGestorUser(user) && canWriteModule(user, "Forecast");
  
  const handleStatusChange = async (novoStatus: string, confirmacao?: string) => {
    if (!(await confirmDialog(confirmacao || `Tem certeza que deseja alterar o status para ${novoStatus}?`, {
      title: "Alterar status",
      confirmLabel: "Confirmar",
    }))) return;
    setLoading(true);
    try {
      await forecastService.changeStatus(forecast.forecast_id, deptId, novoStatus);
      onStatusChanged();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Erro ao alterar status");
    } finally {
      setLoading(false);
    }
  };

  const handleSolicitarReabertura = async () => {
    const motivo = window.prompt("Por favor, informe o motivo da solicitação de reabertura:");
    if (!motivo) return;
    setLoading(true);
    try {
      await forecastService.solicitarReabertura(forecast.forecast_id, deptId, motivo);
      onStatusChanged();
      alert("Solicitação enviada aos administradores!");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Erro ao solicitar reabertura");
    } finally {
      setLoading(false);
    }
  };

  const handleAprovarReabertura = async () => {
    if (!(await confirmDialog("Aprovar a reabertura edita este mesmo forecast. Uma cópia do estado fechado fica guardada. Deseja continuar?", {
      title: "Aprovar reabertura",
      confirmLabel: "Aprovar",
    }))) return;
    setLoading(true);
    try {
      await forecastService.aprovarReabertura(forecast.forecast_id, deptId);
      onStatusChanged();
      alert("Reabertura aprovada. Este mesmo forecast ficou editável; o acompanhamento permanece com os valores fechados.");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Erro ao aprovar reabertura");
    } finally {
      setLoading(false);
    }
  };

  const handleDestravar = async () => {
    if (!(await confirmDialog("Deseja forçar o destravamento deste forecast? O outro usuário poderá perder as edições não salvas.", {
      title: "Forçar destravamento",
      confirmLabel: "Destravar",
      variant: "danger",
    }))) return;
    setLoading(true);
    try {
      await forecastService.destravarForecast(forecast.forecast_id, deptId);
      onStatusChanged();
      alert("Forecast destravado com sucesso!");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Erro ao destravar forecast");
    } finally {
      setLoading(false);
    }
  };

  const handleExcluir = async () => {
    if (!(await confirmDialog("Deseja realmente excluir este Forecast permanentemente? Todos os dados orçados nesta versão serão perdidos.", {
      title: "Excluir forecast",
      variant: "danger",
    }))) return;
    setLoading(true);
    try {
      await forecastService.excluirForecast(forecast.forecast_id, deptId);
      // Recarrega os dados limpando a visão atual
      onStatusChanged();
      alert("Forecast excluído com sucesso!");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Erro ao excluir forecast");
    } finally {
      setLoading(false);
    }
  };

  const colorClass = statusColors[forecast.status] || statusColors["Rascunho"];

  return (
    <div className="bg-white border rounded-lg shadow-sm p-4 mb-6 flex flex-col gap-4">
      <div className="flex justify-between items-start">
        <div className="flex gap-4 items-center">
          <div className="h-10 w-10 bg-slate-100 rounded-full flex items-center justify-center text-slate-500">
            <GitCommit size={20} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              Forecast de {forecast.tipo === "DESPESAS" ? "Despesas" : "Vendas"} {forecast.ano}
              <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${colorClass}`}>
                {forecast.status === "Importado Sienge" ? "Base Inicial" : forecast.status}
              </span>
            </h2>
            <div className="flex items-center gap-4 text-xs text-slate-500 mt-1">
              <span className="flex items-center gap-1"><FileText size={12}/> v{forecast.versao_numero}</span>
              <span className="flex items-center gap-1"><Clock size={12}/> {forecast.data_criacao ? new Date(forecast.data_criacao).toLocaleDateString() : "N/A"}</span>
            </div>
          </div>
        </div>

        {/* Workflow Actions */}
        <div className="flex gap-2">
          {forecast.status === "Rascunho" || forecast.status === "Reaberto" ? (
            <Button size="sm" variant="outline" onClick={() => handleStatusChange("Em aprovação", "Enviar este forecast para aprovação?")} disabled={loading}>
              Enviar para Aprovação
            </Button>
          ) : null}

          {forecast.status === "Em aprovação" && podeAprovar ? (
            <>
              <Button size="sm" variant="outline" className="text-red-600 border-red-200 hover:bg-red-50" onClick={() => handleStatusChange("Rascunho", "Rejeitar e devolver ao rascunho?")} disabled={loading}>
                Rejeitar
              </Button>
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => handleStatusChange("Fechado", "Aprovar e fechar este forecast?")} disabled={loading}>
                <CheckCircle size={14} className="mr-1" /> Aprovar
              </Button>
            </>
          ) : null}

          {(forecast.status === "Fechado" || forecast.status === "Aprovado") ? (
            <Button size="sm" variant="outline" onClick={handleSolicitarReabertura} disabled={loading}>
              <RefreshCw size={14} className="mr-1" /> Solicitar Reabertura
            </Button>
          ) : null}

          {forecast.status === "Solicitação Reabertura" && isAdminUserFlag ? (
            <div className="flex items-center gap-2 border-l pl-2 border-slate-200">
              <span className="text-xs font-semibold text-orange-600">Aprovar Reabertura?</span>
              <Button size="sm" variant="outline" onClick={() => handleStatusChange("Fechado")} disabled={loading}>Não</Button>
              <Button size="sm" className="bg-orange-600 hover:bg-orange-700 text-white" onClick={handleAprovarReabertura} disabled={loading}>Sim, reabrir</Button>
            </div>
          ) : null}

          {podeAprovar && (forecast.status === "Rascunho" || forecast.status === "Reaberto") ? (
            <Button size="sm" variant="outline" className="text-red-600 border-red-200 hover:bg-red-50 ml-2" onClick={handleExcluir} disabled={loading} title="Excluir Forecast permanentemente">
              <Trash2 size={14} className="mr-1" /> Excluir
            </Button>
          ) : null}
        </div>
      </div>
      
      {forecast.motivo_reabertura && (
        <div className="bg-orange-50 border border-orange-100 rounded p-3 text-sm flex gap-2 items-start text-orange-800">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <div>
            <strong>Motivo da Reabertura:</strong> {forecast.motivo_reabertura}
          </div>
        </div>
      )}

      {forecast.is_locked_by_other && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm flex justify-between items-center text-red-800">
          <div className="flex gap-2 items-center">
            <Lock size={16} className="shrink-0" />
            <span>
              <strong>Forecast em edição:</strong> Bloqueado por {forecast.usuario_edicao_nome}. Apenas visualização.
            </span>
          </div>
          {isAdminUserFlag && (
            <Button size="sm" variant="outline" className="bg-white text-red-600 border-red-200 hover:bg-red-100" onClick={handleDestravar} disabled={loading}>
              Forçar Destravamento
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
