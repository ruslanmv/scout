/* Homepage profession and skill suggestions; source labels prevent false trend claims. */
(function () {
  "use strict";
  const R=window.React;
  function MiniSuggestions({city,country,profile,onProfession,data,status}) {
    const professions=window.ScoutSuggestions.professions(data,city,country);
    const skills=window.ScoutSuggestions.skills(data,city,country);
    const topRoles=professions.items.slice(0,5),topSkills=skills.items.slice(0,5);
    return R.createElement("div",{
      className:"l-quick-tags l-an d4", "aria-label":"Career and skill suggestions"
    },
      R.createElement("div",{className:"l-quick-group"},
        R.createElement("span",{className:"l-quick-title"},
          professions.observed?"Top 5 observed professions · "+professions.region:"Suggested professions · curated"),
        R.createElement("div",{className:"l-quick-row","aria-live":"polite"},
          topRoles.map(role=>R.createElement("button",{
            className:"l-quick-chip"+(profile===role.name?" selected":""),
            key:role.name,type:"button",
            title:role.observed?
              role.sample_size.toLocaleString()+" source-reported posting mentions · "+role.source:
              "Curated example · not a verified hiring trend",
            onClick:()=>onProfession(role.name)
          },role.name)))
      ),
      R.createElement("div",{className:"l-quick-group"},
        R.createElement("span",{className:"l-quick-title"},
          skills.source==="topic_proxy"?"Skills · Scout topic-association signals":
            "Skills to explore · curated"),
        R.createElement("div",{className:"l-quick-row"},
          topSkills.map(skill=>R.createElement("a",{
            className:"l-quick-chip",key:skill.name,
            title:skills.source==="topic_proxy"?"Topic-association score · not observed employer demand":
              "Curated skill · not verified hiring demand",
            href:"trends/?kind=skills&item="+encodeURIComponent(skill.name)+
              "&city="+encodeURIComponent(city)+"&country="+encodeURIComponent(country)
          },skill.name)))
      ),
      R.createElement("a",{className:"l-quick-link",
        href:"trends/?country="+encodeURIComponent(country)+"&city="+encodeURIComponent(city)
      },"Explore Scout Pulse →"),
      R.createElement("span",{className:"l-quick-method"},
        professions.observed?
          "Source-reported job posting mentions · "+professions.region+" · not total employment":
          "Curated professions are starter suggestions, not a regional popularity or demand ranking"+
          (status==="error"?" · live feed unavailable":""))
    );
  }
  window.ScoutPulse=MiniSuggestions;
})();
