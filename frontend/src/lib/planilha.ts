/**
 * Planilhas Excel no navegador com exceljs.
 *
 * Substitui a biblioteca xlsx 0.18.5 do npm, que tem falhas conhecidas (poluição de
 * protótipo e ReDoS ao ler arquivos) e não recebe mais correções no npm.
 * Carregada só quando o usuário baixa ou importa uma planilha (import dinâmico).
 */
export type Celula = string | number | boolean | Date | null | undefined;

function normalizar(v: unknown): Celula {
  if (v === null || v === undefined) return null;
  if (typeof v === "string" || typeof v === "number" || typeof v === "boolean" || v instanceof Date) return v;
  if (typeof v === "object") {
    const o = v as Record<string, unknown>;
    if ("result" in o) return normalizar(o.result); // fórmula
    if (Array.isArray(o.richText)) return (o.richText as { text: string }[]).map((t) => t.text).join("");
    if ("text" in o) return String(o.text); // hiperlink
    if ("error" in o) return null;
  }
  return String(v);
}

function lerCsv(texto: string): Celula[][] {
  const sep = (texto.split("\n")[0].match(/;/g) || []).length > (texto.split("\n")[0].match(/,/g) || []).length ? ";" : ",";
  const linhas: Celula[][] = [];
  let linha: Celula[] = [];
  let campo = "";
  let aspas = false;
  for (let i = 0; i < texto.length; i++) {
    const c = texto[i];
    if (aspas) {
      if (c === '"' && texto[i + 1] === '"') { campo += '"'; i++; }
      else if (c === '"') aspas = false;
      else campo += c;
    } else if (c === '"') aspas = true;
    else if (c === sep) { linha.push(campo); campo = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && texto[i + 1] === "\n") i++;
      linha.push(campo); linhas.push(linha); linha = []; campo = "";
    } else campo += c;
  }
  if (campo !== "" || linha.length) { linha.push(campo); linhas.push(linha); }
  return linhas.filter((l) => l.some((x) => x !== ""));
}

/** Linhas da primeira aba (como o antigo sheet_to_json com header: 1). Aceita .xlsx e .csv. */
export async function lerPrimeiraAba(buffer: ArrayBuffer, nomeArquivo = ""): Promise<Celula[][]> {
  if (nomeArquivo.toLowerCase().endsWith(".csv")) {
    return lerCsv(new TextDecoder("utf-8").decode(buffer));
  }
  if (nomeArquivo.toLowerCase().endsWith(".xls")) {
    throw new Error("Formato .xls antigo não é aceito. Salve a planilha como .xlsx e importe de novo.");
  }
  const ExcelJS = (await import("exceljs")).default;
  const wb = new ExcelJS.Workbook();
  await wb.xlsx.load(buffer);
  const ws = wb.worksheets[0];
  if (!ws) return [];
  const linhas: Celula[][] = [];
  ws.eachRow({ includeEmpty: false }, (row) => {
    const valores = (row.values as unknown[]).slice(1); // exceljs começa na coluna 1
    linhas.push(Array.from(valores, normalizar));
  });
  return linhas;
}

/** Gera e baixa um .xlsx a partir de linhas (primeira linha = cabeçalho). */
export async function baixarXlsx(linhas: Celula[][], nomeAba: string, arquivo: string, larguras?: number[]): Promise<void> {
  const ExcelJS = (await import("exceljs")).default;
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet(nomeAba.slice(0, 31));
  linhas.forEach((l) => ws.addRow(l.map((v) => (v === undefined ? null : v))));
  if (larguras) larguras.forEach((w, i) => { ws.getColumn(i + 1).width = w; });
  if (linhas.length) ws.getRow(1).font = { bold: true };
  const buf = await wb.xlsx.writeBuffer();
  const url = URL.createObjectURL(new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = arquivo.endsWith(".xlsx") ? arquivo : `${arquivo}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Igual ao antigo json_to_sheet: colunas = chaves do primeiro objeto. */
export async function baixarXlsxDeObjetos(objetos: Record<string, Celula>[], nomeAba: string, arquivo: string): Promise<void> {
  const cab = objetos.length ? Object.keys(objetos[0]) : [];
  await baixarXlsx([cab, ...objetos.map((o) => cab.map((k) => o[k]))], nomeAba, arquivo);
}
