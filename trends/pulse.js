/* Scout Pulse: dependency-free, source-aware exploration. No simulated values are presented as real evidence. */
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const COLORS = ["#c3ff70", "#b7a2ff", "#66d6ee", "#f7bc74", "#ff9fc6"];
  const CITIES = [
    ["Rome", "Italy"], ["Milan", "Italy"], ["Turin", "Italy"],
    ["Berlin", "Germany"], ["Munich", "Germany"], ["Madrid", "Spain"],
    ["Barcelona", "Spain"], ["San Francisco", "United States"],
    ["New York", "United States"], ["Austin", "United States"],
    ["London", "United Kingdom"], ["Manchester", "United Kingdom"],
    ["Bengaluru", "India"], ["Mumbai", "India"]
  ];
  const DEFAULTS = {
    skill: ["SQL", "Financial analysis", "Python"],
    profession: ["Data Analyst", "Developer", "Nurse"],
    emerging: ["AI Agents", "Vector databases", "Data visualization", "Cloud architecture", "LLM evaluation"]
  };
  const params = new URLSearchParams(location.search);
  const state = {kind: params.get("kind") === "careers" ? "profession" : "skill", days: 90,
    city: params.get("city") || "Rome", country: params.get("country") || "Italy",
    item: params.get("item") || (params.get("kind") === "careers" ? params.get("profile") || "" : ""),
    focusRole: params.get("profile") || "Developer",
    selected: {skill:null,profession:null}, hidden: {skill:[],profession:[]},
    feed: null, series: null, mode: "demo"};
  const seriesURL = "../data/pulse/series.json";
  const latestURL = "../data/pulse/latest.json";
  function track(name, extra) {
    const event = {event:"scout_" + name, source:"pulse", ...extra};
    if (Array.isArray(window.dataLayer)) window.dataLayer.push(event);
    try { window.dispatchEvent(new CustomEvent("scout:analytics", { detail:event })); } catch (_) {}
  }
  function planLink() {
    const query = new URLSearchParams({profile:state.focusRole,city:state.city,country:state.country,goal:"build_portfolio"});
    return "../?" + query.toString();
  }
  function syncPlanLinks() { ["hero-plan","bottom-plan"].forEach(id => $(id).href = planLink()); }
  function safe(s) { const el=document.createElement("span");el.textContent=String(s);return el.innerHTML; }
  function dISO(d) { return new Date(d).toISOString().slice(0,10); }
  function dateAgo(n) { const d=new Date();d.setUTCHours(12,0,0,0);d.setUTCDate(d.getUTCDate()-n);return dISO(d); }
  function toMs(s) { const d=new Date(s+"T12:00:00Z");return Number.isFinite(d.getTime())?d.getTime():NaN; }
  function pct(n) { return (n >= 0 ? "+" : "") + n.toFixed(1) + "%"; }
  function money(n) { return Number(n).toLocaleString("en-US"); }
  function hash(s) { let h=2166136261;for(const c of s){h=Math.imul(h^c.charCodeAt(0),16777619)}return h>>>0; }
  function demoValues(name, days, city) {
    const seed=hash(city+"|"+name), slope=(name.toLowerCase().includes("sql")?.20:
      name.toLowerCase().includes("financial")?.10:name.toLowerCase().includes("data analyst")?.14:
      name.toLowerCase().includes("python")?-.04:.03);
    return Array.from({length:days},(_,i)=>{
      const n=(Math.sin((i+seed%23)*.31)+Math.sin((i+seed%11)*.72)*.4)*1.3;
      const curve=Math.sin(i/days*6.3+seed%7)*8.5 + (i/days)*30*slope;
      return {date:dateAgo(days-1-i),value:Math.max(48,100+curve+n+(i/days-0.5)*20*slope)};
    });
  }
  function demoNames() {
    const names=(state.kind === "skill" ? DEFAULTS.skill : DEFAULTS.profession).slice();
    if(state.item && state.kind===(params.get("kind")==="careers"?"profession":"skill")){
      const existing=names.findIndex(n=>n.toLowerCase()===state.item.toLowerCase());
      if(existing>=0) names.splice(existing,1);
      names.unshift(state.item);
      return names.slice(0,3);
    }
    return names;
  }
  function topicProxy(d) {
    return d && Array.isArray(d.observations) ? d.observations : [];
  }
  function available(region, kind) {
    const data=topicProxy(state.series), country=CITIES.find(x=>x[0]===region)?.[1]||state.country;
    const measurement=kind==="profession"?"job_postings":"topic_proxy";
    return data.filter(o=>o.kind===kind && o.measurement===measurement &&
      (kind==="skill" ? (o.region==="Worldwide" || o.region===region || o.region===country) :
        (o.region===region || o.region===country)));
  }
  function seriesNames(raw) {
    const grouped=new Map();
    for(const row of raw){
      if(!row.date || !Number.isFinite(Number(row.value))) continue;
      const k=row.name;
      const r=grouped.get(k)||new Map();
      const old=r.get(row.date);
      if(!old || (row.region===state.city && old.region!==state.city))r.set(row.date,row);
      grouped.set(k,r);
    }
    const candidates=[...grouped.entries()].map(([name,records])=>({name,records:[...records.values()].sort((a,b)=>a.date.localeCompare(b.date))}))
      .filter(x=>new Set(x.records.map(d=>d.date)).size>=14)
      .sort((a,b)=>b.records.length-a.records.length || a.name.localeCompare(b.name));
    if(state.item && state.kind===(params.get("kind")==="careers"?"profession":"skill")){const p=candidates.find(x=>x.name.toLowerCase()===state.item.toLowerCase());if(p){candidates.splice(candidates.indexOf(p),1);candidates.unshift(p);}}
    return candidates;
  }
  function rolling(data, window=7) {
    return data.map(o=>{
      const ts=toMs(o.date);
      const prev=data.filter(p=>toMs(p.date)<=ts&&toMs(p.date)>=ts-(window-1)*86400000);
      return {...o,avg:prev.reduce((sum,x)=>sum+x.value,0)/prev.length};
    });
  }
  // Only offer observed series with comparable coverage for the selected window.
  // When that coverage is absent, all additional choices remain clearly DEMO PREVIEW.
  function chartCatalog() {
    const since=toMs(dateAgo(state.days-1));
    const observed=seriesNames(available(state.city,state.kind))
      .filter(item=>item.records.filter(row=>toMs(row.date)>=since).length>=14);
    const real=observed.length>=2;
    const extra=state.kind==="profession"?
      (window.SCOUT?.OCCUPATIONS||[]).map(o=>o.name):
      ["SQL","Python","Financial analysis","Machine learning","Cloud architecture","Data visualization"];
    const names=real?observed.map(o=>o.name):[...new Set([...demoNames(),...extra])];
    if(state.selected[state.kind]===null){
      state.selected[state.kind]=names.slice(0,3);
    }else{
      state.selected[state.kind]=state.selected[state.kind].filter(name=>names.includes(name));
    }
    state.hidden[state.kind]=state.hidden[state.kind].filter(name=>state.selected[state.kind].includes(name));
    return {real,observed,names};
  }
  function pointsForPlot(catalog) {
    const selected=state.selected[state.kind];
    const visible=selected.filter(name=>!state.hidden[state.kind].includes(name));
    state.mode=catalog.real?"observed":"demo";
    return visible.map(name=>{
      const color=COLORS[selected.indexOf(name)%COLORS.length];
      if(!catalog.real){
        const points=rolling(demoValues(name,state.days,state.city));
        const baseline=Math.max(.01,points[0].avg);
        return {name,color,points:points.map(x=>({...x,index:x.avg/baseline*100})),measurement:"illustrative"};
      }
      const item=catalog.observed.find(x=>x.name===name);
      const items=item.records.filter(d=>toMs(d.date)>=toMs(dateAgo(state.days-1)));
      const pts=rolling(items.map(x=>({date:x.date,value:Number(x.value)})));
      const base=Math.max(.01,pts[0].avg);
      return {name,color,points:pts.map(x=>({...x,index:x.avg/base*100})),
        measurement:state.kind==="skill"?"topic_proxy":"job_postings",source:item.records[item.records.length-1].source};
    });
  }
  function scenario(points) {
    if(points.length<30) return [];
    // Experimental linear extrapolation of the recent 7-day rolling series.
    const last=points[points.length-1],start=points[Math.max(0,points.length-22)];
    const avg=(last.index-start.index)/(points.length-1-Math.max(0,points.length-22));
    const drift=Math.max(-.55,Math.min(.55,avg));
    const residual=Math.sqrt(points.slice(-21).reduce((a,p,i,arr)=>a+(p.index-(arr[0].index+drift*i))**2,0)/21);
    return Array.from({length:14},(_,i)=>{
      const h=i+1, v=last.index+drift*h;
      const spread=Math.max(3,residual*.8)*Math.sqrt(1+h/7);
      return {date:dISO(new Date(toMs(last.date)+h*86400000)),index:v,low:v-spread,high:v+spread};
    });
  }
  function svgEl(tag,attrs={},text) {
    const el=document.createElementNS("http://www.w3.org/2000/svg",tag);
    Object.entries(attrs).forEach(([key,value])=>el.setAttribute(key,String(value)));
    if(text!==undefined)el.textContent=text;
    return el;
  }
  function linePath(points,fx,fy,key="index") { return points.map((p,i)=>(i?"L":"M")+fx(p.date).toFixed(1)+","+fy(p[key]).toFixed(1)).join(" "); }
  function renderSeriesControls(catalog) {
    const list=$("chart-legend");
    list.replaceChildren();
    const selected=state.selected[state.kind];
    const hidden=state.hidden[state.kind];
    if(!selected.length){
      const empty=document.createElement("span");
      empty.textContent="No series selected. Search above to add one.";
      list.append(empty);
    }
    selected.forEach((name,i)=>{
      const row=document.createElement("div");row.className="legend-item"+(hidden.includes(name)?" is-hidden":"");
      const button=document.createElement("button");
      button.type="button";button.className="legend-toggle";
      button.setAttribute("aria-pressed",String(!hidden.includes(name)));
      button.setAttribute("aria-label",(hidden.includes(name)?"Show ":"Hide ")+name);
      const dot=document.createElement("i");dot.style.background=COLORS[i%COLORS.length];
      dot.setAttribute("aria-hidden","true");
      const label=document.createElement("span");label.textContent=name;
      const eye=document.createElement("span");eye.className="legend-eye";
      eye.setAttribute("aria-hidden","true");eye.textContent=hidden.includes(name)?"○":"◉";
      button.append(dot,label,eye);
      button.addEventListener("click",()=>{
        state.hidden[state.kind]=hidden.includes(name)?hidden.filter(n=>n!==name):[...hidden,name];
        track("series_visibility",{kind:state.kind,series:name,visible:hidden.includes(name)});
        drawChart();
      });
      const remove=document.createElement("button");remove.type="button";remove.className="legend-remove";
      remove.textContent="×";remove.setAttribute("aria-label","Remove "+name);
      remove.title="Remove "+name+" from comparison";
      remove.addEventListener("click",()=>{
        state.selected[state.kind]=selected.filter(n=>n!==name);
        state.hidden[state.kind]=hidden.filter(n=>n!==name);
        drawChart();
      });
      row.append(button,remove);list.append(row);
    });
    const options=$("compare-options");options.replaceChildren();
    catalog.names.filter(name=>!selected.includes(name)).forEach(name=>{
      const option=document.createElement("option");option.value=name;options.append(option);
    });
    const noun=state.kind==="profession"?"professions":"skills";
    $("compare-input").placeholder="Search "+noun+" to compare…";
    $("compare-help").textContent=catalog.real?
      "Observed "+noun+" with at least 14 dated observations in this time range.":
      "DEMO PREVIEW: additional "+noun+" are illustrative, not measured hiring trends.";
    $("compare-status").textContent="";
  }
  function drawChart() {
    const catalog=chartCatalog(),data=pointsForPlot(catalog),svg=$("momentum-plot");
    svg.replaceChildren();
    $("chart-tooltip").hidden=true;
    renderSeriesControls(catalog);
    const isDemo=state.mode==="demo";
    $("chart-mode").textContent=isDemo?"DEMO PREVIEW":"OBSERVED HISTORY";
    $("chart-description").textContent=isDemo?
      "Illustrative examples · indexed 7-day trailing mean · start = 100":
      (state.kind==="skill"?"Scout topic-association score index":"Observed job-posting count index")+" · 7-day trailing mean · start = 100";
    if(!data.length){
      svg.append(svgEl("text",{x:530,y:193,fill:"#bad8c5","font-size":19,"text-anchor":"middle"},
        "No visible series — add or show a profession or skill above"));
      $("coverage-note").textContent=isDemo?
        "DEMO PREVIEW: illustrative examples only; no measured trend is available.":
        "Observed source data is available, but all comparison lines are hidden or removed.";
      renderKPIs(isDemo,data);renderRanks();renderHeatmap(isDemo);renderEmerging(isDemo);
      return;
    }
    const oldest=data.flatMap(s=>s.points).map(x=>toMs(x.date));
    const minDate=Math.min(...oldest);
    const today=data.flatMap(s=>s.points).map(x=>toMs(x.date)).reduce((a,b)=>Math.max(a,b),0);
    const projections=data.map(s=>scenario(s.points));
    const complete=projections.every(p=>p.length>0);
    const sufficientRealHistory=s=>s.points.length>=56 &&
      toMs(s.points.at(-1).date)>=toMs(dateAgo(3)) &&
      s.points.every((p,i)=>!i || toMs(p.date)-toMs(s.points[i-1].date)<=2*86400000);
    const project=complete && (isDemo || data.every(sufficientRealHistory));
    const end=project?today+14*86400000:today;
    const allValues=data.flatMap(s=>s.points.map(p=>p.index)).concat(project?projections.flatMap(p=>p.flatMap(x=>[x.low,x.high])):[]);
    const low=Math.floor((Math.min(...allValues)-7)/10)*10, high=Math.ceil((Math.max(...allValues)+7)/10)*10;
    const fX=ms=>55+(ms-minDate)/(end-minDate||1)*965;
    const x=date=>fX(toMs(date));
    const y=n=>331-(n-low)/(high-low||1)*285;
    svg.append(svgEl("rect",{x:0,y:0,width:1060,height:385,fill:"transparent"}));
    if(project){
      const start=fX(today);
      svg.append(svgEl("rect",{x:start,y:25,width:1020-start,height:310,fill:"#53f39d",opacity:".055"}));
      svg.append(svgEl("line",{x1:start,y1:22,x2:start,y2:332,stroke:"#9fcdb5","stroke-width":1.2,"stroke-dasharray":"5 6"}));
      svg.append(svgEl("text",{x:start+8,y:17,fill:"#c2d5c9","font-size":12},"14-day exploratory scenario →"));
    }
    for(let i=0;i<=4;i++){
      const v=low+(high-low)*i/4, py=y(v);
      svg.append(svgEl("line",{x1:55,x2:1020,y1:py,y2:py,stroke:"#6f9c82","stroke-opacity":".25","stroke-dasharray":"4 7"}));
      svg.append(svgEl("text",{x:43,y:py+4,fill:"#95b0a1","font-size":13,"text-anchor":"end"},String(Math.round(v))));
    }
    for(let i=0;i<6;i++){
      const ms=minDate+(today-minDate)*i/5,px=fX(ms),dt=new Date(ms);
      svg.append(svgEl("text",{x:px,y:362,fill:"#99b3a5","font-size":12,"text-anchor":"middle"},
        dt.toLocaleDateString("en-US",{month:"short",day:"numeric",timeZone:"UTC"})));
    }
    data.forEach((s,j)=>{
      if(!s.points.length)return;
      const path=linePath(s.points,x,y),last=s.points[s.points.length-1];
      if(project){
        const forecast=projections[j],coords=[last,...forecast];
        const upper=coords.map((p,i)=>(i?"L":"M")+x(p.date)+","+y(p.high??p.index)).join(" ");
        const lower=coords.slice().reverse().map(p=>"L"+x(p.date)+","+y(p.low??p.index)).join(" ");
        svg.append(svgEl("path",{d:upper+" "+lower+" Z",fill:s.color,opacity:".075"}));
        svg.append(svgEl("path",{d:linePath(coords,x,y),fill:"none",stroke:s.color,"stroke-width":2.6,"stroke-dasharray":"5 6","stroke-linecap":"round"}));
      }
      svg.append(svgEl("path",{d:path,fill:"none",stroke:s.color,"stroke-width":3.3,"stroke-linecap":"round","stroke-linejoin":"round"}));
      svg.append(svgEl("circle",{cx:x(last.date),cy:y(last.index),r:3.2,fill:s.color}));
    });
    $("coverage-note").textContent=isDemo?
      "Preview only: all plotted values and projections are generated examples, not observed market activity or validated forecasts. Connect daily observations to display measured history.":
      ("Observed data through "+(state.feed?.date||"latest")+". "+(state.kind==="skill"?"Skills measure Scout topic associations, not job postings.":"Careers measure source-reported job posting counts, not vacancies filled.")+
      (project?" Dotted paths show exploratory extrapolation with unvalidated ranges, not prediction confidence.":" Forecast hidden until at least 56 near-daily observations per series are available."));
    svg.onpointermove=event=>{
      const rect=svg.getBoundingClientRect(),svgX=(event.clientX-rect.left)*1060/rect.width;
      const ms=minDate+(svgX-55)/965*(end-minDate);
      const s=data[0];if(!s||svgX<55||svgX>1020){$("chart-tooltip").hidden=true;return;}
      const point=s.points.reduce((a,b)=>Math.abs(toMs(a.date)-ms)<Math.abs(toMs(b.date)-ms)?a:b);
      $("chart-tooltip").hidden=false;
      $("chart-tooltip").textContent=point.date+" · "+s.name+": "+point.index.toFixed(1)+(isDemo?" (demo)":" (indexed)");
      $("chart-tooltip").style.left=Math.min(Math.max(0,(event.clientX-rect.left)),rect.width-180)+"px";
      $("chart-tooltip").style.top="32px";
    };
    svg.onpointerleave=()=>{$("chart-tooltip").hidden=true;};
    renderKPIs(isDemo,data);
    renderRanks(isDemo,data);
    renderHeatmap(isDemo);
    renderEmerging(isDemo,data);
    track("chart_view",{kind:state.kind,range:state.days,mode:state.mode});
  }
  function makeRankList(id,names,values,measured,kind) {
    const container=$(id);
    container.replaceChildren();
    const max=Math.max(...values,1);
    names.forEach((name,i)=>{
      const li=document.createElement("li");
      const rank=document.createElement("span");rank.className="index";rank.textContent=String(i+1).padStart(2,"0");
      const link=document.createElement("a");link.className="rank-name";link.href=kind==="profession"?
        "../?"+new URLSearchParams({profile:name,city:state.city,country:state.country,goal:"build_portfolio"}).toString() :
        "./?"+new URLSearchParams({kind:"skills",item:name,city:state.city,country:state.country}).toString();
      link.textContent=name;link.title=kind==="profession"?"Create a plan for "+name:"Explore "+name;
      link.addEventListener("click",()=>{if(kind==="profession")state.focusRole=name;track(kind==="profession"?"profession_selected":"skill_selected",{mode:state.mode});});
      const bar=document.createElement("div");bar.className="rank-bar";bar.setAttribute("aria-label",String(values[i])+" relative units");
      const fill=document.createElement("div");fill.className="rank-fill";fill.style.width=(values[i]/max*100).toFixed(1)+"%";bar.append(fill);
      const score=document.createElement("span");score.className="rank-score";score.textContent=kind==="profession" && measured?money(values[i]):Math.round(values[i]).toString();
      li.append(rank,link,bar,score);container.append(li);
    });
  }
  function renderKPIs(isDemo,series) {
    const feed=state.feed;
    $("kpi-postings").textContent=isDemo?"PREVIEW":money((feed?.role_observations||[]).filter(x=>x.region===state.country).reduce((a,b)=>a+Number(b.sample_size||0),0));
    $("kpi-postings-note").textContent=isDemo?"Illustrative series · no measured trend available":"Source-reported mention totals · "+state.country;
    const observedRoles=window.ScoutRanking.roles(state.feed,state.city,state.country);
    $("kpi-roles").textContent=observedRoles?String(observedRoles.items.length).padStart(2,"0"):"—";
    $("kpi-roles-note").textContent=observedRoles?"Observed regional top-five":"No verified regional role ranking";
    const observedSkills=window.ScoutRanking.skills(state.feed,state.city,state.country);
    $("kpi-skills").textContent=observedSkills.length?String(observedSkills.length).padStart(2,"0"):"—";
    $("kpi-rising").textContent=observedSkills.length?observedSkills[0].name:"—";
    $("kpi-rising-note").textContent=observedSkills.length?
      "Highest Scout topic association · not verified growth":"No current skill signals";
    $("status-bar").textContent=isDemo?
      "DEMO MODE · Interactive example · no verified historical trends connected":
      ("OBSERVED HISTORY · "+(feed?.date||"dataset")+" · "+(state.kind==="skill"?"Topic proxies":"Job-posting signals"));
  }
  function renderRanks() {
    // Shared source-backed ranking across homepage and Scout Pulse.
    const current = window.ScoutRanking.roles(state.feed, state.city, state.country);
    if (current) {
      const list = current.items;
      makeRankList("top-roles",list.map(x=>x.name),list.map(x=>x.sample_size),true,"profession");
      $("roles-sub").textContent = "Observed posting mentions · "+current.region+
        " · collected "+new Date(current.generated_at).toLocaleDateString();
    } else {
      $("top-roles").replaceChildren();
      const li=document.createElement("li"); li.className="empty-ranking";
      li.textContent="No recent, verified top-five ranking for "+state.city+", "+state.country+
        ". Choose or type any profession on Scout to build a career plan.";
      $("top-roles").append(li);
      $("roles-sub").textContent="Current source-attributed job-posting counts only";
    }
    const skills=window.ScoutRanking.skills(state.feed,state.city,state.country);
    if(skills.length){
      makeRankList("top-skills",skills.map(s=>s.name),skills.map(s=>Number(s.score)),false,"skill");
      $("skills-sub").textContent="Scout topic-association scores · NOT employer-request counts";
    } else {
      $("top-skills").replaceChildren();
      const li=document.createElement("li");li.className="empty-ranking";
      li.textContent="No current topic-association scores available.";
      $("top-skills").append(li);
      $("skills-sub").textContent="Awaiting next published data snapshot";
    }
  }
  function renderHeatmap(isDemo) {
    const el=$("city-matrix");el.replaceChildren();
    // Only compare observed like-for-like role samples; topic proxy has no valid regional posting baseline.
    const rows=(state.series?.observations||[]).filter(x=>x.kind==="profession"&&x.measurement==="job_postings");
    const regions=[...new Set(rows.map(x=>x.region))].filter(Boolean);
    const last=state.feed?.date;
    const recent=rows.filter(x=>toMs(x.date)>=toMs(dateAgo(7)));
    const byRole={};
    for(const r of recent){(byRole[r.name] ||= new Set()).add(r.region);}
    const role=Object.keys(byRole).find(name=>byRole[name].size>=5);
    if(!isDemo && role){
      const matched=[...byRole[role]].slice(0,5);
      const names=[role],countries=matched;
      const matrix=document.createElement("div");matrix.className="heatmap";
      matrix.append(document.createElement("span"));
      countries.forEach(c=>{const s=document.createElement("span");s.textContent=c;matrix.append(s);});
      names.forEach(name=>{
        const label=document.createElement("span");label.textContent=name;matrix.append(label);
        const values=countries.map(c=>recent.filter(r=>r.name===name&&r.region===c).map(r=>Number(r.value)).at(-1)||0);
        const max=Math.max(...values,1);
        values.forEach(v=>{const cell=document.createElement("div");cell.className="cell";cell.style.background="rgba(83,243,157,"+(0.06+v/max*.88).toFixed(2)+")";cell.title=name+": "+v.toLocaleString()+" observed mentions";matrix.append(cell);});
      });el.append(matrix);$("cities-sub").textContent="Observed role-query counts · last 7 days";
    } else if(isDemo) {
      const names=["SQL","Python","Data analysis","Cloud skills","Machine learning"];
      const cities=["New York","San Francisco","London","Berlin","Rome"];
      const matrix=document.createElement("div");matrix.className="heatmap";
      matrix.append(document.createElement("span"));
      cities.forEach(c=>{const s=document.createElement("span");s.textContent=c;matrix.append(s);});
      names.forEach((name,i)=>{
        const label=document.createElement("span");label.textContent=name;matrix.append(label);
        cities.forEach((city,j)=>{const v=24+(hash(name+city)%77);const cell=document.createElement("div");cell.className="cell";
          cell.style.background="rgba(83,243,157,"+(0.1+v/100*.75).toFixed(2)+")";cell.title="Demo only · "+name+" in "+city;matrix.append(cell);});
      });
      el.append(matrix);$("cities-sub").textContent="Illustrative comparisons · not observed local hiring demand";
    } else {
      const note=document.createElement("p");note.className="heatmap-note";note.textContent="City comparison will appear when at least five regions have comparable, source-attributed observations for the same profession. No values have been estimated.";
      el.append(note);$("cities-sub").textContent="Coverage pending · no fabricated city estimates";
    }
  }
  function renderEmerging(isDemo) {
    const box=$("emerging-list");box.replaceChildren();
    let items=[];
    if(isDemo){
      items=DEFAULTS.emerging.map((name,i)=>({name,description:"Example topic",growth:[12.5,10.4,9.2,7.5,6.3][i]}));
      $("emerging-sub").textContent="Example momentum · illustrative percentages";
    } else {
      const rows=available(state.city,state.kind), grouped=new Map();
      for(const row of rows){const set=grouped.get(row.name)||[];set.push(row);grouped.set(row.name,set);}
      items=[...grouped.entries()].map(([name,arr])=>{
        const ordered=arr.sort((a,b)=>a.date.localeCompare(b.date));
        const latest=ordered.at(-1),old=ordered.find(x=>toMs(x.date)>=toMs(latest.date)-28*86400000);
        const growth=old&&Number(old.value)>0&&toMs(latest.date)-toMs(old.date)>=21*86400000?
          (Number(latest.value)/Number(old.value)-1)*100:null;
        return {name,growth};
      }).filter(x=>x.growth!==null&&Number.isFinite(x.growth)).sort((a,b)=>b.growth-a.growth).slice(0,5);
      $("emerging-sub").textContent="Observed 28-day growth where comparison coverage exists";
    }
    if(!items.length){const p=document.createElement("p");p.className="heatmap-note";p.textContent="Not enough comparable daily observations to calculate momentum yet.";box.append(p);return;}
    items.forEach((item,i)=>{
      const el=document.createElement("div");el.className="emerging-row";
      const idx=document.createElement("small");idx.textContent=String(i+1).padStart(2,"0");
      const name=document.createElement("strong");name.textContent=item.name;
      const val=document.createElement("span");val.textContent=pct(item.growth);
      el.append(idx,name,val);box.append(el);
    });
  }
  function setupFilters(){
    const sel=$("region-select");
    CITIES.forEach(([city,country])=>{
      const opt=document.createElement("option");opt.value=city;opt.textContent=city+", "+country;sel.append(opt);
    });
    if(CITIES.some(x=>x[0]===state.city))sel.value=state.city;
    else {state.city="Rome";state.country="Italy";sel.value=state.city;}
    sel.addEventListener("change",()=>{
      state.city=sel.value;state.country=CITIES.find(x=>x[0]===state.city)[1];
      state.selected={skill:null,profession:null};state.hidden={skill:[],profession:[]};
      syncPlanLinks();drawChart();
      track("region_selected",{city:state.city});
    });
    document.querySelectorAll("[data-range]").forEach(btn=>btn.addEventListener("click",()=>{
      state.days=Number(btn.dataset.range);
      document.querySelectorAll("[data-range]").forEach(b=>b.classList.toggle("active",b===btn));
      drawChart();
    }));
    document.querySelectorAll("[data-kind]").forEach(btn=>btn.addEventListener("click",()=>{
      state.kind=btn.dataset.kind;
      document.querySelectorAll("[data-kind]").forEach(b=>b.classList.toggle("active",b===btn));
      drawChart();
    }));
    $("compare-form").addEventListener("submit",event=>{
      event.preventDefault();
      const raw=$("compare-input").value.trim();
      const catalog=chartCatalog(),name=catalog.names.find(n=>n.toLocaleLowerCase()===raw.toLocaleLowerCase());
      const selected=state.selected[state.kind];
      if(!name){$("compare-status").textContent="Choose a profession or skill from the available suggestions.";return;}
      if(selected.includes(name)){$("compare-status").textContent="Already in comparison — use Show if it is hidden.";return;}
      if(selected.length>=5){$("compare-status").textContent="Compare up to five series. Remove one to add another.";return;}
      state.selected[state.kind]=[...selected,name];
      if(state.kind==="profession"){state.focusRole=name;syncPlanLinks();}
      $("compare-input").value="";
      track("series_added",{kind:state.kind,series:name,mode:state.mode});drawChart();
    });
    $("series-show-all").addEventListener("click",()=>{state.hidden[state.kind]=[];drawChart();});
    $("series-hide-all").addEventListener("click",()=>{
      state.hidden[state.kind]=state.selected[state.kind]||[];drawChart();
    });
    $("series-reset").addEventListener("click",()=>{
      state.selected[state.kind]=null;state.hidden[state.kind]=[];drawChart();
    });
    document.querySelectorAll('a.button.primary').forEach(a=>a.addEventListener("click",()=>track("plan_cta_clicked",{city:state.city,mode:state.mode})));
    document.querySelectorAll("[data-kind]").forEach(b=>b.classList.toggle("active",b.dataset.kind===state.kind));
  }
  async function init(){
    setupFilters();syncPlanLinks();
    const [feed,series]=await Promise.all([
      fetch(latestURL,{cache:"no-store"}).then(x=>x.ok?x.json():null).catch(()=>null),
      fetch(seriesURL,{cache:"no-store"}).then(x=>x.ok?x.json():null).catch(()=>null)
    ]);
    state.feed=feed && feed.schema_version===1 ? feed:null;
    state.series=series && series.schema_version===1 && Array.isArray(series.observations)?series:null;
    drawChart();
  }
  init();
})();
