// POST /api/signup — waitlist / pilot reservation form.
import { readJson, json, sameOrigin, str, oneOf } from "../../lib/http.js";

const INDUSTRIES = ["fiduciary", "legal", "medical", "planning", "other"];
const SIZES = ["1-9", "10-20", "21-60", "61-100", "100+"];
const PLANS = ["undecided", "start", "business", "pro"];
const TIMELINES = ["lt6", "6to12", "gt12", "info"];
const PRICE_VIEWS = ["cheap", "fair", "expensive", "unsure"];
const PAYMENT_PREFS = ["monthly", "prepay", "purchase", "undecided"];
const RECOMMENDED = ["start", "business", "pro"];
const CURRENT_IT = ["own_server", "m365", "nas", "swiss_cloud", "it_partner", "unknown"];
const PAINS = ["confidentiality", "ransomware", "server_eol", "cost", "ai", "performance"];
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function pick(list, allowed) {
  return Array.isArray(list) ? [...new Set(list.filter((v) => allowed.includes(v)))] : [];
}

export async function onRequestPost({ request, env, waitUntil }) {
  if (!sameOrigin(request)) return json({ error: "forbidden" }, 403);

  const b = await readJson(request, 16384);
  if (!b) return json({ error: "bad request" }, 400);

  // Honeypot filled in: pretend success, store nothing.
  if (typeof b.website === "string" && b.website.trim() !== "") return json({ ok: true, ref: crypto.randomUUID() });

  const name = str(b.name, 120);
  const company = str(b.company, 160);
  const email = str(b.email, 200)?.toLowerCase() || null;
  const industry = oneOf(b.industry, INDUSTRIES);
  const size = oneOf(b.size, SIZES);

  if (!name || !company || !email || !EMAIL_RE.test(email) || !industry || !size || b.consent !== true) {
    return json({ error: "invalid", fields: { name: !!name, company: !!company, email: !!email && EMAIL_RE.test(email), industry: !!industry, size: !!size, consent: b.consent === true } }, 422);
  }

  // Double submit within 10 minutes: accept, don't store twice.
  const recent = await env.DB.prepare(
    "SELECT token FROM signups WHERE email = ?1 AND ts > strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-10 minutes') LIMIT 1"
  ).bind(email).first();
  if (recent) return json({ ok: true, ref: recent.token });

  // Private reference for the optional second step (/api/details). Never shown, never emailed.
  const token = crypto.randomUUID();

  const utm = b.utm && typeof b.utm === "object" ? b.utm : {};
  const plan = oneOf(b.plan, PLANS) || "undecided";

  await env.DB.prepare(
    `INSERT INTO signups (name, company, email, phone, industry, size, current_it, pains, plan, timeline, price_view,
                          message, wants_call, lang, utm_source, utm_medium, utm_campaign, ref, country, payment_pref, token, recommended_plan)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19, ?20, ?21, ?22)`
  ).bind(
    name,
    company,
    email,
    str(b.phone, 40),
    industry,
    size,
    JSON.stringify(pick(b.current_it, CURRENT_IT)),
    JSON.stringify(pick(b.pains, PAINS)),
    plan,
    oneOf(b.timeline, TIMELINES),
    oneOf(b.price_view, PRICE_VIEWS),
    str(b.message, 2000),
    b.wants_call === true ? 1 : 0,
    oneOf(b.lang, ["de", "en"]),
    str(utm.utm_source, 100),
    str(utm.utm_medium, 100),
    str(utm.utm_campaign, 100),
    str(b.ref, 100),
    request.cf?.country || null,
    oneOf(b.payment_pref, PAYMENT_PREFS),
    token,
    oneOf(b.recommended_plan, RECOMMENDED)
  ).run();

  // Optional chat notification (Slack/Teams incoming webhook). No email or phone in the message.
  if (env.NOTIFY_WEBHOOK_URL) {
    const text = `New pilot reservation: ${company} (${industry}, ${size} staff), plan ${plan}${b.wants_call === true ? ", wants a call" : ""}.`;
    waitUntil(
      fetch(env.NOTIFY_WEBHOOK_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      }).catch(() => {})
    );
  }

  return json({ ok: true, ref: token }, 201);
}
