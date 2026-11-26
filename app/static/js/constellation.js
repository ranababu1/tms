// Landing-page particle field: cursor attraction with a tangential swirl.
// No-op under prefers-reduced-motion.
(function () {
  "use strict";
  const canvas = document.getElementById("constellation");
  if (!canvas) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const ctx = canvas.getContext("2d");
  const ATTRACT_RADIUS = 220, LINK_DISTANCE = 150;
  const ATTRACT_STRENGTH = 0.028, SWIRL_STRENGTH = 0.012;
  const MAX_SPEED = 0.9, DRIFT_SPEED = 0.18;
  let w = 0, h = 0, dpr = 1, particles = [], raf = 0;
  const mouse = { x: -9999, y: -9999, active: false };

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const rand = (a, b) => a + Math.random() * (b - a);

  function resize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = rect.width; h = rect.height;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = clamp(Math.floor((w * h) / 9000), 70, 220);
    particles = Array.from({ length: count }, () => ({
      x: rand(0, w), y: rand(0, h),
      vx: rand(-DRIFT_SPEED, DRIFT_SPEED), vy: rand(-DRIFT_SPEED, DRIFT_SPEED),
      r: rand(0.8, 2.2), hue: rand(190, 320), phase: rand(0, Math.PI * 2),
    }));
  }

  function step(t) {
    ctx.clearRect(0, 0, w, h);
    ctx.globalCompositeOperation = "lighter";

    for (const p of particles) {
      if (mouse.active) {
        const dx = mouse.x - p.x, dy = mouse.y - p.y;
        const dist = Math.hypot(dx, dy);
        if (dist < ATTRACT_RADIUS && dist > 1) {
          const f = 1 - dist / ATTRACT_RADIUS;
