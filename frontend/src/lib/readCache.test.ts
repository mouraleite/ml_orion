import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { cachedRead } from "./readCache";

describe("cachedRead", () => {
  it("reuses a successful result within the TTL", async () => {
    let calls = 0;
    const fn = async () => {
      calls += 1;
      return { n: calls };
    };
    const a = await cachedRead("test:ttl", fn, 5_000);
    const b = await cachedRead("test:ttl", fn, 5_000);
    assert.equal(a.n, 1);
    assert.equal(b.n, 1);
    assert.equal(calls, 1);
  });

  it("dedupes concurrent inflight requests", async () => {
    let calls = 0;
    const fn = async () => {
      calls += 1;
      await new Promise((r) => setTimeout(r, 20));
      return { n: calls };
    };
    const [a, b] = await Promise.all([
      cachedRead("test:inflight", fn, 5_000),
      cachedRead("test:inflight", fn, 5_000),
    ]);
    assert.equal(a.n, 1);
    assert.equal(b.n, 1);
    assert.equal(calls, 1);
  });
});
