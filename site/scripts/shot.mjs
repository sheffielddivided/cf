// Usage: node scripts/shot.mjs <url> <out.png> [width] [dark] [fullPage]
import { chromium } from "playwright-core";
const [url, out, width = "1200", dark = "", full = "1"] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: "/usr/bin/google-chrome", args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: Number(width), height: 900 }, colorScheme: dark ? "dark" : "light", deviceScaleFactor: 1 });
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push(String(e)));
await page.goto(url, { waitUntil: "networkidle" });
await page.waitForTimeout(300);
await page.screenshot({ path: out, fullPage: full === "1" });
if (errors.length) console.log("ERRORS:", errors.join("\n"));
await browser.close();
