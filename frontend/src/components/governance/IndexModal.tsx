import { useState, useEffect } from "react";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";

interface IndexData {
  id?: number;
  name: string;
  symbol: string;
  current_value: number;
  projected_value: number;
}

interface IndexModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialData?: IndexData | null;
}

export function IndexModal({ isOpen, onClose, onSuccess, initialData }: IndexModalProps) {
  const [formData, setFormData] = useState<IndexData>({
    name: "",
    symbol: "%",
    current_value: 0,
    projected_value: 0,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (initialData) {
      setFormData(initialData);
    } else {
      setFormData({ name: "", symbol: "%", current_value: 0, projected_value: 0 });
    }
  }, [initialData, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      if (initialData?.id) {
        await api.put(`/governance/indices/${initialData.id}`, formData);
      } else {
        await api.post("/governance/indices", formData);
      }
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Erro ao salvar índice.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={initialData ? "Editar Índice" : "Novo Índice"}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <div className="text-sm text-red-500">{error}</div>}
        
        <div className="space-y-2">
          <label className="text-sm font-medium text-ml-text">Nome do Índice</label>
          <Input
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Ex: INCC"
            required
            disabled={!!initialData} // Geralmente o nome não muda
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-ml-text">Símbolo</label>
          <Input
            value={formData.symbol}
            onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
            placeholder="Ex: % ou R$"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-ml-text">Valor Atual</label>
            <Input
              type="number"
              step="0.01"
              value={formData.current_value}
              onChange={(e) => setFormData({ ...formData, current_value: parseFloat(e.target.value) })}
              required
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-ml-text">Valor Projetado</label>
            <Input
              type="number"
              step="0.01"
              value={formData.projected_value}
              onChange={(e) => setFormData({ ...formData, projected_value: parseFloat(e.target.value) })}
              required
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <Button type="button" onClick={onClose} className="bg-gray-700 hover:bg-gray-600">
            Cancelar
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? "Salvando..." : "Salvar"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
