export function formatPlanId(id: string | number | undefined | null): string {
  if (id === undefined || id === null) return '';
  const str = String(id);
  
  if (str.length === 0) return '';
  
  // Se for impar, pega 1 char primeiro (ex: 1 -> 1, 101 -> 1.01)
  // Se for par, pega 2 chars primeiro (ex: 11 -> 11, 1101 -> 11.01)
  const firstGroupLength = str.length % 2 === 0 ? 2 : 1;
  let formatted = str.substring(0, firstGroupLength);
  
  for (let i = firstGroupLength; i < str.length; i += 2) {
    formatted += '.' + str.substring(i, i + 2);
  }
  
  return formatted;
}
