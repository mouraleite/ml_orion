/** Parse do nome de centro de custo Sienge → cidade + produto (grades orçamento/forecast). */

export function parseCentroNome(nome: string): { cidade: string; produto: string } {
  if (!nome) return { cidade: "", produto: "" };
  if (nome.toUpperCase().includes("AUTOMÓVEL") || nome.toUpperCase().includes("AUTOMOVEL")) {
    return { cidade: "FROTA", produto: "FROTA" };
  }
  const partes = nome.split(" -").map((p) => p.trim());
  if (partes.length >= 2) {
    const cidade = partes[0];
    const sufixos = ["INATIVO", "ATIVO", "ENCERRADO", "SUSPENSO"];
    const ultimaParte = partes[partes.length - 1].toUpperCase();
    const temSufixo = sufixos.includes(ultimaParte);
    let produto: string;
    if (partes.length === 2 && !temSufixo) {
      produto = partes[1];
    } else if (partes.length === 2 && temSufixo) {
      produto = partes[1];
    } else {
      const meioParts = temSufixo ? partes.slice(1, -1) : partes.slice(1);
      produto = meioParts.join(" -");
    }
    return { cidade, produto };
  }
  return { cidade: "", produto: nome };
}
