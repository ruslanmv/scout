/* Source-ranked profession search with a clearly labeled occupation-catalog fallback.
   Taxonomy suggestions are not hiring-demand rankings. */
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
  // Browse the maintained occupation taxonomy even when the job collector is offline.
  // Catalog entries are suggestions, never evidence of hiring popularity.
  function catalogProfessions() {
    const catalog = window.SCOUT && Array.isArray(window.SCOUT.OCCUPATIONS) ?
      window.SCOUT.OCCUPATIONS : [];
    const seen = new Set();
    return catalog.filter(item => {
      if (!item || typeof item.name !== "string" || !item.name.trim()) return false;
      const key=item.name.trim().toLocaleLowerCase();
      if(seen.has(key))return false;
      seen.add(key);return true;
    }).map(item => ({name:item.name.trim(),domain:item.domain || "Profession",
      observed:false, catalog:true}));
  }
  function professions(feed, city, country, now = Date.now()) {
    const catalog=catalogProfessions();
    const observed=[];
    let region="";
    if(feed && feed.schema_version===1 && recent(feed.generated_at,now)){
      for(const candidate of [...new Set([city,country].filter(Boolean))]){
        const direct=feed.regions?.[candidate];
        const records=[
          ...(direct?.status==="measured" && Array.isArray(direct.items)?direct.items:[]),
          ...(Array.isArray(feed.role_observations)?
            feed.role_observations.filter(row=>row.region===candidate):[])
        ];
        const byName=new Map();
        for(const row of records){
          if(!row || typeof row.name!=="string" || !row.name.trim() ||
            !validSource(row.source) || !recent(row.collected_at,now))continue;
          const count=Number(row.sample_size);
          if(!Number.isFinite(count)||count<=0)continue;
          const name=row.name.trim(),key=name.toLocaleLowerCase();
          const old=byName.get(key);
          if(!old || old.sample_size<count){
            byName.set(key,{name,sample_size:count,source:row.source,
              collected_at:row.collected_at,observed:true,domain:"Observed job postings"});
          }
        }
        const ranked=[...byName.values()].sort((x,y)=>
          y.sample_size-x.sample_size || x.name.localeCompare(y.name));
        if(ranked.length){observed.push(...ranked);region=candidate;break;}
      }
    }
    const seen=new Set(observed.map(item=>item.name.toLocaleLowerCase()));
    const items=[...observed,...catalog.filter(item=>!seen.has(item.name.toLocaleLowerCase()))];
    return {items,observed:observed.length>0,region,
      recommended:observed.length?observed[0].name:""};
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
  // Google-style relevance: starts-with, word-prefix, then substring.
  // Within the same match tier, measured results precede catalog suggestions.
  function matches(items, input, max=5) {
    const query=String(input||"").trim().toLocaleLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g,"");
    if(!query)return items.slice(0,max);
    const scored=[];
    for(let index=0;index<items.length;index++){
      const item=items[index];
      const name=item.name.toLocaleLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g,"");
      let score=3;
      if(name===query)score=0;
      else if(name.startsWith(query))score=1;
      else if(name.split(/[^a-z0-9]+/).some(word=>word.startsWith(query)))score=2;
      else if(!name.includes(query))continue;
      scored.push({item,score,index});
    }
    scored.sort((a,b)=>a.score-b.score ||
      Number(Boolean(b.item.observed))-Number(Boolean(a.item.observed)) ||
      (a.item.observed&&b.item.observed?
        Number(b.item.sample_size||0)-Number(a.item.sample_size||0):0) ||
      a.index-b.index);
    return scored.slice(0,max).map(x=>x.item);
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
        meta.textContent=item.observed?"Observed job-posting mentions · "+item.source:"Occupation catalog · "+(item.domain || "Profession");
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
