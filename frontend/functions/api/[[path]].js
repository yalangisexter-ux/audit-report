const DEFAULT_API_ORIGIN = "https://audit-report-web.onrender.com";

const HOP_BY_HOP_HEADERS = [
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "cf-connecting-ip",
  "cf-ray",
  "cf-visitor",
  "cf-worker",
  "x-forwarded-for",
  "x-forwarded-host",
  "x-forwarded-proto",
];

function resolveApiOrigin(value) {
  const parsed = new URL(String(value || DEFAULT_API_ORIGIN).trim());
  if (
    parsed.protocol !== "https:" ||
    parsed.username ||
    parsed.password ||
    !["", "/"].includes(parsed.pathname) ||
    parsed.search ||
    parsed.hash
  ) {
    throw new Error("API_ORIGIN must be an HTTPS origin without credentials or a path.");
  }
  return parsed.origin;
}

export async function onRequest({ request, env }) {
  const incoming = new URL(request.url);
  if (incoming.pathname !== "/api" && !incoming.pathname.startsWith("/api/")) {
    return new Response("Not Found", { status: 404 });
  }

  let origin;
  try {
    origin = resolveApiOrigin(env?.API_ORIGIN);
  } catch {
    return Response.json(
      { detail: "The application API proxy is not configured correctly." },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }

  const target = new URL(incoming.pathname + incoming.search, origin);
  const upstreamRequest = new Request(target.toString(), request);
  const headers = new Headers(upstreamRequest.headers);
  const clientIp = request.headers.get("CF-Connecting-IP");

  for (const name of HOP_BY_HOP_HEADERS) headers.delete(name);
  if (clientIp) headers.set("X-Forwarded-For", clientIp);
  headers.set("X-Forwarded-Host", incoming.host);
  headers.set("X-Forwarded-Proto", incoming.protocol.slice(0, -1));
  headers.set("Cache-Control", "no-store");

  try {
    const response = await fetch(
      new Request(upstreamRequest, { headers, redirect: "manual" }),
    );
    const responseHeaders = new Headers(response.headers);
    responseHeaders.set("Cache-Control", "no-store");
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch {
    return Response.json(
      { detail: "The application API is temporarily unavailable." },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}
