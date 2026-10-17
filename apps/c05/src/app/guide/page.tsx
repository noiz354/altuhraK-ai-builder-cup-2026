import Link from "next/link";
import { HEALTH_COPY, SIGNAL_COPY, STATUS_COPY } from "@/lib/claim-copy";
import type { HealthPriority, IncidentStatus } from "@/lib/c05-types";

const TOC = [
  { id: "tour", label: "5-minute tour" },
  { id: "roles", label: "Roles" },
  { id: "crew", label: "Check a meal" },
  { id: "admin", label: "Review checks" },
  { id: "report", label: "Report an illness" },
  { id: "claims", label: "Illness reports" },
  { id: "supply", label: "Trace ingredients" },
  { id: "glossary", label: "Glossary" },
  { id: "faq", label: "FAQ" },
];

const TOUR = [
  {
    href: "/crew",
    page: "Check meal",
    title: "Check a meal photo",
    body: "Choose a photo of a meal tray and press Run inspection. The result says whether every component is present.",
  },
  {
    href: "/admin",
    page: "Review",
    title: "Approve or reject it",
    body: "Open the new check in the review queue, compare it with the meal list, pick a QC disposition and approve or reject. Only people decide.",
  },
  {
    href: "/report",
    page: "Report illness",
    title: "See the public side",
    body: "Send a test report as a parent would. It appears in Illness reports under that kitchen and date within seconds.",
  },
  {
    href: "/claims",
    page: "Illness reports",
    title: "Triage illness reports",
    body: "Set the role to ADMIN, press “Load demo scenario” and open the incident with the red score bar. Click a signal to see the reports behind it.",
  },
  {
    href: "/claims",
    page: "Illness reports",
    title: "Trace the meal back to its suppliers",
    body: "Open the real-outbreak incident and press “Trace this day’s ingredients”: that day’s chicken came from a distant supplier without a cold chain and arrived warm.",
  },
];

const ROLES = [
  {
    role: "CREW",
    who: "Kitchen staff",
    can: "Record deliveries, check meal photos, see ingredient checks.",
    cannot: "Approve checks, see illness reports or prepare briefs.",
  },
  {
    role: "SUPERVISOR",
    who: "Kitchen supervisor",
    can: "Everything crew can, plus approve or reject checks, prepare briefs, view illness reports and escalate to the health office.",
    cannot: "Close an illness incident.",
  },
  {
    role: "ADMIN",
    who: "Program admin",
    can: "Everything, including closing incidents and loading the demo scenario.",
    cannot: "Change an approval or a closure after it is recorded.",
  },
];

const LABELS = [
  { key: "meal_complete", text: "All expected components are visible on the plate." },
  { key: "missing_component", text: "At least one component (rice, protein or vegetables) is missing." },
  { key: "uncertain", text: "The photo cannot tell: blurred, dark, covered or cut off. Retake it." },
];

const REVIEW = [
  { key: "UNVERIFIED", text: "No usable result yet, or the check could not finish. Needs a person." },
  { key: "PENDING REVIEW", text: "A result exists and waits for a supervisor." },
  { key: "APPROVED / REJECTED", text: "A supervisor decided. Final; checking again creates a new revision." },
];

const SUPPLY_CHECKS = [
  ["Arrived warm", "A chilled item (chicken, fish) arrived above 5°C."],
  ["No cold chain", "The supplier ships a chilled item without cold transport."],
  ["Long time on the road", "Transit from dispatch to the kitchen door is longer than the item allows."],
  ["Past or near use-by", "Stock on the shelf is expired or must be used within a day."],
  ["Low stock", "Stocked items (rice, oil) will run out in under a day and a half."],
  ["Price vs reference", "More than 15% above, or more than 20% below, the reference price. Very cheap stock can mean lower grade."],
  ["Price rising", "The price rose more than 10% across the last seven days."],
  ["Late delivery", "Arrived more than 30 minutes after the agreed time."],
];

