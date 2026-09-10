"use client";

import React, { useState, useRef, useCallback } from "react";
import {
  Download, Upload, CheckCircle2, XCircle, AlertTriangle,
  FileSpreadsheet, ArrowRight, RotateCcw, Loader2, X
} from "lucide-react";
import { api } from "@/lib/api";

interface ErroLinha {
  linha: number;
  campo: string;
  codigo: string;
  mensagem: string;
}

interface ValidationResult {
  tipo: string;
  ano: number;
  total_linhas: number;
  total_erros: number;
  total_validas: number;
  pode_importar: boolean;
  erros: ErroLinha[];
}

type Step = "download" | "upload" | "validating" | "review" | "importing" | "done";

const CODIGO_LABEL: Record<string, string> = {
  V01: "Campo obrigatório",
  V02: "Produto inexistente",
  V03: "Plano inexistente",
  V04: "Plano não autorizado",
  V05: "Ano/mês inválido",
  V06: "Valor inválido",
  V07: "Duplicidade",
};

const CODIGO_COLOR: Record<string, string> = {
  V01: "bg-brand-orange/10 text-brand-orange",
  V02: "bg-brand-red-light/30 text-brand-red",
  V03: "bg-brand-red-light/30 text-brand-red",
  V04: "bg-brand-orange-light/50 text-brand-orange",
  V05: "bg-brand-orange-light/30 text-brand-orange",
  V06: "bg-brand-red-light/30 text-brand-red",
  V07: "bg-brand-orange/20 text-brand-orange",
};

export type ExcelApiBase = "orcamentos" | "forecasts";

