"use client";

import React, { useState } from "react";

import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { OrcamentoBaseResponse, orcamentoService } from "@/services/orcamento";
import { GitCommit, Clock, User, FileText, CheckCircle, Lock, AlertCircle, RefreshCw } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { isAdminUser, isGestorUser, canWriteModule } from "@/lib/roles";

interface VersionHeaderProps {
  orcamento: OrcamentoBaseResponse | null;
  deptId: number;
  onStatusChanged: () => void;
}

const statusColors: Record<string, string> = {
  "Rascunho": "bg-slate-100 text-slate-700 border-slate-200",
  "Em aprovação": "bg-yellow-100 text-yellow-700 border-yellow-200",
  "Aprovado": "bg-brand-green/10 text-brand-dark-green border-brand-green-light",
  "Fechado": "bg-slate-100 text-slate-700 border-slate-200",
  "Reaberto": "bg-brand-orange-light/30 text-brand-orange border-brand-orange-light",
  "Solicitação Reabertura": "bg-orange-100 text-orange-700 border-orange-200",
};

export function VersionHeader({ orcamento, deptId, onStatusChanged }: VersionHeaderProps) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  
  if (!orcamento) return null;

  const isAdminUserFlag = isAdminUser(user);
  const podeAprovar = isGestorUser(user) && canWriteModule(user, "Orçamento");
  
  const handleStatusChange = async (novoStatus: string, confirmacao?: string) => {
    if (!(await confirmDialog(confirmacao || `Tem certeza que deseja alterar o status para ${novoStatus}?`, {
      title: "Alterar status",
      confirmLabel: "Confirmar",
    }))) return;
    setLoading(true);
    try {
      await orcamentoService.changeStatus(orcamento.orcamento_id, deptId, novoStatus);
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
      await orcamentoService.solicitarReabertura(orcamento.orcamento_id, deptId, motivo);
      onStatusChanged();
      alert("Solicitação enviada aos administradores!");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Erro ao solicitar reabertura");
    } finally {
      setLoading(false);
    }
  };

  const handleAprovarReabertura = async () => {
    if (!(await confirmDialog("Aprovar a reabertura irá criar uma NOVA VERSÃO do orçamento ligada a esta. Deseja continuar?", {
      title: "Aprovar reabertura",
      confirmLabel: "Aprovar",
    }))) return;
    setLoading(true);
    try {
      await orcamentoService.aprovarReabertura(orcamento.orcamento_id, deptId);
      onStatusChanged();
      alert("Reabertura aprovada! Nova versão gerada.");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Erro ao aprovar reabertura");
    } finally {
      setLoading(false);
    }
  };

  const handleDestravar = async () => {
    if (!(await confirmDialog("Deseja forçar o destravamento deste orçamento? O outro usuário poderá perder as edições não salvas.", {
      title: "Forçar destravamento",
      confirmLabel: "Destravar",
      variant: "danger",
    }))) return;
    setLoading(true);
    try {
      await orcamentoService.destravarOrcamento(orcamento.orcamento_id, deptId);
      onStatusChanged();
      alert("Orçamento destravado com sucesso!");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Erro ao destravar orçamento");
    } finally {
      setLoading(false);
    }
  };

  const colorClass = statusColors[orcamento.status] || statusColors["Rascunho"];

  return (
    <div className="bg-white border rounded-lg shadow-sm p-4 mb-6 flex flex-col gap-4">
      <div className="flex justify-between items-start">
        <div className="flex gap-4 items-center">
          <div className="h-10 w-10 bg-slate-100 rounded-full flex items-center justify-center text-slate-500">
            <GitCommit size={20} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              Orçamento de {orcamento.tipo === "DESPESAS" ? "Despesas" : orcamento.tipo === "RECEITAS" ? "Receitas" : "Vendas"} {orcamento.ano}
              <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${colorClass}`}>
                {orcamento.status}
              </span>
            </h2>
            <div className="flex items-center gap-4 text-xs text-slate-500 mt-1">
              <span className="flex items-center gap-1"><FileText size={12}/> v{orcamento.versao_numero}</span>
              <span className="flex items-center gap-1"><Clock size={12}/> {orcamento.data_criacao ? new Date(orcamento.data_criacao).toLocaleDateString() : "N/A"}</span>
              {orcamento.versao_base_id && (
                <span className="flex items-center gap-1 text-brand-600 font-medium">Baseada na v{orcamento.versao_numero - 1} (ID: {orcamento.versao_base_id})</span>
              )}
            </div>
          </div>
        </div>

        {/* Workflow Actions */}
        <div className="flex gap-2">
          {orcamento.status === "Rascunho" || orcamento.status === "Reaberto" ? (
            <Button size="sm" variant="outline" onClick={() => handleStatusChange("Em aprovação", "Enviar este orçamento para aprovação?")} disabled={loading}>
              Enviar para Aprovação
            </Button>
          ) : null}

          {orcamento.status === "Em aprovação" && podeAprovar ? (
            <>
              <Button size="sm" variant="outline" className="text-brand-red border-brand-red-light hover:bg-brand-red-light/10" onClick={() => handleStatusChange("Rascunho", "Rejeitar e devolver ao rascunho?")} disabled={loading}>
                Rejeitar
              </Button>
              <Button size="sm" className="bg-brand-green hover:opacity-90 text-white" onClick={() => handleStatusChange("Fechado", "Aprovar e fechar este orçamento?")} disabled={loading}>
                <CheckCircle size={14} className="mr-1" /> Aprovar
              </Button>
            </>
          ) : null}

          {(orcamento.status === "Fechado" || orcamento.status === "Aprovado") ? (
            <Button size="sm" variant="outline" onClick={handleSolicitarReabertura} disabled={loading}>
              <RefreshCw size={14} className="mr-1" /> Solicitar Reabertura
            </Button>
          ) : null}

          {orcamento.status === "Solicitação Reabertura" && isAdminUserFlag ? (
            <div className="flex items-center gap-2 border-l pl-2 border-slate-200">
              <span className="text-xs font-semibold text-orange-600">Aprovar Reabertura?</span>
              <Button size="sm" variant="outline" onClick={() => handleStatusChange("Fechado")} disabled={loading}>Não</Button>
              <Button size="sm" className="bg-orange-600 hover:bg-orange-700 text-white" onClick={handleAprovarReabertura} disabled={loading}>Sim, Criar v{orcamento.versao_numero + 1}</Button>
            </div>
          ) : null}
        </div>
      </div>
      
      {orcamento.motivo_reabertura && (
        <div className="bg-orange-50 border border-orange-100 rounded p-3 text-sm flex gap-2 items-start text-orange-800">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <div>
            <strong>Motivo da Reabertura:</strong> {orcamento.motivo_reabertura}
          </div>
        </div>
      )}

      {orcamento.is_locked_by_other && (
        <div className="bg-brand-red-light/10 border border-brand-red-light rounded p-3 text-sm flex justify-between items-center text-brand-red">
          <div className="flex gap-2 items-center">
            <Lock size={16} className="shrink-0" />
            <span>
              <strong>Orçamento em edição:</strong> Bloqueado por {orcamento.usuario_edicao_nome} desde {orcamento.data_inicio_edicao ? new Date(orcamento.data_inicio_edicao).toLocaleTimeString() : ""}. Apenas visualização.
            </span>
          </div>
          {isAdminUserFlag && (
            <Button size="sm" variant="outline" className="bg-white text-brand-red border-brand-red-light hover:bg-brand-red-light/30" onClick={handleDestravar} disabled={loading}>
              Forçar Destravamento
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
