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
          p.vx += (dx / dist) * ATTRACT_STRENGTH * f - (dy / dist) * SWIRL_STRENGTH * f;
          p.vy += (dy / dist) * ATTRACT_STRENGTH * f + (dx / dist) * SWIRL_STRENGTH * f;
        }
      }
      p.vx += rand(-0.01, 0.01); p.vy += rand(-0.01, 0.01);
      const speed = Math.hypot(p.vx, p.vy);
      if (speed > MAX_SPEED) { p.vx = (p.vx / speed) * MAX_SPEED; p.vy = (p.vy / speed) * MAX_SPEED; }
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x += w; else if (p.x > w) p.x -= w;
      if (p.y < 0) p.y += h; else if (p.y > h) p.y -= h;
    }

    for (let i = 0; i < particles.length; i++) {
      const a = particles[i];
      for (let j = i + 1; j < particles.length; j++) {
        const b = particles[j];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < LINK_DISTANCE) {
          ctx.strokeStyle = `hsla(${(a.hue + b.hue) / 2}, 90%, 65%, ${0.16 * (1 - d / LINK_DISTANCE)})`;
          ctx.lineWidth = 0.6;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        }
      }
    }

    for (const p of particles) {
      const twinkle = 0.6 + 0.4 * Math.sin(t / 700 + p.phase);
      const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 6);
      glow.addColorStop(0, `hsla(${p.hue}, 95%, 70%, ${0.35 * twinkle})`);
      glow.addColorStop(1, `hsla(${p.hue}, 95%, 70%, 0)`);