export interface ExcelImportModalProps {
  apiBase: ExcelApiBase;
  tipo: "DESPESAS" | "RECEITAS" | "VENDAS";
  ano: number;
  deptId: number;
  entityId?: number;
  exportLabel?: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export function ExcelImportModal({
  apiBase,
  tipo,
  ano,
  deptId,
  entityId,
  exportLabel = "Exportar versão atual",
  onClose,
  onSuccess,
}: ExcelImportModalProps) {
  const [step, setStep] = useState<Step>("download");
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [importResult, setImportResult] = useState<{ gravado: boolean; mensagem: string; total_linhas?: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const tipoLabel = tipo.charAt(0) + tipo.slice(1).toLowerCase();
  const prefix = `/${apiBase}/excel`;

  const downloadModelo = useCallback(async () => {
    try {
      const response = await api.get(`${prefix}/modelo/${tipo}/${ano}`, {
        responseType: "blob",
        headers: { "X-Department-Id": String(deptId) },
      });
      const url = URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `modelo_${tipo.toLowerCase()}_${ano}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Erro ao baixar o modelo. Verifique a conexão.");
    }
  }, [prefix, tipo, ano, deptId]);

  const exportarPreenchido = useCallback(async () => {
    if (!entityId) return;
    try {
      const response = await api.get(`${prefix}/exportar/${entityId}`, {
        responseType: "blob",
        headers: { "X-Department-Id": String(deptId) },
      });
      const url = URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${apiBase}_${entityId}_${tipo.toLowerCase()}_${ano}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Erro ao exportar a planilha.");
    }
  }, [prefix, entityId, apiBase, tipo, ano, deptId]);

  const validarArquivo = useCallback(async (f: File) => {
    setStep("validating");
    setError(null);
    const formData = new FormData();
    formData.append("file", f);
    try {
      const { data } = await api.post(`${prefix}/validar/${tipo}/${ano}`, formData, {
        headers: { "Content-Type": "multipart/form-data", "X-Department-Id": String(deptId) },
      });
      setValidation(data);
      setStep("review");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err?.response?.data?.detail || "Erro ao validar o arquivo.");
      setStep("upload");
    }
  }, [prefix, tipo, ano, deptId]);

  const confirmarImportacao = useCallback(async () => {
    if (!file) return;
    setStep("importing");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const { data } = await api.post(`${prefix}/importar/${tipo}/${ano}`, formData, {
        headers: { "Content-Type": "multipart/form-data", "X-Department-Id": String(deptId) },
      });
      setImportResult(data);
      setStep("done");
      if (data.gravado && onSuccess) onSuccess();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err?.response?.data?.detail || "Erro ao importar.");
      setStep("review");
    }
  }, [file, prefix, tipo, ano, deptId, onSuccess]);

  const handleFile = (f: File) => {
    if (!f.name.endsWith(".xlsx")) {
      setError("Apenas arquivos .xlsx são aceitos.");
      return;
    }
    setFile(f);
    setError(null);
    validarArquivo(f);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const resetFlow = () => {
    setStep("upload");
    setFile(null);
    setValidation(null);
    setImportResult(null);
    setError(null);
  };

  const steps = ["download", "upload", "review", "done"] as const;
  const stepIdx = step === "validating" ? 1 : step === "importing" ? 2 : steps.indexOf(step as typeof steps[number]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-brand-green-light bg-brand-dark-green text-white rounded-t-2xl">
          <div className="flex items-center gap-3">
            <FileSpreadsheet className="w-5 h-5 text-brand-green-light" />
            <div>
              <h2 className="font-bold text-lg">Importação / Exportação Excel</h2>
              <p className="text-slate-300 text-xs">{tipoLabel} — {ano}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/20 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex items-center px-6 py-3 bg-slate-50 border-b border-slate-200 gap-3">
          {[
            { label: "1. Download", icon: Download },
            { label: "2. Upload", icon: Upload },
            { label: "3. Revisão", icon: AlertTriangle },
            { label: "4. Concluído", icon: CheckCircle2 },
          ].map(({ label, icon: Icon }, i) => (
            <React.Fragment key={label}>
              <div className={`flex items-center gap-1.5 text-xs font-semibold transition-colors ${i <= stepIdx ? "text-slate-800" : "text-slate-400"}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${i < stepIdx ? "bg-brand-green text-white" : i === stepIdx ? "bg-brand-dark-green text-white" : "bg-slate-200 text-slate-500"}`}>
                  {i < stepIdx ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Icon className="w-3.5 h-3.5" />}
                </div>
                {label}
              </div>
              {i < 3 && <ArrowRight className="w-3 h-3 text-slate-300 shrink-0" />}
            </React.Fragment>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 flex items-start gap-3 bg-brand-red-light/10 border border-brand-red-light text-brand-red rounded-xl px-4 py-3 text-sm">
              <XCircle className="w-5 h-5 shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {step === "download" && (
            <div className="space-y-5">
              <div className="bg-slate-50 border border-brand-gray-green/30 rounded-xl p-4 text-sm text-slate-800">
                <p className="font-semibold mb-1 text-brand-dark-green">Como funciona a importação:</p>
                <ol className="list-decimal list-inside space-y-1 text-slate-600">
                  <li>Baixe o modelo Excel com os cabeçalhos corretos e dropdowns preenchidos.</li>
                  <li>Preencha os dados offline e salve o arquivo <strong>.xlsx</strong>.</li>
                  <li>Faça upload do arquivo — o sistema valida sem gravar.</li>
                  <li>Revise o relatório de erros, corrija se necessário e reimporte.</li>
                  <li>Confirme a importação. Tudo ou nada: nenhuma linha é salva parcialmente.</li>
                </ol>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <button
                  onClick={downloadModelo}
                  className="flex flex-col items-center gap-3 p-6 border-2 border-dashed border-brand-green-light bg-brand-green/5 rounded-xl hover:bg-brand-green/10 hover:border-brand-green transition group"
                >
                  <div className="w-12 h-12 rounded-xl bg-brand-green flex items-center justify-center group-hover:scale-110 transition-transform shadow">
                    <Download className="w-6 h-6 text-white" />
                  </div>
                  <div className="text-center">
                    <div className="font-bold text-slate-700">Baixar Modelo</div>
                    <div className="text-xs text-slate-500 mt-1">Template .xlsx com dropdowns para {tipoLabel}</div>
                  </div>
                </button>

                {entityId && (
                  <button
                    onClick={exportarPreenchido}
                    className="flex flex-col items-center gap-3 p-6 border-2 border-dashed border-brand-orange-light bg-brand-orange/5 rounded-xl hover:bg-brand-orange/10 hover:border-brand-orange transition group"
                  >
                    <div className="w-12 h-12 rounded-xl bg-brand-orange flex items-center justify-center group-hover:scale-110 transition-transform shadow">
                      <FileSpreadsheet className="w-6 h-6 text-white" />
                    </div>
                    <div className="text-center">
                      <div className="font-bold text-slate-700">{exportLabel}</div>
                      <div className="text-xs text-slate-500 mt-1">Exportar a versão atual preenchida</div>
                    </div>
                  </button>
                )}
              </div>

              <div className="flex justify-end">
                <button
                  onClick={() => setStep("upload")}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium bg-brand-green text-white hover:opacity-90 transition"
                >
                  Próximo: Importar arquivo <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {step === "upload" && (
            <div className="space-y-5">
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileRef.current?.click()}
                className={`flex flex-col items-center justify-center gap-4 p-12 border-2 border-dashed rounded-2xl cursor-pointer transition-all ${
                  isDragging
                    ? "border-green-400 bg-brand-green/5 scale-[1.01]"
                    : "border-slate-300 bg-slate-50 hover:border-slate-400 hover:bg-slate-100"
                }`}
              >
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all ${isDragging ? "bg-brand-green" : "bg-slate-200"}`}>
                  <Upload className={`w-8 h-8 ${isDragging ? "text-white" : "text-slate-500"}`} />
                </div>
                <div className="text-center">
                  <p className="font-semibold text-slate-700 text-lg">
                    {isDragging ? "Solte o arquivo aqui" : "Arraste o arquivo .xlsx aqui"}
                  </p>
                  <p className="text-slate-500 text-sm mt-1">ou clique para selecionar</p>
                  <p className="text-slate-400 text-xs mt-2">Somente arquivos .xlsx são aceitos</p>
                </div>
              </div>
              <input ref={fileRef} type="file" accept=".xlsx" className="hidden"
                onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }} />

              <div className="flex justify-between">
                <button onClick={() => setStep("download")} className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700">
                  ← Voltar
                </button>
              </div>
            </div>
          )}

