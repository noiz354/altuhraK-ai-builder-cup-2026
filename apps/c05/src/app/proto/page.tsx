import Link from "next/link";
import { BarChart3, GitBranch, ScanLine, Soup, UtensilsCrossed, ListChecks } from "lucide-react";

const ROLES = [
  { href: "/proto/scan", icon: Soup, role: "Kru dapur", task: "Foto cartridge sebelum dikirim", mode: "HP" },
  { href: "/proto/scan", icon: UtensilsCrossed, role: "Guru", task: "Foto cartridge setelah makan", mode: "HP" },
  { href: "/proto/analisa", icon: ListChecks, role: "Owner dapur", task: "Lihat sisa makanan & ganti menu", mode: "Web" },
  { href: "/proto/analisa", icon: GitBranch, role: "Dinas", task: "Telusuri sampai supplier", mode: "Web" },
];

export default function ProtoHome() {
  return (
    <div className="m3 min-h-dvh">
      <main className="mx-auto flex max-w-[1080px] flex-col gap-10 px-4 py-10 md:px-8 md:py-16">
        <header className="anim-rise flex flex-col gap-3">
          <span className="flex items-center gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element -- static logo */}
            <img src="/logo.png" alt="" width={36} height={36} className="size-9 rounded-[10px]" />
            <span className="t-title">Meal QC</span>
            <span className="badge-ai ml-2">Prototipe UI</span>
          </span>
          <h1 className="text-[36px] leading-[44px] md:text-[57px] md:leading-[64px] md:tracking-[-0.25px]">Masuk sebagai</h1>
          <p className="t-body-l muted max-w-[620px]">
            Satu aplikasi, dua mode: <b>Scan</b> di HP untuk kru dapur dan guru, <b>Analisa</b> di web untuk owner dan dinas. Mode demo, tanpa login.
          </p>
        </header>

        <div className="grid gap-4 sm:grid-cols-2">
          {[
            { href: "/proto/scan", icon: ScanLine, title: "Scan", sub: "Tampilan mobile · foto before & after", tone: "primary" },
            { href: "/proto/analisa", icon: BarChart3, title: "Analisa", sub: "Tampilan web · dashboard, usulan menu, trace", tone: "secondary" },
          ].map((m, i) => (
            <Link
              key={m.title}
              href={m.href}
              className="anim-rise group flex items-center gap-5 rounded-[28px] p-6 transition-shadow duration-200 hover:shadow-[var(--m3-shadow-3)]"
              style={{
                background: m.tone === "primary" ? "var(--m3-primary-container)" : "var(--m3-secondary-container)",
                color: m.tone === "primary" ? "var(--m3-on-primary-container)" : "var(--m3-on-secondary-container)",
                "--i": i + 1,
              } as React.CSSProperties}
            >
              <span className="grid size-16 shrink-0 place-items-center rounded-[20px] transition-transform duration-300 group-hover:scale-105" style={{ background: "var(--m3-surface-card)" }}>
                <m.icon className="size-8" style={{ color: "var(--m3-primary)" }} />
              </span>
              <span>
                <span className="block text-[28px] leading-[36px]">{m.title}</span>
                <span className="t-body">{m.sub}</span>
              </span>
            </Link>
          ))}
        </div>

        <section className="flex flex-col gap-3">
          <h2 className="t-title muted">Peran</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {ROLES.map((r, i) => (
              <Link
                key={r.role}
                href={r.href}
                className="card anim-rise flex flex-col gap-3 p-5 transition-colors duration-200 hover:bg-[var(--m3-surface-low)]"
                style={{ "--i": i + 3 } as React.CSSProperties}
              >
                <span className="flex items-center justify-between">
                  <span className="grid size-10 place-items-center rounded-full" style={{ background: "var(--m3-surface-container)" }}>
                    <r.icon className="size-5" style={{ color: "var(--m3-primary)" }} />
                  </span>
                  <span className="t-label-s muted">{r.mode}</span>
                </span>
                <span className="t-title">{r.role}</span>
                <span className="t-body muted">{r.task}</span>
              </Link>
            ))}
          </div>
        </section>

        <p className="t-label-s muted">Data demo sintetis. Hasil analisis di prototipe ini adalah simulasi; keputusan selalu di tangan manusia.</p>
      </main>
    </div>
  );
}
