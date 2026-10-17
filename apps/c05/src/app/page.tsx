import Link from "next/link";

const GAPS = [
  {
    stage: "Before cooking",
    title: "Nobody knows where the ingredients came from.",
    body: "Deliveries are not recorded per lot. When people fall ill, no one can say which supplier, how long the food travelled or how warm it arrived. Price rises, long routes and running-out stock stay invisible until money or food is lost.",
  },
  {
    stage: "Before serving",
    title: "Meals are checked by eye and not recorded.",
    body: "Quality control happens under time pressure and leaves no trace. A missing protein or vegetable is noticed only after someone has eaten.",
  },
  {
    stage: "After serving",
    title: "Illness reports cannot be checked quickly.",
    body: "Real outbreaks arrive mixed with inflated or copy-pasted claims. Without delivery and ingredient records, sick children wait or kitchens are blamed unfairly.",
  },
];

const GOALS = [
  {
    title: "Every ingredient traceable",
    body: "Each lot carries its supplier, origin, distance, time on the road, arrival temperature and price. Any meal traces back to its suppliers in one click.",
  },
  {
    title: "Insights, not just records",
    body: "Automatic checks point out what matters: warm deliveries, expiring stock, prices above reference, distant suppliers, late trucks.",
  },
  {
    title: "People decide, everything is recorded",
    body: "The system suggests and explains. Supervisors accept, hold or escalate, and every step lands in the audit trail.",
  },
];

const STEPS = [
  { href: "/crew", stage: "Before serving", who: "Kitchen crew", title: "Check meal", body: "Photograph a tray and see which components are present or missing." },
  { href: "/admin", stage: "Before serving", who: "Supervisor", title: "Review", body: "Accept, hold or reject the batch. Nothing is approved automatically." },
  { href: "/report", stage: "After serving", who: "Parent or school", title: "Report illness", body: "A two-minute public form that points to the Puskesmas / 119 first." },
  { href: "/claims", stage: "After serving", who: "Supervisor or admin", title: "Triage reports", body: "Check reports against delivery records and trace that day's ingredients back to their suppliers." },
];

const AUDIENCES = ["MBG school-meal kitchens (SPPG)", "Restaurants and catering", "Food and beverage producers", "Central kitchens and franchises"];

export default function Home() {
  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-8">
      <section>
        <p className="label text-[var(--brand)]">Food quality control and ingredient traceability</p>
        <h1 className="mt-1 max-w-[30ch] text-[30px] leading-[36px] font-semibold">
          Know what went into every meal: where it came from, how it arrived, and what it cost.
        </h1>
        <p className="mt-2 max-w-[75ch] text-[15px] leading-[22px] text-[var(--ink-2)]">
          Meal QC traces every ingredient lot from supplier to plate, checks each delivery and each tray, and turns
          the records into insights. It is built first for Indonesia&rsquo;s free school-meal programme
          (MBG), where food-poisoning cases made traceability urgent, and works the same way for any food or drink
          business that needs to keep its raw materials in check.
        </p>
        <ul className="mt-3 flex flex-wrap gap-1.5" aria-label="Who it is for">
          {AUDIENCES.map((a) => (
            <li key={a} className="rounded-full border border-[var(--hairline)] bg-[var(--raised)] px-2.5 py-1 text-[13px]">
              {a}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="gap">
        <h2 id="gap" className="text-[18px] font-semibold">
          The problem
        </h2>
        <div className="mt-2 grid gap-3 md:grid-cols-3">
          {GAPS.map((g) => (
            <div key={g.stage} className="panel p-4" style={{ borderLeft: "4px solid var(--defect)" }}>
              <p className="meta">{g.stage}</p>
              <p className="mt-1 text-[17px] leading-[24px] font-semibold">{g.title}</p>
              <p className="mt-1 text-[14px] leading-[21px] text-[var(--ink-2)]">{g.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="goal" className="panel p-4" style={{ borderLeft: "4px solid var(--pass)" }}>
        <h2 id="goal" className="text-[18px] font-semibold">
          The goal
        </h2>
        <ul className="mt-2 grid gap-3 text-[14px] leading-[21px] sm:grid-cols-3">
          {GOALS.map((g) => (
            <li key={g.title}>
              <strong className="block">{g.title}</strong>
              <span className="text-[var(--ink-2)]">{g.body}</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="how">
        <h2 id="how" className="text-[18px] font-semibold">
          How it works: four steps
        </h2>
        <ol className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <li key={s.href}>
              <Link
                href={s.href}
                className="panel flex h-full flex-col p-4 transition-colors duration-150 hover:bg-[var(--sunken)]"
              >
                <span className="meta">{s.stage}</span>
                <span className="mt-1.5 flex items-center gap-2">
                  <span
                    aria-hidden
                    className="flex size-6 shrink-0 items-center justify-center rounded-full bg-[var(--brand)] text-[12px] font-bold text-white"
                  >
                    {i + 1}
                  </span>
                  <span className="text-[18px] leading-[24px] font-semibold">{s.title}</span>
                </span>
                <span className="meta mt-1">{s.who}</span>
                <span className="mt-1 flex-1 text-[14px] leading-[20px] text-[var(--ink-2)]">{s.body}</span>
                <span className="mt-3 text-[14px] font-medium text-[var(--action)]">Open →</span>
              </Link>
            </li>
          ))}
        </ol>
        <p className="mt-3 text-[14px] leading-[20px] text-[var(--ink-2)]">
          First time here?{" "}
          <Link href="/guide" className="font-medium text-[var(--action)] underline underline-offset-2">
            Read the 5-minute guide
          </Link>
          .
        </p>
      </section>
    </div>
  );
}
