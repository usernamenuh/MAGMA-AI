// scripts/check-rsc-cves.mjs
import { execSync } from "node:child_process";

const RSC_PKGS = new Set(["react-server-dom-webpack", "react-server-dom-parcel", "react-server-dom-turbopack"]);

// React blog: vulnerable versions include 19.0.0–19.0.2, 19.1.0–19.1.2, 19.2.0–19.2.2
// Fixes backported to 19.0.3, 19.1.4, 19.2.3. :contentReference[oaicite:1]{index=1}
function isVulnerableReactServerDom(v) {
  const m = String(v).match(/^(\d+)\.(\d+)\.(\d+)/);
  if (!m) return false;
  const [maj, min, pat] = m.slice(1).map(Number);
  if (maj !== 19) return false;
  if (min === 0) return pat <= 2;
  if (min === 1) return pat <= 2;
  if (min === 2) return pat <= 2;
  return false;
}

// Next.js Dec 11 fixed versions table (DoS + source exposure): 14.2.35, 15.0.7, 15.1.11, 15.2.8, 15.3.8, 15.4.10, 15.5.9, 16.0.10. :contentReference[oaicite:2]{index=2}
function isVulnerableNext(v) {
  const m = String(v).match(/^(\d+)\.(\d+)\.(\d+)/);
  if (!m) return false;
  const [maj, min, pat] = m.slice(1).map(Number);

  if (maj === 14) return min === 2 ? pat < 35 : true; // 14.0/14.1/14.2<35 vulnerable
  if (maj === 15) {
    if (min === 0) return pat < 7;
    if (min === 1) return pat < 11;
    if (min === 2) return pat < 8;
    if (min === 3) return pat < 8;
    if (min === 4) return pat < 10;
    if (min === 5) return pat < 9;
    return true; // unknown 15.x line -> be strict
  }
  if (maj === 16) return min === 0 ? pat < 10 : true;
  return false;
}

function walk(node, out = []) {
  if (!node || !node.dependencies) return out;
  for (const [name, dep] of Object.entries(node.dependencies)) {
    const version = dep?.version;
    if (version) out.push({ name, version });
    walk(dep, out);
  }
  return out;
}

let tree;
try {
  tree = JSON.parse(execSync("npm ls --json --all", { stdio: ["ignore", "pipe", "ignore"], encoding: "utf-8" }));
} catch (e) {
  // npm ls may exit with code 1 if there are issues, but the JSON output is still valid
  try {
    tree = JSON.parse(e.stdout);
  } catch {
    console.error("❌ Failed to parse npm ls output");
    process.exit(1);
  }
}

const deps = walk(tree);

const bad = [];

// Check react-server-dom-* packages
for (const { name, version } of deps) {
  if (RSC_PKGS.has(name) && isVulnerableReactServerDom(version)) {
    bad.push(`${name}@${version} (needs >= 19.0.3 / 19.1.4 / 19.2.3)`);
  }
}

// Check Next.js (only relevant if you use App Router/RSC; Pages Router isn’t affected per Next) :contentReference[oaicite:3]{index=3}
const next = deps.find((d) => d.name === "next");
if (next && isVulnerableNext(next.version)) {
  bad.push(`next@${next.version} (upgrade to patched version for your line; see Next.js fixed versions)`);
}

if (bad.length) {
  console.error("\n❌ Vulnerable dependency versions detected:\n- " + bad.join("\n- "));
  process.exit(1);
}

console.log("✅ No vulnerable React Server Components / Next.js versions detected.");
