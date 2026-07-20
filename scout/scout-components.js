/* Compiled from scout-components.jsx by @babel/preset-react. Do not edit directly; edit the .jsx and re-run scripts/build_scout_report.js. */
(function () {
/* global React */
const {
  useState,
  useEffect,
  useRef
} = React;
const S = window.SCOUT;

/* ---------- brand mark: concentric radar ---------- */
function Mark({
  size = 26,
  dark = false
}) {
  const ring = dark ? "#54d98c" : "#15a05a";
  return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 32 32",
    fill: "none",
    style: {
      flex: "none"
    }
  }, /*#__PURE__*/React.createElement("circle", {
    cx: "16",
    cy: "16",
    r: "14.5",
    stroke: ring,
    strokeWidth: "1.4",
    opacity: ".4"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "16",
    cy: "16",
    r: "9",
    stroke: ring,
    strokeWidth: "1.4",
    opacity: ".7"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "16",
    cy: "16",
    r: "3.2",
    fill: ring
  }), /*#__PURE__*/React.createElement("path", {
    d: "M16 16 L29 9",
    stroke: ring,
    strokeWidth: "1.4",
    strokeLinecap: "round"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "24.5",
    cy: "11",
    r: "2",
    fill: ring
  }));
}

/* ---------- animated score ring (with count-up) ---------- */
function ScoreRing({
  value,
  size = 56,
  stroke = 5,
  label,
  dark = false
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const [off, setOff] = useState(c);
  const [num, setNum] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setOff(c - value / 100 * c), 80);
    return () => clearTimeout(t);
  }, [value, c]);
  useEffect(() => {
    let raf;
    const dur = 900,
      start = performance.now();
    const tick = now => {
      const p = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      setNum(Math.round(value * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  const track = dark ? "rgba(255,255,255,.14)" : "#e7f4ec";
  const gid = "rg-" + (dark ? "d" : "l");
  return /*#__PURE__*/React.createElement("div", {
    className: "ring-wrap",
    style: {
      width: size,
      height: size
    }
  }, /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    style: {
      transform: "rotate(-90deg)"
    }
  }, /*#__PURE__*/React.createElement("circle", {
    cx: size / 2,
    cy: size / 2,
    r: r,
    stroke: track,
    strokeWidth: stroke,
    fill: "none"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: size / 2,
    cy: size / 2,
    r: r,
    stroke: `url(#${gid})`,
    strokeWidth: stroke,
    fill: "none",
    strokeLinecap: "round",
    strokeDasharray: c,
    strokeDashoffset: off,
    style: {
      transition: "stroke-dashoffset 1.1s cubic-bezier(.2,.7,.2,1)"
    }
  }), /*#__PURE__*/React.createElement("defs", null, /*#__PURE__*/React.createElement("linearGradient", {
    id: gid,
    x1: "0",
    y1: "0",
    x2: "1",
    y2: "1"
  }, /*#__PURE__*/React.createElement("stop", {
    stopColor: dark ? "#54d98c" : "#15a05a"
  }), /*#__PURE__*/React.createElement("stop", {
    offset: "1",
    stopColor: dark ? "#34d399" : "#0e7340"
  })))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      inset: 0,
      display: "grid",
      placeItems: "center",
      lineHeight: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: "center"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--mono)",
      fontWeight: 700,
      fontSize: size > 70 ? "1.3rem" : ".98rem",
      color: dark ? "#f2f8f4" : "var(--ink)",
      fontVariantNumeric: "tabular-nums"
    }
  }, num), label && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--mono)",
      fontSize: ".5rem",
      letterSpacing: ".12em",
      color: dark ? "#9fbdb0" : "var(--faint)",
      textTransform: "uppercase",
      marginTop: 2
    }
  }, label))));
}

/* ---------- radar bars ---------- */
function RadarBars({
  dims,
  dark = false
}) {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setOn(true), 120);
    return () => clearTimeout(t);
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    className: "radarbars"
  }, Object.entries(dims).map(([k, v]) => /*#__PURE__*/React.createElement("div", {
    className: "rb " + (dark ? "dk" : "lt"),
    key: k
  }, /*#__PURE__*/React.createElement("span", {
    className: "lab"
  }, k), /*#__PURE__*/React.createElement("span", {
    className: "track"
  }, /*#__PURE__*/React.createElement("i", {
    className: "fill",
    style: {
      width: on ? v + "%" : 0
    }
  })), /*#__PURE__*/React.createElement("span", {
    className: "num"
  }, v))));
}

