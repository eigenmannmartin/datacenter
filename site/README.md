# Engagement-test website

A German landing page (with an English toggle) at [rechenbox.ch](https://rechenbox.ch) that tests demand for Rechenbox before any hardware is bought. It shows real prices, lets visitors "reserve a pilot slot" (a fake door that says plainly it is a free, non-binding pilot reservation), and asks qualifying questions. The go/no-go thresholds are in the business plan, section 1b.

- `public/`: static site: `index.html`, `datenschutz.html` (privacy and legal notice), `assets/`
- `functions/_middleware.js`: pre-launch password gate and `noindex` (see below)
- `functions/api/`: Cloudflare Pages Functions: `signup` (form step 1), `details` (optional answers, form step 2)
- `lib/http.js`: shared helpers for the functions
- `schema.sql`: D1 table `signups`

The picture of the box on the first screen is a rendering, not a photo, and the page says so ("Visualisierung"). There is one file per colour scheme, `public/assets/img/rack-light.webp` and `rack-dark.webp`, made with [`docs/rack.py`](../docs/rack.py):

```sh
python3 docs/rack.py --shot studio-light --samples 192 --scale 1.0 --out out/studio-light.png   # about 11 minutes on 3 cores
python3 docs/rack.py --shot studio-dark  --samples 192 --scale 1.0 --out out/studio-dark.png
```

then resize to 1200 x 1500 px and save as WebP with the alpha channel. On load the box settles into place, a sheen crosses its glass door and the status lights come on; after that only the lights keep moving (nothing moves for visitors who ask for reduced motion). Sheen and lights are drawn over the picture: the lights' positions are the `--x` / `--y` values in `public/index.html`, the outline of the door is the `clip-path` of `.rack-sheen` in `public/assets/styles.css`. Both are shares of the picture's size and have to be set again if the camera or the order of the devices changes.

No cookies. The Schibsted Grotesk font is self-hosted in `public/assets/fonts/` (SIL Open Font License, licence file alongside). Visitor statistics come from Cloudflare Web Analytics, which Cloudflare injects at the edge; the site code contains no tracking. Light and dark mode follow the system; the switch in the header overrides it for the current visit only.

## Pre-launch password gate

Until the marketing campaign starts, the whole site (both `rechenbox.ch` and `rechenbox.pages.dev`) asks for a password, sends `X-Robots-Tag: noindex, nofollow` and serves a `robots.txt` that disallows all crawlers. Any user name works; the password is the Pages secret `SITE_PASSWORD`.

To launch:

```sh
cd site
npx wrangler pages secret delete SITE_PASSWORD --project-name rechenbox
```

then redeploy (Actions → Deploy site → Run workflow). Without the secret the middleware does nothing. Also submit `https://rechenbox.ch` in Google Search Console once it is public.

## Reading the results

Everything is in the Cloudflare dashboard, behind your Cloudflare login. Nothing needs to be built or hosted for it.

| What | Where |
| --- | --- |
| Visits, sources, countries, pages, devices | [Web Analytics](https://dash.cloudflare.com/a1121094b30551cad6cd3d7681e5018a/web-analytics) → rechenbox.ch |
| Sign-ups: browse, filter, edit, delete | [D1 → rechenbox](https://dash.cloudflare.com/a1121094b30551cad6cd3d7681e5018a/workers/d1/databases/04a95002-a17e-4d1d-9f9c-0aff3d9c9333) → Tables → `signups` |
| Funnel numbers | Same database → Console, with the queries below |

Each sign-up row holds the contact details, the plan chosen, what the plan picker recommended (`recommended_plan`), the optional answers (pains, timeline, payment preference, price view) and the lead source (`utm_source`, `utm_campaign`, `ref`). Visit-to-sign-up conversion = sign-ups ÷ visits in Web Analytics for the same period.

Queries for the D1 console:

```sql
-- Sign-ups, newest first
SELECT ts, name, company, email, phone, industry, size, plan, recommended_plan, wants_call FROM signups ORDER BY ts DESC;

-- Go/no-go: total, share wanting a call, share calling the price too expensive
SELECT COUNT(*) AS signups,
       ROUND(100.0 * SUM(wants_call) / COUNT(*), 1) AS pct_want_call,
       ROUND(100.0 * SUM(price_view = 'expensive') / NULLIF(SUM(price_view IS NOT NULL), 0), 1) AS pct_too_expensive
FROM signups;

-- Which pains come up most
SELECT j.value AS pain, COUNT(*) AS n FROM signups, json_each(signups.pains) j GROUP BY pain ORDER BY n DESC;

-- By industry, plan, payment preference or lead source (swap the column)
SELECT industry, COUNT(*) AS n FROM signups GROUP BY industry ORDER BY n DESC;
SELECT COALESCE(utm_source, ref, 'direct') AS source, COUNT(*) AS n FROM signups GROUP BY source ORDER BY n DESC;
```

Optional: get a chat message for every new sign-up (Slack or Teams incoming webhook, no email or phone in the message):
`npx wrangler pages secret put NOTIFY_WEBHOOK_URL --project-name rechenbox`.

## Running the test

Tag every ad and post link with UTM parameters, e.g.
`https://rechenbox.ch/?utm_source=linkedin&utm_medium=paid&utm_campaign=treuhand-sg`.
Use `?lang=en` to link to the English version.

## Deploy

Every push to `main` that touches `site/` deploys automatically via `.github/workflows/deploy-site.yml`: it checks the JavaScript, applies `schema.sql` to the remote database (idempotent), deploys to Cloudflare Pages and smoke-tests the result. It can also be started by hand under Actions → Deploy site → Run workflow.

Every pull request that touches `site/` gets a preview via `.github/workflows/preview-site.yml`, at `https://<branch>.rechenbox.pages.dev`. The workflow posts the link as a comment on the pull request and updates it on each push. Previews use the separate D1 database `rechenbox-preview` (EU), so test sign-ups never mix with real ones, and the same password gate as production. Pull requests from forks are skipped, because they get no secrets.

Set up in Cloudflare (account `a1121094b30551cad6cd3d7681e5018a`):

- Zone `rechenbox.ch`, nameservers `apollo.ns.cloudflare.com` and `kate.ns.cloudflare.com`; always HTTPS, TLS 1.2 minimum, strict SSL
- DNS: `rechenbox.ch` and `www` as proxied CNAMEs to `rechenbox.pages.dev`; a redirect rule sends `www.rechenbox.ch` to `rechenbox.ch` (301)
- Web Analytics for `rechenbox.ch`, injected automatically
- Mail at Infomaniak: MX `mta-gw.infomaniak.ch` (priority 5), SPF `include:spf.infomaniak.ch -all`, DMARC `p=reject`, `autodiscover`/`autoconfig` CNAMEs to `infomaniak.com` (all DNS only, not proxied). DKIM still to add from the Infomaniak Manager
- D1 databases `rechenbox` (production) and `rechenbox-preview` (pull request previews), both EU jurisdiction
- Pages project `rechenbox` (production branch `main`) with the D1 binding, both custom domains and the `SITE_PASSWORD` secret
- Account API token `rechenbox-github-deploy` (Pages Write, D1 Write on this account only; expires 2027-11-26), stored as the repository secret `CLOUDFLARE_API_TOKEN` next to `CLOUDFLARE_ACCOUNT_ID`. Renew it before it expires: Manage Account → Account API Tokens.

## Run locally

```sh
cd site
npx wrangler d1 execute rechenbox --local --file=schema.sql
npx wrangler pages dev
# open http://localhost:8788
```

## Before launch

- [ ] Fill in the legal notice placeholders in `public/datenschutz.html` and have the privacy text checked
- [ ] Set `bookingUrl` and `contactPhone` in `public/assets/config.js`, and make sure the mailbox `hallo@rechenbox.ch` exists
- [ ] Check the name "Rechenbox" in Zefix and Swissreg
- [ ] Add an "About us" section with the founders' names, photos and background: the page review flagged this as the biggest trust gap for this audience
- [ ] Check four statements the page makes as given, which `docs/hardware.md` describes as planned: the sync app for PC, Mac and phone with sharing by link, sign-in for remote access confirmed on the phone, business software (accounting, practice, CAD licence server) running on the box, and that files stay with the old provider until the customer has checked the move
- [ ] The task durations in the portal section are labelled as targets and the portal picture as a draft: measure them once the portal exists
- [ ] Measure power draw and noise in the lab; the page gives the design target for power and says both are not measured yet
- [ ] Decide whether "I'd like a short call" in the form stays pre-ticked: it raises the share of sign-ups that ask for a call, which is one of the go/no-go figures
- [ ] Submit a test sign-up on the live site, find it in the D1 table, then delete it there
