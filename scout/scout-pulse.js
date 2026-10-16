/* Landing hero: link to Scout Pulse; no redundant static career chips. */
(function () {
  "use strict";
  function MiniSuggestions({city,country}) {
    return window.React.createElement("div",{className:"l-quick-tags l-an d4"},
      window.React.createElement("a",{
        className:"l-quick-link",
        href:"trends/?country="+encodeURIComponent(country)+"&city="+encodeURIComponent(city)
      },"Explore Scout Pulse →"));
  }
  window.ScoutPulse=MiniSuggestions;
})();
