/* Rechenbox landing page: language and theme switches, plan recommender,
 * portal demo, two-step sign-up form, and anonymous cookie-less event logging
 * to /api/event (first party only). */
(function () {
  "use strict";

  var CONFIG = window.RECHENBOX_CONFIG || {};
  var EN = window.RECHENBOX_EN || {};
  var root = document.documentElement;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Strings that only exist in JavaScript.
  var MSG = {
    de: {
      langToggle: "Switch to English",
      themeToDark: "Dunkles Design einschalten",
      themeToLight: "Helles Design einschalten",
      required: "Bitte füllen Sie die markierten Felder aus.",
      email: "Bitte geben Sie eine gültige E-Mail-Adresse ein.",
      consent: "Bitte bestätigen Sie die Einwilligung zur Datenspeicherung.",
      network: "Die Übermittlung hat nicht geklappt. Bitte prüfen Sie Ihre Verbindung und versuchen Sie es erneut.",
      server: "Die Übermittlung hat nicht geklappt. Bitte versuchen Sie es später erneut oder schreiben Sie uns eine E-Mail.",
      sending: "Wird gesendet…",
      skipped: "Alles klar. Wir melden uns bald.",
      typedName: "Anna Meier",
      rStart: "Ein Tag Ausfall ist verkraftbar. Eine Box mit Ersatzgerät am nächsten Arbeitstag reicht.",
      rSize: "Ab etwa 20 Mitarbeitenden lohnt sich die Ausfallsicherheit von drei Servern.",
      rDowntime: "Ein Ausfall kostet Sie Umsatz oder Arbeitszeit. Drei Server ersetzen sich gegenseitig, ohne Unterbruch.",
      rHours: "Business: Reaktion am selben Arbeitstag.",
      rNow: "Pro: Alarmierung rund um die Uhr, Reaktion am selben Tag, auch am Wochenende.",
      rCritical: "Wenn Sie ohne IT nicht arbeiten können, zählt auch das Wochenende."
    },
    en: {
      langToggle: "Auf Deutsch wechseln",
      themeToDark: "Switch to dark design",
      themeToLight: "Switch to light design",
      required: "Please fill in the highlighted fields.",
      email: "Please enter a valid email address.",
      consent: "Please confirm your consent to storing your details.",
      network: "Sending failed. Please check your connection and try again.",
      server: "Sending failed. Please try again later or send us an email.",
      sending: "Sending…",
      skipped: "All right. We'll be in touch soon.",
      typedName: "Anna Meier",
      rStart: "A day of downtime is bearable. One box with a replacement on the next working day is enough.",
      rSize: "From about 20 staff, the failover of three servers pays off.",
      rDowntime: "Downtime costs you revenue or working time. Three servers stand in for each other without interruption.",
      rHours: "Business: response on the same working day.",
      rNow: "Pro: alerting around the clock, response the same day, weekends included.",
      rCritical: "If you cannot work without IT, weekends count too."
    }
  };

  var PLAN_NAMES = { start: "Start", business: "Business", pro: "Pro" };

  var params = new URLSearchParams(location.search);
  var lang = params.get("lang") === "en" ? "en" : "de";

  // ---------- Event logging ----------
  // A random id per page load, kept in memory only: no cookies, no storage.
  var pageId = Math.random().toString(36).slice(2, 12);
  var utm = {};
  ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"].forEach(function (k) {
    var v = params.get(k);
    if (v) utm[k] = v.slice(0, 100);
  });
  var referrerHost = "";
  try { referrerHost = document.referrer ? new URL(document.referrer).hostname : ""; } catch (e) { /* ignore */ }

  function track(name, props) {
    if (CONFIG.trackEvents === false) return;
    var body = JSON.stringify({ name: name, props: props || {}, pid: pageId, lang: lang, path: location.pathname, ref: referrerHost, utm: utm, vw: window.innerWidth });
    try {
      if (navigator.sendBeacon && navigator.sendBeacon("/api/event", new Blob([body], { type: "application/json" }))) return;
    } catch (e) { /* fall through */ }
    try { fetch("/api/event", { method: "POST", headers: { "Content-Type": "application/json" }, body: body, keepalive: true }).catch(function () {}); } catch (e) { /* never break the page */ }
  }
  var sentOnce = {};
  function trackOnce(key, name, props) { if (sentOnce[key]) return; sentOnce[key] = true; track(name, props); }

  function money(n) {
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, lang === "en" ? "," : "'");
  }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function $(id) { return document.getElementById(id); }

  // ---------- Theme ----------
  // Follows the system until the visitor picks one. Not stored: the page keeps nothing on the device.
  var systemDark = window.matchMedia("(prefers-color-scheme: dark)");
  function isDark() {
    var t = root.getAttribute("data-theme");
    return t ? t === "dark" : systemDark.matches;
  }
  function updateThemeButton() {
    $("theme-toggle").setAttribute("aria-label", isDark() ? MSG[lang].themeToLight : MSG[lang].themeToDark);
    var meta = document.querySelectorAll('meta[name="theme-color"]');
    meta.forEach(function (m) { m.setAttribute("content", isDark() ? "#0e0f10" : "#ffffff"); m.removeAttribute("media"); });
  }
  $("theme-toggle").addEventListener("click", function () {
    root.setAttribute("data-theme", isDark() ? "light" : "dark");
    updateThemeButton();
    track("theme_switch", { to: isDark() ? "dark" : "light" });
  });
  systemDark.addEventListener("change", updateThemeButton);

  // ---------- Language ----------
  var originals = new Map();
  function remember(el, kind) {
    if (!originals.has(el)) originals.set(el, {});
    var store = originals.get(el);
    if (!(kind in store)) {
      if (kind === "text") store.text = el.textContent;
      else if (kind === "html") store.html = el.innerHTML;
      else store[kind] = el.getAttribute(kind.slice(5));
    }
    return store;
  }

  function applyLang() {
    var en = lang === "en";
    root.lang = en ? "en" : "de-CH";
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var store = remember(el, "text");
      var val = EN[el.getAttribute("data-i18n")];
      el.textContent = en && val ? val : store.text;
    });
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) {
      var store = remember(el, "html");
      var val = EN[el.getAttribute("data-i18n-html")];
      el.innerHTML = en && val ? val : store.html; // values come from our own static dictionary
    });
    document.querySelectorAll("[data-i18n-attr]").forEach(function (el) {
      el.getAttribute("data-i18n-attr").split(";").forEach(function (pair) {
        var parts = pair.split(":");
        var store = remember(el, "attr:" + parts[0]);
        var val = EN[parts[1]];
        el.setAttribute(parts[0], en && val ? val : store["attr:" + parts[0]]);
      });
    });
    document.querySelectorAll(".amount, .amount-plain, #f-plan option").forEach(function (el) {
      el.textContent = en ? el.textContent.replace(/(\d)'(\d)/g, "$1,$2") : el.textContent.replace(/(\d),(\d)/g, "$1'$2");
    });
    var toggle = $("lang-toggle");
    toggle.textContent = en ? "DE" : "EN";
    toggle.setAttribute("lang", en ? "de" : "en");
    toggle.setAttribute("aria-label", MSG[lang].langToggle);
    document.title = en ? "Rechenbox – your server box in the office" : "Rechenbox – Ihre Server-Box im Büro";
    updateThemeButton();
    updateCalc(false);
    if (portal.done) $("portal-typed").textContent = MSG[lang].typedName;
  }

  $("lang-toggle").addEventListener("click", function () {
    lang = lang === "en" ? "de" : "en";
    var p = new URLSearchParams(location.search);
    if (lang === "en") p.set("lang", "en"); else p.delete("lang");
    var qs = p.toString();
    history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
    applyLang();
    track("lang_switch", { to: lang });
  });

  // ---------- Recommender ----------
  // Start is one box; Business and Pro share the same hardware and differ in support.
  var QUESTIONS = ["size", "downtime", "response"];
  var lastTrackedResult = null;
  var resultTimer;

  function answer(q) {
    var el = document.querySelector('input[name="calc-' + q + '"]:checked');
    return el ? el.value : null;
  }

  function recommend(a) {
    var reasons = [];
    var plan;
    if (a.response === "always") {
      plan = "pro";
      reasons.push("rNow");
      if (a.downtime === "critical") reasons.push("rCritical");
    } else if (a.size !== "small" || a.downtime !== "ok" || a.response === "sameday") {
      plan = "business";
      if (a.downtime !== "ok") reasons.push("rDowntime");
      if (a.size !== "small") reasons.push("rSize");
      if (a.response === "sameday") reasons.push("rHours");
    } else {
      plan = "start";
      reasons.push("rStart");
    }
    return { plan: plan, reasons: reasons };
  }

  function updateCalc(fromUser) {
    var a = {};
    var answered = 0;
    QUESTIONS.forEach(function (q) { a[q] = answer(q); if (a[q]) answered++; });
    var done = answered === QUESTIONS.length;
    $("calc-pending").hidden = done;
    $("calc-done").hidden = !done;
    if (fromUser) trackOnce("calc", "calc_use", {});

    var r = done ? recommend(a) : null;
    document.querySelectorAll(".plan").forEach(function (card) {
      card.classList.toggle("recommended", !!r && card.getAttribute("data-plan") === r.plan);
    });
    if (!r) return;

    $("calc-plan-name").textContent = PLAN_NAMES[r.plan];
    var list = $("calc-reasons");
    list.textContent = "";
    r.reasons.forEach(function (key) {
      var li = document.createElement("li");
      li.textContent = MSG[lang][key];
      list.appendChild(li);
    });
    if (fromUser) {
      clearTimeout(resultTimer);
      resultTimer = setTimeout(function () {
        if (r.plan !== lastTrackedResult) { lastTrackedResult = r.plan; track("calc_result", { plan: r.plan }); }
      }, 1500);
    }
  }

  QUESTIONS.forEach(function (q) {
    document.querySelectorAll('input[name="calc-' + q + '"]').forEach(function (el) {
      el.addEventListener("change", function () { updateCalc(true); track("calc_answer", { q: q, a: el.value }); });
    });
  });

  // ---------- Plan buttons ("fake door") ----------
  var planSelect = $("f-plan");
  function goToForm(plan, source) {
    if (plan && planSelect.querySelector('option[value="' + plan + '"]')) planSelect.value = plan;
    track("plan_click", { plan: plan || "none", source: source });
    $("anmelden").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
    setTimeout(function () { $("f-name").focus({ preventScroll: true }); }, reduceMotion ? 0 : 450);
  }
  document.querySelectorAll("[data-plan-select]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var plan = btn.getAttribute("data-plan-select");
      var card = btn.closest(".plan");
      goToForm(plan, card && card.classList.contains("recommended") ? "recommended" : "pricing");
    });
  });
  document.querySelectorAll("[data-track-cta]").forEach(function (a) {
    a.addEventListener("click", function () { track("cta_click", { where: a.getAttribute("data-track-cta") }); });
  });

  // ---------- Portal demo: the page's one orchestrated moment ----------
  var portal = { run: 0, done: false };
  function portalReset() {
    $("portal-dialog").classList.remove("open");
    $("portal-typed").textContent = "";
    $("portal-c1").classList.remove("on");
    $("portal-c2").classList.remove("on");
    $("portal-new").classList.remove("added");
    $("portal-toast").classList.remove("show");
  }
  function portalFinal() {
    portalReset();
    $("portal-typed").textContent = MSG[lang].typedName;
    $("portal-new").classList.add("added");
    portal.done = true;
  }
  async function press(id) {
    var el = $(id);
    el.classList.add("pressed");
    await sleep(180);
    el.classList.remove("pressed");
  }
  async function playPortal() {
    if (reduceMotion) { portalFinal(); return; }
    var run = ++portal.run;
    var alive = function () { return run === portal.run; };
    portalReset();
    portal.done = false;
    await sleep(500); if (!alive()) return;
    await press("portal-add"); if (!alive()) return;
    $("portal-dialog").classList.add("open");
    await sleep(450);
    var name = MSG[lang].typedName;
    for (var i = 1; i <= name.length; i++) {
      if (!alive()) return;
      $("portal-typed").textContent = name.slice(0, i);
      await sleep(70);
    }
    await sleep(350); if (!alive()) return;
    $("portal-c1").classList.add("on");
    await sleep(380); if (!alive()) return;
    $("portal-c2").classList.add("on");
    await sleep(500); if (!alive()) return;
    await press("portal-create"); if (!alive()) return;
    $("portal-dialog").classList.remove("open");
    await sleep(250); if (!alive()) return;
    $("portal-new").classList.add("added");
    $("portal-toast").classList.add("show");
    portal.done = true;
    await sleep(2800); if (!alive()) return;
    $("portal-toast").classList.remove("show");
  }
  if ("IntersectionObserver" in window) {
    var portalIo = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) { portalIo.disconnect(); playPortal(); }
    }, { threshold: 0.55 });
    portalIo.observe($("portal-mock"));
  } else {
    portalFinal();
  }
  $("portal-replay").addEventListener("click", function () { playPortal(); track("portal_replay", {}); });

  // ---------- FAQ ----------
  document.querySelectorAll("details[data-faq]").forEach(function (d) {
    d.addEventListener("toggle", function () { if (d.open) track("faq_open", { q: d.getAttribute("data-faq") }); });
  });
  var cmp = document.querySelector(".compare-details");
  if (cmp) cmp.addEventListener("toggle", function () { if (cmp.open) trackOnce("compare", "compare_open", {}); });

  // ---------- Engagement: sections, scroll depth, time ----------
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          var id = e.target.getAttribute("data-track");
          trackOnce("sec:" + id, "section_view", { section: id });
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.35 });
    document.querySelectorAll("[data-track]").forEach(function (el) { io.observe(el); });
  }
  var depths = [25, 50, 75, 90];
  var scrollTick = false;
  window.addEventListener("scroll", function () {
    if (scrollTick) return;
    scrollTick = true;
    requestAnimationFrame(function () {
      scrollTick = false;
      var max = document.documentElement.scrollHeight - window.innerHeight;
      if (max <= 0) return;
      var pct = (window.scrollY / max) * 100;
      depths.forEach(function (d) { if (pct >= d) trackOnce("scroll" + d, "scroll_depth", { pct: d }); });
    });
  }, { passive: true });
  var visibleMs = 0, lastTick = Date.now();
  setInterval(function () {
    var now = Date.now();
    if (document.visibilityState === "visible") visibleMs += now - lastTick;
    lastTick = now;
    if (visibleMs >= 30000) trackOnce("engaged", "engaged_30s", {});
  }, 1000);

  // ---------- Sign-up, step 1 ----------
  var form = $("signup-form");
  var errorEl = $("form-error");
  var submitBtn = $("submit-btn");
  var signupRef = null;

  form.addEventListener("focusin", function () { trackOnce("form_start", "form_start", {}); });

  function showError(el, msg, field) {
    el.textContent = msg;
    el.hidden = false;
    if (field) field.focus();
  }

  function collect() {
    var fd = new FormData(form);
    return {
      name: (fd.get("name") || "").trim(),
      company: (fd.get("company") || "").trim(),
      email: (fd.get("email") || "").trim(),
      phone: (fd.get("phone") || "").trim(),
      industry: fd.get("industry") || "",
      size: fd.get("size") || "",
      plan: fd.get("plan") || "undecided",
      wants_call: fd.get("wants_call") === "yes",
      consent: fd.get("consent") === "on",
      website: fd.get("website") || "", // honeypot
      lang: lang, utm: utm, ref: referrerHost, pid: pageId
    };
  }

  function validate(data) {
    form.querySelectorAll("[aria-invalid]").forEach(function (el) { el.removeAttribute("aria-invalid"); });
    var missing = ["name", "company", "email", "industry", "size"].filter(function (n) { return !data[n]; }).map(function (n) { return form.elements[n]; });
    if (missing.length) {
      missing.forEach(function (el) { el.setAttribute("aria-invalid", "true"); });
      return { msg: MSG[lang].required, field: missing[0] };
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(data.email)) {
      form.elements.email.setAttribute("aria-invalid", "true");
      return { msg: MSG[lang].email, field: form.elements.email };
    }
    if (!data.consent) return { msg: MSG[lang].consent, field: $("f-consent") };
    return null;
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    errorEl.hidden = true;
    var data = collect();
    var problem = validate(data);
    if (problem) { showError(errorEl, problem.msg, problem.field); track("form_invalid", {}); return; }

    var label = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = MSG[lang].sending;
    fetch("/api/signup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
      .then(function (res) { if (!res.ok) throw new Error("server"); return res.json(); })
      .then(function (json) {
        signupRef = json && json.ref ? json.ref : null;
        track("form_submit", { plan: data.plan, industry: data.industry, size: data.size, wants_call: data.wants_call });
        form.hidden = true;
        var book = $("booking-link");
        if (CONFIG.bookingUrl) {
          book.href = CONFIG.bookingUrl;
          book.addEventListener("click", function () { track("call_click", {}); });
        } else {
          book.hidden = true;
        }
        if (!signupRef) $("details-form").hidden = true;
        var ok = $("form-success");
        ok.hidden = false;
        ok.focus();
      })
      .catch(function (err) {
        showError(errorEl, err && err.message === "server" ? MSG[lang].server : MSG[lang].network);
        track("form_error", {});
      })
      .finally(function () { submitBtn.disabled = false; submitBtn.textContent = label; });
  });

  // ---------- Sign-up, step 2: optional details ----------
  var details = $("details-form");
  var detailsErr = $("details-error");
  var detailsBtn = $("details-btn");

  function finishDetails(text) {
    details.hidden = true;
    var done = $("details-done");
    if (text) done.textContent = text;
    done.hidden = false;
  }

  details.addEventListener("submit", function (ev) {
    ev.preventDefault();
    detailsErr.hidden = true;
    var fd = new FormData(details);
    var body = {
      ref: signupRef,
      current_it: fd.getAll("current_it"),
      pains: fd.getAll("pains"),
      timeline: fd.get("timeline") || "",
      payment_pref: fd.get("payment_pref") || "",
      price_view: fd.get("price_view") || "",
      message: (fd.get("message") || "").trim()
    };
    var label = detailsBtn.textContent;
    detailsBtn.disabled = true;
    detailsBtn.textContent = MSG[lang].sending;
    fetch("/api/details", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (res) { if (!res.ok) throw new Error("server"); })
      .then(function () {
        track("details_submit", { pains: body.pains.length, payment: body.payment_pref || "none" });
        finishDetails();
      })
      .catch(function (err) { showError(detailsErr, err && err.message === "server" ? MSG[lang].server : MSG[lang].network); })
      .finally(function () { detailsBtn.disabled = false; detailsBtn.textContent = label; });
  });
  $("details-skip").addEventListener("click", function () { track("details_skip", {}); finishDetails(MSG[lang].skipped); });

  // ---------- Footer contact ----------
  if (CONFIG.contactEmail) $("contact-link").href = "mailto:" + CONFIG.contactEmail;
  if (CONFIG.contactPhone) {
    var tel = $("contact-phone");
    tel.textContent = CONFIG.contactPhone;
    tel.href = "tel:" + CONFIG.contactPhone.replace(/[^\d+]/g, "");
    tel.hidden = false;
  }

  // ---------- Start ----------
  applyLang();
  track("page_view", {});
})();
