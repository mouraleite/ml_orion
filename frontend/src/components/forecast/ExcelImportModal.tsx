import {
  ExcelImportModal as SharedExcelImportModal,
  type ExcelImportModalProps as SharedProps,
} from "@/components/shared/ExcelImportModal";

type ForecastExcelProps = Omit<SharedProps, "apiBase" | "entityId"> & {
  orcamentoId?: number;
};

export function ForecastExcelImportModal({
  orcamentoId,
  exportLabel = "Exportar Forecast",
  ...props
}: ForecastExcelProps) {
  return (
    <SharedExcelImportModal
      apiBase="forecasts"
      entityId={orcamentoId}
      exportLabel={exportLabel}
      {...props}
    />
  );
}

export { ForecastExcelImportModal as ExcelImportModal };
