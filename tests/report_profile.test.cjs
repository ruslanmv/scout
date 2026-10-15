/* Browser-independent smoke test for report profession/goal/location handoff. */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const html=fs.readFileSync("scout/report/index.html","utf8");
const match=html.match(/<script>\s*(document\.addEventListener\('DOMContentLoaded',[\s\S]*?\}\);)\s*<\/script>/);
assert.ok(match,"Report learning-path form initialization was not found");

function element(){
  return {value:"",textContent:"",children:[],setAttribute(){},addEventListener(){},
    replaceChildren(){this.children=[];},append(item){this.children.push(item);}};
}
function render(search){
  const options=["build_portfolio","career","create_agents","startup","upskill"].map(value=>({value}));
  const goal={options,selectedIndex:0};
  Object.defineProperty(goal,"value",{get(){return options[goal.selectedIndex].value;}});
  const role={...element(),message:"",setCustomValidity(msg){this.message=msg;},
    reportValidity(){return false;},focus(){}};
  let submit,ready;
  const form={addEventListener(event,fn){if(event==="submit")submit=fn;}};
  const popular=element(),popularLabel=element(),roleList=element();
  const elements={"become-goal":goal,"become-role":role,"becomeForm":form,
    "become-popular-options":popular,"become-popular-label":popularLabel,
    "become-roles":roleList};
  const document={
    getElementById(id){return elements[id]||null;},
    querySelectorAll(){return [];},
    createElement(){return element();},
    addEventListener(name,fn){if(name==="DOMContentLoaded")ready=fn;}
  };
  const location={search,href:"https://ruslanmv.com/scout/report/"+search};
  const window={location:{href:""},ScoutSuggestions:{
    professions(){return {items:[{name:"Developer"},{name:"Data Analyst"},{name:"Nurse"}],
      observed:false,recommended:"Developer"};},
    mountAutocomplete(){return {refresh(){},close(){}};}
  }};
  const fetch=()=>Promise.resolve({ok:false});
  vm.runInNewContext(match[1],{document,location,window,URL,URLSearchParams,fetch,Promise});
  assert.equal(typeof ready,"function");
  ready();
  assert.equal(typeof submit,"function");
  function send(){submit({preventDefault(){}});return window.location.href;}
  return {role,goal,send,popular,popularLabel};
}

const marketing=render("?profile=Marketing+Specialist&city=Rome&country=Italy&goal=build_portfolio");
assert.equal(marketing.role.value,"Marketing Specialist","deep-link profession must be preserved");
assert.equal(marketing.goal.value,"build_portfolio");
let url=new URL(marketing.send());
assert.equal(url.pathname,"/scout/learn/");
assert.equal(url.searchParams.get("role"),"Marketing Specialist");
assert.equal(url.searchParams.get("goal"),"build_portfolio");
assert.equal(url.searchParams.get("country"),"Italy");
assert.equal(url.searchParams.get("city"),"Rome");
assert.equal(url.searchParams.get("start"),"1");
assert.equal(marketing.popular.children.length,3);

const another=render("?profile=UX%2FProduct+Designer&city=Berlin&country=Germany&goal=create_agents");
assert.equal(another.role.value,"UX/Product Designer");
assert.equal(another.goal.value,"create_agents");
another.role.value="Data Analyst";
url=new URL(another.send());
assert.equal(url.searchParams.get("role"),"Data Analyst","manual edits must be preserved");
assert.equal(url.searchParams.get("goal"),"create_agents");
assert.equal(url.searchParams.get("city"),"Berlin");

const missing=render("?city=Rome&country=Italy");
assert.equal(missing.role.value,"Developer","curated default is selected when no profile is supplied");
assert.equal(missing.popularLabel.textContent.includes("curated"),true);
url=new URL(missing.send());
assert.equal(url.searchParams.get("role"),"Developer");
missing.role.value="";
missing.send();
assert.ok(missing.role.message.includes("Enter your profession"),
  "cleared profession must fail validation");
console.log("Scout report profession / goal / location handoff passed.");