/* ---------- SVG radar polygon ---------- */
function RadarPolygon({
  dims,
  size = 230,
  dark = false
}) {
  const keys = Object.keys(dims);
  const cx = size / 2,
    cy = size / 2,
    R = size / 2 - 30;
  const pt = (i, rad) => {
    const a = Math.PI * 2 * i / keys.length - Math.PI / 2;
    return [cx + Math.cos(a) * rad, cy + Math.sin(a) * rad];
  };
  const rings = [0.25, 0.5, 0.75, 1];
  const dataPts = keys.map((k, i) => pt(i, dims[k] / 100 * R));
  const [grow, setGrow] = useState(0);
  useEffect(() => {
    let f;
    const start = performance.now();
    const tick = now => {
      const p = Math.min(1, (now - start) / 900);
      setGrow(p < 1 ? 1 - Math.pow(1 - p, 3) : 1);
      if (p < 1) f = requestAnimationFrame(tick);
    };
    f = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(f);
  }, []);
  const gridStroke = dark ? "rgba(120,200,160,.2)" : "rgba(21,160,90,.16)";
  const stroke = dark ? "#54d98c" : "#15a05a";
  const fill = dark ? "rgba(84,217,140,.16)" : "rgba(21,160,90,.12)";
  const lab = dark ? "#9fbdb0" : "#5e6b63";
  const poly = dataPts.map(([x, y]) => [cx + (x - cx) * grow, cy + (y - cy) * grow].join(",")).join(" ");
  return /*#__PURE__*/React.createElement("svg", {
    className: "radar-poly",
    width: size,
    height: size,
    viewBox: `0 0 ${size} ${size}`
  }, rings.map((r, i) => /*#__PURE__*/React.createElement("polygon", {
    key: i,
    points: keys.map((_, j) => pt(j, R * r).join(",")).join(" "),
    fill: "none",
    stroke: gridStroke,
    strokeWidth: "1"
  })), keys.map((_, i) => {
    const [x, y] = pt(i, R);
    return /*#__PURE__*/React.createElement("line", {
      key: i,
      x1: cx,
      y1: cy,
      x2: x,
      y2: y,
      stroke: gridStroke,
      strokeWidth: "1"
    });
  }), /*#__PURE__*/React.createElement("polygon", {
    points: poly,
    fill: fill,
    stroke: stroke,
    strokeWidth: "2"
  }), dataPts.map(([x, y], i) => {
    const px = cx + (x - cx) * grow,
      py = cy + (y - cy) * grow;
    return /*#__PURE__*/React.createElement("circle", {
      key: i,
      cx: px,
      cy: py,
      r: "3.2",
      fill: stroke
    });
  }), keys.map((k, i) => {
    const [x, y] = pt(i, R + 16);
    return /*#__PURE__*/React.createElement("text", {
      key: k,
      x: x,
      y: y,
      fill: lab,
      fontSize: "8.5",
      fontFamily: "var(--mono)",
      fontWeight: "600",
      textAnchor: Math.abs(x - cx) < 4 ? "middle" : x > cx ? "start" : "end",
      dominantBaseline: "middle",
      style: {
        textTransform: "uppercase",
        letterSpacing: ".04em"
      }
    }, k.split(" ")[0]);
  }));
}

/* ---------- confidence (plain language) ---------- */
function Conf({
  trust,
  pct = false
}) {
  const high = trust.score >= 0.87;
  return /*#__PURE__*/React.createElement("span", {
    className: "conf " + (high ? "high" : "med")
  }, /*#__PURE__*/React.createElement("span", {
    className: "d"
  }), high ? "High" : "Medium", pct ? " · " + Math.round(trust.score * 100) + "%" : "");
}

/* ---------- copy button ---------- */
function CopyButton({
  text
}) {
  const [done, setDone] = useState(false);
  return /*#__PURE__*/React.createElement("button", {
    className: "copybtn" + (done ? " done" : ""),
    onClick: e => {
      e.stopPropagation();
      try {
        navigator.clipboard && navigator.clipboard.writeText(text);
      } catch (err) {}
      setDone(true);
      setTimeout(() => setDone(false), 1400);
    }
  }, done ? "✓ Copied" : "Copy");
}

/* ---------- sticky next-move bar ---------- */
function NextBar({
  project,
  onView,
  onClose
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "nextbar"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "nb-l"
  }, "Your next move"), /*#__PURE__*/React.createElement("div", {
    className: "nb-v"
  }, "Build ", project)), /*#__PURE__*/React.createElement("button", {
    className: "btn primary small on-dark",
    onClick: onView
  }, "View plan"), /*#__PURE__*/React.createElement("button", {
    className: "nb-x",
    onClick: onClose,
    "aria-label": "Dismiss"
  }, "\u2715"));
}

