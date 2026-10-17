/**
 * Scripted demo walkthrough: screenshots for the deck and, with --video, a
 * paced screen recording with on-screen captions for the 3-4 minute demo.
 *
 * Usage:
 *   node scripts/demo-walkthrough.mjs [baseUrl] [--video] [--out dir]
 *   node scripts/demo-walkthrough.mjs https://c05-frontend-...run.app --video
 *
 * The run writes into the target's data: one inspection, one review, the demo
 * claim scenario (idempotent), one decision and one test illness report.
 * Point it at staging first.
 *
 * Browser: CHROME_PATH, else Playwright's bundled Chromium, else system Chrome.
 */
import { chromium } from "playwright-core";
import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const args = process.argv.slice(2);
const VIDEO = args.includes("--video");
const outIdx = args.indexOf("--out");
const OUT = outIdx >= 0 ? args[outIdx + 1] : "demo-output";
const BASE = (args.find((a) => /^https?:\/\//.test(a)) ?? "http://localhost:3000").replace(/\/$/, "");
const HERE = dirname(fileURLToPath(import.meta.url));
const TRAY = join(HERE, "demo-tray.jpg");
const W = 1440;
const H = 900;

function findChrome() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const pw = join(
    process.env.PLAYWRIGHT_BROWSERS_PATH ??
      (process.platform === "win32" ? join(homedir(), "AppData/Local/ms-playwright") : join(homedir(), ".cache/ms-playwright")),
  );
  if (existsSync(pw)) {
    const dir = readdirSync(pw).find((d) => /^chromium-\d+$/.test(d));
    if (dir) {
      for (const rel of ["chrome-win64/chrome.exe", "chrome-win/chrome.exe", "chrome-linux64/chrome", "chrome-linux/chrome"]) {
        if (existsSync(join(pw, dir, rel))) return join(pw, dir, rel);
      }
    }
  }
  for (const p of [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "/usr/bin/google-chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ]) {
    if (existsSync(p)) return p;
  }
  throw new Error("No Chromium found; set CHROME_PATH");
}

mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: findChrome(), args: ["--disable-gpu"] });
const context = await browser.newContext({
  viewport: { width: W, height: H },
  deviceScaleFactor: VIDEO ? 1 : 2,
  ...(VIDEO ? { recordVideo: { dir: OUT, size: { width: W, height: H } } } : {}),
});
// Hide the Next.js dev-mode badge so local recordings look like production.
await context.addInitScript(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const style = document.createElement("style");
    style.textContent = "nextjs-portal{display:none!important}";
    document.head.appendChild(style);
  });
});
const page = await context.newPage();
const shots = [];

/** Real pacing only when recording; screenshots run fast. */
const pause = (ms) => page.waitForTimeout(VIDEO ? ms : Math.min(ms, 400));

async function caption(text) {
  console.log(`· ${text}`);
  await page.evaluate((t) => {
    let el = document.getElementById("demo-caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "demo-caption";
      el.setAttribute(
        "style",
        "position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:99999;max-width:1100px;" +
          "background:rgba(22,33,28,.92);color:#fff;font:500 22px/1.35 system-ui,sans-serif;" +
          "padding:14px 22px;border-radius:12px;box-shadow:0 6px 24px rgba(0,0,0,.25);text-align:center",
      );
      document.body.appendChild(el);
    }
    el.textContent = t;
    el.style.display = t ? "block" : "none";
  }, VIDEO ? text : "");
}

async function shot(name) {
  const path = join(OUT, `${name}.png`);
  await page.screenshot({ path });
  shots.push(path);
}

/** Briefly outline what is about to be clicked, so viewers can follow. */
async function spot(locator) {
  // Centre it: the sticky header would otherwise cover anything scrolled to the top edge.
  await locator.evaluate((el) => el.scrollIntoView({ block: "center" }));
  if (!VIDEO) return;
  await locator.evaluate((el) => {
    el.style.outline = "4px solid #f59e0b";
    el.style.outlineOffset = "3px";
    setTimeout(() => {
      el.style.outline = "";
    }, 1400);
  });
  await pause(900);
}

async function click(locator) {
  await spot(locator);
  // The sticky header can still sit over a target near the top edge; fall back
  // to a DOM click on the same element rather than failing the whole recording.
  await locator.click({ timeout: 5000 }).catch(() => locator.dispatchEvent("click"));
}

// Not every page sits in the main nav (Ask AI is on the right, Report illness in
// the footer), so navigate by href anywhere in the page chrome.
const HREF = { Crew: "/crew", Admin: "/admin", Claims: "/claims", "Report illness": "/report" };
async function nav(label) {
  await click(page.locator(`header a[href="${HREF[label]}"], footer a[href="${HREF[label]}"]`).first());
  await page.waitForLoadState("networkidle");
}

async function scrollTo(locator) {
  await locator.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "center" }));
  await pause(1200);
}

// ------------------------------------------------------------------ home
await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
await caption("Meal QC traces every ingredient from supplier to plate, checks every tray, and handles illness reports fairly.");
await pause(5000);
await shot("01-home");

await click(page.getByRole("link", { name: "Read the 5-minute guide" }));
await page.waitForLoadState("networkidle");
await caption("A built-in guide explains every page, role and signal in plain language.");
await pause(4000);
await shot("02-guide");

