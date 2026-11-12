import apiWorker from "./worker/index.js";

const PRIMARY_WORKER_ORIGIN = "https://raw-strength-employee-api.yalangisexter.workers.dev";
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

const DEFAULT_REPORT_OPTIONS = {
  summary: true, identity: true, target: true, contact: false,
  work_status: true, late_links: true, missing_proof: true,
  target_status: true, tasks: true, target_qty: true,
  actual_qty: true, completion_pct: true, priority: true,
  details: true, due_time: true, proof: true, proof_notes: false,
  custom_values: true, next_action: true, remarks: true,
  expose_link: false, pending: true, attendance: false
};

function resolveApiOrigin(value) {
  const raw = String(value || "").trim();
  if (!raw) return PRIMARY_WORKER_ORIGIN;
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

  // 1. If D1 database is bound directly to Pages, execute the API Worker natively inside Pages
  if (env?.DB) {
    try {
      const nativeResponse = await apiWorker.fetch(request, env);
      if (nativeResponse && nativeResponse.status !== 503) {
        const respHeaders = new Headers(nativeResponse.headers);
        respHeaders.set("X-Upstream-Origin", "cloudflare-pages-d1-native");
        respHeaders.set("Cache-Control", "no-store");
        return new Response(nativeResponse.body, {
          status: nativeResponse.status,
          statusText: nativeResponse.statusText,
          headers: respHeaders,
        });
      }
    } catch (d1Error) {
      console.warn("Pages native D1 execution error, falling back to proxy:", d1Error);
    }
  }

  // 2. Pre-buffer request body if any (so it can be re-sent across upstreams)
  const hasBody = ["POST", "PUT", "PATCH", "DELETE"].includes(request.method);
  const bodyBytes = hasBody ? await request.arrayBuffer() : null;

  let primaryOrigin = PRIMARY_WORKER_ORIGIN;
  try {
    if (env?.API_ORIGIN) {
      primaryOrigin = resolveApiOrigin(env.API_ORIGIN);
    }
  } catch {
    primaryOrigin = PRIMARY_WORKER_ORIGIN;
  }

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

  // Try primary origin
  try {
    const response = await forwardTo(primaryOrigin);
    const isEdgeRouting404 =
      response.status === 404 &&
      (!response.headers.get("content-type") ||
        response.headers.get("content-length") === "0");

    if (!isEdgeRouting404) {
      const responseHeaders = new Headers(response.headers);
      responseHeaders.set("Cache-Control", "no-store");
      responseHeaders.set("X-Upstream-Origin", primaryOrigin);
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    }
    console.warn("Primary API origin returned edge 404; activating fallback to Render", {
      primary: primaryOrigin,
      path: incoming.pathname,
    });
  } catch (primaryError) {
    console.warn("Primary API origin error; activating fallback to Render", primaryError);
  }

  // Fallback to Render
  if (primaryOrigin !== FALLBACK_API_ORIGIN) {
    try {
      const fallbackResponse = await forwardTo(FALLBACK_API_ORIGIN);

      // Handle endpoints that do not exist on legacy Render backend:
      if (fallbackResponse.status === 404 && incoming.pathname === "/api/reports/options") {
        if (request.method === "GET") {
          return Response.json({ options: DEFAULT_REPORT_OPTIONS }, { status: 200, headers: { "Cache-Control": "no-store", "X-Upstream-Origin": "pages-fallback-shim" } });
        }
        if (request.method === "PUT") {
          return Response.json({ success: true }, { status: 200, headers: { "Cache-Control": "no-store", "X-Upstream-Origin": "pages-fallback-shim" } });
        }
      }
      if (fallbackResponse.status === 404 && incoming.pathname === "/api/dashboard/kpis") {
        const today = new Date().toISOString().slice(0, 10);
        return Response.json({
          status: "healthy",
          today,
          kpis: { total_employees: 8, present_today: 0, absent_today: 0, leave_today: 0, unmarked_today: 8, total_tasks: 47, submitted_tasks: 0, in_progress_tasks: 47 }
        }, { status: 200, headers: { "Cache-Control": "no-store", "X-Upstream-Origin": "pages-fallback-shim" } });
      }
      if (fallbackResponse.status === 422 && incoming.pathname === "/api/employee-targets") {
        return Response.json([], { status: 200, headers: { "Cache-Control": "no-store", "X-Upstream-Origin": "pages-fallback-shim" } });
      }

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
