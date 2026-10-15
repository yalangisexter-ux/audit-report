import test from "node:test";
import assert from "node:assert/strict";
import worker, { DeviceRegistry } from "../src/index.js";

class MemoryStorage {
  constructor() { this.data = new Map(); this.tail = Promise.resolve(); }
  async get(key) { return this.data.get(key); }
  async put(key, value) { this.data.set(key, value); }
  async transaction(fn) {
    let release;
    const previous = this.tail;
    this.tail = new Promise(resolve => { release = resolve; });
    await previous;
    try { return await fn(this); } finally { release(); }
  }
}
function makeEnv() {
  const registry = new DeviceRegistry({ storage: new MemoryStorage() });
  const binding = { idFromName: name => name, get: () => ({ fetch: (url, init) => registry.fetch(new Request(url, init)) }) };
  return { JWT_SECRET: "test-jwt-secret-that-is-long-enough-123456789", RELEASE_TOKEN_2: "test-github-token", GITHUB_OWNER: "test-owner", GITHUB_REPO: "test-repo", DEVICE_REGISTRY: binding };
}
function makeGitHubMock() {
  const files = new Map();
  const shas = new Map();
  let commit = 0;
  return {
    files,
    fetch: async (input, init = {}) => {
      const url = new URL(input);
      if (url.hostname !== "api.github.com") throw new Error("unexpected fetch host");
      const path = decodeURIComponent(url.pathname.split("/contents/")[1] || "");
      const accept = init.headers?.Accept || init.headers?.get?.("Accept") || "";
      if (init.method === "GET") {
        const bytes = files.get(path);
        if (!bytes) return new Response(JSON.stringify({ message: "Not Found" }), { status: 404 });
        if (accept.includes("raw+json")) return new Response(bytes, { status: 200, headers: { "Content-Type": "application/octet-stream" } });
        return Response.json({ sha: shas.get(path), content: Buffer.from(bytes).toString("base64"), encoding: "base64" });
      }
      if (init.method === "PUT") {
        const body = JSON.parse(init.body);
        const previous = files.get(path);
        if (previous && body.sha !== shas.get(path)) return Response.json({ message: "sha conflict" }, { status: 409 });
        if (!previous && body.sha) return Response.json({ message: "missing" }, { status: 409 });
        files.set(path, Buffer.from(body.content, "base64"));
        shas.set(path, "sha-" + (++commit));
        return Response.json({ content: { path }, commit: { sha: "commit-" + commit } }, { status: 201 });
      }
      throw new Error("unexpected GitHub method");
    },
  };
}
const installA = "a".repeat(32);
const installB = "b".repeat(32);
const deviceA = "1".repeat(32);
const deviceB = "2".repeat(32);
const secretA = "secret-A-".repeat(8);
const secretB = "secret-B-".repeat(8);

test("first registration succeeds; a second device cannot claim the same installation", async () => {
  const env = makeEnv();
  const register = (installation_id, device_id, device_secret) => worker.fetch(new Request("https://worker/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ installation_id, device_id, device_secret }) }), env);
  const first = await register(installA, deviceA, secretA);
  assert.equal(first.status, 200);
  assert.ok((await first.json()).token);
  const second = await register(installA, deviceB, secretB);
  assert.equal(second.status, 409);
  const refresh = await register(installA, deviceA, secretA);
  assert.equal(refresh.status, 200);
});

test("invalid tokens cannot access snapshots", async () => {
  const env = makeEnv();
  const response = await worker.fetch(new Request("https://worker/pull", { method: "POST", headers: { Authorization: "Bearer not-a-jwt", "Content-Type": "application/json" }, body: "{}" }), env);
  assert.equal(response.status, 401);
});

test("push and pull are installation-scoped and return raw encrypted bytes", async () => {
  const env = makeEnv();
  const github = makeGitHubMock();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = github.fetch;
  try {
    const register = async (installation_id, device_id, device_secret) => {
      const response = await worker.fetch(new Request("https://worker/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ installation_id, device_id, device_secret }) }), env);
      return (await response.json()).token;
    };
    const tokenA = await register(installA, deviceA, secretA);
    const tokenB = await register(installB, deviceB, secretB);
    const snapshot = Buffer.from("encrypted snapshot bytes");
    const push = await worker.fetch(new Request("https://worker/push", { method: "POST", headers: { Authorization: "Bearer " + tokenA, "Content-Type": "application/json" }, body: JSON.stringify({ content: snapshot.toString("base64") }) }), env);
    assert.equal(push.status, 200);
    assert.ok(github.files.has("customer-data/" + installA + ".db.enc"));
    assert.equal(github.files.has("customer-data/" + installB + ".db.enc"), false);
    const pull = await worker.fetch(new Request("https://worker/pull", { method: "POST", headers: { Authorization: "Bearer " + tokenA, "Content-Type": "application/json" }, body: "{}" }), env);
    assert.equal(pull.status, 200);
    assert.deepEqual(Buffer.from(await pull.arrayBuffer()), snapshot);
    const noSnapshot = await worker.fetch(new Request("https://worker/pull", { method: "POST", headers: { Authorization: "Bearer " + tokenB, "Content-Type": "application/json" }, body: "{}" }), env);
    assert.equal(noSnapshot.status, 404);
  } finally { globalThis.fetch = originalFetch; }
});

test("bad registration data is rejected", async () => {
  const env = makeEnv();
  const response = await worker.fetch(new Request("https://worker/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ installation_id: "short", device_id: deviceA, device_secret: secretA }) }), env);
  assert.equal(response.status, 400);
});
