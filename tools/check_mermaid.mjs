// Optional release QA: install mermaid and jsdom in an ignored local prefix.
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
const dependencyRoot=resolve(process.argv[2] || ".local/final-mermaid/node_modules");
const {JSDOM}=await import(pathToFileURL(resolve(dependencyRoot,"jsdom/lib/api.js")));
const dom=new JSDOM("<!doctype html><html><body></body></html>");
globalThis.window=dom.window;
globalThis.document=dom.window.document;
const {default:mermaid}=await import(pathToFileURL(resolve(dependencyRoot,"mermaid/dist/mermaid.esm.mjs")));
mermaid.initialize({startOnLoad:false});
const source=await readFile("portfolio/Project_Horizon_Portfolio.md","utf8");
const blocks=[...source.matchAll(/```mermaid\s*\n([\s\S]*?)```/g)].map(m=>m[1]);
if(blocks.length!==2) throw new Error("Expected two portfolio frameworks");
for(const code of blocks) await mermaid.parse(code);
const report={status:"PASS",parser:"mermaid",blocks:blocks.length};
await writeFile("tmp/mermaid_validation.json",JSON.stringify(report,null,2));
console.log(JSON.stringify(report));
