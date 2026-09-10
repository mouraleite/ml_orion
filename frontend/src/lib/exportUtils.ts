import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

export interface ColumnDef {
  header: string;
  accessor: string;
  format?: (val: any, row?: any) => string;
}

export function exportToExcel(data: any[], columns: ColumnDef[], filename: string) {
  const exportData = data.map(item => {
    const row: any = {};
    columns.forEach(col => {
      let val = item[col.accessor];
      if (col.format) {
        val = col.format(val, item);
      }
      row[col.header] = val;
    });
    return row;
  });

  const worksheet = XLSX.utils.json_to_sheet(exportData);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Relatório');
  XLSX.writeFile(workbook, `${filename}.xlsx`);
}

export function exportToPDF(
  data: any[],
  columns: ColumnDef[],
  filename: string,
  title: string,
  orientation: 'portrait' | 'landscape' = 'landscape'
) {
  const doc = new jsPDF({ orientation });

  // Adiciona Título
  doc.setFontSize(18);
  doc.text(title, 14, 22);

  // Adiciona Data
  doc.setFontSize(11);
  doc.setTextColor(100);
  doc.text(`Gerado em: ${new Date().toLocaleString('pt-BR')}`, 14, 30);

  // Prepara dados para a tabela
  const tableColumn = columns.map(col => col.header);
  const tableRows = data.map(item => {
    return columns.map(col => {
      let val = item[col.accessor];
      if (col.format) {
        val = col.format(val, item);
      }
      return val !== null && val !== undefined ? String(val) : '-';
    });
  });

  autoTable(doc, {
    head: [tableColumn],
    body: tableRows,
    startY: 40,
    styles: { fontSize: 8, cellPadding: 2 },
    headStyles: { fillColor: [15, 23, 42] }, // Slate-900 color for header
    alternateRowStyles: { fillColor: [248, 250, 252] }, // Slate-50 alternating
  });

  doc.save(`${filename}.pdf`);
}
