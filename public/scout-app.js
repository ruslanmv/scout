/* Compiled from scout-app.jsx by @babel/preset-react. Do not edit directly; edit the .jsx and recompile. */
(function () {
/* global React, ReactDOM */
const {
  useState: uS,
  useEffect: uE
} = React;
const SA = window.SCOUT;
const UI = window.ScoutUI;
const Drawer = window.DeepDiveDrawer;
const Landing = window.ScoutLanding;
const SCAN_LINES = ["Reading developer signals…", "GitHub · Hugging Face", "Jobs · news · community", "Matching to your goal", "Building your report"];
function ranked(goal) {
  const w = (SA.GOALS.find(g => g.id === goal) || SA.GOALS[0]).weight;
  return [...SA.TOPICS].sort((a, b) => SA.composite(b) * 0.6 + b.signals[w] * 0.4 - (SA.composite(a) * 0.6 + a.signals[w] * 0.4));
}
function ToolHeader() {
  return /*#__PURE__*/React.createElement("header", {
    className: "tool-header"
  }, /*#__PURE__*/React.createElement("div", {
    className: "tool-header__in"
  }, /*#__PURE__*/React.createElement("a", {
    className: "tool-header__back",
    href: "index.html"
  }, "\u2190 ", /*#__PURE__*/React.createElement("span", null, "All tools")), /*#__PURE__*/React.createElement("div", {
    className: "tool-header__title"
  }, /*#__PURE__*/React.createElement("span", {
    className: "gl"
  }, "\u25C7"), " Scout"), /*#__PURE__*/React.createElement("div", {
    className: "tool-header__user"
  }, /*#__PURE__*/React.createElement("span", {
    className: "live"
  }, /*#__PURE__*/React.createElement("span", {
    className: "dot"
  }), "LIVE"), /*#__PURE__*/React.createElement("span", {
    className: "avatar"
  }, "RM"))));
}
function App() {
  const [phase, setPhase] = uS("hero");
  const [country, setCountry] = uS("Italy");
  const [city, setCity] = uS("Rome");
  const [goal, setGoal] = uS("build_portfolio");
  const [profile, setProfile] = uS("Developer");
  const [scanIdx, setScanIdx] = uS(0);
  const [active, setActive] = uS(null);
  const [open, setOpen] = uS(false);
  const [mode, setMode] = uS("simple");
  const [allLocal, setAllLocal] = uS(false);
  const [allGlobal, setAllGlobal] = uS(false);
  const [barOpen, setBarOpen] = uS(true);
  const [animSafe, setAnimSafe] = uS(false);

  // after entrance animations finish, lock content visible regardless of animation-clock state
  uE(() => {
    setAnimSafe(false);
    const t = setTimeout(() => setAnimSafe(true), 1700);
    return () => clearTimeout(t);
  }, [phase, mode]);
  const goalObj = SA.GOALS.find(g => g.id === goal) || SA.GOALS[0];
  const topics = ranked(goal);
  const top = topics[0];
  const topDims = top ? SA.radar(top) : {};
  const bestCareer = [...SA.TOPICS].sort((a, b) => b.signals.career_value - a.signals.career_value)[0];
  const globalTopics = [...SA.TOPICS].sort((a, b) => SA.radar(b)["Global momentum"] - SA.radar(a)["Global momentum"]);
  const advanced = mode === "advanced";
  const repo = top ? SA.repoName(top) : "";
  const hfName = top ? top.short + " Scout Demo" : "";
  const blogTitle = top ? "How I built a local " + top.short.toLowerCase() + " scout for technology trends" : "";

  // persist mode preference
  uE(() => {
    try {
      const m = localStorage.getItem("scout-mode");
      if (m) setMode(m);
    } catch (e) {}
  }, []);
  uE(() => {
    try {
      localStorage.setItem("scout-mode", mode);
    } catch (e) {}
  }, [mode]);
  function generate() {
    setPhase("scanning");
    setScanIdx(0);
    setBarOpen(true);
    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  }
  uE(() => {
    if (phase !== "scanning") return;
    if (scanIdx >= SCAN_LINES.length) {
      const t = setTimeout(() => setPhase("report"), 340);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setScanIdx(i => i + 1), scanIdx === 0 ? 360 : 300);
    return () => clearTimeout(t);
  }, [phase, scanIdx]);
  function inspect(t) {
    setActive(t);
    setOpen(true);
  }
  function scrollTo(id) {
    const el = document.getElementById(id);
    if (el) window.scrollTo({
      top: el.getBoundingClientRect().top + window.scrollY - 72,
      behavior: "smooth"
    });
  }
  const location = {
    country,
    city
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "app" + (animSafe ? " anim-safe" : "")
  }, phase === "hero" && /*#__PURE__*/React.createElement(Landing, {
    profile: profile,
    setProfile: setProfile,
    city: city,
    country: country,
    setLocation: (c, co) => {
      setCity(c);
      setCountry(co);
    },
    goal: goal,
    setGoal: setGoal,
    onGenerate: generate
  }), phase === "scanning" && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(ToolHeader, null), /*#__PURE__*/React.createElement("div", {
    className: "wrap"
  }, /*#__PURE__*/React.createElement("section", {
    className: "darkpanel scout-hero"
  }, /*#__PURE__*/React.createElement(UI.Constellation, null), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative"
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "eyebrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "dot"
  }), "Your next move"), /*#__PURE__*/React.createElement("h1", null, "Building ", /*#__PURE__*/React.createElement("span", {
    className: "em"
  }, "your plan"), "\u2026"), /*#__PURE__*/React.createElement("div", {
    className: "scanning"
  }, /*#__PURE__*/React.createElement("div", {
    className: "scan-ring"
  }, /*#__PURE__*/React.createElement(UI.ScoreRing, {
    value: Math.min(100, Math.round(scanIdx / SCAN_LINES.length * 100)),
    size: 92,
    stroke: 6,
    dark: true
  })), /*#__PURE__*/React.createElement("div", {
    className: "scan-log"
  }, SCAN_LINES[Math.min(scanIdx, SCAN_LINES.length - 1)]), /*#__PURE__*/React.createElement("div", {
    className: "scan-sub"
  }, city, ", ", country, " \xB7 ", goalObj.label, " \xB7 ", profile)))))), phase === "report" && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(ToolHeader, null), /*#__PURE__*/React.createElement("main", {
    className: "report wrap",
    id: "report"
  }, /*#__PURE__*/React.createElement("div", {
    className: "report-head reveal"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "meta"
  }, "Scout Report"), /*#__PURE__*/React.createElement("h2", null, city, ", ", country)), /*#__PURE__*/React.createElement("div", {
    className: "head-actions"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mode-seg"
  }, /*#__PURE__*/React.createElement("button", {
    className: mode === "simple" ? "active" : "",
    onClick: () => setMode("simple")
  }, "Simple"), /*#__PURE__*/React.createElement("button", {
    className: mode === "advanced" ? "active" : "",
    onClick: () => setMode("advanced")
  }, "Advanced")), /*#__PURE__*/React.createElement("button", {
    className: "btn small",
    onClick: () => window.print()
  }, "Save as PDF"), /*#__PURE__*/React.createElement("button", {
    className: "btn small ghosticon",
    onClick: () => setPhase("hero"),
    title: "New report"
  }, "\u21BA"))), /*#__PURE__*/React.createElement("article", {
    className: "darkpanel move reveal"
  }, /*#__PURE__*/React.createElement("div", {
    className: "move-main"
  }, /*#__PURE__*/React.createElement("div", {
    className: "verdict"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vbadge"
  }, /*#__PURE__*/React.createElement("span", {
    className: "d"
  }), "Your fastest way to grow"), /*#__PURE__*/React.createElement("h3", {
    className: "vhead"
  }, "Learn ", /*#__PURE__*/React.createElement("span", {
    className: "em"
  }, top.short), "."), /*#__PURE__*/React.createElement("p", {
    className: "vsub"
  }, SA.verdict(top, profile, city))), /*#__PURE__*/React.createElement("div", {
    className: "move-rows"
  }, /*#__PURE__*/React.createElement("div", {
    className: "move-row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "ml"
  }, /*#__PURE__*/React.createElement("span", {
    className: "step-n"
  }, "1"), "Learn it"), /*#__PURE__*/React.createElement("span", {
    className: "mv"
  }, top.short, /*#__PURE__*/React.createElement("span", {
    className: "mv-pay"
  }, "\u2192 ", SA.payoff(top).learn)), /*#__PURE__*/React.createElement("span", {
    className: "eff"
  }, SA.effort(top).learn)), /*#__PURE__*/React.createElement("div", {
    className: "move-row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "ml"
  }, /*#__PURE__*/React.createElement("span", {
    className: "step-n"
  }, "2"), "Build it"), /*#__PURE__*/React.createElement("span", {
    className: "mv"
  }, top.project_ideas[0], /*#__PURE__*/React.createElement("span", {
    className: "mv-pay"
  }, "\u2192 ", SA.payoff(top).build)), /*#__PURE__*/React.createElement("span", {
    className: "eff"
  }, SA.effort(top).build)), /*#__PURE__*/React.createElement("div", {
    className: "move-row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "ml"
  }, /*#__PURE__*/React.createElement("span", {
    className: "step-n"
  }, "3"), "Show it"), /*#__PURE__*/React.createElement("span", {
    className: "mv"
  }, "Put it on GitHub + Hugging Face", /*#__PURE__*/React.createElement("span", {
    className: "mv-pay"
  }, "\u2192 ", SA.payoff(top).show)), /*#__PURE__*/React.createElement("span", {
    className: "eff"
  }, SA.effort(top).show))), /*#__PURE__*/React.createElement("div", {
    className: "gain"
  }, "You'll gain a real project for your portfolio ", /*#__PURE__*/React.createElement("b", null, "and"), " a skill people are hiring for."), /*#__PURE__*/React.createElement("div", {
    className: "move-foot"
  }, /*#__PURE__*/React.createElement("span", {
    className: "conf high on-dark"
  }, /*#__PURE__*/React.createElement("span", {
    className: "d"
  }), "High confidence"), /*#__PURE__*/React.createElement("div", {
    className: "ctarow"
  }, /*#__PURE__*/React.createElement("button", {
    className: "btn primary small on-dark",
    onClick: () => scrollTo("visibility")
  }, "Start step 1 \u2192"), /*#__PURE__*/React.createElement("button", {
    className: "btn small on-dark",
    onClick: () => inspect(top)
  }, "Why this?")))), advanced && /*#__PURE__*/React.createElement("div", {
    className: "move-radar"
  }, /*#__PURE__*/React.createElement(UI.RadarPolygon, {
    dims: topDims,
    dark: true,
    size: 200
  }))), advanced && /*#__PURE__*/React.createElement("div", {
    className: "strip reveal",
    style: {
      marginTop: 24
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "kpi"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kpi__icon"
  }, "\u25CE"), /*#__PURE__*/React.createElement("div", {
    className: "kpi__body"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kpi__label"
  }, "Topic to study"), /*#__PURE__*/React.createElement("div", {
    className: "kpi__value"
  }, top.short), /*#__PURE__*/React.createElement("div", {
    className: "kpi__note"
  }, SA.action(top)))), /*#__PURE__*/React.createElement("div", {
    className: "kpi"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kpi__icon"
  }, "\u25C7"), /*#__PURE__*/React.createElement("div", {
    className: "kpi__body"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kpi__label"
  }, "Project to build"), /*#__PURE__*/React.createElement("div", {
    className: "kpi__value",
    style: {
      fontSize: "1.02rem"
    }
  }, top.project_ideas[0]), /*#__PURE__*/React.createElement("div", {
    className: "kpi__note"
  }, top.short))), /*#__PURE__*/React.createElement("div", {
    className: "kpi"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kpi__icon"
  }, "\u25A3"), /*#__PURE__*/React.createElement("div", {
    className: "kpi__body"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kpi__label"
  }, "Best career value"), /*#__PURE__*/React.createElement("div", {
    className: "kpi__value",
    style: {
      fontSize: "1.02rem"
    }
  }, bestCareer.short), /*#__PURE__*/React.createElement("div", {
    className: "kpi__note"
  }, "Career value ", bestCareer.signals.career_value))), /*#__PURE__*/React.createElement("div", {
    className: "kpi"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kpi__icon"
  }, "\u2B21"), /*#__PURE__*/React.createElement("div", {
    className: "kpi__body"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kpi__label"
  }, "Hype risk"), /*#__PURE__*/React.createElement("div", {
    className: "kpi__value",
    style: {
      fontSize: "1.02rem"
    }
  }, Math.round(top.trust.hype_risk * 100), "%"), /*#__PURE__*/React.createElement("div", {
    className: "kpi__note"
  }, "durable focus")))), /*#__PURE__*/React.createElement("section", {
    className: "section"
  }, /*#__PURE__*/React.createElement("div", {
    className: "section-head"
  }, /*#__PURE__*/React.createElement("h3", null, "What to learn")), /*#__PURE__*/React.createElement("div", {
    className: "opgrid"
  }, (allLocal ? topics : topics.slice(0, 3)).map((t, i) => /*#__PURE__*/React.createElement(UI.OpportunityCard, {
    key: t.id,
    topic: t,
    rank: i + 1,
    onInspect: inspect,
    advanced: advanced
  }))), topics.length > 3 && /*#__PURE__*/React.createElement("div", {
    className: "showall"
  }, /*#__PURE__*/React.createElement("button", {
    className: "btn small",
    onClick: () => setAllLocal(v => !v)
  }, allLocal ? "Show less" : "Show all " + topics.length))), advanced && /*#__PURE__*/React.createElement("section", {
    className: "section"
  }, /*#__PURE__*/React.createElement("div", {
    className: "section-head"
  }, /*#__PURE__*/React.createElement("h3", null, "Trending globally")), /*#__PURE__*/React.createElement("div", {
    className: "opgrid"
  }, (allGlobal ? globalTopics : globalTopics.slice(0, 3)).map((t, i) => /*#__PURE__*/React.createElement(UI.OpportunityCard, {
    key: t.id,
    topic: t,
    rank: i + 1,
    onInspect: inspect,
    advanced: advanced
  }))), globalTopics.length > 3 && /*#__PURE__*/React.createElement("div", {
    className: "showall"
  }, /*#__PURE__*/React.createElement("button", {
    className: "btn small",
    onClick: () => setAllGlobal(v => !v)
  }, allGlobal ? "Show less" : "Show all " + globalTopics.length))), /*#__PURE__*/React.createElement("section", {
    className: "section",
    id: "visibility"
  }, /*#__PURE__*/React.createElement("div", {
    className: "section-head"
  }, /*#__PURE__*/React.createElement("h3", null, "Publish your project")), /*#__PURE__*/React.createElement("article", {
    className: "card vis reveal"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vis-list checklist"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "ck-n"
  }, "1"), /*#__PURE__*/React.createElement("div", {
    className: "ck-body"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vk"
  }, "Create this repo"), /*#__PURE__*/React.createElement("div", {
    className: "copyrow"
  }, /*#__PURE__*/React.createElement("code", null, repo), /*#__PURE__*/React.createElement(UI.CopyButton, {
    text: repo
  })))), /*#__PURE__*/React.createElement("div", {
    className: "vrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "ck-n"
  }, "2"), /*#__PURE__*/React.createElement("div", {
    className: "ck-body"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vk"
  }, "Build this demo"), /*#__PURE__*/React.createElement("div", {
    className: "copyrow"
  }, /*#__PURE__*/React.createElement("code", null, hfName), /*#__PURE__*/React.createElement(UI.CopyButton, {
    text: hfName
  })))), /*#__PURE__*/React.createElement("div", {
    className: "vrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "ck-n"
  }, "3"), /*#__PURE__*/React.createElement("div", {
    className: "ck-body"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vk"
  }, "Write this post"), /*#__PURE__*/React.createElement("div", {
    className: "copyrow"
  }, /*#__PURE__*/React.createElement("code", null, blogTitle), /*#__PURE__*/React.createElement(UI.CopyButton, {
    text: blogTitle
  })))))))), /*#__PURE__*/React.createElement("footer", {
    className: "foot"
  }, /*#__PURE__*/React.createElement("div", {
    className: "wrap row"
  }, /*#__PURE__*/React.createElement("div", {
    className: "brand"
  }, /*#__PURE__*/React.createElement(UI.Mark, {
    size: 24
  }), " Scout"), /*#__PURE__*/React.createElement("div", {
    className: "links"
  }, /*#__PURE__*/React.createElement("a", {
    href: "#"
  }, "API"), /*#__PURE__*/React.createElement("a", {
    href: "#"
  }, "Methodology"), /*#__PURE__*/React.createElement("a", {
    href: "#"
  }, "Trust"), /*#__PURE__*/React.createElement("a", {
    href: "https://www.matrixhub.io",
    target: "_blank",
    rel: "noreferrer"
  }, "Agent-Matrix")), /*#__PURE__*/React.createElement("div", {
    className: "copy"
  }, "Public developer layer of Matrix Scout \xB7 ruslanmv.com")))), phase === "report" && barOpen && /*#__PURE__*/React.createElement(UI.NextBar, {
    project: top.project_ideas[0],
    onView: () => scrollTo("visibility"),
    onClose: () => setBarOpen(false)
  }), /*#__PURE__*/React.createElement(Drawer, {
    topic: active,
    open: open,
    onClose: () => setOpen(false),
    location: location,
    onStart: () => scrollTo("visibility")
  }));
}
ReactDOM.createRoot(document.getElementById("root")).render(/*#__PURE__*/React.createElement(App, null));
})();
