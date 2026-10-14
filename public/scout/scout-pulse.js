/* Home: show only the five verified professions in the latest regional feed. */
(function () {
  "use strict";
  const R = window.React;
  const Rank = window.ScoutRanking;

  function MiniSuggestions({ city, country, profile, onProfession, data, status }) {
    const current = Rank.roles(data, city, country);
    const skills = Rank.skills(data, city, country).slice(0, 3);
    const roles = current ? current.items : [];
    const location = city + ", " + country;
    let statusText;
    if (status === "loading") statusText = "Checking the latest observed job-posting rankings…";
    else if (status === "error") statusText = "Market data could not be loaded. Type a profession above to continue.";
    else statusText = "No current verified top-five ranking for " + location + ". Type your profession above to continue.";

    return R.createElement("div", {
      className: "l-quick-tags l-an d4", "aria-label": "Current career and skill signals"
    },
      R.createElement("div", {className: "l-quick-group"},
        R.createElement("span", {className: "l-quick-title"},
          current ? "Top 5 observed professions · " + current.region : "Current top professions"),
        roles.length
          ? R.createElement("div", {className: "l-quick-row", "aria-live": "polite"},
              roles.map(role => R.createElement("button", {
                className: "l-quick-chip" + (profile === role.name ? " selected" : ""),
                key: role.name, type: "button",
                title: role.sample_size.toLocaleString() + " source-reported posting mentions · " + role.source,
                onClick: () => onProfession(role.name)
              }, role.name)))
          : R.createElement("p", {className: "l-quick-empty", role: "status"}, statusText)
      ),
      R.createElement("div", {className: "l-quick-group"},
        R.createElement("span", {className: "l-quick-title"}, "Skills · Scout topic signals"),
        skills.length
          ? R.createElement("div", {className: "l-quick-row"},
              skills.map(skill => R.createElement("a", {
                className: "l-quick-chip", key: skill.name,
                href: "trends/?kind=skills&item=" + encodeURIComponent(skill.name) +
                  "&city=" + encodeURIComponent(city) + "&country=" + encodeURIComponent(country)
              }, skill.name)))
          : R.createElement("p", {className: "l-quick-empty"},
              status === "loading" ? "Checking skills…" : "No current skill scores available.")
      ),
      R.createElement("a", {className: "l-quick-link",
        href: "trends/?country=" + encodeURIComponent(country) + "&city=" + encodeURIComponent(city)
      }, "Explore Scout Pulse →"),
      current && R.createElement("span", {className: "l-quick-method"},
        "Measured job-posting mentions · fetched " +
        new Date(current.generated_at).toLocaleDateString(undefined,
          {year: "numeric", month: "short", day: "numeric"}) +
        " · not total employment")
    );
  }
  window.ScoutPulse = MiniSuggestions;
})();
