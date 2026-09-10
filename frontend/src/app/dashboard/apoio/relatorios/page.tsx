"use client";

import { useState, useEffect, Suspense } from "react";

import { useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { Download, Search, Filter, FileText, FileSpreadsheet } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { AppLoadingState } from "@/components/shared/BudgetLoadingState";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Card } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { reportConfigs, ReportConfig } from "./reportConfig";
import { exportToExcel, exportToPDF } from "@/lib/exportUtils";

function RelatoriosApoioContent() {
  const searchParams = useSearchParams();
  const reportIdParam = searchParams.get("id");
  
  const activeConfig = useMemo(() => {
    return reportConfigs.find(c => c.id === reportIdParam) || reportConfigs[0];
  }, [reportIdParam]);

  const [data, setData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filters, setFilters] = useState<Record<string, any>>({});
  const [pdfOrientation, setPdfOrientation] = useState<"portrait" | "landscape">("landscape");

  // Carrega os dados quando o tipo de relatório muda
  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const res = await api.get(activeConfig.endpoint);
        let extractedData = res.data;
        if (activeConfig.dataExtractor) {
          extractedData = activeConfig.dataExtractor(res.data);
        }
        setData(Array.isArray(extractedData) ? extractedData : extractedData.items || []);
        setFilters({}); // Reseta filtros
      } catch (error) {
        console.error("Erro ao buscar dados do relatório:", error);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [activeConfig]);

  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const filteredData = useMemo(() => {
    return data.filter((item) => {
      for (const filter of activeConfig.filters) {
        const val = filters[filter.key];
        
        if (filter.type === "text" && val) {
          const matches = Object.values(item).some((v) =>
            String(v).toLowerCase().includes(val.toLowerCase())
          );
          if (!matches) return false;
        }

        if (filter.type === "select" && val && val !== "Todos") {
          if (String(item[filter.key]) !== String(val)) return false;
        }

        if (filter.type === "multi-select" && val && val.length > 0) {
          if (!val.includes(String(item[filter.key]))) return false;
        }
      }
      return true;
    });
  }, [data, filters, activeConfig]);

  const handleExportExcel = () => {
    exportToExcel(filteredData, activeConfig.columns, activeConfig.title.replace(/ /g, "_"));
  };

  const handleExportPDF = () => {
    exportToPDF(
      filteredData, 
      activeConfig.columns, 
      activeConfig.title.replace(/ /g, "_"),
      activeConfig.title,
      pdfOrientation
    );
  };

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-slate-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-800">{activeConfig.title}</h1>
            <p className="text-sm text-slate-500">Gere relatórios customizados e exporte os dados cadastrais.</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Filters Section */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-4 text-sm font-medium text-slate-700">
            <Filter className="w-4 h-4 text-brand-green" />
            Filtros Dinâmicos
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {activeConfig.filters.map((filter) => (
              <div key={filter.key}>
                <label className="block text-xs font-medium text-slate-600 mb-1">{filter.label}</label>
                {filter.type === "text" && (
                  <Input
                    icon={<Search className="w-4 h-4" />}
                    placeholder={filter.placeholder}
                    value={filters[filter.key] || ""}
                    onChange={(e) => handleFilterChange(filter.key, e.target.value)}
                  />
                )}
                {filter.type === "select" && filter.options && (
                  <select
                    className="ml-input w-full"
                    value={filters[filter.key] || "Todos"}
                    onChange={(e) => handleFilterChange(filter.key, e.target.value)}
                  >
                    {filter.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                  </select>
                )}
                {filter.type === "multi-select" && filter.options && (
                  <MultiSelect
                    options={filter.options}
                    value={filters[filter.key] || []}
                    onChange={(val) => handleFilterChange(filter.key, val)}
                    placeholder="Selecione..."
                  />
                )}
              </div>
            ))}

          </div>
        </Card>

        {/* Data Preview */}
        <Card className="p-0 overflow-hidden flex flex-col min-h-[400px]">
          <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-white">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-slate-800">Prévia do Relatório</h3>
              <span className="text-xs font-medium bg-slate-100 text-slate-600 px-2 py-1 rounded-full">
                {filteredData.length} registros encontrados
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 mr-4 border-r border-slate-200 pr-4">
                <label className="text-xs font-medium text-slate-500">Formato PDF:</label>
                <select
                  className="text-xs border-slate-200 rounded text-slate-700 focus:ring-brand-green"
                  value={pdfOrientation}
                  onChange={(e) => setPdfOrientation(e.target.value as "portrait" | "landscape")}
                >
                  <option value="landscape">Paisagem</option>
                  <option value="portrait">Retrato</option>
                </select>
              </div>

              <Button
                variant="outline"
                size="sm"
                className="text-slate-600"
                onClick={handleExportPDF}
                disabled={isLoading || filteredData.length === 0}
              >
                <FileText className="w-4 h-4 mr-2 text-red-500" />
                Gerar PDF
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleExportExcel}
                disabled={isLoading || filteredData.length === 0}
              >
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                Gerar Excel
              </Button>
            </div>
          </div>

          <div className="flex-1 overflow-auto bg-white">
            {isLoading ? (
              <AppLoadingState />
            ) : filteredData.length === 0 ? (
              <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
                Nenhum registro encontrado para os filtros selecionados.
              </div>
            ) : (
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase bg-slate-50 text-slate-500 sticky top-0 shadow-sm z-10">
                  <tr>
                    {activeConfig.columns.map((col) => (
                      <th key={col.accessor} className="px-4 py-3 font-semibold whitespace-nowrap">
                        {col.header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredData.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 transition-colors">
                      {activeConfig.columns.map((col) => {
                        let val = row[col.accessor];
                        if (col.format) val = col.format(val, row);
                        return (
                          <td key={col.accessor} className="px-4 py-3 text-slate-600 truncate max-w-[250px]">
                            {val !== null && val !== undefined ? String(val) : "—"}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

export default function RelatoriosApoioPage() {
  return (
    <Suspense fallback={<AppLoadingState />}>
      <RelatoriosApoioContent />
    </Suspense>
  );
}