// ------------------------------------------------------------------ crew
await nav("Crew");
await caption("Kitchen crew: photograph the tray. The manifest lists what every tray must contain.");
await page.waitForSelector("text=Rice or other carbohydrate");
await pause(4000);
await page.setInputFiles('input[type="file"]', TRAY);
await page.waitForSelector("img[alt='Captured meal preview']");
await scrollTo(page.locator("img[alt='Captured meal preview']"));
await caption("This tray has rice and protein — the vegetable compartment is empty.");
await pause(4500);
await caption("Behind the scenes, Gemini on Vertex AI checks the photo. The result is validated and never auto-approved.");
await click(page.getByRole("button", { name: "Run inspection" }));
await page.waitForSelector("text=3 · Result", { timeout: 180000 });
await scrollTo(page.locator("text=3 · Result"));
await caption("The result arrives marked “not yet reviewed”, with an audit trail.");
await pause(6000);
await shot("03-crew-result");

// ------------------------------------------------------------------ admin
await nav("Admin");
await caption("Supervisor: live counts of checks waiting for a decision.");
await pause(4500);
await shot("04-admin");
await click(page.getByRole("button", { name: "Open", exact: true }).first());
await scrollTo(page.getByText("Reviewer controls"));
await caption("The supervisor compares the result with the meal list and records a disposition.");
await pause(3500);
const hold = page.getByRole("button", { name: "HOLD", exact: true });
if (await hold.isEnabled()) {
  await click(hold);
  await page.getByLabel(/Comment/).fill("Vegetable compartment empty — hold the batch and refill.");
  await pause(1500);
  await click(page.getByRole("button", { name: "Approve review" }));
  await pause(2500);
}
await shot("05-admin-review");

// ------------------------------------------------------------------ claims
await page.getByLabel("Active role").selectOption("ADMIN");
await nav("Claims");
await caption("Illness reports: grouped by kitchen and day, checked against what was actually served.");
await pause(3500);
const seed = page.getByRole("button", { name: "Load demo scenario" });
if (await seed.isVisible()) {
  await click(seed);
  await page.waitForTimeout(1500);
}
const cards = page.locator('section[aria-label="Incidents"] button').filter({ hasText: "report" });
await click(cards.first());
await page.waitForSelector('section[aria-label="Incident detail"]');
await caption("35 reports, 340 people — but this kitchen served only 230 portions to that school.");
await pause(5500);
await shot("06-claims-incident");
await scrollTo(page.getByText("What doesn’t add up"));
await caption("Each conflict is a plain-language signal. Health priority stays URGENT regardless.");
await pause(4500);
await click(page.getByRole("button", { name: /Copy-paste wording/ }));
await scrollTo(page.locator("table").last());
await caption("Click a signal to see the exact reports behind it: one template, three phones, one photo.");
await pause(6000);
await shot("07-claims-signal");
await scrollTo(page.getByText("PATTERN SUMMARY — ADVISORY"));
await click(page.getByRole("button", { name: /Summarize reports|Refresh summary/ }));
await page.waitForTimeout(VIDEO ? 9000 : 3000);
await caption("Behind the scenes, Gemini explains the pattern and suggests checks. It cannot change the score or close the case.");
await pause(6000);
await shot("08-claims-gemini");
const reason = page.getByLabel(/Reason/);
if (await reason.isVisible()) {
  await scrollTo(reason);
  await reason.fill("Delivery records conflict with 32 templated reports; notify Puskesmas and verify by phone.");
  await pause(1500);
  await click(page.getByRole("button", { name: "Escalate to health office" }));
  await caption("Every decision needs a reason and lands in the audit trail. Closing needs medical follow-up first.");
  await pause(5000);
}
await click(cards.nth(1));
await page.waitForSelector('section[aria-label="Incident detail"]');
await caption("Contrast: a real outbreak. No conflicts, clinic visits, one hospitalisation — escalate now.");
await pause(6000);
await shot("09-claims-outbreak");
await click(page.getByRole("link", { name: /Trace this day/ }));
await page.waitForSelector("text=Trace a meal back");
await pause(2500);
await caption("Traced in one click: that day's chicken came 145 km from a trader with no cold chain and arrived at 11.5°C.");
await pause(6500);
await shot("09b-outbreak-trace");

// ------------------------------------------------------------------ report
await nav("Report illness");
await caption("Parents and teachers report from any phone. Care first: the form says go to Puskesmas / 119.");
await pause(4000);
const today = new Date().toISOString().slice(0, 10);
await page.getByLabel("School code").fill("SDN-02");
await page.getByLabel("Date the meal was eaten").fill(today);
await page.getByLabel("When did symptoms start?").fill(`${today}T13:30`);
await click(page.getByRole("button", { name: "Vomiting", exact: true }));
await page.getByLabel("Phone number for follow-up").fill("081200000001");
await page.getByLabel(/What happened/).fill("Demo report: my child vomited once after lunch.");
await pause(2000);
await shot("10-report-form");
await click(page.getByRole("button", { name: "Send report" }));
await page.waitForSelector("text=Report received");
await caption("Phone numbers are stored only as a hash; the report joins today’s incident instantly.");
await pause(4500);

await caption("Meal QC — Gemini works behind the scenes; people decide; everything is audited. Built on Google Cloud.");
await pause(5000);

const video = page.video();
await context.close();
if (video) {
  const target = join(OUT, "demo-walkthrough.webm");
  try {
    await video.saveAs(target);
    await video.delete();
    console.log(`video: ${target}`);
  } catch (e) {
    // Playwright writes nothing when its ffmpeg build is missing or mismatched.
    console.error(`video was not written (${e.message.split("\n")[0]}). Run: npx playwright install ffmpeg`);
    process.exitCode = 1;
  }
}
await browser.close();
console.log(`screenshots: ${shots.length} in ${OUT}`);
