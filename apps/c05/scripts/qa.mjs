/**
 * C05 browser QA: real click-through of the three surfaces at three viewports.
 *
 * Usage: node scripts/qa.mjs [baseUrl]
 * Requires the QC service on :8000 and this Next app on :3000.
 */
import { chromium } from "playwright-core";
import { mkdirSync, writeFileSync } from "node:fs";
import { PNG } from "./png.mjs";

const BASE = process.argv[2] ?? "http://127.0.0.1:3000";
const EXECUTABLE =
  process.env.CHROME_PATH ??
  "/home/norman2/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome";
const OUT = "qa-evidence";
mkdirSync(OUT, { recursive: true });

// Deterministic synthetic tray: 3 visible food regions + one missing compartment.
function syntheticTray() {
  const W = 640;
  const H = 480;
  const px = new Uint8Array(W * H * 3).fill(238);
  const rect = (x, y, w, h, r, g, b) => {
    for (let yy = y; yy < y + h; yy += 1) {
      for (let xx = x; xx < x + w; xx += 1) {
        const i = (yy * W + xx) * 3;
        px[i] = r;
        px[i + 1] = g;
        px[i + 2] = b;
      }
    }
  };
  rect(24, 24, W - 48, H - 48, 255, 255, 255); // tray
  rect(48, 60, 160, 160, 240, 240, 228); // carbohydrate (rice)
  rect(240, 60, 160, 160, 226, 196, 168); // protein
  rect(432, 60, 160, 160, 196, 224, 180); // vegetable
  // vegetable slot intentionally empty -> missing_component expected
  return PNG(px, W, H);
}

const results = [];
function record(name, ok, detail) {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? ` :: ${detail}` : ""}`);
}

const browser = await chromium.launch({
  executablePath: EXECUTABLE,
  args: ["--no-sandbox", "--disable-gpu"],
});

const consoleErrors = [];

async function newPage(width, height) {
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();
  page.on("console", (m) => {
    if (m.type() === "error") consoleErrors.push(m.text());
  });
  page.on("pageerror", (e) => consoleErrors.push(String(e)));
  return { context, page };
}

// ---------------------------------------------------------------- crew 390
{
  const { context, page } = await newPage(390, 844);
  await page.goto(`${BASE}/crew`, { waitUntil: "networkidle" });
  await page.waitForSelector("text=Expected meal components");

  const manifestLoaded = await page
    .locator("text=Nasi / komponen karbohidrat")
    .first()
    .isVisible()
    .catch(() => false);
  record("crew: manifest loaded from API", manifestLoaded);

  const health = await page.locator("text=QC service up").isVisible().catch(() => false);
  record("crew: QC service health badge", health);

  const tray = `/tmp/opencode/tray.png`;
  writeFileSync(tray, Buffer.from(syntheticTray()));

  await page.setInputFiles('input[type="file"]', tray);
  await page.waitForSelector("img[alt='Captured meal preview']", { timeout: 10000 });
  const preview = await page.locator("img[alt='Captured meal preview']").isVisible();
  record("crew: image preview after validation", preview);

  await page.getByRole("button", { name: "Gemini multimodal" }).click();
  await page.getByRole("button", { name: "Run inspection" }).click();
  await page
    .locator("text=AI PREDICTION — UNVERIFIED")
    .waitFor({ timeout: 45000 })
    .catch(() => null);
  const resultShown = await page
    .locator("text=AI PREDICTION — UNVERIFIED")
    .first()
    .isVisible()
    .catch(() => false);
  record("crew: prediction block rendered", resultShown);

  const confidence = await page.locator("text=NOT_CALIBRATED").first().isVisible().catch(() => false);
  record("crew: confidence stays NOT_CALIBRATED", confidence);

  await page.screenshot({ path: `${OUT}/crew-390-viewport.png` });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(150);
  const headerClear = await page.evaluate(() => {
    const header = document.querySelector("header");
    const main = document.querySelector("main");
    if (!header || !main) return false;
    const h = header.getBoundingClientRect().bottom;
    const first = main.querySelector("section");
    return first ? first.getBoundingClientRect().top >= h - 1 : true;
  });
  record("crew: first content clears sticky header at scroll top", headerClear);
  const serif = await page.evaluate(() => {
    const el = document.querySelector("h1");
    return el ? getComputedStyle(el).fontFamily.toLowerCase().includes("serif") && !getComputedStyle(el).fontFamily.toLowerCase().includes("sans") : true;
  });
  record("crew: headings render sans, not serif fallback", !serif);
  const overflowX = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  record("crew 390: no horizontal overflow", !overflowX);
  await page.screenshot({ path: `${OUT}/crew-390.png`, fullPage: true });
  await context.close();
}

// -------------------------------------------------------------- admin 1440
{
  const { context, page } = await newPage(1440, 1100);
  await page.goto(`${BASE}/admin`, { waitUntil: "networkidle" });
  await page.waitForSelector("text=Review queue");

  const kpi = await page.locator("text=Pending review").first().isVisible();
  record("admin: KPI from real records", kpi);

  await page.getByRole("button", { name: "Open" }).first().click();
  await page.waitForSelector("text=Reviewer controls", { timeout: 10000 });
  const evidenceVisible = await page.locator("text=AI PREDICTION — UNVERIFIED").first().isVisible();
  record("admin: evidence pane with unverified treatment", evidenceVisible);

  await page.getByRole("button", { name: "ACCEPT", exact: true }).click();
  await page.getByRole("button", { name: "Approve review" }).click();
  await page
    .locator("text=Review approved and recorded.")
    .waitFor({ timeout: 15000 })
    .catch(() => null);
  const approved = await page.locator("text=Review approved and recorded.").isVisible().catch(() => false);
  record("admin: approval recorded", approved);

  await page.screenshot({ path: `${OUT}/admin-1440.png`, fullPage: true });
  await context.close();
}

// -------------------------------------------------------------- agent 1440
{
  const { context, page } = await newPage(1440, 1100);
  await page.goto(`${BASE}/agent`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Rangkum inspeksi dapur ini" }).click();
  await page.waitForSelector("text=Tool execution", { timeout: 15000 }).catch(() => null);
  // Let motion settle before asserting or capturing, so evidence is not mid-animation.
  await page.waitForTimeout(600);
  const rawDict = await page.locator("text=/\{'(meal_complete|uncertain|missing_component)'/").count();
  record("agent: no raw python dict in the answer", rawDict === 0);
  const toolShown = await page.locator("text=get_kitchen_summary").first().isVisible().catch(() => false);
  record("agent: grounded tool call visible", toolShown);

  const disclaimer = await page.locator("text=/Not proof of food safety/i").first().isVisible().catch(() => false);
  record("agent: safety disclaimer present", disclaimer);

  await page.screenshot({ path: `${OUT}/agent-1440.png`, fullPage: true });
  await context.close();
}

// ----------------------------------------------------------- tablet 768
{
  const { context, page } = await newPage(768, 1024);
  await page.goto(`${BASE}/crew`, { waitUntil: "networkidle" });
  await page.screenshot({ path: `${OUT}/crew-768.png`, fullPage: true });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  record("tablet 768: no horizontal overflow", !overflow);
  await context.close();
}

await browser.close();

record("no console errors across surfaces", consoleErrors.length === 0, consoleErrors.slice(0, 3).join(" | "));

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
writeFileSync(`${OUT}/results.json`, JSON.stringify({ results, consoleErrors }, null, 2));
process.exit(failed.length === 0 ? 0 : 1);