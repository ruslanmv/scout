/* Scout Pulse landing chips: reads the daily published dataset, never fabricates hiring rankings. */
(function () {
  "use strict";
  const R = window.React;
  const FALLBACK_ROLES = [
    "Developer", "Data Analyst", "Nurse", "Teacher", "Accountant",
    "Marketing Specialist", "UX/Product Designer", "Electrician"
  ];
  const FALLBACK_SKILLS = ["Python", "SQL", "Communication", "User research", "Safety practices"];
  const FALLBACK_TOOLS = ["Excel", "Figma", "Power BI", "Docker", "Git"];

  function shuffle(items) {
    const out = items.slice();
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  }

  function PulseTags({ city, country, profile, onProfession }) {
    const [pulse, setPulse] = R.useState(null);
    const [rotation, setRotation] = R.useState(0);
    R.useEffect(() => {
      let mounted = true;
      fetch("data/pulse/latest.json", { cache: "no-store" })
        .then(response => {
          if (!response.ok) throw new Error("Pulse data unavailable");
          return response.json();
        })
        .then(data => { if (mounted && data && data.schema_version === 1) setPulse(data); })
        .catch(() => { /* A missing feed retains the honest curated fallback. */ });
      return () => { mounted = false; };
    }, []);

    const regionKey = (country + ":" + city).toLowerCase();
    const cityFeed = pulse && pulse.regions && pulse.regions[city];
    const countryFeed = pulse && pulse.regions && pulse.regions[country];
    const feed = (cityFeed && cityFeed.status === "measured" && cityFeed)
      || (countryFeed && countryFeed.status === "measured" && countryFeed)
      || (pulse && pulse.regions && pulse.regions.Worldwide);
    const measured = !!(feed && feed.status === "measured");
    const measuredPlace = cityFeed && cityFeed.status === "measured" ? city : country;
    const localSkills = pulse && pulse.skills_by_region && (pulse.skills_by_region[regionKey] || pulse.skills_by_region[country.toLowerCase()]);
    const localTools = pulse && pulse.tools_by_region && (pulse.tools_by_region[regionKey] || pulse.tools_by_region[country.toLowerCase()]);
    const names = measured
      ? feed.items.slice(0, 5).map(item => item.name)
      : FALLBACK_ROLES;
    const professions = R.useMemo(
      () => shuffle(names).slice(0, 5),
      [city, country, pulse, rotation]
    );
    const rankedSkills = localSkills && localSkills.length ? localSkills : (pulse && pulse.skills);
    const rankedTools = localTools && localTools.length ? localTools : (pulse && pulse.tools);
    const skills = rankedSkills && rankedSkills.length
      ? rankedSkills.slice(0, 5).map(item => item.name) : FALLBACK_SKILLS;
    const tools = rankedTools && rankedTools.length
      ? rankedTools.slice(0, 5).map(item => item.name) : FALLBACK_TOOLS;
    const dataDate = pulse && /^\d{4}-\d{2}-\d{2}$/.test(pulse.date || "")
      ? pulse.date : null;

    return R.createElement("section", { className: "l-pulse l-an d2", "aria-label": "Scout daily career discovery" },
      R.createElement("div", { className: "l-pulse-top" },
        R.createElement("span", { className: "l-pulse-caption" }, measured ? "Job-posting signals" : "Curated career ideas"),
        R.createElement("button", { type: "button", className: "l-pulse-shuffle",
          onClick: () => setRotation(n => n + 1), "aria-label": "Shuffle featured professions" }, "↻ Shuffle")
      ),
      R.createElement("div", { className: "l-pulse-label" }, measured ? "Top 5 professions in " + measuredPlace : "5 professions to explore"),
      R.createElement("div", { className: "l-chips", "aria-live": "polite" },
        professions.map((name, index) => R.createElement("button", {
          key: name, type: "button",
          className: "l-chip" + (name === profile ? " on" : ""),
          onClick: () => onProfession(name),
          title: index === 0 ? "Featured profession for this visit" : "Choose " + name
        }, index === 0 ? "✦ " + name : name))
      ),
      R.createElement("div", { className: "l-pulse-label" }, "5 skills to explore · Scout topic signals"),
      R.createElement("div", { className: "l-chips l-pulse-secondary" },
        skills.map(name => R.createElement("span", { key: name, className: "l-chip l-pulse-static" }, name))
      ),
      R.createElement("div", { className: "l-pulse-label" }, "5 tools to explore · Topic associations"),
      R.createElement("div", { className: "l-chips l-pulse-secondary" },
        tools.map(name => R.createElement("span", { key: name, className: "l-chip l-pulse-static" }, name))
      ),
      R.createElement("p", { className: "l-pulse-note" },
        measured ? "Observed regional job advertisements; not total employment." :
          "Professions are suggestions, not a measured local top-five ranking.",
        dataDate ? " · Dataset " + dataDate : " · Offline fallback",
        " · ", R.createElement("a", { href: "dataset/" }, "Methodology")
      )
    );
  }

  window.ScoutPulse = PulseTags;
})();
