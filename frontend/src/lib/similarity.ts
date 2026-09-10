export function calculateAISimilarity(original: string | null | undefined, current: string | null | undefined): number {
  if (original === current) return 100;
  if (!original && !current) return 100;
  if (!original) return 0;
  if (!current) return 0;

  // Normalize: lower case, remove punctuation, multiple spaces
  const normalize = (text: string) => text.toLowerCase().replace(/[^\w\s\u00C0-\u00FF]/g, ' ').replace(/\s+/g, ' ').trim();
  
  const origWords = normalize(original).split(' ').filter(w => w.length > 0);
  const currWords = normalize(current).split(' ').filter(w => w.length > 0);

  if (origWords.length === 0 && currWords.length === 0) return 100;
  if (origWords.length === 0 || currWords.length === 0) return 0;

  // Helper to create bigrams
  const getBigrams = (words: string[]) => {
    const bigrams = [];
    for (let i = 0; i < words.length - 1; i++) {
      bigrams.push(`${words[i]} ${words[i+1]}`);
    }
    return bigrams;
  };

  const origBigrams = getBigrams(origWords);
  const currBigrams = getBigrams(currWords);

  if (origBigrams.length === 0 && currBigrams.length === 0) {
      // Fallback for very short text (1 word)
      if (origWords[0] === currWords[0]) return 100;
      return 0;
  }

  // Count intersections honoring duplicates (multiset intersection)
  const currMap = new Map<string, number>();
  for (const bg of currBigrams) {
      currMap.set(bg, (currMap.get(bg) || 0) + 1);
  }

  let intersectionCount = 0;
  for (const bg of origBigrams) {
      if (currMap.has(bg) && currMap.get(bg)! > 0) {
          intersectionCount++;
          currMap.set(bg, currMap.get(bg)! - 1);
      }
  }

  const dice = (2.0 * intersectionCount) / (origBigrams.length + currBigrams.length);
  return Math.round(dice * 100);
}
