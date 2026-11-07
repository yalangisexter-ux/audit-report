import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { onRequest } from "../../frontend/functions/api/[[path]].js";

test("Pages invokes the proxy only for application API routes", async () => {
  const manifest = JSON.parse(
    await readFile(new URL("../../frontend/public/_routes.json", import.meta.url), "utf8"),
  );
  assert.deepEqual(manifest, {
    version: 1,
    include: ["/api", "/api/*"],
    exclude: [],
  });
});

test("API proxy preserves auth, method, query, and streamed request body", async () => {
  const originalFetch = globalThis.fetch;
  let forwarded;
  globalThis.fetch = async request => {
    forwarded = request;
    return new Response("created", {
      status: 201,
      headers: { "Content-Type": "text/plain" },
    });
  };

  try {
    const request = new Request(
      "https://raw-strength-audit.pages.dev/api/employees?active=1",
      {
        method: "POST",
        headers: {
          Authorization: "Bearer customer-session-token",
          "Content-Type": "application/json",
          "CF-Connecting-IP": "203.0.113.9",
          "X-Forwarded-For": "198.51.100.44",
          "X-Forwarded-Host": "attacker.example",
        },
        body: JSON.stringify({ employee_name: "Parity Test" }),
      },
    );
    const response = await onRequest({
      request,
      env: { API_ORIGIN: "https://api.example.test" },
    });

    assert.equal(forwarded.url, "https://api.example.test/api/employees?active=1");
    assert.equal(forwarded.method, "POST");
    assert.equal(forwarded.headers.get("authorization"), "Bearer customer-session-token");
    assert.equal(forwarded.headers.get("x-forwarded-for"), "203.0.113.9");
    assert.equal(forwarded.headers.get("x-forwarded-host"), "raw-strength-audit.pages.dev");
    assert.equal(forwarded.headers.get("host"), null);
    assert.equal(forwarded.headers.get("x-forwarded-proto"), "https");
    assert.deepEqual(await forwarded.json(), { employee_name: "Parity Test" });
    assert.equal(response.status, 201);
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.equal(await response.text(), "created");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("API proxy rejects non-HTTPS or path-based upstream configuration", async () => {
  const request = new Request("https://raw-strength-audit.pages.dev/api/health");
  const response = await onRequest({
    request,
    env: { API_ORIGIN: "http://untrusted.example/api" },
  });
  assert.equal(response.status, 503);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(await response.json(), {
    detail: "The application API proxy is not configured correctly.",
  });
});

test("API proxy returns a non-cacheable 502 when the upstream is unavailable", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("upstream unavailable");
  };
  try {
    const response = await onRequest({
      request: new Request("https://raw-strength-audit.pages.dev/api/health"),
      env: { API_ORIGIN: "https://api.example.test" },
    });
    assert.equal(response.status, 502);
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.deepEqual(await response.json(), {
      detail: "The application API is temporarily unavailable.",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
