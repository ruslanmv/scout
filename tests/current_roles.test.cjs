/* Shared current-source ranking gate; no fabricated roles. */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const env={window:{}};
vm.runInNewContext(fs.readFileSync("scout/scout-ranking.js","utf8"),env);
const Rank=env.window.ScoutRanking,now=Date.parse("2026-10-15T12:00:00Z");
const collected="2026-10-15T08:00:00Z";
const names=["Marketing Specialist","Data Analyst","Developer","UX/Product Designer","AI Engineer","Data Scientist"];
const counts=[500,900,650,450,720,200];
const records=names.map((name,i)=>({name,source:"adzuna",sample_size:counts[i],collected_at:collected}));
const feed={
  schema_version:1,generated_at:collected,date:"2026-10-15",
  regions:{
    Worldwide:{status:"curated",items:[{name:"Teacher",source:"curated"}]},
    Italy:{status:"measured",items:records},
    Germany:{status:"curated",items:[{name:"Nurse",source:"curated"}]}
  },
  skills:[
    {name:"Docker",source:"topic_proxy",score:180},
    {name:"Python",source:"topic_proxy",score:440},
    {name:"SQL",source:"topic_proxy",score:120},
    {name:"Fake",source:"demo",score:999}
  ]
};
const ranked=Rank.roles(feed,"Rome","Italy",now);
assert.ok(ranked);
assert.equal(ranked.region,"Italy");
assert.deepEqual(Array.from(ranked.items,x=>x.name),
  ["Data Analyst","AI Engineer","Developer","Marketing Specialist","UX/Product Designer"]);
assert.equal(ranked.items.length,5);
assert.ok(!ranked.items.some(x=>["Teacher","Nurse"].includes(x.name)));
assert.equal(Rank.roles(feed,"Berlin","Germany",now),null,"never borrow a different region");
assert.equal(Rank.roles(feed,"Rome","United States",now),null);
assert.equal(Rank.roles(null,"Rome","Italy",now),null);
assert.equal(Rank.roles({...feed,schema_version:2},"Rome","Italy",now),null);
assert.equal(Rank.roles({...feed,generated_at:"2026-10-01T08:00:00Z"},"Rome","Italy",now),null);
const old=records.map(x=>({...x,collected_at:"2026-09-01T08:00:00Z"}));
assert.equal(Rank.roles({...feed,regions:{Italy:{status:"measured",items:old}}},"Rome","Italy",now),null,
  "republishing old observations must not renew them");
assert.equal(Rank.roles({...feed,regions:{Italy:{status:"measured",items:records.slice(0,4)}}},"Rome","Italy",now),null);
assert.equal(Rank.roles({...feed,regions:{Italy:{status:"measured",items:[...records.slice(0,4),{...records[4],source:"curated"}]}}},"Rome","Italy",now),null);
assert.equal(Rank.roles({...feed,regions:{Italy:{status:"measured",items:[...records.slice(0,4),{...records[4],sample_size:0}]}}},"Rome","Italy",now),null);
assert.deepEqual(Array.from(Rank.skills(feed,"Rome","Italy",now),x=>x.name),["Python","Docker","SQL"]);
assert.equal(Rank.skills({...feed,generated_at:"2026-10-01T00:00:00Z"},"Rome","Italy",now).length,0);
// Both pages consume the same feed and selector.
const landing=fs.readFileSync("scout/scout-pulse.js","utf8");
const app=fs.readFileSync("scout/scout-app.js","utf8");
const chart=fs.readFileSync("scout/trends/pulse.js","utf8");
const index=fs.readFileSync("scout/index.html","utf8");
assert.ok(index.indexOf('src="scout-ranking.js"')<index.indexOf('src="scout-pulse.js"'));
assert.ok(app.includes("ScoutRanking.roles"));
assert.ok(app.includes('fetch("data/pulse/latest.json"'));
assert.ok(app.includes('query.get("profile")'));
assert.ok(app.includes("userSelectedRole.current"));
assert.ok(!app.includes('uS("Developer")'));
assert.ok(!landing.includes("Math.random"));
assert.ok(!landing.includes('"Teacher"'));
assert.ok(!landing.includes('"Nurse"'));
assert.ok(!landing.includes('fetch("data/pulse/latest.json"'));
assert.ok(chart.includes("ScoutRanking.roles"));
assert.ok(chart.includes("ScoutRanking.skills"));
assert.ok(!chart.includes("DEFAULTS.roles"));
assert.ok(!chart.includes("DEFAULTS.skills"));
console.log("Source-backed roles, freshness and common-feed contracts passed.");
