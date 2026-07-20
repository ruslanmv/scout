/* Compiled from scout-drawer.jsx by @babel/preset-react. Do not edit directly; edit the .jsx and recompile. */
(function () {
/* global React */
const {
  useState: useStateD,
  useEffect: useEffectD
} = React;
const SD = window.SCOUT;
function DeepDiveDrawer({
  topic,
  open,
  onClose,
  location,
  onStart
}) {
  const [tab, setTab] = useStateD("why");
  useEffectD(() => {
    if (open) setTab("why");
  }, [open, topic && topic.id]);
  useEffectD(() => {
    const h = e => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  const TABS = [["why", "Why this?"], ["plan", "Your plan"], ["advanced", "Advanced"]];
  const {
    RadarBars
  } = window.ScoutUI;
  function body() {
    if (!topic) return null;
    const s = topic.signals;
    const dims = SD.radar(topic);
    const high = topic.trust.score >= 0.87;
    const reasons = SD.whyReasons(topic, location.city);
    const steps = SD.planSteps(topic);
    const evRows = [["GitHub activity", s.github_activity], ["GitHub growth", s.github_growth], ["Hugging Face", s.huggingface_activity], ["News / RSS", s.news_mentions], ["Job demand", s.job_demand], ["Community", s.community_activity]];
    switch (tab) {
      case "why":
        return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("ol", {
          className: "reasons"
        }, reasons.map((r, i) => /*#__PURE__*/React.createElement("li", {
          key: i
        }, /*#__PURE__*/React.createElement("span", {
          className: "rn"
        }, i + 1), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
          className: "rt"
        }, r.t), /*#__PURE__*/React.createElement("div", {
          className: "rd"
        }, r.d))))), /*#__PURE__*/React.createElement("div", {
          className: "next-cta"
        }, /*#__PURE__*/React.createElement("div", {
          className: "nc-l"
        }, "Next"), /*#__PURE__*/React.createElement("p", null, "Start small: build ", /*#__PURE__*/React.createElement("b", null, topic.project_ideas[0]), ", then publish it."), /*#__PURE__*/React.createElement("button", {
          className: "btn primary",
          onClick: () => {
            onClose();
            if (onStart) onStart();
          }
        }, "Start step 1 \u2192")));
      case "plan":
        return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
          className: "planlist"
        }, steps.map(st => /*#__PURE__*/React.createElement("div", {
          className: "planstep",
          key: st.n
        }, /*#__PURE__*/React.createElement("span", {
          className: "ps-n"
        }, st.n), /*#__PURE__*/React.createElement("div", {
          className: "ps-body"
        }, /*#__PURE__*/React.createElement("div", {
          className: "ps-t"
        }, st.t), /*#__PURE__*/React.createElement("div", {
          className: "ps-d"
        }, st.d)), /*#__PURE__*/React.createElement("span", {
          className: "ps-time"
        }, st.time)))), /*#__PURE__*/React.createElement("h4", null, "Skills you'll show"), /*#__PURE__*/React.createElement("div", {
          className: "chip-list"
        }, topic.skills.map(s2 => /*#__PURE__*/React.createElement("span", {
          className: "tag",
          key: s2
        }, s2))));
      case "advanced":
        return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h4", null, "Why we recommend this"), evRows.map(([n, v]) => /*#__PURE__*/React.createElement("div", {
          className: "evline",
          key: n
        }, /*#__PURE__*/React.createElement("span", {
          className: "en"
        }, n), /*#__PURE__*/React.createElement("span", {
          className: "et"
        }, /*#__PURE__*/React.createElement("i", {
          style: {
            width: v + "%"
          }
        })), /*#__PURE__*/React.createElement("span", {
          className: "ev"
        }, SD.evidence(v)))), /*#__PURE__*/React.createElement("h4", null, "Signal radar"), /*#__PURE__*/React.createElement(RadarBars, {
          dims: dims
        }), /*#__PURE__*/React.createElement("h4", null, "Trust"), /*#__PURE__*/React.createElement("p", null, /*#__PURE__*/React.createElement("b", {
          style: {
            color: high ? "var(--green-700)" : "var(--amber)"
          }
        }, high ? "High confidence" : "Medium confidence", " \xB7 ", Math.round(topic.trust.score * 100), "%"), /*#__PURE__*/React.createElement("br", null), "Cross-checked across ", topic.sources.length, " independent sources. Hype-risk index ", Math.round(topic.trust.hype_risk * 100), "%."), /*#__PURE__*/React.createElement("h4", null, "Watch out for"), topic.risks.map((r, i) => /*#__PURE__*/React.createElement("div", {
          className: "risk",
          key: i
        }, /*#__PURE__*/React.createElement("span", {
          className: "ri"
        }, "\u26A0"), /*#__PURE__*/React.createElement("p", null, r))), /*#__PURE__*/React.createElement("details", {
          className: "adv"
        }, /*#__PURE__*/React.createElement("summary", null, "Agent opportunities"), /*#__PURE__*/React.createElement("div", {
          className: "advbody amx"
        }, /*#__PURE__*/React.createElement("div", {
          className: "ax"
        }, /*#__PURE__*/React.createElement("div", {
          className: "axk"
        }, "Agent category"), /*#__PURE__*/React.createElement("div", {
          className: "axv"
        }, "Developer intelligence \xB7 ", topic.short)), /*#__PURE__*/React.createElement("div", {
          className: "ax"
        }, /*#__PURE__*/React.createElement("div", {
          className: "axk"
        }, "MCP surface"), /*#__PURE__*/React.createElement("div", {
          className: "axv"
        }, "Expose ", topic.short, " signals as an MCP tool for agents to query.")), /*#__PURE__*/React.createElement("div", {
          className: "ax"
        }, /*#__PURE__*/React.createElement("div", {
          className: "axk"
        }, "Register in MatrixHub"), /*#__PURE__*/React.createElement("div", {
          className: "axv"
        }, "Publish ", /*#__PURE__*/React.createElement("span", {
          style: {
            fontFamily: "var(--mono)",
            color: "var(--green-700)"
          }
        }, SD.repoName(topic)), " as a discoverable agent.")))), /*#__PURE__*/React.createElement("details", {
          className: "adv"
        }, /*#__PURE__*/React.createElement("summary", null, "Raw data (JSON)"), /*#__PURE__*/React.createElement("div", {
          className: "advbody"
        }, /*#__PURE__*/React.createElement("pre", {
          className: "json"
        }, JSON.stringify({
          id: topic.id,
          composite_score: SD.composite(topic),
          radar: dims,
          signals: topic.signals,
          trust: topic.trust
        }, null, 2)))));
      default:
        return null;
    }
  }
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    className: "scrim" + (open ? " open" : ""),
    onClick: onClose
  }), /*#__PURE__*/React.createElement("aside", {
    className: "drawer" + (open ? " open" : ""),
    "aria-hidden": !open
  }, topic && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    className: "dh"
  }, /*#__PURE__*/React.createElement("button", {
    className: "x",
    onClick: onClose,
    "aria-label": "Close"
  }, "\u2715"), /*#__PURE__*/React.createElement("div", {
    className: "ek"
  }, "Why this topic"), /*#__PURE__*/React.createElement("h3", null, "Why ", topic.short, "?")), /*#__PURE__*/React.createElement("div", {
    className: "tabs"
  }, TABS.map(([id, lab]) => /*#__PURE__*/React.createElement("button", {
    key: id,
    className: "tab" + (tab === id ? " active" : ""),
    onClick: () => setTab(id)
  }, lab))), /*#__PURE__*/React.createElement("div", {
    className: "dbody"
  }, /*#__PURE__*/React.createElement("div", {
    key: tab,
    className: "tabpane"
  }, body())))));
}
window.DeepDiveDrawer = DeepDiveDrawer;
})();
