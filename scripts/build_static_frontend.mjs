import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const cwdSiteDir = path.join(process.cwd(), "site");
const siteDir = fs.existsSync(cwdSiteDir) ? cwdSiteDir : path.join(root, "frontend", "site");
const outDir = fs.existsSync(cwdSiteDir) ? path.join(process.cwd(), "dist") : path.join(root, "frontend", "dist");

if (!fs.existsSync(siteDir)) {
  throw new Error(`Static site source missing: ${siteDir}`);
}

fs.rmSync(outDir, { recursive: true, force: true });
fs.cpSync(siteDir, outDir, { recursive: true });

for (const route of ["demo", "ops", "pricing", "proof"]) {
  const indexFile = path.join(outDir, route, "index.html");
  if (!fs.existsSync(indexFile)) {
    throw new Error(`Missing route index: ${indexFile}`);
  }
}

console.log(`Static frontend build: ${outDir}`);
