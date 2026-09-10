"use client";

import React, { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { fechamentoService, ClosedMonthResponse } from "@/services/fechamento";
import { Lock, Unlock } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { isAdminUser } from "@/lib/roles";

const toast = {
  success: (msg: string) => alert(msg),
  error: (msg: string) => alert(msg)
};

const MESES_NOME = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

export default function FechamentoPage() {
  const { user } = useAuth();
  const nextYear = new Date().getFullYear() + 1;
  const [ano, setAno] = useState<number>(nextYear);
  const [mesesFechados, setMesesFechados] = useState<ClosedMonthResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const isAdminUserFlag = isAdminUser(user);

  const carregarDados = async () => {
    setLoading(true);
    try {
      const data = await fechamentoService.getMesesFechados();
      setMesesFechados(data);
    } catch (err) {
      toast.error("Erro ao carregar meses fechados.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarDados();
  }, []);

  const toggleMes = async (mes: number) => {
    if (!isAdminUserFlag) return toast.error("Sem permissão");
    
    const isFechado = mesesFechados.find(m => m.ano === ano && m.mes === mes);
    try {
      if (isFechado) {
        await fechamentoService.abrirMes(ano, mes);
        toast.success(`Mês ${mes} reaberto.`);
      } else {
        await fechamentoService.fecharMes(ano, mes);
        toast.success(`Mês ${mes} fechado.`);
      }
      carregarDados();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao alterar status do mês.");
    }
  };

  const mesesDoAno = mesesFechados.filter(m => m.ano === ano);

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Fechamento de Mês</h1>
          <p className="text-slate-500">Trave a edição de meses no Forecast de toda a empresa.</p>
        </div>
        <select 
          value={ano} 
          onChange={(e) => setAno(Number(e.target.value))}
          className="border-slate-300 rounded-md shadow-sm focus:border-brand-500 focus:ring-brand-500 p-2"
        >
          {[ano - 1, ano, ano + 1, ano + 2].map(a => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
      </div>

      <Card className="p-6">
        {loading ? (
          <AppLoadingState />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
            {MESES_NOME.map((nome, index) => {
              const mesIdx = index + 1;
              const isFechado = mesesDoAno.some(m => m.mes === mesIdx);
              
              return (
                <div 
                  key={mesIdx} 
                  className={`border rounded-lg p-4 flex flex-col items-center justify-center space-y-3 transition-colors ${
                    isFechado ? "bg-slate-50 border-slate-300" : "bg-white border-brand-200 hover:border-brand-300 shadow-sm"
                  }`}
                >
                  <span className="font-semibold text-lg text-slate-700">{nome} / {ano}</span>
                  
                  <div className={`px-3 py-1 rounded-full text-xs font-medium flex items-center space-x-1 ${
                    isFechado ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"
                  }`}>
                    {isFechado ? <><Lock size={12}/> <span>Fechado</span></> : <><Unlock size={12}/> <span>Aberto</span></>}
                  </div>
                  
                  {isAdminUserFlag && (
                    <Button 
                      variant={isFechado ? "outline" : "primary"}
                      size="sm"
                      className="w-full mt-2"
                      onClick={() => toggleMes(mesIdx)}
                    >
                      {isFechado ? "Reabrir Mês" : "Fechar Mês"}
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>
      
      {!isAdminUserFlag && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 p-4 rounded-md">
          Apenas administradores podem fechar ou reabrir meses.
        </div>
      )}
    </div>
  );
}
