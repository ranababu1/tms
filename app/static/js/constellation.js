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

