/* Browser-independent end-to-end smoke check for report context handoff. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const html = fs.readFileSync("scout/report/index.html", "utf8");
const code = html.match(/<script>\s*(\(function\(\)\{[\s\S]*?\}\)\(\);)\s*<\/script>/);
assert.ok(code, "Report learning-path form script was not found");

function render(search) {
  const links = [];
  const options = ["build_portfolio", "career", "create_agents", "startup", "upskill"].map(value => ({value}));
  const goal = {options, selectedIndex: 0};
  Object.defineProperty(goal, "value", {get(){return options[goal.selectedIndex].value;}});
  const role = {value: "", message: "", setCustomValidity(msg){this.message=msg;},
    reportValidity(){return false;}};
  let submit;
  const form = {addEventListener(event, fn){if(event === "submit")submit=fn;}};
  const doc = {
    getElementById(id){return id==="become-goal"?goal:id==="become-role"?role:id==="becomeForm"?form:null;},
    querySelectorAll(){return [];}
  };
  const location = {search,href:"https://ruslanmv.com/scout/report/"+search};
  const window = {location:{href:""}};
  vm.runInNewContext(code[1], {document:doc,location,window,URL,URLSearchParams});
  assert.equal(typeof submit, "function");
  function send(){
    submit({preventDefault(){}});
    return window.location.href;
  }
  return {role,goal,send};
}

const marketing = render("?profile=Marketing+Specialist&city=Rome&country=Italy&goal=build_portfolio");
assert.equal(marketing.role.value,"Marketing Specialist","profile must carry over from landing");
assert.equal(marketing.goal.value,"build_portfolio");
let url = new URL(marketing.send());
assert.equal(url.pathname,"/scout/learn/");
assert.equal(url.searchParams.get("role"),"Marketing Specialist");
assert.equal(url.searchParams.get("goal"),"build_portfolio");
assert.equal(url.searchParams.get("country"),"Italy");
assert.equal(url.searchParams.get("city"),"Rome");
assert.equal(url.searchParams.get("start"),"1");
assert.notEqual(url.searchParams.get("role"),"AI Engineer");

const another = render("?profile=UX%2FProduct+Designer&city=Berlin&country=Germany&goal=create_agents");
assert.equal(another.role.value,"UX/Product Designer");
assert.equal(another.goal.value,"create_agents");
another.role.value = "Data Analyst";
url = new URL(another.send());
assert.equal(url.searchParams.get("role"),"Data Analyst","manual edits must be preserved");
assert.equal(url.searchParams.get("goal"),"create_agents");
assert.equal(url.searchParams.get("city"),"Berlin");

const missing = render("?city=Rome&country=Italy");
assert.equal(missing.role.value,"","must not default to AI Engineer");
assert.equal(missing.send(),"","empty profession must not submit");
assert.ok(missing.role.message.includes("Enter your profession"));

console.log("Scout report profession / goal / location handoff passed.");
