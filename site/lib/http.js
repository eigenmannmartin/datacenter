// Shared helpers for the Pages Functions. Lives outside functions/ so it is not routed.

export function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...extraHeaders,
    },
  });
}

export function noContent() {
  return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
}

// Reads a JSON body with a hard size cap. Returns null when missing, too large or invalid.
export async function readJson(request, maxBytes) {
  const declared = Number(request.headers.get("Content-Length") || 0);
  if (declared > maxBytes) return null;
  let text;
  try {
    text = await request.text();
  } catch {
    return null;
  }
  if (!text || text.length > maxBytes) return null;
  try {
    const value = JSON.parse(text);
    return value && typeof value === "object" && !Array.isArray(value) ? value : null;
  } catch {
    return null;
  }
}

// Rejects requests posted from other sites. Beacons and fetches from our own page carry our Origin.
export function sameOrigin(request) {
  const origin = request.headers.get("Origin");
  if (!origin) return true; // some browsers omit Origin on same-origin beacons
  try {
    return new URL(origin).host === new URL(request.url).host;
  } catch {
    return false;
  }
}

const BOT_RE = /bot|crawl|spider|slurp|preview|headless|lighthouse|monitor|curl|wget|python-requests|httpclient/i;
export function isBot(request) {
  return BOT_RE.test(request.headers.get("User-Agent") || "");
}

export function str(value, max) {
  if (typeof value !== "string") return null;
  const v = value.trim();
  return v ? v.slice(0, max) : null;
}

export function oneOf(value, allowed) {
  return allowed.includes(value) ? value : null;
}

// Constant-time string comparison for the stats token.
export function safeEqual(a, b) {
  const enc = new TextEncoder();
  const x = enc.encode(String(a));
  const y = enc.encode(String(b));
  let diff = x.length ^ y.length;
  const len = Math.max(x.length, y.length);
  for (let i = 0; i < len; i++) diff |= (x[i] || 0) ^ (y[i] || 0);
  return diff === 0;
}
