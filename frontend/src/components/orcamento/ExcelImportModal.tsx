import {
  ExcelImportModal as SharedExcelImportModal,
  type ExcelImportModalProps as SharedProps,
} from "@/components/shared/ExcelImportModal";

type OrcamentoExcelProps = Omit<SharedProps, "apiBase" | "entityId"> & {
  orcamentoId?: number;
};

export function ExcelImportModal({
  orcamentoId,
  exportLabel = "Exportar Orçamento",
  ...props
}: OrcamentoExcelProps) {
  return (
    <SharedExcelImportModal
      apiBase="orcamentos"
      entityId={orcamentoId}
      exportLabel={exportLabel}
      {...props}
    />
  );
}
