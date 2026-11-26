// POST /api/event — anonymous engagement events from the landing page.
import { readJson, noContent, json, sameOrigin, isBot, str } from "../../lib/http.js";

const ALLOWED = new Set([
  "page_view", "section_view", "scroll_depth", "engaged_30s",
  "cta_click", "plan_click", "calc_use", "calc_answer", "calc_result", "ai_toggle",
  "faq_open", "lang_switch", "theme_switch", "portal_replay", "compare_open",
  "form_start", "form_invalid", "form_submit", "form_error", "call_click", "details_submit", "details_skip",
]);

// Only known, short, primitive properties are kept, so nothing personal can slip in.
const PROP_KEYS = new Set(["section", "pct", "where", "plan", "source", "staff", "on", "q", "to", "industry", "size", "wants_call", "a", "pains", "payment"]);
function cleanProps(props) {
  const out = {};
  if (!props || typeof props !== "object") return out;
  for (const [k, v] of Object.entries(props).slice(0, 12)) {
    if (!PROP_KEYS.has(k)) continue;
    if (typeof v === "string") out[k] = v.slice(0, 60);
    else if (typeof v === "number" && Number.isFinite(v)) out[k] = v;
    else if (typeof v === "boolean") out[k] = v;
  }
  return out;
}

export async function onRequestPost({ request, env }) {
  if (!sameOrigin(request)) return json({ error: "forbidden" }, 403);
  if (isBot(request)) return noContent();

  const body = await readJson(request, 4096);
  if (!body || !ALLOWED.has(body.name)) return json({ error: "bad request" }, 400);

  const pid = str(body.pid, 16);
  if (!pid) return json({ error: "bad request" }, 400);
  const utm = body.utm && typeof body.utm === "object" ? body.utm : {};

  await env.DB.prepare(
    `INSERT INTO events (pid, name, props, lang, path, ref, utm_source, utm_medium, utm_campaign, utm_content, country, vw)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)`
  ).bind(
    pid,
    body.name,
    JSON.stringify(cleanProps(body.props)),
    str(body.lang, 5),
    str(body.path, 100),
    str(body.ref, 100),
    str(utm.utm_source, 100),
    str(utm.utm_medium, 100),
    str(utm.utm_campaign, 100),
    str(utm.utm_content, 100),
    request.cf?.country || null,
    Number.isInteger(body.vw) ? Math.min(Math.max(body.vw, 0), 10000) : null
  ).run();

  return noContent();
}
