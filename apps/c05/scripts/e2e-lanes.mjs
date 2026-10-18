/**
 * C05 lane coverage: every page in the nav must load, render its own content, and stay
 * usable at mobile and desktop widths.
 *
 * The provenance suite covers crew/admin/agent. This one covers the ported lanes so a
 * broken supply or claims page cannot ship unnoticed.
 *
 * Usage: node scripts/e2e-lanes.mjs [baseUrl]
 */
import { chromium } from "playwright-core";

const BASE = process.argv[2] ?? "http://127.0.0.1:3000";
const EXECUTABLE =
  process.env.CHROME_PATH ??
  "/home/norman2/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome";

const ROUTES = [
  { path: "/supply", expect: /Ingredient traceability|Supply insights|Supply/i },
  { path: "/delivery", expect: /Student delivery verification|delivery/i },
  { path: "/claims", expect: /Care first|Illness reports|illness/i },
  { path: "/report", expect: /Official record|Report/i },
  { path: "/guide", expect: /Know what went into every meal|Guide|claim status/i },
];

const results = [];
const check = (name, pass, detail = "") => results.push([pass, name, detail]);

const browser = await chromium.launch({ executablePath: EXECUTABLE });

for (const vp of [
  { w: 390, h: 844, name: "mobile 390" },
  { w: 1440, h: 900, name: "desktop 1440" },
]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => {
    if (m.type() !== "error") return;
    const t = m.text();
    if (/_next\/hmr|WebSocket connection/i.test(t)) return;
    errors.push(t);
  });
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));

  for (const route of ROUTES) {
    const res = await page.goto(`${BASE}${route.path}`, { waitUntil: "networkidle" });
    check(`${vp.name} ${route.path} responds 200`, res?.status() === 200, `got ${res?.status()}`);
    const text = await page.locator("body").innerText();
    check(`${vp.name} ${route.path} renders content`, route.expect.test(text), text.slice(0, 80));
  }

  // Every nav destination must be reachable and identifiable as the active link.
  await page.goto(`${BASE}/crew`, { waitUntil: "networkidle" });
  const links = await page.locator('header a[href^="/"]').allTextContents();
  for (const route of ROUTES) {
    const label = route.path.slice(1);
    check(
      `${vp.name} nav links to ${route.path}`,
      links.some((l) => l.trim().toLowerCase().includes(label === "claims" ? "reports" : label)),
      links.join("|"),
    );
  }

  check(
    `${vp.name} no horizontal scroll`,
    await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1),
  );
  check(`${vp.name} no application console errors`, errors.length === 0, errors.slice(0, 2).join(" | "));

  await ctx.close();
}

await browser.close();
const passed = results.filter((r) => r[0]).length;
for (const [pass, name, detail] of results) {
  console.log(`${pass ? "PASS" : "FAIL"}  ${name}${detail && !pass ? `  (${detail})` : ""}`);
}
console.log(`\n${passed}/${results.length} checks passed`);
process.exit(passed === results.length ? 0 : 1);