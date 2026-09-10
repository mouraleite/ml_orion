"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { confirmDialog } from "@/components/ui/confirmDialog";
import { FileText, Upload, Download, Folder, Pencil, Trash2 } from "lucide-react";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";

interface DocumentsTabProps {
  phaseId: number;
}

export function DocumentsTab({ phaseId }: DocumentsTabProps) {
  const [documents, setDocuments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const res = await api.get(`/viabilities/phases/${phaseId}/documents`);
      setDocuments(res.data);
    } catch (error) {
      console.error("Erro ao carregar documentos", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [phaseId]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);

    setIsUploading(true);
    try {
      await api.post(`/viabilities/phases/${phaseId}/documents`, formData, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });
      alert("Documento anexado com sucesso!");
      fetchDocuments();
    } catch (error) {
      alert("Erro ao enviar documento.");
    } finally {
      setIsUploading(false);
      e.target.value = ''; // Reset input
    }
  };
  const handleRename = async (doc: any) => {
    const newName = window.prompt("Novo nome do documento:", doc.name);
    if (!newName || newName === doc.name) return;
    try {
      await api.put(`/viabilities/phases/${phaseId}/documents/${doc.id}`, { new_name: newName });
      fetchDocuments();
    } catch (error) {
      alert("Erro ao renomear documento.");
    }
  };

  const handleDelete = async (docId: string) => {
    if (!(await confirmDialog("Tem certeza que deseja excluir este documento?", { variant: "danger" }))) return;
    try {
      await api.delete(`/viabilities/phases/${phaseId}/documents/${docId}`);
      fetchDocuments();
    } catch (error) {
      alert("Erro ao excluir documento.");
    }
  };

  if (isLoading) return <AppLoadingState />;

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Folder className="w-6 h-6 text-ml-orange" />
            Documentos do Projeto (GED)
          </h2>
          <p className="text-sm text-slate-500 mt-1">Armazene e consulte os arquivos oficiais desta viabilidade na nuvem (SharePoint).</p>
        </div>
        <div>
          <label className="cursor-pointer">
            <input type="file" className="hidden" onChange={handleUpload} disabled={isUploading} />
            <div className={`px-4 py-2 rounded-md font-medium text-sm flex items-center gap-2 ${isUploading ? 'bg-slate-200 text-slate-500' : 'bg-ml-green hover:bg-ml-dark text-white shadow-sm'}`}>
              <Upload className="w-4 h-4" />
              {isUploading ? "Enviando..." : "Anexar Arquivo"}
            </div>
          </label>
        </div>
      </div>

      <Card className="overflow-hidden">
        {documents.length === 0 ? (
          <div className="p-8 text-center text-slate-500 bg-slate-50">
            Nenhum documento anexado ainda.
          </div>
        ) : (
          <table className="w-full text-sm text-left text-slate-700">
            <thead className="text-xs text-slate-500 uppercase bg-slate-50 border-b">
              <tr>
                <th className="px-6 py-4 font-medium">Nome do Arquivo</th>
                <th className="px-6 py-4 font-medium">Tamanho</th>
                <th className="px-6 py-4 font-medium">Data de Upload</th>
                <th className="px-6 py-4 font-medium text-right">Ação</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc, idx) => (
                <tr key={doc.id} className={idx % 2 === 0 ? 'bg-white border-b' : 'bg-slate-50 border-b'}>
                  <td className="px-6 py-4 font-medium flex items-center gap-2">
                    <FileText className="w-4 h-4 text-ml-green" />
                    {doc.name}
                  </td>
                  <td className="px-6 py-4">{doc.size}</td>
                  <td className="px-6 py-4">{doc.date}</td>
                  <td className="px-6 py-4 text-right flex justify-end gap-2">
                    <Button variant="outline" size="sm" onClick={() => handleRename(doc)} className="text-slate-600 hover:text-blue-600" title="Renomear">
                      <Pencil className="w-4 h-4" />
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleDelete(doc.id)} className="text-slate-600 hover:text-red-600 hover:bg-red-50" title="Excluir">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                    <Button variant="secondary" size="sm" className="text-ml-green hover:text-ml-dark hover:bg-green-50" title="Baixar">
                      <Download className="w-4 h-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
