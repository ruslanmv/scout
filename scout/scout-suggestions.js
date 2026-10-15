/* Profession autocomplete only from timestamped, source-backed weekly observations.
   No curated profession list, catalog padding, or fabricated popularity labels. */
(function () {
  "use strict";
  const WEEK_MS = 8 * 24 * 60 * 60 * 1000;
  const DENIED = new Set(["curated", "unknown", "demo", "sample", "synthetic"]);
  function recent(value, now) {
    const ts = Date.parse(value);
    return Number.isFinite(ts) && ts <= now + 60 * 60 * 1000 && now - ts <= WEEK_MS;
  }
  function validSource(source) {
    return typeof source === "string" && source.trim() &&
      !DENIED.has(source.trim().toLowerCase());
  }
  function professions(feed, city, country, now = Date.now()) {
    if (!feed || feed.schema_version !== 1 || !recent(feed.generated_at,now)) {
      return {items:[],observed:false,region:"",recommended:""};
    }
    const regions = [...new Set([city,country].filter(Boolean))];
    for (const region of regions) {
      const direct = feed.regions?.[region];
      const records = [
        ...(direct?.status === "measured" && Array.isArray(direct.items) ? direct.items : []),
        ...(Array.isArray(feed.role_observations) ?
          feed.role_observations.filter(row=>row.region===region) : [])
      ];
      const byName = new Map();
      for (const row of records) {
        if (!row || typeof row.name !== "string" || !row.name.trim() ||
            !validSource(row.source) || !recent(row.collected_at,now)) continue;
        const count = Number(row.sample_size);
        if (!Number.isFinite(count) || count <= 0) continue;
        const name = row.name.trim(), key = name.toLocaleLowerCase();
        const previous = byName.get(key);
        if (!previous || previous.sample_size < count) {
          byName.set(key, {name, sample_size:count, source:row.source,
            collected_at:row.collected_at, observed:true, domain:"Observed job postings"});
        }
      }
      const items=[...byName.values()].sort((a,b)=>
        b.sample_size-a.sample_size || a.name.localeCompare(b.name));
      if (items.length) {
        return {items, observed:true, region, recommended:items[0].name};
      }
    }
    return {items:[],observed:false,region:"",recommended:""};
  }
  function skills(feed, city, country, now = Date.now()) {
    if (!feed || feed.schema_version !== 1 || !recent(feed.generated_at,now)) {
      return {items:[],source:"unavailable"};
    }
    const key=(country+":"+city).toLowerCase();
    const input=(feed.skills_by_region||{})[key] || feed.skills || [];
    return {items:Array.isArray(input)?
      input.filter(item=>item && typeof item.name==="string" &&
        item.source==="topic_proxy" && Number.isFinite(Number(item.score)))
        .sort((a,b)=>Number(b.score)-Number(a.score) || a.name.localeCompare(b.name)).slice(0,5):[],
      source:"topic_proxy"};
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
        meta.textContent=item.observed?"Observed job postings · last 7 days":(item.domain || "Profession");
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
