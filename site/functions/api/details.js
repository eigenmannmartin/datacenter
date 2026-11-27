// POST /api/details — optional answers sent after an order (second form step).
// Identified by the private reference returned from /api/signup; accepted once.
// Payment and start come with the order itself, so this step leaves them alone.
import { readJson, json, sameOrigin, str, oneOf } from "../../lib/http.js";

const PRICE_VIEWS = ["cheap", "fair", "expensive", "unsure"];
const CURRENT_IT = ["own_server", "m365", "nas", "swiss_cloud", "it_partner", "unknown"];
const PAINS = ["confidentiality", "ransomware", "server_eol", "cost", "ai", "performance"];
const REF_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

function pick(list, allowed) {
  return Array.isArray(list) ? [...new Set(list.filter((v) => allowed.includes(v)))] : [];
}

export async function onRequestPost({ request, env }) {
  if (!sameOrigin(request)) return json({ error: "forbidden" }, 403);
  const b = await readJson(request, 8192);
  if (!b || typeof b.ref !== "string" || !REF_RE.test(b.ref)) return json({ error: "bad request" }, 400);

  const result = await env.DB.prepare(
    `UPDATE signups SET current_it = ?2, pains = ?3, price_view = ?4,
            message = COALESCE(?5, message), details_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE token = ?1 AND details_at IS NULL
       AND ts > strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-1 day')`
  ).bind(
    b.ref,
    JSON.stringify(pick(b.current_it, CURRENT_IT)),
    JSON.stringify(pick(b.pains, PAINS)),
    oneOf(b.price_view, PRICE_VIEWS),
    str(b.message, 2000)
  ).run();

  // Unknown, expired or already used reference: answer the same way, reveal nothing.
  if (!result.meta || result.meta.changes !== 1) return json({ ok: true, stored: false });
  return json({ ok: true, stored: true });
}
