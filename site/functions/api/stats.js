// GET /api/stats — funnel and sign-up breakdowns. Requires "Authorization: Bearer <STATS_TOKEN>".
import { json, safeEqual } from "../../lib/http.js";

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

async function count(db, sql, since) {
  const row = await db.prepare(sql).bind(since).first();
  return row ? Number(row.n) || 0 : 0;
}

async function groups(db, sql, since) {
  const { results } = await db.prepare(sql).bind(since).all();
  return results.map((r) => ({ k: r.k === null ? null : String(r.k), n: Number(r.n) }));
}

export async function onRequestGet({ request, env }) {
  if (!env.STATS_TOKEN) return json({ error: "stats disabled: set STATS_TOKEN" }, 503);
  const auth = request.headers.get("Authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  if (!token || !safeEqual(token, env.STATS_TOKEN)) return json({ error: "unauthorized" }, 401);

  const sinceParam = new URL(request.url).searchParams.get("since");
  const since = sinceParam && DATE_RE.test(sinceParam) ? sinceParam : "1970-01-01";
  const db = env.DB;
  const ev = (name) => `FROM events WHERE name = '${name}' AND ts >= ?1`; // names are constants, never user input

  const [
    pageViews, engaged, pricingViews, planClicks, formStarts, aiInterest,
    planClickGroups, sources, sections, faq,
    total, wantsCall, industry, size, plan, priceView, timeline, pains, currentIt, signupSources, paymentPref, calcResults, calcAnswers,
  ] = await Promise.all([
    count(db, `SELECT COUNT(*) n ${ev("page_view")}`, since),
    count(db, `SELECT COUNT(DISTINCT pid) n ${ev("engaged_30s")}`, since),
    count(db, `SELECT COUNT(DISTINCT pid) n ${ev("section_view")} AND json_extract(props, '$.section') = 'pricing'`, since),
    count(db, `SELECT COUNT(*) n ${ev("plan_click")}`, since),
    count(db, `SELECT COUNT(DISTINCT pid) n ${ev("form_start")}`, since),
    count(db, `SELECT COUNT(DISTINCT pid) n FROM events WHERE ts >= ?1 AND (
                 (name = 'ai_toggle' AND json_extract(props, '$.on') = 1) OR
                 (name = 'section_view' AND json_extract(props, '$.section') = 'ai'))`, since),
    groups(db, `SELECT json_extract(props, '$.plan') k, COUNT(*) n ${ev("plan_click")} GROUP BY k ORDER BY n DESC`, since),
    groups(db, `SELECT COALESCE(utm_source, NULLIF(ref, ''), 'direct') k, COUNT(*) n ${ev("page_view")} GROUP BY k ORDER BY n DESC LIMIT 20`, since),
    groups(db, `SELECT json_extract(props, '$.section') k, COUNT(DISTINCT pid) n ${ev("section_view")} GROUP BY k ORDER BY n DESC`, since),
    groups(db, `SELECT json_extract(props, '$.q') k, COUNT(*) n ${ev("faq_open")} GROUP BY k ORDER BY n DESC`, since),
    count(db, "SELECT COUNT(*) n FROM signups WHERE ts >= ?1", since),
    count(db, "SELECT COUNT(*) n FROM signups WHERE wants_call = 1 AND ts >= ?1", since),
    groups(db, "SELECT industry k, COUNT(*) n FROM signups WHERE ts >= ?1 GROUP BY k ORDER BY n DESC", since),
    groups(db, "SELECT size k, COUNT(*) n FROM signups WHERE ts >= ?1 GROUP BY k ORDER BY n DESC", since),
    groups(db, "SELECT plan k, COUNT(*) n FROM signups WHERE ts >= ?1 GROUP BY k ORDER BY n DESC", since),
    groups(db, "SELECT price_view k, COUNT(*) n FROM signups WHERE ts >= ?1 GROUP BY k ORDER BY n DESC", since),
    groups(db, "SELECT timeline k, COUNT(*) n FROM signups WHERE ts >= ?1 GROUP BY k ORDER BY n DESC", since),
    groups(db, "SELECT j.value k, COUNT(*) n FROM signups, json_each(signups.pains) j WHERE signups.ts >= ?1 GROUP BY k ORDER BY n DESC", since),
    groups(db, "SELECT j.value k, COUNT(*) n FROM signups, json_each(signups.current_it) j WHERE signups.ts >= ?1 GROUP BY k ORDER BY n DESC", since),
    groups(db, "SELECT COALESCE(utm_source, NULLIF(ref, ''), 'direct') k, COUNT(*) n FROM signups WHERE ts >= ?1 GROUP BY k ORDER BY n DESC", since),
    groups(db, "SELECT payment_pref k, COUNT(*) n FROM signups WHERE ts >= ?1 GROUP BY k ORDER BY n DESC", since),
    // Last recommendation per page view, so changing answers doesn't double count
    groups(db, `SELECT plan k, COUNT(*) n FROM (
                  SELECT pid, json_extract(props, '$.plan') plan, MAX(id) FROM events
                  WHERE name = 'calc_result' AND ts >= ?1 GROUP BY pid)
                GROUP BY k ORDER BY n DESC`, since),
    groups(db, `SELECT json_extract(props, '$.q') || ': ' || json_extract(props, '$.a') k, COUNT(DISTINCT pid) n
                FROM events WHERE name = 'calc_answer' AND json_extract(props, '$.q') != 'staff' AND ts >= ?1
                GROUP BY k ORDER BY k`, since),
  ]);

  return json({
    generated_at: new Date().toISOString(),
    since: sinceParam && DATE_RE.test(sinceParam) ? since : null,
    funnel: {
      page_views: pageViews,
      engaged,
      pricing_views: pricingViews,
      plan_clicks: planClicks,
      form_starts: formStarts,
      ai_interest: aiInterest,
    },
    plan_clicks: planClickGroups,
    calc_results: calcResults,
    calc_answers: calcAnswers,
    sources,
    sections,
    faq,
    signups: {
      total,
      wants_call: wantsCall,
      industry,
      size,
      plan,
      price_view: priceView,
      timeline,
      pains,
      current_it: currentIt,
      sources: signupSources,
      payment_pref: paymentPref,
    },
  });
}