/* ---------- opportunity card (quiet; ring + metrics only in advanced) ---------- */
function OpportunityCard({
  topic,
  rank,
  onInspect,
  advanced
}) {
  const dims = S.radar(topic);
  const score = S.composite(topic);
  const diff = S.difficulty(topic);
  return /*#__PURE__*/React.createElement("article", {
    className: "card opcard",
    onClick: () => onInspect(topic)
  }, /*#__PURE__*/React.createElement("div", {
    className: "head"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("h4", {
    className: "title"
  }, topic.short), /*#__PURE__*/React.createElement("div", {
    className: "act"
  }, S.actionShort(topic))), advanced ? /*#__PURE__*/React.createElement(ScoreRing, {
    value: score
  }) : /*#__PURE__*/React.createElement("span", {
    className: "diff " + diff
  }, diff)), advanced && /*#__PURE__*/React.createElement("div", {
    className: "metrics"
  }, /*#__PURE__*/React.createElement("div", {
    className: "metric"
  }, /*#__PURE__*/React.createElement("div", {
    className: "ml"
  }, "Local relevance"), /*#__PURE__*/React.createElement("div", {
    className: "mv"
  }, /*#__PURE__*/React.createElement("span", {
    className: "minibar"
  }, /*#__PURE__*/React.createElement("i", {
    style: {
      width: dims["Local relevance"] + "%"
    }
  })), dims["Local relevance"])), /*#__PURE__*/React.createElement("div", {
    className: "metric"
  }, /*#__PURE__*/React.createElement("div", {
    className: "ml"
  }, "Global momentum"), /*#__PURE__*/React.createElement("div", {
    className: "mv"
  }, /*#__PURE__*/React.createElement("span", {
    className: "minibar"
  }, /*#__PURE__*/React.createElement("i", {
    style: {
      width: dims["Global momentum"] + "%"
    }
  })), dims["Global momentum"])), /*#__PURE__*/React.createElement("div", {
    className: "metric"
  }, /*#__PURE__*/React.createElement("div", {
    className: "ml"
  }, "Career value"), /*#__PURE__*/React.createElement("div", {
    className: "mv"
  }, /*#__PURE__*/React.createElement("span", {
    className: "minibar"
  }, /*#__PURE__*/React.createElement("i", {
    style: {
      width: dims["Career value"] + "%"
    }
  })), dims["Career value"])), /*#__PURE__*/React.createElement("div", {
    className: "metric"
  }, /*#__PURE__*/React.createElement("div", {
    className: "ml"
  }, "Difficulty"), /*#__PURE__*/React.createElement("div", {
    className: "mv"
  }, /*#__PURE__*/React.createElement("span", {
    className: "diff " + diff
  }, diff)))), /*#__PURE__*/React.createElement("div", {
    className: "bestproj"
  }, /*#__PURE__*/React.createElement("span", {
    className: "bp-k"
  }, "Build"), topic.project_ideas[0]), /*#__PURE__*/React.createElement("div", {
    className: "foot"
  }, /*#__PURE__*/React.createElement("span", {
    className: "whyrank"
  }, S.whyRank(topic)), /*#__PURE__*/React.createElement("span", {
    className: "inspect"
  }, "Why? \u2192")));
}

/* ---------- project card ---------- */
function ProjectCard({
  idea,
  topic
}) {
  const diff = S.difficulty(topic);
  return /*#__PURE__*/React.createElement("article", {
    className: "card proj"
  }, /*#__PURE__*/React.createElement("div", {
    className: "ph"
  }, /*#__PURE__*/React.createElement("span", {
    className: "ptag"
  }, topic.short), /*#__PURE__*/React.createElement("span", {
    className: "diff " + diff,
    style: {
      marginLeft: "auto"
    }
  }, diff)), /*#__PURE__*/React.createElement("h4", null, idea), /*#__PURE__*/React.createElement("p", null, "Turn the ", topic.short, " signal into a portfolio piece \u2014 a focused repo, a live demo, and a writeup."), /*#__PURE__*/React.createElement("div", {
    className: "stack"
  }, topic.skills.slice(0, 4).map(s => /*#__PURE__*/React.createElement("span", {
    className: "tag",
    key: s
  }, s))));
}

/* ---------- constellation decoration for dark panels ---------- */
function Constellation() {
  return /*#__PURE__*/React.createElement("svg", {
    className: "net",
    viewBox: "0 0 600 300",
    preserveAspectRatio: "xMidYMid slice",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M-20 210 C 120 150, 240 250, 380 160 S 640 120, 700 170",
    stroke: "rgba(84,217,140,.22)",
    strokeWidth: "1"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M-20 250 C 140 220, 260 280, 420 210 S 660 190, 720 220",
    stroke: "rgba(84,217,140,.14)",
    strokeWidth: "1"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M120 40 L 300 110 L 470 60",
    stroke: "rgba(84,217,140,.16)",
    strokeWidth: "1"
  }), [[120, 40], [300, 110], [470, 60], [380, 160], [560, 130], [60, 150]].map(([x, y], i) => /*#__PURE__*/React.createElement("g", {
    key: i
  }, /*#__PURE__*/React.createElement("circle", {
    cx: x,
    cy: y,
    r: "8",
    fill: "rgba(84,217,140,.12)"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: x,
    cy: y,
    r: "2.6",
    fill: "#54d98c"
  }))));
}
window.ScoutUI = {
  Mark,
  ScoreRing,
  RadarBars,
  RadarPolygon,
  Conf,
  CopyButton,
  NextBar,
  OpportunityCard,
  ProjectCard,
  Constellation
};
})();
