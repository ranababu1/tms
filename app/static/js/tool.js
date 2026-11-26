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
