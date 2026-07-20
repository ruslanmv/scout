#!/usr/bin/env node
/*
 * Precompile the Scout Report (professional landing) JSX sources into the plain
 * .js files that dashboard/Scout Report.html loads. The page ships vendored
 * React (dashboard/vendor/) and these precompiled scripts, so it stays fully
 * self-contained — no CDN and no in-browser Babel.
 *
 * Usage:
 *   npm install --no-save @babel/core @babel/preset-react
 *   node scripts/build_scout_report.js
 *
 * Edit the .jsx sources, then re-run this to regenerate the .js files.
 */
const babel = require("@babel/core");
const fs = require("fs");
const path = require("path");

const DASH = path.join(__dirname, "..", "scout");
const FILES = ["scout-components", "scout-landing", "scout-app"];

for (const f of FILES) {
  const src = fs.readFileSync(path.join(DASH, f + ".jsx"), "utf8");
  const out = babel.transformSync(src, {
    sourceType: "script",
    presets: [["@babel/preset-react", { runtime: "classic" }]],
    comments: true,
    compact: false,
  });
  // Wrap each file in an IIFE so its top-level declarations stay file-scoped
  // (the sources share globals only through window.*), preventing collisions
  // such as scout-landing's `function Landing` vs scout-app's `const Landing`.
  const header =
    "/* Compiled from " + f +
    ".jsx by @babel/preset-react. Do not edit directly; edit the .jsx and re-run scripts/build_scout_report.js. */\n(function () {\n";
  const footer = "\n})();\n";
  fs.writeFileSync(path.join(DASH, f + ".js"), header + out.code + footer);
  console.log("compiled " + f + ".jsx -> " + f + ".js");
}
console.log("done");
