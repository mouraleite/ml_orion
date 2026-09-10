"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useUnsavedChanges } from "@/contexts/UnsavedChangesContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Save, Calendar } from "lucide-react";
import { Card } from "@/components/ui/Card";

interface DatesTabProps {
  phaseId: number;
  isReadonly?: boolean;
}

export function DatesTab({ phaseId, isReadonly }: DatesTabProps) {
  const [data, setData] = useState<any>({
    data_registro: "",
    data_lancamento: "",
    data_inicio_obras: "",
    data_inicio_projetos: "",
    data_inicio_aquisicao: "",
    data_inicio_comercial: "",
    data_inicio_mkt: "",
  });
  const { setHasUnsavedChanges } = useUnsavedChanges();
  const [initialData, setInitialData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get(`/viabilities/phases/${phaseId}/dates`);
        const fetchedData = {
            data_registro: res.data.data_registro || "",
            data_lancamento: res.data.data_lancamento || "",
            data_inicio_obras: res.data.data_inicio_obras || "",
            data_inicio_projetos: res.data.data_inicio_projetos || "",
            data_inicio_aquisicao: res.data.data_inicio_aquisicao || "",
            data_inicio_comercial: res.data.data_inicio_comercial || "",
            data_inicio_mkt: res.data.data_inicio_mkt || "",
        };
        setData(fetchedData);
        setInitialData(fetchedData);
      } catch (e) {
        console.error(e);
      }
    };
    fetchData();
  }, [phaseId]);

  const hasChanges = JSON.stringify(data) !== JSON.stringify(initialData);

  useEffect(() => {
    setHasUnsavedChanges(hasChanges);
  }, [hasChanges, setHasUnsavedChanges]);

  const handleSave = async () => {
    setIsLoading(true);
    setMessage("");
    try {
      await api.put(`/viabilities/phases/${phaseId}/dates`, data);
      setInitialData(data);
      setMessage("Cronograma salvo com sucesso!");
      setTimeout(() => setMessage(""), 3000);
    } catch (e) {
      console.error(e);
      alert("Erro ao salvar datas");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field: string, value: string) => {
    setData((prev: any) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="p-6 space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Datas e Cronograma</h2>
          <p className="text-sm text-slate-500">Defina as datas chave para o deslocamento das curvas financeiras.</p>
        </div>
        <div className="flex items-center gap-4">
          {message && <span className="text-sm text-green-600 font-medium">{message}</span>}
          {!isReadonly && (
            <Button
              onClick={handleSave}
              disabled={!hasChanges || isLoading}
              className="bg-ml-green hover:bg-ml-green/90 text-white flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              {isLoading ? "Salvando..." : "Salvar Datas"}
            </Button>
          )}
        </div>
      </div>

      <Card className="p-6 max-w-4xl mx-auto border-0 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
                <h3 className="font-bold text-slate-700 border-b pb-2 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-slate-400"/>
                    Marcos Principais
                </h3>
                
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Registro (RI)</label>
                    <Input
                        type="date"
                        value={data.data_registro}
                        onChange={(e) => handleChange("data_registro", e.target.value)}
                        disabled={isReadonly}
                        className="w-full"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Lançamento</label>
                    <Input
                        type="date"
                        value={data.data_lancamento}
                        onChange={(e) => handleChange("data_lancamento", e.target.value)}
                        disabled={isReadonly}
                        className="w-full"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Início das Obras</label>
                    <Input
                        type="date"
                        value={data.data_inicio_obras}
                        onChange={(e) => handleChange("data_inicio_obras", e.target.value)}
                        disabled={isReadonly}
                        className="w-full"
                    />
                </div>
            </div>

            <div className="space-y-4">
                <h3 className="font-bold text-slate-700 border-b pb-2 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-slate-400"/>
                    Serviços e Comercial
                </h3>
                
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Início dos Projetos</label>
                    <Input
                        type="date"
                        value={data.data_inicio_projetos}
                        onChange={(e) => handleChange("data_inicio_projetos", e.target.value)}
                        disabled={isReadonly}
                        className="w-full"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Início Aquisição de Área</label>
                    <Input
                        type="date"
                        value={data.data_inicio_aquisicao}
                        onChange={(e) => handleChange("data_inicio_aquisicao", e.target.value)}
                        disabled={isReadonly}
                        className="w-full"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Início do Comercial</label>
                    <Input
                        type="date"
                        value={data.data_inicio_comercial}
                        onChange={(e) => handleChange("data_inicio_comercial", e.target.value)}
                        disabled={isReadonly}
                        className="w-full"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Início do Marketing</label>
                    <Input
                        type="date"
                        value={data.data_inicio_mkt}
                        onChange={(e) => handleChange("data_inicio_mkt", e.target.value)}
                        disabled={isReadonly}
                        className="w-full"
                    />
                </div>
            </div>
        </div>
      </Card>
    </div>
  );
}
