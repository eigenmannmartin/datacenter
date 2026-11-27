/* Rechenbox landing page: language and theme switches, plan picker and two-step sign-up form.
 * Visitor statistics come from Cloudflare Web Analytics (injected at the edge, no cookies), not from this file. */
(function () {
  "use strict";

  var CONFIG = window.RECHENBOX_CONFIG || {};
  var EN = window.RECHENBOX_EN || {};
  var root = document.documentElement;

  // Strings that only exist in JavaScript. The script keeps the key of what it shows, not the sentence,
  // so everything it has written can be written again when the language changes.
  var MSG = {
    de: {
      langToggle: "EN: Switch to English",
      themeToDark: "Dunkles Design einschalten",
      themeToLight: "Helles Design einschalten",
      missing: "Bitte ausfüllen.",
      choose: "Bitte wählen.",
      email: "Bitte geben Sie eine gültige E-Mail-Adresse ein.",
      consent: "Bitte bestätigen Sie, dass wir Ihre Angaben speichern dürfen.",
      check: "Bitte prüfen Sie die markierten Felder.",
      network: "Die Übermittlung hat nicht geklappt. Bitte prüfen Sie Ihre Verbindung und versuchen Sie es erneut.",
      server: "Die Übermittlung hat nicht geklappt. Bitte versuchen Sie es später erneut oder schreiben Sie uns an {email}.",
      sending: "Wird gesendet…",
      answered: "Danke für Ihre Antworten.",
      skipped: "In Ordnung, das klären wir in der Analyse.",
      calcResult: "Zu Ihren Antworten passt {plan}.",
      rStart: "Einen Tag Ausfall können Sie verkraften. Dann genügt ein Server, den wir bei einem Defekt am nächsten Arbeitstag ersetzen.",
      rSize: "Start ist für Betriebe bis 20 Mitarbeitende gedacht.",
      rDowntime: "Fällt bei Business ein Server aus, übernehmen die zwei anderen.",
      rHours: "Auf Störungen reagieren wir bei Business am selben Arbeitstag.",
      rNow: "Bei Pro erreichen uns Alarme rund um die Uhr, und wir reagieren am selben Tag, auch am Wochenende.",
      rCritical: "Defekte Hardware ersetzen wir bei Pro innert eines Tages."
    },
    en: {
      langToggle: "DE: Auf Deutsch wechseln",
      themeToDark: "Switch to dark mode",
      themeToLight: "Switch to light mode",
      missing: "Please fill this in.",
      choose: "Please choose.",
      email: "Please enter a valid email address.",
      consent: "Please confirm that we may store your details.",
      check: "Please check the highlighted fields.",
      network: "Sending failed. Please check your connection and try again.",
      server: "Sending failed. Please try again later or write to us at {email}.",
      sending: "Sending…",
      answered: "Thank you for your answers.",
      skipped: "All right, we will cover that in the assessment.",
      calcResult: "Your answers point to {plan}.",
      rStart: "You can cope with a day's outage. One server is then enough, and if it fails we replace it on the next working day.",
      rSize: "Start is meant for firms with up to 20 staff.",
      rDowntime: "If a server fails on Business, the other two take over.",
      rHours: "On Business we respond to incidents on the same working day.",
      rNow: "On Pro, alerts reach us around the clock and we respond the same day, weekends included.",
      rCritical: "On Pro we replace faulty hardware within a day."
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

  function $(id) { return document.getElementById(id); }
  function msg(key) { return MSG[lang][key].replace("{email}", CONFIG.contactEmail || "hallo@rechenbox.ch"); }

  // ---------- Theme ----------
  // Follows the system until the visitor picks one. The pick is kept for this visit only (sessionStorage, no cookie),
  // so that a reload and the privacy page show the same theme; the script in the head applies it before the first paint.
  var systemDark = window.matchMedia("(prefers-color-scheme: dark)");
  function pickedTheme() {
    var t = root.getAttribute("data-theme");
    return t === "dark" || t === "light" ? t : "";
  }
  function isDark() {
    var picked = pickedTheme();
    return picked ? picked === "dark" : systemDark.matches;
  }
  function updateTheme() {
    // The dark render is chosen by a media query. Once the visitor has picked a theme, that choice replaces the query.
    var picked = pickedTheme();
    $("hero-dark").media = picked ? (picked === "dark" ? "all" : "not all") : "(prefers-color-scheme: dark)";
    $("theme-toggle").setAttribute("aria-label", msg(isDark() ? "themeToLight" : "themeToDark"));
    document.querySelectorAll('meta[name="theme-color"]').forEach(function (m) {
      m.setAttribute("content", isDark() ? "#0e0f10" : "#ffffff");
      m.removeAttribute("media");
    });
  }
  $("theme-toggle").addEventListener("click", function () {
    var next = isDark() ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { sessionStorage.setItem("theme", next); } catch (e) { /* storage is blocked: the pick lasts until the page is left */ }
    updateTheme();
  });
  systemDark.addEventListener("change", updateTheme);

  // ---------- Language ----------
  // German is in the markup. English replaces it from the dictionary and is undone from what was remembered.
  var originals = new Map();
  function remember(el, kind, read) {
    if (!originals.has(el)) originals.set(el, {});
    var store = originals.get(el);
    if (!(kind in store)) store[kind] = read();
    return store[kind];
  }
  // The text of an element with a data-i18n key, in the language in use.
  function textOf(el) {
    var de = remember(el, "text", function () { return el.textContent; });
    return (lang === "en" && EN[el.getAttribute("data-i18n")]) || de;
  }

  function applyLang() {
    var en = lang === "en";
    root.lang = en ? "en" : "de-CH";
    document.querySelectorAll("[data-i18n]").forEach(function (el) { el.textContent = textOf(el); });
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) {
      var de = remember(el, "html", function () { return el.innerHTML; });
      el.innerHTML = (en && EN[el.getAttribute("data-i18n-html")]) || de; // values come from our own static dictionary
    });
    document.querySelectorAll("[data-i18n-attr]").forEach(function (el) {
      el.getAttribute("data-i18n-attr").split(";").forEach(function (pair) {
        var attr = pair.split(":")[0];
        var de = remember(el, attr, function () { return el.getAttribute(attr); });
        el.setAttribute(attr, (en && EN[pair.split(":")[1]]) || de);
      });
    });
    var toggle = $("lang-toggle");
    toggle.textContent = en ? "DE" : "EN";
    toggle.setAttribute("lang", en ? "de" : "en");
    toggle.setAttribute("aria-label", msg("langToggle")); // starts with the visible text
    updateTheme();
    // Everything the script has written follows the switch as well.
    updateCalc();
    form.querySelectorAll("[aria-invalid]").forEach(function (field) { mark(field, problemOf(field)); });
    showMessage(errorEl, errorEl.dataset.msg);
    showMessage(detailsErr, detailsErr.dataset.msg);
    if (doneEl.dataset.msg) doneEl.textContent = msg(doneEl.dataset.msg);
    if (sendingBtn) sendingBtn.textContent = msg("sending");
  }

  $("lang-toggle").addEventListener("click", function () {
    lang = lang === "en" ? "de" : "en";
    var p = new URLSearchParams(location.search);
    if (lang === "en") p.set("lang", "en"); else p.delete("lang");
    var qs = p.toString();
    history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
    applyLang();
  });

  // ---------- Plan picker ----------
  // Start is one server; Business and Pro share the same hardware and differ in support.
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
    var done = true;
    QUESTIONS.forEach(function (q) { a[q] = answer(q); if (!a[q]) done = false; });
    var r = done ? recommend(a) : null;
    recommendedPlan = r ? r.plan : "";
    $("calc-pending").hidden = done;
    $("calc-done").hidden = !done;
    // Mark the plan in the table: its cells get the ink line and the words beside the name, its button is the filled one.
    document.querySelectorAll("#plans [data-plan]").forEach(function (cell) {
      cell.classList.toggle("is-recommended", cell.getAttribute("data-plan") === recommendedPlan);
    });
    document.querySelectorAll("[data-plan-select]").forEach(function (link) {
      var fits = link.getAttribute("data-plan-select") === recommendedPlan;
      link.classList.toggle("btn-primary", fits);
      link.classList.toggle("btn-secondary", !fits);
    });
    if (!r) return;

    var sentences = [msg("calcResult").replace("{plan}", PLAN_NAMES[r.plan])];
    r.reasons.forEach(function (key) { sentences.push(msg(key)); });
    $("calc-text").textContent = sentences.join(" ");
    // The button carries the same words as the plan's button in the table.
    $("calc-cta").textContent = document.querySelector('[data-plan-select="' + r.plan + '"]').textContent;
  }

  QUESTIONS.forEach(function (q) {
    document.querySelectorAll('input[name="calc-' + q + '"]').forEach(function (el) {
      el.addEventListener("change", updateCalc);
    });
  });

  // ---------- Plan buttons ----------
  // Plain links to the form; on the way they preselect the plan there.
  var planSelect = $("f-plan");
  function choosePlan(plan) {
    if (plan && planSelect.querySelector('option[value="' + plan + '"]')) planSelect.value = plan;
  }
  $("calc-cta").addEventListener("click", function () { choosePlan(recommendedPlan); });
  document.querySelectorAll("[data-plan-select]").forEach(function (link) {
    link.addEventListener("click", function () { choosePlan(link.getAttribute("data-plan-select")); });
  });

  // ---------- Messages and buttons the script writes ----------
  // A message line shows the text of a key from MSG, or nothing.
  function showMessage(el, key) {
    el.dataset.msg = key || "";
    el.textContent = key ? msg(key) : "";
    el.hidden = !key;
  }
  // A button that is sending is disabled and says so; afterwards it gets its own label back, in the language in use.
  var sendingBtn = null;
  function setSending(btn, on) {
    sendingBtn = on ? btn : null;
    btn.disabled = on;
    btn.textContent = on ? msg("sending") : textOf(btn);
  }
  function failure(err) { return err && err.message === "server" ? "server" : "network"; }

  // ---------- Sign-up, step 1 ----------
  var form = $("signup-form");
  var errorEl = $("form-error");
  var submitBtn = $("submit-btn");
  var signupRef = null;
  var REQUIRED = ["name", "company", "email", "industry", "size", "consent"].map(function (n) { return form.elements[n]; });

  // What is wrong with a required field: the key of its message, or "" when it is fine.
  function problemOf(field) {
    if (field.type === "checkbox") return field.checked ? "" : "consent";
    var value = field.value.trim();
    if (!value) return field.tagName === "SELECT" ? "choose" : "missing";
    if (field.type === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)) return "email";
    return "";
  }
  // A field with a problem gets a red border and a sentence under it. Both stay until the field is valid.
  function mark(field, key) {
    var note = $(field.id + "-error");
    if (!key) {
      field.removeAttribute("aria-invalid");
      field.removeAttribute("aria-describedby");
      if (note) note.remove();
      return;
    }
    if (!note) {
      note = document.createElement("p");
      note.id = field.id + "-error";
      note.className = "field-error";
      (field.closest(".check") || field).after(note);
    }
    note.textContent = msg(key);
    field.setAttribute("aria-invalid", "true");
    field.setAttribute("aria-describedby", note.id);
  }
  function clearWhenValid(ev) {
    var field = ev.target;
    if (!field.hasAttribute("aria-invalid") || problemOf(field)) return;
    mark(field, "");
    // The line above the button goes with the last marked field.
    if (errorEl.dataset.msg === "check" && !form.querySelector("[aria-invalid]")) showMessage(errorEl, "");
  }
  form.addEventListener("input", clearWhenValid);
  form.addEventListener("change", clearWhenValid);

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
      recommended_plan: recommendedPlan,
      lang: lang, utm: utm, ref: referrerHost
    };
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var invalid = REQUIRED.filter(function (field) {
      var key = problemOf(field);
      mark(field, key);
      return key;
    });
    showMessage(errorEl, invalid.length ? "check" : "");
    if (invalid.length) { invalid[0].focus(); return; }

    setSending(submitBtn, true);
    fetch("/api/signup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(collect()) })
      .then(function (res) { if (!res.ok) throw new Error("server"); return res.json(); })
      .then(function (json) {
        signupRef = json && json.ref ? json.ref : null;
        form.hidden = true;
        $("anmelden").classList.add("is-sent");
        var book = $("booking-link");
        if (CONFIG.bookingUrl) {
          book.href = CONFIG.bookingUrl;
        } else {
          book.parentNode.hidden = true;
        }
        if (!signupRef) details.hidden = true;
        showConfirmation($("form-success"));
      })
      .catch(function (err) { showMessage(errorEl, failure(err)); })
      .finally(function () { setSending(submitBtn, false); });
  });

  // The confirmation has to be seen: its top goes under the header (scroll-padding on <html> leaves the room),
  // and the focus moves to the given element without scrolling a second time.
  function showConfirmation(focusEl) {
    var ok = $("form-success");
    ok.hidden = false;
    ok.scrollIntoView({ block: "start" });
    focusEl.focus({ preventScroll: true });
  }

  // ---------- Sign-up, step 2: optional details ----------
  var details = $("details-form");
  var detailsErr = $("details-error");
  var detailsBtn = $("details-btn");
  var doneEl = $("details-done");

  // After the answers are sent or skipped, one line closes the follow-up and takes the focus.
  function finishDetails(key) {
    details.hidden = true;
    doneEl.dataset.msg = key;
    doneEl.textContent = msg(key);
    doneEl.hidden = false;
    showConfirmation(doneEl);
  }

  details.addEventListener("submit", function (ev) {
    ev.preventDefault();
    showMessage(detailsErr, "");
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
    setSending(detailsBtn, true);
    fetch("/api/details", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (res) { if (!res.ok) throw new Error("server"); })
      .then(function () { finishDetails("answered"); })
      .catch(function (err) { showMessage(detailsErr, failure(err)); })
      .finally(function () { setSending(detailsBtn, false); });
  });
  $("details-skip").addEventListener("click", function () { finishDetails("skipped"); });

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
  root.classList.add("app"); // the script has taken over: the switches show, and the guard in the head steps aside
})();