const FAQ = [
  {
    q: "The summary or brief says “not available”. Is something broken?",
    a: "No. The summary service could not be reached (for example on a local machine). Every check, signal and required next step still works without it.",
  },
  {
    q: "Where do the reference prices come from?",
    a: "In this demo they are sample values. In production they come from a public price feed such as Bapanas’ Panel Harga Pangan and the kitchen’s own purchasing records.",
  },
  {
    q: "Why can’t I close an incident as unsubstantiated?",
    a: "Three rules protect real patients: only ADMIN can close, there must be at least one integrity signal, and for HIGH or URGENT incidents you must tick that medical follow-up is complete.",
  },
  {
    q: "Does a high integrity score mean the reports are fake?",
    a: "No. It means the reports conflict with delivery records or with each other, so verify first. A real outbreak and fake reports can sit in the same incident; click each signal to see exactly which reports it covers.",
  },
  {
    q: "Is a confidence percentage shown anywhere?",
    a: "No, on purpose. A percentage would suggest more certainty than a photo check has. Every result is marked “not yet reviewed” until a person approves it.",
  },
  {
    q: "What happens to phone numbers and photos in reports?",
    a: "Phone numbers are stored only as a one-way hash, photos only as a fingerprint used to spot reuse, and text is masked before it is summarized.",
  },
];

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20">
      <h2 className="text-[20px] leading-[26px] font-semibold">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Steps({ items }: { items: string[] }) {
  return (
    <ol className="flex flex-col gap-2">
      {items.map((t, n) => (
        <li key={n} className="flex gap-3">
          <span
            aria-hidden
            className="flex size-6 shrink-0 items-center justify-center rounded-full bg-[var(--sunken)] text-[12px] font-semibold"
          >
            {n + 1}
          </span>
          <span className="text-[15px] leading-[22px]">{t}</span>
        </li>
      ))}
    </ol>
  );
}

function OpenLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="mt-3 inline-flex h-10 items-center rounded-[var(--r-control)] border border-[var(--hairline)] bg-[var(--raised)] px-3 text-[14px] font-medium hover:bg-[var(--sunken)]"
    >
      {children} →
    </Link>
  );
}

