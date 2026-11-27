// POST /api/signup — pilot order form (step 1).
// A "fake door": the order holds real choices and prices, but nothing is paid and no contract is made.
// The choices beyond the plan (options, start) go to the table order_details, linked by the token.
import { readJson, json, sameOrigin, str, oneOf } from "../../lib/http.js";

const INDUSTRIES = ["fiduciary", "legal", "medical", "planning", "other"];
const SIZES = ["1-9", "10-20", "21-60", "61-100", "100+"];
const PLANS = ["start", "business", "pro"];
const PAYMENT_PREFS = ["monthly", "prepay", "purchase"];
const STARTS = ["lt6", "6to12", "gt12"];
const OPTIONS = ["offsite", "ai", "storage"];
const RECOMMENDED = ["start", "business", "pro"];
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
  const plan = oneOf(b.plan, PLANS);
  const payment = oneOf(b.payment_pref, PAYMENT_PREFS);
  const start = oneOf(b.start, STARTS);
  const emailOk = !!email && EMAIL_RE.test(email);

  if (!name || !company || !emailOk || !industry || !size || !plan || !payment || !start || b.consent !== true) {
    return json({
      error: "invalid",
      fields: {
        name: !!name, company: !!company, email: emailOk, industry: !!industry, size: !!size,
        plan: !!plan, payment_pref: !!payment, start: !!start, consent: b.consent === true,
      },
    }, 422);
  }

  // Double submit within 10 minutes: accept, don't store twice.
  const recent = await env.DB.prepare(
    "SELECT token FROM signups WHERE email = ?1 AND ts > strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-10 minutes') LIMIT 1"
  ).bind(email).first();
  if (recent) return json({ ok: true, ref: recent.token });

  // Private reference for the optional second step (/api/details). Never shown, never emailed.
  const token = crypto.randomUUID();
  const utm = b.utm && typeof b.utm === "object" ? b.utm : {};
  const options = pick(b.options, OPTIONS);

  // One transaction: the order is stored whole or not at all.
  await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO signups (name, company, email, phone, industry, size, plan, lang, utm_source, utm_medium, utm_campaign,
                            ref, country, payment_pref, token, recommended_plan)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16)`
    ).bind(
      name,
      company,
      email,
      str(b.phone, 40),
      industry,
      size,
      plan,
      oneOf(b.lang, ["de", "en"]),
      str(utm.utm_source, 100),
      str(utm.utm_medium, 100),
      str(utm.utm_campaign, 100),
      str(b.ref, 100),
      request.cf?.country || null,
      payment,
      token,
      oneOf(b.recommended_plan, RECOMMENDED)
    ),
    env.DB.prepare("INSERT INTO order_details (token, options, start) VALUES (?1, ?2, ?3)").bind(
      token,
      JSON.stringify(options),
      start
    ),
  ]);

  // Optional chat notification (Slack/Teams incoming webhook). No name, email or phone in the message.
  if (env.NOTIFY_WEBHOOK_URL) {
    const extras = options.length ? ` with ${options.join(", ")}` : "";
    const text = `New pilot order: ${company} (${industry}, ${size} staff), ${plan}${extras}, payment ${payment}, start ${start}.`;
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
