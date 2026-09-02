/* Scout globe — verbatim port of LGlobe from scout/scout-landing.jsx (ruslanmv/scout@master).
   Registered as <scout-globe>; fills its parent, same dot-matrix earth, arcs, sparks, city pulses. */
(function () {
  const L_MAP = [
    "................................................",
    "........#######..####............#####..........",
    "......##########.#####....#####################.",
    "..##############.####.#..######################.",
    "..###.##########.......#.######################.",
    ".......########........########################.",
    ".......########.........###################.....",
    "........######........#####################.....",
    ".........###.........#####################......",
    "..........###........###################........",
    "...........###.......###########.##..##.........",
    ".............#####.....########......######.....",
    ".............######.....#######.......#######...",
    "..............#####......######.........####....",
    "..............####.......#####.#.......######...",
    "...............###........####.........######...",
    "...............##.........###............####...",
    "...............##.............................#.",
    "...............##............................##.",
    "...............##...............................",
    "................................................",
    "................................................",
    "................................................",
    "................................................"
  ].map(r => (r + "................................................").slice(0, 48));

  const D2R = Math.PI / 180;
  const CITIES = [[41.9, 12.5], [51.5, -0.1], [52.5, 13.4], [40.4, -3.7], [40.7, -74]];
  const ARCS = [[0, 1], [0, 2], [0, 4]];

  class ScoutGlobe extends HTMLElement {
    connectedCallback() {
      if (this._canvas) return;
      this.style.position = this.style.position || "absolute";
      const canvas = document.createElement("canvas");
      canvas.setAttribute("aria-hidden", "true");
      canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%;pointer-events:none";
      this.appendChild(canvas);
      this._canvas = canvas;
      this._start(canvas);
    }
    disconnectedCallback() {
      cancelAnimationFrame(this._raf);
      if (this._ro) this._ro.disconnect();
    }
    _start(canvas) {
      const ctx = canvas.getContext("2d");
      const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const host = this;
      let W = 0, H = 0;
      const fit = () => {
        const r = host.getBoundingClientRect();
        W = r.width; H = r.height;
        canvas.width = Math.max(1, W * dpr); canvas.height = Math.max(1, H * dpr);
      };
      fit();
      if (typeof ResizeObserver !== "undefined") { this._ro = new ResizeObserver(fit); this._ro.observe(host); }

      const dots = [];
      for (let ri = 0; ri < 24; ri++) for (let ci = 0; ci < 48; ci++) {
        if (L_MAP[ri][ci] !== "#") continue;
        for (let k = 0; k < 4; k++) {
          dots.push([(90 - (ri + Math.random()) * 7.5) * D2R, (-180 + (ci + Math.random()) * 7.5) * D2R]);
        }
      }
      const specks = [];
      for (let k = 0; k < 36; k++) specks.push([Math.random(), Math.random(), 0.4 + Math.random() * 0.6]);
      const cities = CITIES.map(([a, b]) => [a * D2R, b * D2R]);

      const TILT = 0.55, ct = Math.cos(TILT), st = Math.sin(TILT);
      const toVec = (lat, lon, spin) => {
        const cp = Math.cos(lat);
        return [cp * Math.sin(lon + spin), Math.sin(lat), cp * Math.cos(lon + spin)];
      };
      const slerp = (a, b, u) => {
        const d = Math.max(-1, Math.min(1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]));
        const om = Math.acos(d), so = Math.sin(om) || 1e-6;
        const f = Math.sin((1 - u) * om) / so, g2 = Math.sin(u * om) / so;
        return [a[0] * f + b[0] * g2, a[1] * f + b[1] * g2, a[2] * f + b[2] * g2];
      };

      let t0 = -1;
      const draw = (t) => {
        if (t0 < 0) t0 = t;
        const spin = reduced ? 0.3 : 0.3 + (t - t0) * 0.000022;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, W, H);
        const R = W * 0.42, cx = W * 0.68, cy = H * 1.02;
        const pv = (v, m) => {
          const s = m || 1;
          const y = v[1] * ct - v[2] * st, z = v[1] * st + v[2] * ct;
          return [cx + v[0] * R * s, cy - y * R * s, z];
        };
        let g = ctx.createRadialGradient(cx, cy, R * 0.82, cx, cy, R * 1.28);
        g.addColorStop(0, "rgba(34,200,120,0)"); g.addColorStop(0.5, "rgba(34,200,120,.15)"); g.addColorStop(1, "rgba(34,200,120,0)");
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R * 1.28, 0, 7); ctx.fill();
        g = ctx.createRadialGradient(cx - R * 0.35, cy - R * 0.55, R * 0.1, cx, cy, R);
        g.addColorStop(0, "#104228"); g.addColorStop(0.55, "#072717"); g.addColorStop(1, "#031a10");
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.fill();
        ctx.strokeStyle = "rgba(83,243,157,.22)"; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.stroke();
        for (let i = 0; i < specks.length; i++) {
          const tw = reduced ? 0.6 : 0.35 + 0.35 * Math.sin(t / 900 + i * 2.1);
          ctx.fillStyle = "rgba(83,243,157," + (tw * specks[i][2] * 0.5).toFixed(3) + ")";
          ctx.fillRect(specks[i][0] * W, specks[i][1] * H, 1.5, 1.5);
        }
        for (let i = 0; i < dots.length; i++) {
          const p = pv(toVec(dots[i][0], dots[i][1], spin));
          if (p[2] < 0.02 || p[1] > H + 4) continue;
          ctx.fillStyle = "rgba(83,243,157," + (0.22 + p[2] * 0.6).toFixed(3) + ")";
          const s = 1.3 + p[2] * 1.6;
          ctx.fillRect(p[0] - s / 2, p[1] - s / 2, s, s);
        }
        for (let i = 0; i < ARCS.length; i++) {
          const a = toVec(cities[ARCS[i][0]][0], cities[ARCS[i][0]][1], spin);
          const b = toVec(cities[ARCS[i][1]][0], cities[ARCS[i][1]][1], spin);
          ctx.beginPath();
          let vis = false;
          for (let s2 = 0; s2 <= 26; s2++) {
            const u = s2 / 26;
            const p = pv(slerp(a, b, u), 1 + 0.13 * Math.sin(u * Math.PI));
            if (p[2] < -0.05) { vis = false; continue; }
            if (!vis) { ctx.moveTo(p[0], p[1]); vis = true; } else ctx.lineTo(p[0], p[1]);
          }
          ctx.strokeStyle = "rgba(83,243,157,.4)"; ctx.lineWidth = 1.1; ctx.stroke();
          const u2 = reduced ? 0.5 : ((t / 2200) + i * 0.33) % 1;
          const sp = pv(slerp(a, b, u2), 1 + 0.13 * Math.sin(u2 * Math.PI));
          if (sp[2] > 0) {
            const g3 = ctx.createRadialGradient(sp[0], sp[1], 0, sp[0], sp[1], 6);
            g3.addColorStop(0, "rgba(125,255,181,.95)"); g3.addColorStop(1, "rgba(125,255,181,0)");
            ctx.fillStyle = g3; ctx.beginPath(); ctx.arc(sp[0], sp[1], 6, 0, 7); ctx.fill();
          }
        }
        for (let i = 0; i < cities.length; i++) {
          const p = pv(toVec(cities[i][0], cities[i][1], spin));
          if (p[2] < 0.05) continue;
          const pulse = reduced ? 1 : 0.75 + 0.25 * Math.sin(t / 620 + i * 1.7);
          const g4 = ctx.createRadialGradient(p[0], p[1], 0, p[0], p[1], 11 * pulse);
          g4.addColorStop(0, "rgba(83,243,157,.75)"); g4.addColorStop(1, "rgba(83,243,157,0)");
          ctx.fillStyle = g4; ctx.beginPath(); ctx.arc(p[0], p[1], 11 * pulse, 0, 7); ctx.fill();
          ctx.fillStyle = "#7dffb5"; ctx.beginPath(); ctx.arc(p[0], p[1], 2.2, 0, 7); ctx.fill();
        }
        if (!reduced) this._raf = requestAnimationFrame(draw);
      };
      this._raf = requestAnimationFrame(draw);
    }
  }
  if (!customElements.get("scout-globe")) customElements.define("scout-globe", ScoutGlobe);
})();
