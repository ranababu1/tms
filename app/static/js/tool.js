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
