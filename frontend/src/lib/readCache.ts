const TTL_MS = 30_000;
const store = new Map<string, { at: number; data: unknown }>();
const inflight = new Map<string, Promise<unknown>>();

/** Cache curto de GET (navegação entre telas de orçamento/forecast). Não altera o payload. */
export async function cachedRead<T>(key: string, fn: () => Promise<T>, ttlMs = TTL_MS): Promise<T> {
  const hit = store.get(key);
  if (hit && Date.now() - hit.at < ttlMs) return hit.data as T;
  const pending = inflight.get(key);
  if (pending) return pending as Promise<T>;
  const p = fn()
    .then((data) => {
      store.set(key, { at: Date.now(), data });
      inflight.delete(key);
      return data;
    })
    .catch((err) => {
      inflight.delete(key);
      throw err;
    });
  inflight.set(key, p);
  return p as Promise<T>;
}
