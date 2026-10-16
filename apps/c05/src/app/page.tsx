import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col gap-4">
      <section>
        <p className="label text-[var(--brand)]">C05 · Food Production Visual QC</p>
        <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">
          One inspection record, three working surfaces.
        </h1>
        <p className="mt-2 max-w-[70ch] text-[15px] leading-[22px] text-[var(--ink-2)]">
          Crew captures a meal photo and asks Gemini to check the expected components against a
          versioned manifest. Supervisors review the evidence and record a QC disposition. The operations
          agent retrieves authorized records only. Nothing is auto-approved, and a photo never proves food
          safety.
        </p>
      </section>

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          { href: "/crew", title: "Field Crew", body: "Capture, validate, run one inspection request." },
          { href: "/admin", title: "Admin Command Center", body: "Real-record KPIs, review queue, immutable audit." },
          { href: "/agent", title: "Operations Agent", body: "Grounded retrieval with confirmed writes only." },
        ].map((c) => (
          <Link key={c.href} href={c.href} className="panel block p-4 transition-colors duration-150 hover:bg-[var(--sunken)]">
            <h2 className="text-[20px] leading-[26px] font-semibold">{c.title}</h2>
            <p className="mt-1 text-[15px] leading-[22px] text-[var(--ink-2)]">{c.body}</p>
          </Link>
        ))}
      </div>

      <section className="panel p-4">
        <h2 className="label">Prerequisites</h2>
        <pre className="mono mt-2 text-[var(--ink-2)]">{`python -m pip install -r requirements.txt
python run.py --project C05 --port 8000   # QC service
npm run dev                              # this app on :3000`}</pre>
      </section>
    </div>
  );
}