export default function GuidePage() {
  return (
    <div className="grid gap-8 lg:grid-cols-[200px_minmax(0,1fr)]">
      <nav aria-label="Guide sections" className="hidden lg:block">
        <ul className="sticky top-20 space-y-1">
          {TOC.map((t) => (
            <li key={t.id}>
              <a href={`#${t.id}`} className="block rounded-[var(--r-control)] px-2 py-1.5 text-[14px] text-[var(--ink-2)] hover:bg-[var(--sunken)]">
                {t.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="flex min-w-0 max-w-[820px] flex-col gap-10">
        <header>
          <p className="label text-[var(--brand)]">User guide</p>
          <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">How to use Meal QC</h1>
          <p className="mt-2 text-[15px] leading-[22px] text-[var(--ink-2)]">
            Meal QC tracks every ingredient from supplier to plate, checks every tray before it leaves, and helps
            supervisors handle illness reports fairly. The system checks and explains; people make every decision.
          </p>
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            {[
                            ["Check meals", "A photo per tray shows missing components."],
              ["Review", "A supervisor approves or rejects. Nothing is automatic."],
              ["Illness reports", "Checked against delivery records, traced to ingredient suppliers. Health first."],
            ].map(([t, b]) => (
              <div key={t} className="well p-3">
                <p className="text-[14px] font-semibold">{t}</p>
                <p className="mt-0.5 text-[13px] leading-[18px] text-[var(--ink-2)]">{b}</p>
              </div>
            ))}
          </div>
        </header>

        <Section id="tour" title="5-minute tour">
          <p className="mb-3 text-[15px] leading-[22px] text-[var(--ink-2)]">
            New here? Follow these steps in order. The role and kitchen switches (“Demo as … at …”) are at the top
            right of each page.
          </p>
          <ol className="grid gap-2">
            {TOUR.map((s, n) => (
              <li key={n} className="panel flex gap-3 p-3">
                <span
                  aria-hidden
                  className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[var(--brand)] text-[14px] font-bold text-white"
                >
                  {n + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[15px] font-semibold">{s.title}</p>
                  <p className="mt-0.5 text-[14px] leading-[20px] text-[var(--ink-2)]">{s.body}</p>
                </div>
                <Link href={s.href} className="self-center text-[13px] whitespace-nowrap text-[var(--action)] underline underline-offset-2">
                  {s.page}
                </Link>
              </li>
            ))}
          </ol>
        </Section>

        <Section id="roles" title="Roles: who can do what">
          <p className="mb-3 text-[15px] leading-[22px] text-[var(--ink-2)]">
            Switch roles with <strong>Demo as</strong> at the top of each page. In a real deployment each person signs
            in with one role; the switch exists so you can try every view.
          </p>
          <div className="grid gap-2 sm:grid-cols-3">
            {ROLES.map((r) => (
              <div key={r.role} className="panel p-3">
                <p className="font-mono text-[13px] font-semibold">{r.role}</p>
                <p className="meta">{r.who}</p>
                <p className="mt-2 text-[13px] leading-[18px]">
                  <span className="text-[var(--pass)]">Can:</span> {r.can}
                </p>
                <p className="mt-1 text-[13px] leading-[18px]">
                  <span className="text-[var(--defect)]">Cannot:</span> {r.cannot}
                </p>
              </div>
            ))}
          </div>
        </Section>

        <Section id="crew" title="Check a meal (Crew)">
          <Steps
            items={[
              "Pick the shift and production batch. The list below them shows what every tray must contain.",
              "Press Open camera to photograph the tray, or Choose file to upload one (JPEG/PNG, at least 320×240, up to 4 MB).",
              "Press Run inspection. The result appears in an amber box marked “not yet reviewed”: it is a suggestion until a supervisor reviews it.",
              "If the result is “uncertain”, retake the photo: better light, whole tray in frame, nothing covering the food.",
            ]}
          />
          <OpenLink href="/crew">Open Check meal</OpenLink>
        </Section>

        <Section id="admin" title="Review checks (Supervisor)">
          <Steps
            items={[
              "The tiles at the top count today’s checks by state.",
              "Use the filter buttons on the review queue, then press Open on a row.",
              "Compare the check result with the expected components.",
              "Pick a QC disposition — ACCEPT (send out), HOLD (check again) or REJECT (do not serve) — and press Approve review or Reject review. A rejection needs a comment.",
              "Need a second look? Checking again creates a new revision and keeps the old one in the audit trail.",
            ]}
          />
          <OpenLink href="/admin">Open Review</OpenLink>
        </Section>

        <Section id="report" title="Report an illness (parents, teachers, health workers)">
          <Steps
            items={[
              "If anyone is unwell right now, go to the nearest Puskesmas or call 119 first.",
              "Pick the kitchen, type the school code and the date the meal was eaten.",
              "Tap the symptoms, say when they started and how many people are affected.",
              "Leave a phone number for follow-up. It is stored only as a one-way hash.",
              "Press Send report and keep the reference number.",
            ]}
          />
          <OpenLink href="/report">Open Report illness</OpenLink>
        </Section>

        <Section id="claims" title="Triage illness reports (Supervisor / Admin)">
          <div className="mb-4 rounded-[var(--r-panel)] border border-[var(--defect)] p-3 text-[14px] leading-[20px]">
            <strong>Health first.</strong> Every report is treated as a possible real illness. The tools below decide
            what to verify first — never whether someone gets care.
          </div>
          <Steps
            items={[
              "Reports are grouped into incidents: one kitchen, one meal date. The list is sorted by health priority first.",
              "Read the two numbers on each incident card. The red/amber/green badge is health priority. The bar is the integrity score (0–100): how much the reports conflict with delivery records or with each other.",
              "Open an incident. Click any signal to filter the reports table to just the reports behind it; click again to show all.",
              "Press “Trace this day’s ingredients” to see which lots and suppliers went into those meals.",
              "Press Summarize reports for a plain-English summary and suggested checks. It cannot change the score or close the case.",
              "Follow the Required next steps — they always start with making sure people get medical care.",
              "Record a decision with a reason. Supervisors can escalate or start field verification; only Admin can close.",
            ]}
          />
          <h3 className="mt-6 text-[16px] font-semibold">What the signals mean</h3>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {Object.entries(SIGNAL_COPY).map(([code, s]) => (
              <div key={code} className="well p-3">
                <p className="text-[14px] font-medium">{s.title}</p>
                <p className="mt-0.5 text-[13px] leading-[18px] text-[var(--ink-2)]">{s.explain}</p>
                <p className="mono mt-1 text-[var(--ink-3)]">{code}</p>
              </div>
            ))}
          </div>
          <h3 className="mt-6 text-[16px] font-semibold">Health priority</h3>
          <ul className="mt-2 grid gap-1.5">
            {(Object.keys(HEALTH_COPY) as HealthPriority[]).map((k) => (
              <li key={k} className="text-[14px] leading-[20px]">
                <span className="mr-2 font-mono text-[13px] font-semibold">{k}</span>
                {HEALTH_COPY[k]}
              </li>
            ))}
          </ul>
          <h3 className="mt-6 text-[16px] font-semibold">Decisions</h3>
          <ul className="mt-2 grid gap-1.5">
            {(Object.keys(STATUS_COPY) as IncidentStatus[]).map((k) => (
              <li key={k} className="text-[14px] leading-[20px]">
                <span className="mr-2 font-medium">{STATUS_COPY[k].label}:</span>
                {STATUS_COPY[k].explain}
              </li>
            ))}
          </ul>
          <OpenLink href="/claims">Open Illness reports</OpenLink>
        </Section>

        <Section id="supply" title="Trace ingredients (from an illness report)">
          <Steps
            items={[
              "Open it from an incident in Illness reports with “Trace this day’s ingredients”.",
              "The tiles at the top summarize the last seven days: ingredient cost per portion, spend, average supplier distance, time on the road, on-time deliveries and how many problems need action now.",
              "Read the checks list. It is ordered by priority: food safety first, then stock, cost and distance & time. Each check names the lot and what to do.",
              "Supervisors can press Prepare brief to combine the checks into a short summary with actions.",
              "Pick a date under “Trace a meal” to see every lot used that day: supplier, origin, distance, time on the road, arrival temperature and price.",
              "Use the tabs (Suppliers, Prices, Stock, Deliveries) for the detail, and Record a delivery when a truck arrives.",
            ]}
          />
          <h3 className="mt-6 text-[16px] font-semibold">What the checks mean</h3>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {SUPPLY_CHECKS.map(([t, b]) => (
              <div key={t} className="well p-3">
                <p className="text-[14px] font-medium">{t}</p>
                <p className="mt-0.5 text-[13px] leading-[18px] text-[var(--ink-2)]">{b}</p>
              </div>
            ))}
          </div>
          <OpenLink href="/claims">Open Illness reports</OpenLink>
        </Section>

        <Section id="glossary" title="Glossary">
          <h3 className="text-[16px] font-semibold">Check results</h3>
          <ul className="mt-2 grid gap-1.5">
            {LABELS.map((l) => (
              <li key={l.key} className="text-[14px] leading-[20px]">
                <span className="mr-2 font-mono text-[13px]">{l.key}</span>
                {l.text}
              </li>
            ))}
          </ul>
          <h3 className="mt-5 text-[16px] font-semibold">Review status</h3>
          <ul className="mt-2 grid gap-1.5">
            {REVIEW.map((l) => (
              <li key={l.key} className="text-[14px] leading-[20px]">
                <span className="mr-2 font-mono text-[13px]">{l.key}</span>
                {l.text}
              </li>
            ))}
          </ul>
          <h3 className="mt-5 text-[16px] font-semibold">Colors</h3>
          <ul className="mt-2 grid gap-1.5 text-[14px] leading-[20px]">
            <li>
              <span className="font-medium text-[var(--review)]">Amber</span> — an automatic result or something
              waiting for a person.
            </li>
            <li>
              <span className="font-medium text-[var(--pass)]">Green</span> — approved by a person, or no problem
              found.
            </li>
            <li>
              <span className="font-medium text-[var(--defect)]">Red</span> — rejected, failed, or a health priority.
            </li>
          </ul>
        </Section>

        <Section id="faq" title="FAQ">
          <div className="flex flex-col gap-2">
            {FAQ.map((f) => (
              <details key={f.q} className="panel p-3">
                <summary className="cursor-pointer text-[15px] font-medium">{f.q}</summary>
                <p className="mt-2 text-[14px] leading-[20px] text-[var(--ink-2)]">{f.a}</p>
              </details>
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}
