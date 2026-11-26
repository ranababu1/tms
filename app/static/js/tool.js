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
