/* Shared profession and skill suggestions. Curated choices are not hiring rankings. */
(function () {
  "use strict";
  const FALLBACK_ROLES = [
    "Developer", "Data Analyst", "Nurse", "Teacher", "Accountant",
    "Marketing Specialist", "UX/Product Designer", "AI Engineer"
  ];
  const FALLBACK_SKILLS = ["Python", "SQL", "Communication", "Data analysis", "Project management"];
  function unique(items) {
    const seen = new Set();
    return items.filter(item => {
      if (!item || typeof item.name !== "string" || !item.name.trim()) return false;
      const key = item.name.trim().toLocaleLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
  function professions(feed, city, country) {
    const observed = window.ScoutRanking && window.ScoutRanking.roles(feed, city, country);
    const catalog = (window.SCOUT && window.SCOUT.OCCUPATIONS) || [];
    const curated = (feed && feed.regions && feed.regions.Worldwide &&
      Array.isArray(feed.regions.Worldwide.items) ?
      feed.regions.Worldwide.items.filter(item => item.source === "curated") : []);
    const items = unique([
      ...(observed ? observed.items.map(item => ({...item, observed:true})) : []),
      ...curated.map(item => ({name:item.name, domain:"Curated profession"})),
      ...FALLBACK_ROLES.map(name => ({name, domain:"Curated profession"})),
      ...catalog.map(item => ({name:item.name, domain:item.domain || "Profession"}))
    ]);
    return {
      items,
      observed: Boolean(observed),
      region: observed ? observed.region : "",
      recommended: items.length ? items[0].name : "Developer"
    };
  }
  function skills(feed, city, country) {
    const ranked = window.ScoutRanking ? window.ScoutRanking.skills(feed, city, country) : [];
    if (ranked.length) return {items: ranked, source: "topic_proxy"};
    // These are merely labels from the Scout taxonomy, not measured skill demand.
    const catalog = (window.SCOUT && window.SCOUT.TOPICS) || [];
    const counts = new Map();
    for (const topic of catalog) for (const name of (topic.skills || [])) {
      counts.set(name, (counts.get(name) || 0) + 1);
    }
    const suggested = [...counts].sort((a,b) => b[1]-a[1] || a[0].localeCompare(b[0]))
      .map(([name])=>({name,source:"curated"}));
    return {items: unique([...suggested,...FALLBACK_SKILLS.map(name=>({name,source:"curated"}))]).slice(0,5),
      source: "curated"};
  }
  function matches(items, input, max=5) {
    const query = String(input || "").trim().toLocaleLowerCase();
    if (!query) return items.slice(0,max);
    // A focused field containing an exact selected profession still shows alternatives.
    const selected = items.some(item => item.name.toLocaleLowerCase() === query);
    if (selected) return items.slice(0,max);
    function weight(name) {
      const value = name.toLocaleLowerCase();
      if (value.startsWith(query)) return 0;
      if (value.split(/[^a-z0-9]+/).some(part => part.startsWith(query))) return 1;
      return 2;
    }
    return items.filter(item=>item.name.toLocaleLowerCase().includes(query))
      .sort((a,b)=>weight(a.name)-weight(b.name) ||
        Number(Boolean(b.observed))-Number(Boolean(a.observed)) ||
        a.name.localeCompare(b.name)).slice(0,max);
  }
  // DOM-based combobox for non-React report pages; landing uses the same match logic.
  function mountAutocomplete(input, list, getOptions, onChoose) {
    if (!input || !list) return null;
    let expanded=false, active=0, current=[];
    function close() {
      expanded=false;list.hidden=true;list.replaceChildren();
      input.setAttribute("aria-expanded","false");
      input.removeAttribute("aria-activedescendant");
    }
    function choose(item) {
      input.value=item.name;
      if (onChoose) onChoose(item);
      close();
      input.focus();
    }
    function draw() {
      current=matches(getOptions(),input.value);
      list.replaceChildren();
      if (!expanded || !current.length) {close();return;}
      current.forEach((item,i)=>{
        const button=document.createElement("button");button.type="button";
        button.id=list.id+"-option-"+i;button.className="become-option";
        button.setAttribute("role","option");button.setAttribute("aria-selected",String(i===active));
        const name=document.createElement("strong");name.textContent=item.name;
        const meta=document.createElement("small");
        meta.textContent=item.observed?"Observed regional signal":(item.domain || "Curated profession");
        button.append(name,meta);
        button.addEventListener("pointerdown",event=>event.preventDefault());
        button.addEventListener("click",()=>choose(item));
        list.append(button);
      });
      active=Math.min(active,current.length-1);
      list.hidden=false;
      input.setAttribute("aria-expanded","true");
      input.setAttribute("aria-activedescendant",list.id+"-option-"+active);
      [...list.children].forEach((el,i)=>el.setAttribute("aria-selected",String(i===active)));
    }
    input.setAttribute("role","combobox");input.setAttribute("aria-autocomplete","list");
    input.setAttribute("aria-controls",list.id);input.setAttribute("aria-expanded","false");
    input.addEventListener("focus",()=>{expanded=true;active=0;draw();});
    input.addEventListener("input",()=>{expanded=true;active=0;draw();});
    input.addEventListener("keydown",event=>{
      if(event.key==="Escape"){close();return;}
      if(!current.length)return;
      if(event.key==="ArrowDown"||event.key==="ArrowUp"){
        event.preventDefault();expanded=true;
        active=(active+(event.key==="ArrowDown"?1:-1)+current.length)%current.length;
        draw();
      }else if(event.key==="Enter"&&expanded){
        event.preventDefault();choose(current[active]);
      }
    });
    document.addEventListener("pointerdown",event=>{
      if(event.target!==input && !list.contains(event.target))close();
    });
    return {refresh:()=>{if(expanded)draw();},close};
  }
  window.ScoutSuggestions = {professions,skills,matches,mountAutocomplete};
})();
