const PRIMARY_API_ORIGIN = "https://raw-strength-employee-api.yalangisexter.workers.dev";
const FALLBACK_API_ORIGIN = "https://audit-report-web.onrender.com";

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
  const raw = String(value || "").trim();
  if (!raw) return PRIMARY_API_ORIGIN;
  const parsed = new URL(raw);
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

  let primaryOrigin = PRIMARY_API_ORIGIN;
  try {
    if (env?.API_ORIGIN) {
      primaryOrigin = resolveApiOrigin(env.API_ORIGIN);
    }
  } catch {
    primaryOrigin = PRIMARY_API_ORIGIN;
  }

  // Pre-buffer request body if any (so it can be re-sent on fallback)
  const hasBody = ["POST", "PUT", "PATCH", "DELETE"].includes(request.method);
  const bodyBytes = hasBody ? await request.arrayBuffer() : null;

  async function forwardTo(origin) {
    const target = new URL(incoming.pathname + incoming.search, origin);
    const headers = new Headers(request.headers);
    const clientIp = request.headers.get("CF-Connecting-IP");

    for (const name of HOP_BY_HOP_HEADERS) headers.delete(name);
    if (clientIp) headers.set("X-Forwarded-For", clientIp);
    headers.set("X-Forwarded-Host", incoming.host);
    headers.set("X-Forwarded-Proto", incoming.protocol.slice(0, -1));
    headers.set("Cache-Control", "no-store");

    const init = {
      method: request.method,
      headers,
      redirect: "manual",
    };
    if (bodyBytes) {
      init.body = bodyBytes;
    }
    return fetch(target.toString(), init);
  }

  try {
    const response = await forwardTo(primaryOrigin);

    // Detect Cloudflare edge routing 404s (e.g. PoP propagation delay where edge returns empty 404)
    const isEdgeRouting404 =
      response.status === 404 &&
      (!response.headers.get("content-type") ||
        response.headers.get("content-length") === "0");

    if (isEdgeRouting404 && primaryOrigin !== FALLBACK_API_ORIGIN) {
      console.warn("Primary API origin returned edge 404; activating fallback origin", {
        primary: primaryOrigin,
        fallback: FALLBACK_API_ORIGIN,
        path: incoming.pathname,
      });
      try {
        const fallbackResponse = await forwardTo(FALLBACK_API_ORIGIN);
        const respHeaders = new Headers(fallbackResponse.headers);
        respHeaders.set("Cache-Control", "no-store");
        respHeaders.set("X-Upstream-Origin", FALLBACK_API_ORIGIN);
        respHeaders.set("X-Upstream-Fallback", "true");
        return new Response(fallbackResponse.body, {
          status: fallbackResponse.status,
          statusText: fallbackResponse.statusText,
          headers: respHeaders,
        });
      } catch (fallbackError) {
        console.error("Fallback API request failed", fallbackError);
      }
    }

    const responseHeaders = new Headers(response.headers);
    responseHeaders.set("Cache-Control", "no-store");
    responseHeaders.set("X-Upstream-Origin", primaryOrigin);
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (primaryError) {
    console.warn("Primary API origin error; activating fallback", primaryError);
    if (primaryOrigin !== FALLBACK_API_ORIGIN) {
      try {
        const fallbackResponse = await forwardTo(FALLBACK_API_ORIGIN);
        const respHeaders = new Headers(fallbackResponse.headers);
        respHeaders.set("Cache-Control", "no-store");
        respHeaders.set("X-Upstream-Origin", FALLBACK_API_ORIGIN);
        respHeaders.set("X-Upstream-Fallback", "true");
        return new Response(fallbackResponse.body, {
          status: fallbackResponse.status,
          statusText: fallbackResponse.statusText,
          headers: respHeaders,
        });
      } catch (fallbackError) {
        console.error("Fallback API request failed", fallbackError);
      }
    }

    return Response.json(
      { detail: "The application API is temporarily unavailable." },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}
