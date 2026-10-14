/* Scout landing: compact suggestions below the primary conversion CTA. */
(function () {
  "use strict";
  const R = window.React;
  const defaults = ["Developer", "Data Analyst", "Marketing Specialist", "Nurse", "UX/Product Designer", "Electrician", "Teacher", "Accountant"];
  const fallbackSkills = ["Python", "SQL", "User research"];

  // These are clearly curated starting ideas, NOT measured market leaders.
  // Store only the last suggested defaults (never the visitor's own edits).
  function nextSuggestion(items, key) {
    if (!items.length) return "";
    let previous = "";
    try { previous = window.localStorage.getItem(key) || ""; } catch (_) {}
    const candidates = items.filter(item => item !== previous);
    const choices = candidates.length ? candidates : items;
    const chosen = choices[Math.floor(Math.random() * choices.length)];
    try { window.localStorage.setItem(key, chosen); } catch (_) {}
    return chosen;
  }

  function initialSelection(query, goals, locations) {
    const requestedRole = (query.get("profile") || "").trim();
    const requestedGoal = (query.get("goal") || "").trim();
    const goalsAvailable = (goals || []).map(g => g.id);
    const requestedCity = (query.get("city") || "").trim();
    const requestedCountry = (query.get("country") || "").trim();
    const detectedCountry = (locations || []).find(l => l.cities.includes(requestedCity));
    const country = requestedCountry || (detectedCountry && detectedCountry.country) || "Italy";
    const countryCities = (locations || []).find(l => l.country === country);
    return {
      profile: requestedRole || nextSuggestion(defaults, "scout:last-suggested-role"),
      goal: goalsAvailable.includes(requestedGoal)
        ? requestedGoal : nextSuggestion(goalsAvailable, "scout:last-suggested-goal"),
      city: requestedCity || (countryCities && countryCities.cities[0]) || "Rome",
      country: country
    };
  }
  window.ScoutLandingPresets = { initialSelection: initialSelection, professions: defaults.slice() };
  function pick(items, count) {
    const out = items.slice();
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out.slice(0, count);
  }
  function MiniSuggestions({ city, country, profile, onProfession }) {
    const [data, setData] = R.useState(null);
    const [sample, setSample] = R.useState(() => pick(defaults, 3));
    R.useEffect(() => {
      const controller = new AbortController();
      fetch("data/pulse/latest.json", { cache: "no-store", signal: controller.signal })
        .then(r => { if (!r.ok) throw new Error("Pulse unavailable"); return r.json(); })
        .then(d => { if (d && d.schema_version === 1) setData(d); })
        .catch(() => {});
      return () => controller.abort();
    }, []);
    R.useEffect(() => { setSample(pick(defaults, 3)); }, [country, city]);
    const regions = data && data.regions || {};
    const ranked = [regions[city], regions[country]].find(x => x && x.status === "measured");
    const roles = ranked ? ranked.items.slice(0, 3).map(r => r.name)
      : defaults.includes(profile) ? [profile, ...sample.filter(name => name !== profile)].slice(0, 3) : sample;
    const key = (country + ":" + city).toLowerCase();
    const skills = (data && ((data.skills_by_region || {})[key] || (data.skills_by_region || {})[country.toLowerCase()] || data.skills)) || [];
    const skillNames = skills.length ? skills.slice(0, 3).map(s => s.name) : fallbackSkills;
    return R.createElement("div", { className: "l-quick-tags l-an d4", "aria-label": "Explore careers and skills" },
      R.createElement("div", { className: "l-quick-group" },
        R.createElement("span", { className: "l-quick-title" }, ranked ? "In-demand roles · " + country : "Explore roles"),
        R.createElement("div", { className: "l-quick-row" }, roles.map(name =>
          R.createElement("button", { className: "l-quick-chip" + (profile === name ? " selected" : ""), type: "button", key: name, onClick: () => onProfession(name) }, name)
        ))
      ),
      R.createElement("div", { className: "l-quick-group" },
        R.createElement("span", { className: "l-quick-title" }, "Explore skills"),
        R.createElement("div", { className: "l-quick-row" }, skillNames.map(name =>
          R.createElement("a", { className: "l-quick-chip", key: name, href: "trends/?kind=skills&item=" + encodeURIComponent(name) }, name)
        ))
      ),
      R.createElement("a", { className: "l-quick-link", href: "trends/?country=" + encodeURIComponent(country) + "&city=" + encodeURIComponent(city) }, "Explore market pulse →")
    );
  }
  window.ScoutPulse = MiniSuggestions;
})();
