/* Rechenbox landing page: language and theme switches, plan recommender,
 * portal and agent demos, order form and the optional questions after it. Visitor statistics come from
 * Cloudflare Web Analytics (injected at the edge, no cookies), not from this file. */
(function () {
  "use strict";

  var CONFIG = window.RECHENBOX_CONFIG || {};
  var EN = window.RECHENBOX_EN || {};
  var root = document.documentElement;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Strings that only exist in JavaScript.
  var MSG = {
    de: {
      langToggle: "EN: Switch to English",
      themeToDark: "Dunkles Design einschalten",
      themeToLight: "Helles Design einschalten",
      required: "Bitte füllen Sie die markierten Felder aus.",
      email: "Bitte geben Sie eine gültige E-Mail-Adresse ein.",
      consent: "Bitte bestätigen Sie, dass wir Ihre Angaben speichern dürfen.",
      network: "Die Übermittlung hat nicht geklappt. Bitte prüfen Sie Ihre Verbindung und versuchen Sie es erneut.",
      server: "Die Übermittlung hat nicht geklappt. Bitte versuchen Sie es später erneut oder schreiben Sie uns an {email}.",
      sending: "Wird gesendet…",
      skipped: "In Ordnung, das klären wir im Gespräch.",
      calcCta: "{plan} bestellen",
      typedName: "Anna Meier",
      from: "ab",
      opt_offsite: "Backup-Kopie im Schweizer Rechenzentrum",
      opt_ai: "Private KI",
      opt_storage: "6\u00a0TB mehr Speicher",
      payNote_prepay: "Wenn Sie jährlich im Voraus zahlen, erhalten Sie 4\u00a0% Rabatt.",
      payNote_purchase: "Wenn Sie die Hardware kaufen, sinkt der Monatspreis. Beide Beträge nennen wir Ihnen vor dem Vertrag.",
      recap: "Ihre Auswahl: {what}, {pay}, Start {start}.",
      with: " mit ",
      and: " und ",
      pay_monthly: "monatliche Zahlung",
      pay_prepay: "jährliche Zahlung im Voraus",
      pay_purchase: "Kauf der Hardware",
      start_lt6: "innert 6 Monaten",
      start_6to12: "in 6 bis 12 Monaten",
      start_gt12: "später",
      rStart: "Ein Tag Ausfall ist für Sie verkraftbar. Dann genügt ein Server, den wir bei einem Defekt am nächsten Arbeitstag ersetzen.",
      rSize: "Mit mehr als 20 Mitarbeitenden lohnt sich die Ausfallsicherheit von drei Servern.",
      rDowntime: "Ein Ausfall kostet Sie Umsatz oder Arbeitszeit. Mit drei Servern arbeiten Sie weiter, wenn einer ausfällt.",
      rHours: "Bei Business reagieren wir am selben Arbeitstag.",
      rNow: "Bei Pro erreichen uns Alarme rund um die Uhr, und wir reagieren am selben Tag, auch am Wochenende.",
      rCritical: "Ihr Betrieb steht ohne IT still. Bei Pro ersetzen wir defekte Hardware innert eines Tages, auch am Wochenende."
    },
    en: {
      langToggle: "DE: Auf Deutsch wechseln",
      themeToDark: "Switch to dark mode",
      themeToLight: "Switch to light mode",
      required: "Please fill in the highlighted fields.",
      email: "Please enter a valid email address.",
      consent: "Please confirm that we may store your details.",
      network: "Sending failed. Please check your connection and try again.",
      server: "Sending failed. Please try again later or write to us at {email}.",
      sending: "Sending…",
      skipped: "All right, we will cover that in the call.",
      calcCta: "Order {plan}",
      typedName: "Anna Meier",
      from: "from",
      opt_offsite: "Backup copy in a Swiss data centre",
      inline_offsite: "a backup copy in a Swiss data centre",
      opt_ai: "Private AI",
      opt_storage: "6\u00a0TB more storage",
      payNote_prepay: "If you pay a year in advance, you get 4% off.",
      payNote_purchase: "If you buy the hardware, the monthly price goes down. We will give you both amounts before the contract.",
      recap: "Your choice: {what}, {pay}, start {start}.",
      with: " with ",
      and: " and ",
      pay_monthly: "monthly payment",
      pay_prepay: "yearly payment in advance",
      pay_purchase: "hardware purchase",
      start_lt6: "within 6 months",
      start_6to12: "in 6 to 12 months",
      start_gt12: "later",
      rStart: "You can cope with a day of downtime. One server is then enough, and we replace it on the next working day if it fails.",
      rSize: "With more than 20 staff, the failover of three servers pays off.",
      rDowntime: "Downtime costs you revenue or working time. With three servers you keep working when one fails.",
      rHours: "With Business we respond on the same working day.",
      rNow: "With Pro, alerts reach us around the clock and we respond the same day, weekends included.",
      rCritical: "Your business stops without IT. With Pro we replace faulty hardware within a day, weekends included."
    }
  };

  var PLAN_NAMES = { start: "Start", business: "Business", pro: "Pro" };

  var params = new URLSearchParams(location.search);
  var lang = params.get("lang") === "en" ? "en" : "de";

  // ---------- Lead source ----------
  // Sent with the sign-up only, so each lead can be traced to its ad or post.
  var utm = {};
  ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"].forEach(function (k) {
    var v = params.get(k);
    if (v) utm[k] = v.slice(0, 100);
  });
  var referrerHost = "";
  try { referrerHost = document.referrer ? new URL(document.referrer).hostname : ""; } catch (e) { /* ignore */ }

  function money(n) {
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, lang === "en" ? "," : "'");
  }
  function serverMsg() { return MSG[lang].server.replace("{email}", CONFIG.contactEmail || "hallo@rechenbox.ch"); }
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
    // The dark picture of the box is chosen by a media query. Once the visitor has picked a theme, the pick replaces it.
    var picked = root.getAttribute("data-theme");
    $("hero-dark").media = picked ? (picked === "dark" ? "all" : "not all") : "(prefers-color-scheme: dark)";
    var meta = document.querySelectorAll('meta[name="theme-color"]');
    meta.forEach(function (m) { m.setAttribute("content", isDark() ? "#0e0f10" : "#ffffff"); m.removeAttribute("media"); });
  }
  $("theme-toggle").addEventListener("click", function () {
    root.setAttribute("data-theme", isDark() ? "light" : "dark");
    updateThemeButton();
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
    document.querySelectorAll(".amount, .amount-plain").forEach(function (el) {
      el.textContent = en ? el.textContent.replace(/(\d)'(\d)/g, "$1,$2") : el.textContent.replace(/(\d),(\d)/g, "$1'$2");
    });
    var toggle = $("lang-toggle");
    toggle.textContent = en ? "DE" : "EN";
    toggle.setAttribute("lang", en ? "de" : "en");
    toggle.setAttribute("aria-label", MSG[lang].langToggle);
    document.title = en ? "Rechenbox – your server in your office, run by us" : "Rechenbox – Ihr Server im Büro, von uns betrieben";
    updateThemeButton();
    updateCalc(false);
    renderSummary();
    renderRecap();
    if (portal.done) $("portal-typed").textContent = MSG[lang].typedName;
  }

  $("lang-toggle").addEventListener("click", function () {
    lang = lang === "en" ? "de" : "en";
    var p = new URLSearchParams(location.search);
    if (lang === "en") p.set("lang", "en"); else p.delete("lang");
    var qs = p.toString();
    history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
    applyLang();
  });

  // ---------- Recommender ----------
  // Start is one box; Business and Pro share the same hardware and differ in support.
  var QUESTIONS = ["size", "downtime", "response"];
  var recommendedPlan = "";

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

  function updateCalc() {
    var a = {};
    var answered = 0;
    QUESTIONS.forEach(function (q) { a[q] = answer(q); if (a[q]) answered++; });
    var done = answered === QUESTIONS.length;
    $("calc-pending").hidden = done;
    $("calc-done").hidden = !done;

    var r = done ? recommend(a) : null;
    recommendedPlan = r ? r.plan : "";
    document.querySelectorAll(".plan").forEach(function (card) {
      var plan = card.getAttribute("data-plan");
      var lead = r ? plan === r.plan : plan === "business";
      card.classList.toggle("recommended", !!r && plan === r.plan);
      var btn = card.querySelector(".plan-btn");
      btn.classList.toggle("btn-primary", lead);
      btn.classList.toggle("btn-secondary", !lead);
    });
    if (!r) return;

    $("calc-plan-name").textContent = PLAN_NAMES[r.plan];
    $("calc-cta").textContent = MSG[lang].calcCta.replace("{plan}", PLAN_NAMES[r.plan]);
    var list = $("calc-reasons");
    list.textContent = "";
    r.reasons.forEach(function (key) {
      var li = document.createElement("li");
      li.textContent = MSG[lang][key];
      list.appendChild(li);
    });
  }

  QUESTIONS.forEach(function (q) {
    document.querySelectorAll('input[name="calc-' + q + '"]').forEach(function (el) {
      el.addEventListener("change", function () { updateCalc(true); });
    });
  });

  // ---------- Portal demo: the page's one orchestrated moment ----------
  // It plays once when it comes into view; a click on the card plays it again once it has finished.
  var portal = { run: 0, done: false, playing: false };
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
    portal.playing = true;
    try {
      await portalSteps(alive);
    } finally {
      if (alive()) portal.playing = false;
    }
  }
  async function portalSteps(alive) {
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
      if (entries[0].isIntersecting) { portalIo.disconnect(); if (!portal.playing) playPortal(); }
    }, { threshold: 0.55 });
    portalIo.observe($("portal-mock"));
  } else {
    portalFinal();
  }
  $("portal-mock").addEventListener("click", function () { if (!portal.playing) playPortal(); });

  // ---------- Private KI demo: an agent works through a task, then waits for a person to approve ----------
  var agent = { run: 0, playing: false };
  var AGENT_STEPS = ["agent-s1", "agent-s2", "agent-s3"];
  function agentReset() {
    AGENT_STEPS.forEach(function (id) { $(id).classList.remove("shown", "working"); });
    $("agent-approve").classList.remove("shown", "approved");
  }
  function agentFinal() {
    agentReset();
    AGENT_STEPS.forEach(function (id) { $(id).classList.add("shown"); });
    $("agent-approve").classList.add("shown", "approved");
  }
  async function playAgent() {
    if (reduceMotion) { agentFinal(); return; }
    var run = ++agent.run;
    var alive = function () { return run === agent.run; };
    agent.playing = true;
    try {
      await agentSteps(alive);
    } finally {
      if (alive()) agent.playing = false;
    }
  }
  async function agentSteps(alive) {
    agentReset();
    await sleep(400); if (!alive()) return;
    for (var i = 0; i < AGENT_STEPS.length; i++) {
      var step = $(AGENT_STEPS[i]);
      step.classList.add("shown", "working");
      await sleep(900); if (!alive()) return;
      step.classList.remove("working");
      await sleep(250); if (!alive()) return;
    }
    $("agent-approve").classList.add("shown");
    await sleep(1200); if (!alive()) return;
    await press("agent-ok"); if (!alive()) return;
    $("agent-approve").classList.add("approved");
  }
  // With reduced motion the finished state shows at once; otherwise the demo starts when the card is in view.
  if (reduceMotion || !("IntersectionObserver" in window)) {
    agentFinal();
  } else {
    var agentIo = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) { agentIo.disconnect(); if (!agent.playing) playAgent(); }
    }, { threshold: 0.55 });
    agentIo.observe($("agent-mock"));
  }
  $("agent-mock").addEventListener("click", function () { if (!agent.playing) playAgent(); });

  // ---------- Order form ----------
  // A "fake door" for the pilot: the visitor orders with real prices and choices, but pays nothing and signs nothing.
  // After sending, the page thanks them for their interest in the pilot and says we will get back to them.
  // Prices: keep them in step with the plan cards and the comparison table in index.html.
  var PRICES = {
    start: { monthly: 790, setup: 2900, offsite: 90 },
    business: { monthly: 1890, setup: 6900, offsite: 140 },
    pro: { monthly: 2890, setup: 8900, offsite: 240 }
  };
  var ADDON_PRICES = { ai: 590, storage: 190 };
  var PILOT_DISCOUNT = 0.3; // pilot customers, first year
  // The choices an order needs, with the fieldset that holds each.
  var GROUPS = { plan: "q-plan", payment_pref: "q-pay", start: "q-start" };

  var form = $("order-form");
  var errorEl = $("form-error");
  var submitBtn = $("submit-btn");
  var signupRef = null;
  var sentOrder = null;

  function chf(n) { return "CHF " + money(n); }
  function picked(name) {
    var el = form.querySelector('input[name="' + name + '"]:checked');
    return el ? el.value : "";
  }
  function pickedAll(name) {
    return Array.prototype.map.call(form.querySelectorAll('input[name="' + name + '"]:checked'), function (el) { return el.value; });
  }

  // The summary: what the chosen plan and options cost per month, per month in the pilot's first year, and once for setup.
  function renderSummary() {
    var plan = picked("plan");
    var p = PRICES[plan];
    $("offsite-price").textContent = p ? chf(p.offsite) : MSG[lang].from + " " + chf(PRICES.start.offsite);
    $("summary-empty").hidden = !!p;
    $("summary-body").hidden = !p;
    if (!p) return;
    var rows = [[PLAN_NAMES[plan], p.monthly]];
    pickedAll("options").forEach(function (o) {
      rows.push([MSG[lang]["opt_" + o], o === "offsite" ? p.offsite : ADDON_PRICES[o]]);
    });
    var lines = $("summary-lines");
    lines.textContent = "";
    var total = 0;
    rows.forEach(function (r) {
      total += r[1];
      var tr = document.createElement("tr");
      var th = document.createElement("th");
      th.scope = "row";
      th.textContent = r[0];
      var td = document.createElement("td");
      td.textContent = chf(r[1]);
      tr.append(th, td);
      lines.appendChild(tr);
    });
    $("sum-total").textContent = chf(total);
    $("sum-pilot").textContent = chf(total * (1 - PILOT_DISCOUNT));
    $("sum-setup").textContent = chf(p.setup);
    var note = MSG[lang]["payNote_" + picked("payment_pref")] || "";
    $("summary-pay").textContent = note;
    $("summary-pay").hidden = !note;
  }

  function clearGroup(fieldset) {
    fieldset.classList.remove("invalid");
    fieldset.querySelectorAll("input").forEach(function (el) { el.removeAttribute("aria-invalid"); });
  }
  form.addEventListener("change", function (ev) {
    var group = ev.target.closest(".q");
    if (group) clearGroup(group);
    renderSummary();
  });
  // A marked field loses its mark as soon as it has an answer; the check on sending runs again anyway.
  form.addEventListener("input", function (ev) {
    if (ev.target.getAttribute("aria-invalid") === "true" && ev.target.value.trim()) ev.target.removeAttribute("aria-invalid");
  });

  // The plan buttons and the recommender lead to the form with that plan chosen.
  function goToForm(plan) {
    var input = plan ? form.querySelector('input[name="plan"][value="' + plan + '"]') : null;
    if (input) {
      input.checked = true;
      clearGroup($("q-plan"));
      renderSummary();
    }
    $("bestellen").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
    var target = input || form.querySelector('input[name="plan"]');
    setTimeout(function () { target.focus({ preventScroll: true }); }, reduceMotion ? 0 : 450);
  }
  $("calc-cta").addEventListener("click", function () { goToForm(recommendedPlan); });
  document.querySelectorAll("[data-plan-select]").forEach(function (btn) {
    btn.addEventListener("click", function () { goToForm(btn.getAttribute("data-plan-select")); });
  });

  function showError(el, msg, field) {
    el.textContent = msg;
    el.hidden = false;
    if (field) field.focus();
  }

  function collect() {
    var fd = new FormData(form);
    return {
      plan: fd.get("plan") || "",
      options: fd.getAll("options"),
      payment_pref: fd.get("payment_pref") || "",
      start: fd.get("start") || "",
      name: (fd.get("name") || "").trim(),
      company: (fd.get("company") || "").trim(),
      email: (fd.get("email") || "").trim(),
      phone: (fd.get("phone") || "").trim(),
      industry: fd.get("industry") || "",
      size: fd.get("size") || "",
      consent: fd.get("consent") === "on",
      website: fd.get("website") || "", // honeypot
      recommended_plan: recommendedPlan,
      lang: lang, utm: utm, ref: referrerHost
    };
  }

  // Marks every missing answer and returns the first one, in the order of the form.
  function validate(data) {
    form.querySelectorAll("[aria-invalid]").forEach(function (el) { el.removeAttribute("aria-invalid"); });
    form.querySelectorAll(".q.invalid").forEach(function (el) { el.classList.remove("invalid"); });
    var missing = [];
    Object.keys(GROUPS).forEach(function (n) {
      if (data[n]) return;
      var group = $(GROUPS[n]);
      group.classList.add("invalid");
      group.querySelectorAll("input").forEach(function (el) { el.setAttribute("aria-invalid", "true"); });
      missing.push(group.querySelector("input"));
    });
    ["name", "company", "email", "industry", "size"].forEach(function (n) {
      if (data[n]) return;
      form.elements[n].setAttribute("aria-invalid", "true");
      missing.push(form.elements[n]);
    });
    if (missing.length) return { msg: MSG[lang].required, field: missing[0] };
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(data.email)) {
      form.elements.email.setAttribute("aria-invalid", "true");
      return { msg: MSG[lang].email, field: form.elements.email };
    }
    if (!data.consent) return { msg: MSG[lang].consent, field: $("f-consent") };
    return null;
  }

  function listOf(items) {
    return items.length < 2 ? items.join("") : items.slice(0, -1).join(", ") + MSG[lang].and + items[items.length - 1];
  }
  // The confirmation repeats what was ordered.
  function renderRecap() {
    if (!sentOrder) return;
    var o = sentOrder;
    var what = PLAN_NAMES[o.plan];
    if (o.options.length) what += MSG[lang].with + listOf(o.options.map(function (k) { return MSG[lang]["inline_" + k] || MSG[lang]["opt_" + k]; }));
    $("success-recap").textContent = MSG[lang].recap
      .replace("{what}", what)
      .replace("{pay}", MSG[lang]["pay_" + o.payment_pref])
      .replace("{start}", MSG[lang]["start_" + o.start]);
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    errorEl.hidden = true;
    var data = collect();
    var problem = validate(data);
    if (problem) { showError(errorEl, problem.msg, problem.field); return; }

    var label = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = MSG[lang].sending;
    fetch("/api/signup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
      .then(function (res) { if (!res.ok) throw new Error("server"); return res.json(); })
      .then(function (json) {
        signupRef = json && json.ref ? json.ref : null;
        sentOrder = data;
        renderRecap();
        form.hidden = true;
        if (!signupRef) $("details-form").hidden = true;
        var ok = $("form-success");
        ok.hidden = false;
        // Bring the confirmation to the top of the window first: the questions below it are long, and a plain
        // focus() leaves its heading above the window on phones and small laptops.
        ok.scrollIntoView({ block: "start", behavior: "auto" });
        ok.focus({ preventScroll: true });
      })
      .catch(function (err) {
        showError(errorEl, err && err.message === "server" ? serverMsg() : MSG[lang].network);
      })
      .finally(function () { submitBtn.disabled = false; submitBtn.textContent = label; });
  });

  // ---------- After the order: optional questions ----------
  var details = $("details-form");
  var detailsErr = $("details-error");
  var detailsBtn = $("details-btn");

  function finishDetails(text) {
    details.hidden = true;
    var done = $("details-done");
    if (text) { done.removeAttribute("data-i18n"); done.textContent = text; }
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
      price_view: fd.get("price_view") || "",
      message: (fd.get("message") || "").trim()
    };
    var label = detailsBtn.textContent;
    detailsBtn.disabled = true;
    detailsBtn.textContent = MSG[lang].sending;
    fetch("/api/details", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (res) { if (!res.ok) throw new Error("server"); })
      .then(function () { finishDetails(); })
      .catch(function (err) { showError(detailsErr, err && err.message === "server" ? serverMsg() : MSG[lang].network); })
      .finally(function () { detailsBtn.disabled = false; detailsBtn.textContent = label; });
  });
  $("details-skip").addEventListener("click", function () { finishDetails(MSG[lang].skipped); });

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
  // From here on the forms are handled above; the small script in the page head stops blocking them.
  root.classList.add("app");
})();
