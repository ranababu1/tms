// One parameterised app for all four tool pages: (gemini|claude) x (simple|god).
// Config comes from the server in #page-config. DOM is built with textContent only.
(function () {
  "use strict";

  const cfg = JSON.parse(document.getElementById("page-config").textContent);
  const isGod = cfg.mode === "god";
  const isClaude = cfg.provider === "claude";
  const L = cfg.limits;
  const $ = (id) => document.getElementById(id);
  const LANG_NAMES = Object.fromEntries(cfg.languages.map((l) => [l.code, l.label]));

  // ---------- helpers ----------
  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else if (k === "text") node.textContent = v;
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return node;
  }
  const store = {
    get(k) { try { return k ? sessionStorage.getItem(k) : null; } catch { return null; } },
    set(k, v) { try { if (k) sessionStorage.setItem(k, v); } catch { /* storage blocked */ } },
    del(k) { try { if (k) sessionStorage.removeItem(k); } catch { /* storage blocked */ } },
  };
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const usd2 = (v) => "$" + v.toFixed(2);
  const usdSmart = (v) => "$" + (v < 0.01 ? v.toFixed(4) : v.toFixed(2));
  const inrSmart = (v) => "₹" + (v < 1 ? v.toFixed(3) : v.toFixed(2));
  const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
  const full = new Intl.NumberFormat("en");

  async function postJSON(url, body) {
    let res;
    try {
      res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch {
      throw new Error("Network error. Check your connection and try again.");
    }
    let data = null;
    try { data = await res.json(); } catch { /* non-JSON body */ }
    if (!res.ok) throw new Error((data && data.error) || `Request failed (${res.status}).`);
    return data;
  }

  // ---------- state ----------
  const S = {
    apiKey: store.get(cfg.storage.key) || "",
    verifyEnabled: store.get(cfg.storage.verify) === "1",
    models: cfg.fallbackModels,
    fetchedAt: null,
    catalogFallback: true,
    fetchedForKey: null,
    model: cfg.defaultModel,
    source: "auto",
    target: (cfg.storage.target && store.get(cfg.storage.target)) || "tr",
    panel: "input",
    busy: false,
    phase: null, // "translate" | "review"
    loading: false,
    msgIdx: 0,
    error: null,
    lastWithReview: false,
    translatedText: null,
    draftText: null,
    critiqueText: null,
    outputTokens: null,
    attempts: [],
    pending: null, // {n, kind: "verify"|"fix"}
    retryError: null,
    review: { state: "idle" }, // idle | waiting | running | done | error
    currentCost: 0,
    sessionCost: 0,
    copied: false,
    god: null,
  };
  if (!LANG_NAMES[S.target] || S.target === "auto") S.target = "tr";
  if (!S.models.some((m) => m.id === S.model)) S.model = S.models[0].id;

  const activeModel = () => S.models.find((m) => m.id === S.model) || S.models[0];
  const modelOutputLimit = () => activeModel().outputTokenLimit || (isClaude ? L.claudeDefaultMaxTokens : L.geminiDefaultMaxTokens);
  const godMaxCap = () => Math.min(modelOutputLimit(), isClaude ? L.claudeMaxCap : L.geminiMaxCap);
  const supportsSampling = () => !/^claude-(opus|sonnet)-5/i.test(S.model);
  const supportsEffort = () => /^claude-(opus|sonnet)-5/i.test(S.model);

  function addUsage(usage) {
    if (!usage) return;
    const p = activeModel().pricing;
    const cost = (usage.inputTokens / 1e6) * p.inputPer1M + (usage.outputTokens / 1e6) * p.outputPer1M;
    S.currentCost += cost;
    S.sessionCost += cost;
    const tag = isGod ? "[God Mode]" : isClaude ? "[Claude]" : "[Gemini]";
    console.groupCollapsed(`${tag} token usage`);
    console.log("model:", S.model);
    console.log("input:", usage.inputTokens, "output:", usage.outputTokens, "total:", usage.totalTokens);
    console.log("cost (USD):", cost.toFixed(6));
    console.groupEnd();
    renderCost();
  }

  // ---------- God Mode params ----------
  function godDefaults(resetAll) {
    if (isClaude) {
      return {
        temperature: 0.7, topK: 40, effort: "high",
        maxTokens: Math.min(L.claudeDefaultMaxTokens, godMaxCap()),
      };
    }
    return {
      temperature: 0.7, topP: 0.95, topK: 40, presencePenalty: 0, frequencyPenalty: 0,
      seed: "", thinkingLevel: "HIGH",
      maxTokens: resetAll ? godMaxCap() : Math.min(L.geminiDefaultMaxTokens, godMaxCap()),
    };
  }
  const templateFor = (lang) => (cfg.promptTemplates || {})[lang] || "";

  // ---------- controls: model + languages ----------
  const modelSelect = $("model-select");
  const sourceSelect = $("source-select");
  const targetSelect = $("target-select");
  const swapBtn = $("swap-btn");

  function renderModelSelect() {
    modelSelect.replaceChildren(
      ...S.models.map((m) => el("option", { value: m.id, selected: m.id === S.model }, m.label))
    );
    const m = activeModel();
    $("meta-in").textContent = `In: ${compact.format(m.inputTokenLimit)} tokens`;
    $("meta-out").textContent = `Out: ${compact.format(m.outputTokenLimit)} tokens`;
  }

  function renderLanguageSelects() {
    sourceSelect.replaceChildren(
      ...cfg.languages.map((l) => el("option", { value: l.code, selected: l.code === S.source }, l.label))
    );
    targetSelect.replaceChildren(
      ...cfg.languages.filter((l) => l.code !== "auto").map((l) =>
        el("option", {
          value: l.code,
          selected: l.code === S.target,
          class: !isGod && !cfg.languagesWithPrompt.includes(l.code) ? "no-prompt" : null,
        }, l.label)
      )
    );
    targetSelect.classList.toggle(
      "no-prompt-selected", !isGod && !cfg.languagesWithPrompt.includes(S.target)
    );
    targetSelect.style.color = !isGod && !cfg.languagesWithPrompt.includes(S.target) ? "var(--violet)" : "";
    swapBtn.disabled = S.source === "auto" || S.busy;
  }

  function setTarget(newTarget) {
    const old = S.target;
    S.target = newTarget;
    store.set(cfg.storage.target, newTarget);
    if (isGod) {
      const prompt = $("system-prompt");
      if (prompt.value === templateFor(old)) prompt.value = templateFor(newTarget);
    }
  }

  modelSelect.addEventListener("change", () => {
    S.model = modelSelect.value;
    if (isGod) S.god.maxTokens = clamp(S.god.maxTokens, 1, godMaxCap());
    renderModelSelect();
    renderGodControls();
  });
  sourceSelect.addEventListener("change", () => { S.source = sourceSelect.value; renderLanguageSelects(); });
  targetSelect.addEventListener("change", () => { setTarget(targetSelect.value); renderLanguageSelects(); });
  swapBtn.addEventListener("click", () => {
    if (S.source === "auto") return;
    const src = S.source;
    S.source = S.target;
    setTarget(src);
    renderLanguageSelects();
  });

  async function refreshModels() {
    const key = S.apiKey.trim();
    if (key.length < 10 || S.fetchedForKey === key) return;
    S.fetchedForKey = key;
    try {
      const data = await postJSON(cfg.endpoints.models, { apiKey: key });
      if (data && Array.isArray(data.models) && data.models.length) {
        S.models = data.models;
        S.fetchedAt = data.fetchedAt;
        S.catalogFallback = !!data.fallback;
        if (!S.models.some((m) => m.id === S.model)) S.model = S.models[0].id;
        if (isGod) S.god.maxTokens = clamp(S.god.maxTokens, 1, godMaxCap());
        renderModelSelect();
        renderGodControls();
      }
    } catch { /* keep the fallback list */ }
  }

  // ---------- God Mode controls ----------
  function godControlSpecs() {
    const claudeSamplingNote = "Not supported by Opus/Sonnet 5 models — not sent.";
    if (isClaude) {
      return [
        { key: "temperature", label: "Temperature", min: 0, max: 1, step: 0.05,
          disabled: !supportsSampling(), note: !supportsSampling() && claudeSamplingNote },
        { key: "topK", label: "Top-k", min: 1, max: 500, step: 1,
          disabled: !supportsSampling(), note: !supportsSampling() && claudeSamplingNote },
        { key: "maxTokens", label: "Max output tokens", min: 1, max: godMaxCap(), step: 1, number: true },
        { key: "effort", label: "Effort", select: L.effortLevels,
          disabled: !supportsEffort(), note: !supportsEffort() && "Effort isn't supported by this model — not sent." },
      ];
    }
    return [
      { key: "temperature", label: "Creativity (temperature)", min: 0, max: 1, step: 0.05 },
      { key: "topP", label: "Top-p", min: 0.05, max: 1, step: 0.05 },
      { key: "topK", label: "Top-k", min: 1, max: 100, step: 1 },
      { key: "maxTokens", label: "Max output tokens", min: 1, max: godMaxCap(), step: 1, number: true },
      { key: "presencePenalty", label: "Presence penalty", min: -2, max: 2, step: 0.1 },
      { key: "frequencyPenalty", label: "Frequency penalty", min: -2, max: 2, step: 0.1 },
      { key: "seed", label: "Seed", seed: true },
      { key: "thinkingLevel", label: "Thinking level", select: L.thinkingLevels },
    ];
  }

  function fmtParam(spec, v) {
    if (spec.number) return full.format(v);
    return spec.step < 1 ? Number(v).toFixed(2) : String(v);
  }

  function renderGodControls() {
    if (!isGod) return;
    const host = $("gm-controls");
    host.replaceChildren(...godControlSpecs().map((spec) => {
      const v = S.god[spec.key];
      const valueLabel = el("span", { class: "val" }, spec.select || spec.seed ? "" : fmtParam(spec, v));
      let input;
      if (spec.select) {
        input = el("select", { class: "select", disabled: spec.disabled || null,
          onchange: (e) => { S.god[spec.key] = e.target.value; } },
          spec.select.map((o) => el("option", { value: o, selected: o === v }, o)));
      } else if (spec.seed) {
        input = el("input", { class: "input", type: "number", min: 0, step: 1, placeholder: "Random", value: v,
          oninput: (e) => { S.god.seed = e.target.value; } });
      } else {
        const slider = el("input", { class: "gm-slider", type: "range", min: spec.min, max: spec.max,
          step: spec.step, value: v, disabled: spec.disabled || null });
        slider.addEventListener("input", () => {
          S.god[spec.key] = Number(slider.value);
          valueLabel.textContent = fmtParam(spec, S.god[spec.key]);
          if (numberBox) numberBox.value = slider.value;
        });
        let numberBox = null;
        if (spec.number) {
          numberBox = el("input", { class: "input", type: "number", min: spec.min, max: spec.max, step: 1, value: v });
          numberBox.addEventListener("change", () => {
            const n = clamp(Math.round(Number(numberBox.value) || spec.min), spec.min, spec.max);
            S.god[spec.key] = n; numberBox.value = n; slider.value = n;
            valueLabel.textContent = fmtParam(spec, n);
          });
        }
        input = el("div", { class: "stack", style: "gap: 6px" }, slider, numberBox);
      }
      return el("div", { class: "gm-control" + (spec.disabled ? " disabled" : "") },
        el("div", { class: "gm-head" }, el("span", {}, spec.label), valueLabel),
        input,
        spec.note ? el("span", { class: "gm-note" }, spec.note) : null);
    }));
  }

  if (isGod) {
    S.god = godDefaults(false);
    $("system-prompt").value = templateFor(S.target);
    $("btn-reset-prompt").addEventListener("click", () => { $("system-prompt").value = templateFor(S.target); });
    $("btn-reset-all").addEventListener("click", () => {
      $("system-prompt").value = templateFor(S.target);
      S.god = godDefaults(true);
      renderGodControls();
    });
  }

  // ---------- input panel ----------
  const input = $("input-text");
  const btnTranslate = $("btn-translate");
  const btnReview = $("btn-review");

  function autoResize() {
    input.style.height = "auto";
    input.style.height = clamp(input.scrollHeight + 2, 360, 500) + "px";
  }
  function renderInputState() {
    const n = input.value.length;
    $("input-counter").textContent = `${full.format(n)} chars | ~${full.format(Math.ceil(n / 4))} tokens`;
    $("key-hint").classList.toggle("hidden", S.apiKey.trim().length >= 10);
    const noText = !input.value.trim();
    btnTranslate.disabled = noText || S.busy;
    btnTranslate.classList.toggle("btn-translate-live", S.busy && S.phase === "translate");
    btnTranslate.querySelector(".label").textContent =
      S.busy && S.phase === "translate" ? "Translating..." : "Translate";
    if (btnReview) {
      btnReview.disabled = noText || S.busy;
      btnReview.textContent = S.busy && S.phase === "review" ? "Reviewing..." : "Translate and Review";
    }
    swapBtn.disabled = S.source === "auto" || S.busy;
  }
  input.addEventListener("input", () => { autoResize(); renderInputState(); });
  btnTranslate.addEventListener("click", () => handleTranslate(false));
  if (btnReview) btnReview.addEventListener("click", () => handleTranslate(true));
  window.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !keyModalOpen() && !S.busy) {
      e.preventDefault();
      if (input.value.trim()) handleTranslate(false);
    }
  });

  // ---------- tabs ----------
  function tabButton(id, ...label) {
    return el("button", {
      class: "tab" + (S.panel === id ? " active" : ""),
      type: "button",
      onclick: () => { S.panel = id; render(); },
    }, ...label);
  }
  function renderTabs() {
    const tabs = [tabButton("input", "Input")];
    if (S.draftText != null) tabs.push(tabButton("draft", "Draft"));
    if (S.critiqueText != null) tabs.push(tabButton("critique", "Critique"));
    for (const a of S.attempts) {
      tabs.push(tabButton(`attempt-${a.n}`, `Attempt ${a.n} `,
        a.allPassed ? el("span", { class: "ok" }, "✓") : el("span", { class: "bad" }, "✕")));
    }
    if (S.pending) {
      const pend = tabButton("pending", `Attempt ${S.pending.n}`);
      pend.classList.add("pending");
      tabs.push(pend);
    }
    tabs.push(tabButton("output", "Output"));
    $("tabs").replaceChildren(...tabs);
  }
  function renderCost() {
    $("cost-display").textContent = `Current: ${usd2(S.currentCost)} · Session: ${usd2(S.sessionCost)}`;
  }

  // ---------- panels ----------
  function loaderView(title, message) {
    return el("div", { class: "translation-wow animate-fade-in" },
      el("div", { class: "translation-wow-card" },
        el("div", { class: "ai-orb" },
          el("div", { class: "ai-orb-ring" }), el("div", { class: "ai-orb-ring r2" }), el("div", { class: "ai-orb-core" })),
        el("p", { class: "translation-wow-title loading-text-shimmer" }, title),
        el("div", { class: "translation-message-rail" },
          el("div", { class: "translation-message-text", id: "loading-message" }, message)),
        el("div", { class: "ai-progress-track" }, el("div", { class: "ai-progress-fill" }))));
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = el("textarea", { style: "position:fixed;opacity:0" });
      ta.value = text;
      document.body.append(ta);
      ta.select();
      try { document.execCommand("copy"); } catch { /* ignore */ }
      ta.remove();
    }
    S.copied = true; render();
    setTimeout(() => { S.copied = false; render(); }, 1500);
  }

  function reviewView() {
    if (!cfg.endpoints.review) return null;
    const r = S.review;
    if (r.state === "idle") {
      return el("p", { class: "modal-note" }, "Use Translate and Review for a second-pass quality check.");
    }
    if (r.state === "waiting") {
      return el("div", { class: "review-card loading-text-shimmer" }, "Translation agent done. Starting review agent in 5 seconds...");
    }
    if (r.state === "running") {
      return el("div", { class: "review-card loading-text-shimmer" }, "Review agent working on quality and accuracy checks...");
    }
    if (r.state === "error") {
      return el("div", { class: "review-card" }, el("h4", {}, "Review Summary"), el("p", { class: "muted" }, r.error));
    }
    const res = r.result;
    const issues = (res.issues || []).slice(0, 5);
    return el("div", { class: "review-card animate-fade-in" },
      el("h4", {}, "Review Summary"),
      issues.length
        ? el("ul", {}, issues.map((i) => el("li", {}, i)))
        : el("p", { class: "muted" }, "No issues found. Translation looks good."),
      res.correctedTranslation && !r.applied
        ? el("button", { class: "btn btn-accent btn-sm", type: "button", onclick: () => {
            S.translatedText = res.correctedTranslation;
            S.review = { ...S.review, applied: true };
            render();
          } }, "Provide corrected version")
        : null);
  }

  function outputView() {
    if (S.loading) {
      return loaderView("Translator Agent In Action", cfg.loadingMessages[S.msgIdx % cfg.loadingMessages.length]);
    }
    if (S.error) {
      return el("div", { class: "error-box animate-fade-in" },
        el("span", {}, S.error),
        el("button", { class: "btn btn-sm", type: "button", onclick: () => handleTranslate(S.lastWithReview) }, "Try again"));
    }
    if (S.translatedText == null) {
      return el("pre", { class: "output-block empty" }, "Translation will appear here");
    }
    const n = S.translatedText.length;
    const tokens = S.outputTokens == null ? "—" : full.format(S.outputTokens);
    const status = S.pending
      ? el("span", { class: "loading-text-shimmer" },
          S.pending.kind === "verify" ? "Running verification..." : "Fixing failing checks...")
      : null;
    return el("div", { class: "animate-fade-in" },
      el("div", { class: "output-toolbar" },
        el("span", {}, `${full.format(n)} chars | ${tokens} tokens | ${usdSmart(S.currentCost)}`),
        status,
        el("span", { class: "header-actions" },
          el("button", { class: "btn btn-sm", type: "button", onclick: () => copyText(S.translatedText) },
            S.copied ? "Copied!" : "Copy"),
          el("button", { class: "btn btn-sm", type: "button", disabled: S.busy || null, onclick: newTranslation }, "New Translation"))),
      el("pre", { class: "output-block" }, el("code", {}, S.translatedText)),
      S.retryError && !S.panel.startsWith("attempt") ? el("p", { class: "modal-note" }, "Verification stopped: " + S.retryError) : null,
      reviewView());
  }

  function attemptView(n) {
    const a = S.attempts.find((x) => x.n === n);
    if (!a) return el("p", { class: "muted" }, "Attempt not found.");
    if (a.error) {
      return el("div", {},
        el("div", { class: "banner bad" }, `Attempt ${n} of ${L.maxAttempts} — verification could not complete.`),
        el("div", { class: "error-box" }, el("span", {}, a.error)));
    }
    return el("div", { class: "animate-fade-in" },
      el("div", { class: "banner " + (a.allPassed ? "ok" : "bad") },
        a.allPassed
          ? `Attempt ${n} of ${L.maxAttempts} — all checks passed on independent review.`
          : `Attempt ${n} of ${L.maxAttempts} — some checks did not pass on independent review.`),
      el("ul", { class: "check-list" }, a.results.map((r, idx) =>
        el("li", {},
          el("span", { class: r.pass ? "mark-ok" : "mark-bad" }, r.pass ? "✓" : "✕"),
          el("span", {}, a.checklist[idx] || `Check ${r.item}`,
            r.note ? el("div", { class: "note" }, r.note) : null)))),
      el("div", { class: "field-label", style: "margin-bottom:6px" }, "Text graded in this attempt"),
      el("pre", { class: "output-block" }, el("code", {}, a.translatedText)));
  }

  function pendingView() {
    if (!S.pending) return el("p", { class: "muted" }, "No verification in progress.");
    const msg = S.pending.kind === "verify"
      ? `Running verification for attempt ${S.pending.n}...`
      : `Fixing failing checks for attempt ${S.pending.n}...`;
    return loaderView(msg, "Independent reviewer at work");
  }

  function renderPanel() {
    const inputPanel = $("panel-input");
    const dyn = $("panel-dynamic");
    inputPanel.classList.toggle("hidden", S.panel !== "input");
    dyn.classList.toggle("hidden", S.panel === "input");
    if (S.panel === "input") return;
    let view;
    if (S.panel === "output") view = outputView();
    else if (S.panel === "draft") view = el("pre", { class: "output-block" }, el("code", {}, S.draftText || ""));
    else if (S.panel === "critique") view = el("pre", { class: "output-block" }, el("code", {}, S.critiqueText || ""));
    else if (S.panel === "pending") view = pendingView();
    else if (S.panel.startsWith("attempt-")) view = attemptView(Number(S.panel.slice(8)));
    else view = outputView();
    dyn.replaceChildren(view);
  }

  function render() {
    if (S.panel === "pending" && !S.pending) S.panel = "output";
    renderTabs();
    renderPanel();
    renderInputState();
    renderCost();
  }

  // ---------- requests ----------
  function translationBody() {
    const base = {
      text: input.value, sourceLang: S.source, targetLang: S.target, model: S.model, apiKey: S.apiKey,
    };
    if (!isGod) return { ...base, maxOutputTokens: modelOutputLimit() };
    const g = S.god;
    const systemPrompt = $("system-prompt").value;
    if (isClaude) {
      return { ...base, systemPrompt, temperature: g.temperature, topK: g.topK,
        maxOutputTokens: g.maxTokens, effort: g.effort };
    }
    const body = { ...base, systemPrompt, temperature: g.temperature, topP: g.topP, topK: g.topK,
      maxOutputTokens: g.maxTokens, presencePenalty: g.presencePenalty,
      frequencyPenalty: g.frequencyPenalty, thinkingLevel: g.thinkingLevel };
    const seed = Number.parseInt(g.seed, 10);
    if (g.seed !== "" && Number.isFinite(seed) && seed >= 0) body.seed = seed;
    return body;
  }

  async function runVerificationLoop(finalText) {
    if (isGod || !S.verifyEnabled || !cfg.endpoints.verify) return finalText;
    let attempt = 1;
    let current = finalText;
    const common = { originalText: input.value, targetLang: S.target, model: S.model, apiKey: S.apiKey };
    for (;;) {
      S.pending = { n: attempt, kind: "verify" };
      render();
      let v;
      try {
        v = await postJSON(cfg.endpoints.verify, { ...common, translatedText: current });
      } catch (e) {
        S.retryError = e.message;
        S.attempts.push({ n: attempt, error: e.message, translatedText: current });
        break;
      }
      addUsage(v.usage);
      S.attempts.push({ n: attempt, translatedText: current, checklist: v.checklist, results: v.results, allPassed: v.allPassed });
      if (v.allPassed || attempt >= L.maxAttempts) break;
      const failing = v.results
        .map((r, idx) => ({ r, idx }))
        .filter(({ r }) => !r.pass)
        .map(({ r, idx }) => ({ description: v.checklist[idx], note: r.note }));
      if (!failing.length) break;
      S.pending = { n: attempt + 1, kind: "fix" };
      render();
      try {
        const f = await postJSON(cfg.endpoints.fix, { ...common, currentTranslation: current, failingChecks: failing });
        addUsage(f.usage);
        current = f.translatedText;
        S.translatedText = current; // Output tab always shows the latest text
      } catch (e) {
        S.retryError = e.message;
        break;
      }
      attempt += 1;
    }
    S.pending = null;
    render();
    return current;
  }

  let msgTimer = null;
  function startMessages() {
    S.msgIdx = 0;
    stopMessages();
    msgTimer = setInterval(() => {
      S.msgIdx += 1;
      const node = $("loading-message");
      if (node && S.loading) {
        node.textContent = cfg.loadingMessages[S.msgIdx % cfg.loadingMessages.length];
        node.style.animation = "none"; void node.offsetWidth; node.style.animation = "";
      }
    }, 1500);
  }
  function stopMessages() { if (msgTimer) clearInterval(msgTimer); msgTimer = null; }

  function resetResults() {
    Object.assign(S, {
      error: null, translatedText: null, draftText: null, critiqueText: null, outputTokens: null,
      attempts: [], pending: null, retryError: null, review: { state: "idle" }, currentCost: 0,
    });
  }

  async function handleTranslate(withReview) {
    if (S.busy) return;
    S.lastWithReview = withReview;
    resetResults();
    S.panel = "output";
    if (S.apiKey.trim().length < 10) { S.error = cfg.noKeyError; render(); return; }
    if (!input.value.trim()) { S.error = "Please enter some text to translate."; render(); return; }

    S.busy = true; S.phase = "translate"; S.loading = true;
    startMessages();
    render();
    let result;
    try {
      result = await postJSON(cfg.endpoints.translate, translationBody());
    } catch (e) {
      S.error = e.message;
      S.busy = false; S.loading = false; S.phase = null;
      stopMessages(); render();
      return;
    }
    stopMessages();
