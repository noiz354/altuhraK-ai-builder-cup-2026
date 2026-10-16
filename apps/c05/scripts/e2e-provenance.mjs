/**
 * C05 provenance + accessibility E2E.
 *
 * Two viewports, three surfaces. The target-size assertion follows WCAG 2.2
 * properly rather than applying one number everywhere: AA SC 2.5.8 requires
 * 24x24 CSS px on any pointer, while a coarse pointer used by kitchen staff
 * needs a genuinely comfortable target, so the mobile bar is 40px.
 *
 * Excluded from the target check: visually hidden controls, which are not
 * pointer targets at all (`.sr-only`, clip/1px sizing, `aria-hidden`).
 *
 * Usage: node scripts/e2e-provenance.mjs [baseUrl]
 */
import { chromium } from "playwright-core";

const BASE = process.argv[2] ?? "http://127.0.0.1:3000";
const EXECUTABLE =
  process.env.CHROME_PATH ??
  "/home/norman2/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome";

const results = [];
const check = (name, pass, detail = "") => results.push([pass, name, detail]);

const TARGET_PROBE = `(() => {
  const hidden = (e) => {
    const cs = getComputedStyle(e);
    if (cs.display === "none" || cs.visibility === "hidden") return true;
    if (e.closest(".sr-only,[hidden],[aria-hidden='true']")) return true;
    const r = e.getBoundingClientRect();
    // Visually hidden controls keep a 1x1 box on purpose.
    return r.width <= 1 || r.height <= 1;
  };
  return [...document.querySelectorAll("button,[role=button],a,input,select,textarea")]
    .filter((e) => !hidden(e))
    .map((e) => {
      const r = e.getBoundingClientRect();
      return { tag: e.tagName.toLowerCase(), text: (e.textContent || "").trim().slice(0, 24),
               w: Math.round(r.width), h: Math.round(r.height) };
    });
})()`;

const browser = await chromium.launch({ executablePath: EXECUTABLE });

for (const vp of [
  { w: 390, h: 844, name: "mobile 390", min: 40 },
  { w: 1440, h: 900, name: "desktop 1440", min: 24 },
]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => {
    if (m.type() !== "error") return;
    const t = m.text();
    // HMR is a dev-server transport, not application behaviour. It is absent in
    // a production build and its failure says nothing about the app.
    if (/_next\/hmr|WebSocket connection/i.test(t)) return;
    errors.push(t);
  });
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));

  await page.goto(`${BASE}/crew`, { waitUntil: "networkidle" });
  const crewText = await page.locator("body").innerText();
  check(`${vp.name} crew loads`, crewText.length > 200);
  check(`${vp.name} crew renders capture controls`, /capture|foto|tray|inspection/i.test(crewText));

  await page.goto(`${BASE}/admin`, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  const adminText = await page.locator("body").innerText();
  check(`${vp.name} admin loads`, adminText.length > 200);
  check(`${vp.name} admin shows model-inference provenance`, /Model inference/i.test(adminText));
  check(`${vp.name} admin separates baseline from model`, /Baseline only/i.test(adminText));

  await page.goto(`${BASE}/agent`, { waitUntil: "networkidle" });
  check(`${vp.name} agent loads`, (await page.locator("body").innerText()).length > 150);

  await page.goto(`${BASE}/admin`, { waitUntil: "networkidle" });
  const targets = await page.evaluate(TARGET_PROBE);
  const small = targets.filter((t) => t.h < vp.min || t.w < vp.min);
  check(
    `${vp.name} target size >= ${vp.min}px`,
    small.length === 0,
    small.slice(0, 3).map((s) => `${s.tag}"${s.text}" ${s.w}x${s.h}`).join(" | ")
  );
  check(`${vp.name} no horizontal scroll`, await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1
  ));
  check(`${vp.name} no application console errors`, errors.length === 0, errors.slice(0, 2).join(" | "));

  await ctx.close();
}

await browser.close();
const passed = results.filter((r) => r[0]).length;
for (const [pass, name, detail] of results) {
  console.log(`${pass ? "PASS" : "FAIL"}  ${name}${detail ? `  (${detail})` : ""}`);
}
console.log(`\n${passed}/${results.length} checks passed`);
process.exit(passed === results.length ? 0 : 1);
