/* Tests without React rendering or a browser; every new mount must pick
 * independent, valid defaults and keep explicit deep-link values. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("scout/scout-pulse.js", "utf8");

function environment(brokenStorage) {
  const memory = new Map();
  const store = brokenStorage
    ? {getItem(){throw new Error("blocked");},setItem(){throw new Error("blocked");}}
    : {getItem(key){return memory.get(key) || null;},setItem(key,v){memory.set(key,v);}};
  const context = {window:{React:{},localStorage:store},URLSearchParams,Math};
  vm.runInNewContext(source,context,{filename:"scout-pulse.js"});
  return context.window.ScoutLandingPresets;
}

const goals=[
  {id:"build_portfolio"},{id:"career"},{id:"create_agents"},{id:"startup"}
];
const locations=[
  {country:"Italy",cities:["Rome","Milan"]},
  {country:"Germany",cities:["Berlin","Munich"]}
];
const defaults=environment(false);
const first=defaults.initialSelection(new URLSearchParams(), goals, locations);
const second=defaults.initialSelection(new URLSearchParams(), goals, locations);
assert.notEqual(first.profile,second.profile, "role should not repeat across visits");
assert.notEqual(first.goal,second.goal, "goal should not repeat across visits");
assert.ok(defaults.professions.includes(first.profile));
assert.ok(goals.map(x=>x.id).includes(second.goal));
assert.equal(first.city,"Rome");
assert.equal(second.country,"Italy");

const deep=defaults.initialSelection(new URLSearchParams(
  "profile=Data%20Scientist&goal=startup&city=Berlin&country=Germany"
),goals,locations);
assert.equal(deep.profile,"Data Scientist");
assert.equal(deep.goal,"startup");
assert.equal(deep.city,"Berlin");
assert.equal(deep.country,"Germany");
const countryOnly=defaults.initialSelection(
  new URLSearchParams("country=Germany"),goals,locations);
assert.equal(countryOnly.city,"Berlin");
const cityOnly=defaults.initialSelection(
  new URLSearchParams("city=Munich"),goals,locations);
assert.equal(cityOnly.country,"Germany");

const invalidGoal=defaults.initialSelection(
  new URLSearchParams("profile=Nurse&goal=not_a_goal"),goals,locations);
assert.equal(invalidGoal.profile,"Nurse");
assert.ok(goals.some(x=>x.id===invalidGoal.goal));

const blocked=environment(true);
const safe=blocked.initialSelection(new URLSearchParams(),goals,locations);
assert.ok(blocked.professions.includes(safe.profile));
assert.ok(goals.some(x=>x.id===safe.goal));
console.log("Landing default rotation and deep-link tests passed.");
