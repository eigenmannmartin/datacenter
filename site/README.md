# Engagement-test website

A German landing page (with an English toggle) that tests demand for Rechenbox before any hardware is bought. It shows real prices, lets visitors "reserve a pilot slot" (a fake door that says plainly it is a free, non-binding pilot reservation), and asks qualifying questions. The go/no-go thresholds are in the business plan, section 1b.

- `public/`: static site: `index.html`, `datenschutz.html` (privacy and legal notice), `stats.html` (results dashboard), `assets/`
- `functions/api/`: Cloudflare Pages Functions: `event` (anonymous events), `signup` (form step 1), `details` (optional answers, form step 2), `stats` (funnel, token-protected)
- `lib/http.js`: shared helpers for the functions
- `schema.sql`: D1 tables `events` and `signups`

No cookies, no third-party requests: the Schibsted Grotesk font is self-hosted in `public/assets/fonts/` (SIL Open Font License, licence file alongside). Events carry a random id per page load that lives only in memory. Light and dark mode follow the system; the switch in the header overrides it for the current visit only.

## Run locally

```sh
cd site
npx wrangler d1 execute rechenbox --local --file=schema.sql
echo 'STATS_TOKEN=dev-token' > .dev.vars
npx wrangler pages dev
# open http://localhost:8788, and http://localhost:8788/stats with token "dev-token"
```

## Deploy

Every push to `main` that touches `site/` deploys automatically via `.github/workflows/deploy-site.yml`: it checks the JavaScript, applies `schema.sql` to the remote database (idempotent), deploys to Cloudflare Pages and smoke-tests the result. It can also be started by hand under Actions → Deploy site → Run workflow.

Already set up in Cloudflare (account `a1121094b30551cad6cd3d7681e5018a`):

- Zone `rechenbox.ch`, nameservers `apollo.ns.cloudflare.com` and `kate.ns.cloudflare.com`; always HTTPS, TLS 1.2 minimum, strict SSL
- DNS: `rechenbox.ch` and `www` as proxied CNAMEs to `rechenbox.pages.dev`; a redirect rule sends `www.rechenbox.ch` to `rechenbox.ch` (301)
- D1 database `rechenbox` (EU jurisdiction), schema applied
- Pages project `rechenbox` (production branch `main`) with the D1 binding, the `STATS_TOKEN` secret and both custom domains

Repository secrets the workflow needs: `CLOUDFLARE_API_TOKEN` (custom token with Account → Cloudflare Pages → Edit and Account → D1 → Edit) and `CLOUDFLARE_ACCOUNT_ID`.

Optional chat notification for new sign-ups: `npx wrangler pages secret put NOTIFY_WEBHOOK_URL --project-name rechenbox`.

## Before launch

- [ ] Fill in the legal notice placeholders in `public/datenschutz.html` and have the privacy text checked
- [ ] Set `bookingUrl` and `contactPhone` in `public/assets/config.js`, and make sure the mailbox `hallo@rechenbox.ch` exists
- [ ] Replace the working name "Rechenbox" once the name and trademark are decided
- [ ] Add an "About us" section with the founders' names, photos and background: the page review flagged this as the biggest trust gap for this audience
- [ ] Submit a test sign-up on the live site and check it in `/stats`

## Running the test

Tag every ad and post link with UTM parameters, e.g.
`https://rechenbox.ch/?utm_source=linkedin&utm_medium=paid&utm_campaign=treuhand-sg`.
Use `?lang=en` to link to the English version.

Read the results at `/stats`, or from the command line:

```sh
curl -s -H "Authorization: Bearer $STATS_TOKEN" https://rechenbox.ch/api/stats | jq .
```

Export the sign-ups (contains personal data, keep it safe):

```sh
npx wrangler d1 execute rechenbox --remote --json \
  --command "SELECT ts, name, company, email, phone, industry, size, plan, wants_call, timeline, price_view FROM signups ORDER BY ts DESC"
```

Events tracked: `page_view`, `section_view`, `scroll_depth`, `engaged_30s`, `cta_click`, `plan_click`, `calc_use`, `calc_answer`, `calc_result`, `faq_open`, `compare_open`, `lang_switch`, `theme_switch`, `portal_replay`, `form_start`, `form_invalid`, `form_submit`, `form_error`, `call_click`, `details_submit`, `details_skip`.