          {step === "validating" && (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <Loader2 className="w-12 h-12 text-slate-600 animate-spin" />
              <p className="font-semibold text-slate-700 text-lg">Validando planilha...</p>
              <p className="text-slate-400 text-sm">Verificando todas as regras da Seção 19.1</p>
            </div>
          )}

          {step === "review" && validation && (
            <div className="space-y-5">
              <div className={`flex items-start gap-4 p-4 rounded-xl border ${validation.pode_importar ? "bg-brand-green/5 border-brand-green-light" : "bg-brand-red-light/10 border-brand-red-light"}`}>
                {validation.pode_importar ? (
                  <CheckCircle2 className="w-6 h-6 text-brand-green shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-6 h-6 text-brand-red shrink-0 mt-0.5" />
                )}
                <div>
                  <p className={`font-bold ${validation.pode_importar ? "text-brand-dark-green" : "text-brand-red"}`}>
                    {validation.pode_importar ? "Planilha válida — pronta para importar" : `${validation.total_erros} erro(s) encontrado(s)`}
                  </p>
                  <div className="flex gap-4 mt-1 text-sm">
                    <span className="text-slate-600"><strong>{validation.total_linhas}</strong> linhas lidas</span>
                    <span className="text-brand-red"><strong>{validation.total_erros}</strong> com erro</span>
                    <span className="text-brand-dark-green"><strong>{validation.total_validas}</strong> válidas</span>
                  </div>
                  {file && <p className="text-xs text-slate-500 mt-1">📄 {file.name}</p>}
                </div>
              </div>

              {validation.erros.length > 0 && (
                <div className="rounded-xl border border-brand-red-light overflow-hidden">
                  <div className="bg-brand-red-light/10 px-4 py-2.5 border-b border-brand-red-light">
                    <h3 className="font-bold text-brand-red text-sm">Relatório de Erros — corrija e reimporte</h3>
                  </div>
                  <div className="overflow-x-auto max-h-64">
                    <table className="min-w-full text-xs">
                      <thead className="sticky top-0 bg-slate-50">
                        <tr className="border-b border-slate-200">
                          <th className="text-left px-4 py-2 font-semibold text-slate-600 w-16">Linha</th>
                          <th className="text-left px-3 py-2 font-semibold text-slate-600 w-28">Campo</th>
                          <th className="text-left px-3 py-2 font-semibold text-slate-600 w-32">Código</th>
                          <th className="text-left px-4 py-2 font-semibold text-slate-600">Descrição do Erro</th>
                        </tr>
                      </thead>
                      <tbody>
                        {validation.erros.map((e, i) => (
                          <tr key={i} className="border-b border-slate-100 hover:bg-brand-red-light/10/30">
                            <td className="px-4 py-2 font-mono font-bold text-slate-700">{e.linha}</td>
                            <td className="px-3 py-2 text-slate-600 font-medium">{e.campo}</td>
                            <td className="px-3 py-2">
                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${CODIGO_COLOR[e.codigo] || "bg-slate-100 text-slate-600"}`}>
                                {e.codigo} · {CODIGO_LABEL[e.codigo] || e.codigo}
                              </span>
                            </td>
                            <td className="px-4 py-2 text-slate-700">{e.mensagem}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between gap-3">
                <button onClick={resetFlow} className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition">
                  <RotateCcw className="w-4 h-4" /> Reimportar arquivo
                </button>
                {validation.pode_importar && (
                  <button
                    onClick={confirmarImportacao}
                    className="flex items-center gap-2 px-6 py-2.5 bg-brand-green text-white rounded-xl font-bold hover:bg-brand-dark-green transition shadow-sm"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Confirmar Importação ({validation.total_validas} linhas)
                  </button>
                )}
              </div>
            </div>
          )}

          {step === "importing" && (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <Loader2 className="w-12 h-12 text-brand-green animate-spin" />
              <p className="font-semibold text-slate-700 text-lg">Gravando dados...</p>
              <p className="text-slate-400 text-sm">Aguarde — importação em andamento</p>
            </div>
          )}

          {step === "done" && importResult && (
            <div className="flex flex-col items-center justify-center py-12 gap-5">
              {importResult.gravado ? (
                <>
                  <div className="w-20 h-20 rounded-full bg-brand-green/10 flex items-center justify-center">
                    <CheckCircle2 className="w-10 h-10 text-brand-green" />
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-slate-800">{importResult.mensagem}</p>
                    <p className="text-slate-500 text-sm mt-1">
                      {importResult.total_linhas} linha(s) gravada(s) com sucesso. Auditoria registrada.
                    </p>
                  </div>
                  <button onClick={onClose} className="px-6 py-2.5 bg-brand-green text-white rounded-xl font-bold hover:bg-brand-dark-green transition">
                    Fechar
                  </button>
                </>
              ) : (
                <>
                  <div className="w-20 h-20 rounded-full bg-brand-red-light/30 flex items-center justify-center">
                    <XCircle className="w-10 h-10 text-brand-red" />
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-brand-red">Importação recusada</p>
                    <p className="text-slate-500 text-sm mt-1">{importResult.mensagem}</p>
                  </div>
                  <button onClick={resetFlow} className="flex items-center gap-2 px-6 py-2.5 bg-slate-800 text-white rounded-xl font-bold hover:bg-slate-700 transition">
                    <RotateCcw className="w-4 h-4" /> Tentar novamente
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
