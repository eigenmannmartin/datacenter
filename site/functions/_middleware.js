// Pre-launch gate for the whole site (pages, assets and API).
//
// While the Pages secret SITE_PASSWORD is set:
//   - every request needs HTTP Basic auth: any user name, that password
//   - every response carries "X-Robots-Tag: noindex, nofollow"
//   - /robots.txt disallows all crawlers
// To launch: delete the secret (npx wrangler pages secret delete SITE_PASSWORD --project-name rechenbox)
// and redeploy. Without the secret this middleware does nothing.

const REALM = "Rechenbox Vorschau";
const NOINDEX = "noindex, nofollow";

function sameText(a, b) {
  const enc = new TextEncoder();
  const x = enc.encode(String(a));
  const y = enc.encode(String(b));
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) diff |= (x[i] || 0) ^ (y[i] || 0);
  return diff === 0;
}

function passwordFrom(request) {
  const auth = request.headers.get("Authorization") || "";
  if (!auth.startsWith("Basic ")) return null;
  try {
    const decoded = atob(auth.slice(6));
    return decoded.slice(decoded.indexOf(":") + 1);
  } catch {
    return null;
  }
}

export async function onRequest({ request, env, next }) {
  const password = env.SITE_PASSWORD;
  if (!password) return next();

  const url = new URL(request.url);
  if (url.pathname === "/robots.txt") {
    return new Response("User-agent: *\nDisallow: /\n", {
      headers: { "Content-Type": "text/plain; charset=utf-8", "X-Robots-Tag": NOINDEX },
    });
  }

  const given = passwordFrom(request);
  if (given === null || !sameText(given, password)) {
    return new Response("Diese Seite ist noch nicht öffentlich. / This site is not public yet.\n", {
      status: 401,
      headers: {
        "WWW-Authenticate": `Basic realm="${REALM}", charset="UTF-8"`,
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
        "X-Robots-Tag": NOINDEX,
      },
    });
  }

  const res = await next();
  const out = new Response(res.body, res);
  out.headers.set("X-Robots-Tag", NOINDEX);
  out.headers.set("Cache-Control", "private, no-store");
  return out;
}
