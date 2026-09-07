/* Compiled from scout-app.jsx by @babel/preset-react. Do not edit directly; edit the .jsx and re-run scripts/build_scout_report.js. */
(function () {
/* global React, ReactDOM */
/* Scout landing entry — hero + scanning animation, then a real navigation to
   the dedicated report page (multi-page product; the report and its sections
   are separate routes under report/). */
const {
  useState: uS,
  useEffect: uE
} = React;
const SA = window.SCOUT;
const UI = window.ScoutUI;
const Landing = window.ScoutLanding;
const SCAN_LINES = ["Reading developer signals…", "GitHub · Hugging Face", "Jobs · news · community", "Matching to your goal", "Building your report"];
function ToolHeader() {
  return /*#__PURE__*/React.createElement("header", {
    className: "tool-header"
  }, /*#__PURE__*/React.createElement("div", {
    className: "tool-header__in"
  }, /*#__PURE__*/React.createElement("a", {
    className: "tool-header__back",
    href: "./"
  }, "← ", /*#__PURE__*/React.createElement("span", null, "Home")), /*#__PURE__*/React.createElement("div", {
    className: "tool-header__title"
  }, /*#__PURE__*/React.createElement("span", {
    className: "gl"
  }, "◇"), " Scout"), /*#__PURE__*/React.createElement("div", {
    className: "tool-header__user"
  }, /*#__PURE__*/React.createElement("span", {
    className: "live"
  }, /*#__PURE__*/React.createElement("span", {
    className: "dot"
  }), "LIVE"), /*#__PURE__*/React.createElement("span", {
    className: "avatar"
  }, "RM"))));
}
function reportUrl(profile, city, country, goal) {
  const q = new URLSearchParams({
    profile,
    city,
    country,
    goal
  });
  return "report/?" + q.toString();
}
function App() {
  const [phase, setPhase] = uS("hero");
  const [country, setCountry] = uS("Italy");
  const [city, setCity] = uS("Rome");
  const [goal, setGoal] = uS("build_portfolio");
  const [profile, setProfile] = uS("Developer");
  const [scanIdx, setScanIdx] = uS(0);
  const [animSafe, setAnimSafe] = uS(false);
  uE(() => {
    setAnimSafe(false);
    const t = setTimeout(() => setAnimSafe(true), 1700);
    return () => clearTimeout(t);
  }, [phase]);
  const goalObj = SA.GOALS.find(g => g.id === goal) || SA.GOALS[0];
  function generate() {
    setPhase("scanning");
    setScanIdx(0);
    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  }

  // Advance the scanning log, then navigate to the real report route.
  uE(() => {
    if (phase !== "scanning") return;
    if (scanIdx >= SCAN_LINES.length) {
      const t = setTimeout(() => {
        window.location.href = reportUrl(profile, city, country, goal);
      }, 420);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setScanIdx(i => i + 1), scanIdx === 0 ? 360 : 300);
    return () => clearTimeout(t);
  }, [phase, scanIdx, profile, city, country, goal]);
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
  }, "your plan"), "…"), /*#__PURE__*/React.createElement("div", {
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
  }, city, ", ", country, " · ", goalObj.label, " · ", profile)))))));
}
ReactDOM.createRoot(document.getElementById("root")).render(/*#__PURE__*/React.createElement(App, null));
})();
