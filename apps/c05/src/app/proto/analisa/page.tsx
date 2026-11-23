"use client";

import { useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Check,
  GitBranch,
  LayoutDashboard,
  ListChecks,
  Minus,
  Moon,
  ShieldCheck,
  Sparkles,
  Sun,
} from "lucide-react";
import {
  CHAIN,
  FLOW,
  KPI,
  MENU_TODAY,
  MENU_WASTE,
  PROPOSALS,
  TRACE_MENUS,
  TREND_MONTH,
  TREND_WEEK,
  type MenuRow,
} from "../_data";
import { GeminiBadge, Logo, ModeSwitch, Snackbar } from "../_components";

type View = "ringkasan" | "usulan" | "trace";

const NAV: { key: View; label: string; icon: typeof LayoutDashboard; role: string }[] = [
  { key: "ringkasan", label: "Ringkasan", icon: LayoutDashboard, role: "Owner" },
  { key: "usulan", label: "Usulan menu", icon: ListChecks, role: "Owner" },
  { key: "trace", label: "Trace", icon: GitBranch, role: "Dinas" },
];

export default function AnalisaPage() {
  const [view, setView] = useState<View>("ringkasan");
  const [dark, setDark] = useState(false);
  const [snack, setSnack] = useState<string | null>(null);
  const [applied, setApplied] = useState(false);

  const showSnack = (text: string) => {
    setSnack(text);
    window.setTimeout(() => setSnack(null), 3400);
  };

  return (
    <div className={`m3 ${dark ? "dark" : ""} flex min-h-dvh`}>
      {/* Navigation rail (≥1024 px) */}
      <aside className="sticky top-0 hidden h-dvh w-24 shrink-0 flex-col items-center gap-3 py-5 lg:flex" style={{ background: "var(--m3-surface)" }}>
        {/* eslint-disable-next-line @next/next/no-img-element -- static logo */}
        <img src="/logo.png" alt="Meal QC" width={36} height={36} className="mb-4 size-9 rounded-[10px]" />
        {NAV.map(({ key, label, icon: Icon }) => (
          <button key={key} type="button" onClick={() => setView(key)} className="flex w-20 flex-col items-center gap-1" aria-current={view === key ? "page" : undefined}>
            <span
              className="grid h-8 w-14 place-items-center rounded-full transition-colors duration-200"
              style={{ background: view === key ? "var(--m3-secondary-container)" : "transparent", color: view === key ? "var(--m3-on-secondary-container)" : "var(--m3-on-surface-variant)" }}
            >
              <Icon className="size-5" />
            </span>
            <span className="t-label-s text-center" style={{ color: view === key ? "var(--m3-on-surface)" : "var(--m3-on-surface-variant)" }}>{label}</span>
          </button>
        ))}
        <button type="button" aria-label={dark ? "Tema terang" : "Tema gelap"} onClick={() => setDark((d) => !d)} className="mt-auto grid size-10 place-items-center rounded-full muted">
          {dark ? <Sun className="size-5" /> : <Moon className="size-5" />}
        </button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="flex flex-wrap items-center gap-3 px-4 pb-2 pt-4 md:px-8 lg:pl-2">
          <span className="lg:hidden"><Logo /></span>
          <span className="t-label-s muted hidden lg:inline">{MENU_TODAY.kitchen} · Mode demo, tanpa login</span>
          <div className="ml-auto flex items-center gap-2">
            <ModeSwitch current="analisa" />
            <button type="button" aria-label={dark ? "Tema terang" : "Tema gelap"} onClick={() => setDark((d) => !d)} className="grid size-10 place-items-center rounded-full muted lg:hidden">
              {dark ? <Sun className="size-5" /> : <Moon className="size-5" />}
            </button>
          </div>
        </header>

        {/* Tabs on small screens */}
        <nav aria-label="Bagian" className="flex gap-1 overflow-x-auto px-4 lg:hidden">
          {NAV.map(({ key, label }) => (
            <button key={key} type="button" className="chip shrink-0" aria-pressed={view === key} onClick={() => setView(key)}>
              {label}
            </button>
          ))}
        </nav>

        <main className="flex-1 px-4 pb-16 pt-4 md:px-8 lg:pl-2">
          <div className="mx-auto max-w-[1360px]" key={view}>
            {view === "ringkasan" ? <Ringkasan onOpenUsulan={() => setView("usulan")} applied={applied} /> : null}
            {view === "usulan" ? (
              <Usulan
                applied={applied}
                onApply={(n) => {
                  setApplied(true);
                  showSnack(`Menu minggu depan diperbarui · ${n} perubahan`);
                }}
              />
            ) : null}
            {view === "trace" ? <Trace /> : null}
          </div>
        </main>
      </div>

      {snack ? <Snackbar>{snack}</Snackbar> : null}
    </div>
  );
}

/* ---------------------------------------------------------------- O1 */

function Ringkasan({ onOpenUsulan, applied }: { onOpenUsulan: () => void; applied: boolean }) {
  const [range, setRange] = useState<"minggu" | "bulan">("minggu");
  const trend = range === "minggu" ? TREND_WEEK : TREND_MONTH;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-x-8 gap-y-4">
        <div className="anim-rise">
          <h1 className="text-[36px] leading-[44px] font-normal tracking-[-0.25px] md:text-[45px] md:leading-[52px]">Ringkasan dapur</h1>
          <div className="mt-2 flex items-center gap-3">
            <div className="seg" role="group" aria-label="Rentang waktu">
              <button type="button" aria-pressed={range === "minggu"} onClick={() => setRange("minggu")}>Minggu ini</button>
              <button type="button" aria-pressed={range === "bulan"} onClick={() => setRange("bulan")}>Bulan ini</button>
            </div>
            <span className="t-body muted hidden sm:inline">16–20 Nov 2026 · {KPI.schools} sekolah</span>
          </div>
        </div>
        <div className="ml-auto flex gap-8">
          <Kpi value={`${KPI.waste}%`} label="Sisa makanan" delta={`${KPI.wasteDelta} poin`} good i={1} />
          <Kpi value={applied ? "0" : `${KPI.menusToReview}`} label="Menu perlu ditinjau" delta={applied ? "sudah diterapkan" : "di atas 40% sisa"} i={2} />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        {/* Gauge */}
        <section className="card anim-rise flex flex-col p-5 lg:col-span-4" style={{ "--i": 1 } as React.CSSProperties}>
          <CardHead title="Makanan yang dimakan" />
          <div className="flex flex-1 flex-col items-center justify-center gap-2 py-2">
            <Gauge value={KPI.eaten} />
            <p className="t-body muted">{(KPI.cartridges * KPI.eaten) / 100 | 0} dari {KPI.cartridges.toLocaleString("id-ID")} porsi habis dimakan</p>
          </div>
        </section>

        {/* Menu list with popover */}
        <section className="card anim-rise p-5 lg:col-span-4" style={{ "--i": 2 } as React.CSSProperties}>
          <CardHead title="Sisa per menu" hint="Arahkan kursor untuk detail sekolah" />
          <ul className="mt-3 flex flex-col">
            {MENU_WASTE.map((m, i) => (
              <MenuItem key={m.menu} row={m} i={i} />
            ))}
          </ul>
        </section>

        {/* Insight */}
        <section
          className="anim-rise flex flex-col gap-3 rounded-[16px] p-5 lg:col-span-4"
          style={{ background: "var(--m3-primary-container)", color: "var(--m3-on-primary-container)", "--i": 3 } as React.CSSProperties}
        >
          <div className="flex items-center gap-2">
            <Sparkles className="size-5" />
            <p className="t-title">Insight Gemini</p>
          </div>
          <p className="text-[20px] leading-[28px]">
            Sayur bening bayam sisa <b>68%</b> dalam 5 hari terakhir, terutama di SD. Pertimbangkan <b>tumis buncis wortel</b>: bahan musiman dari supplier 12 km.
          </p>
          <ul className="t-body flex flex-col gap-1 opacity-90">
            <li>· Tumis labu siam sisa 54%, keluhan rasa hambar dari 3 kelas</li>
            <li>· Lauk ayam hampir selalu habis (sisa 9%)</li>
          </ul>
          <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-2">
            <GeminiBadge />
            <button type="button" className="btn-filled" onClick={onOpenUsulan}>
              {applied ? "Lihat menu baru" : "Lihat usulan menu"}
            </button>
          </div>
        </section>

        {/* Flow ribbon */}
        <section className="card anim-rise p-5 lg:col-span-7" style={{ "--i": 4 } as React.CSSProperties}>
          <CardHead title="Alur porsi hari ini" hint="Dimasak → Sisa" />
          <FlowRibbon />
        </section>

        {/* Trend */}
        <section className="card anim-rise p-5 lg:col-span-5" style={{ "--i": 5 } as React.CSSProperties}>
          <CardHead title="Tren sisa makanan" hint={range === "minggu" ? "per hari" : "per minggu"} />
          <TrendChart key={range} data={trend} />
        </section>
      </div>
    </div>
  );
}

function Kpi({ value, label, delta, good, i }: { value: string; label: string; delta: string; good?: boolean; i: number }) {
  return (
    <div className="anim-rise text-right" style={{ "--i": i } as React.CSSProperties}>
      <p className="t-display">{value}</p>
      <p className="t-label muted">{label}</p>
      <p className="t-label-s" style={{ color: good ? "var(--m3-primary)" : "var(--m3-tertiary)" }}>{delta}</p>
    </div>
  );
}

function CardHead({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <h2 className="t-title">{title}</h2>
      {hint ? <span className="t-label-s muted">{hint}</span> : null}
    </div>
  );
}

function Gauge({ value }: { value: number }) {
  // 240° arc gauge, value fills from left.
  const r = 80, cx = 100, cy = 100, start = 150, sweep = 240;
  // Rounded so server and client render identical path strings (no hydration drift).
  const round = (n: number) => Math.round(n * 100) / 100;
  const pt = (deg: number) => [round(cx + r * Math.cos((deg * Math.PI) / 180)), round(cy + r * Math.sin((deg * Math.PI) / 180))];
  const arc = (from: number, to: number) => {
    const [x1, y1] = pt(from), [x2, y2] = pt(to);
    return `M${x1} ${y1} A${r} ${r} 0 ${to - from > 180 ? 1 : 0} 1 ${x2} ${y2}`;
  };
  const end = start + (sweep * value) / 100;
  const len = Math.round((2 * Math.PI * r * sweep * value) / 36000);
  return (
    <svg viewBox="0 0 200 170" className="w-full max-w-[240px]" role="img" aria-label={`${value}% makanan dimakan`}>
      <defs>
        <linearGradient id="g-gauge" x1="0" x2="1">
          <stop offset="0" stopColor="#e07a2e" />
          <stop offset="0.5" stopColor="#c9b23b" />
          <stop offset="1" stopColor="var(--m3-primary)" />
        </linearGradient>
      </defs>
      <path d={arc(start, start + sweep)} fill="none" stroke="var(--m3-surface-high)" strokeWidth="14" strokeLinecap="round" />
      <path d={arc(start, end)} fill="none" stroke="url(#g-gauge)" strokeWidth="14" strokeLinecap="round" className="anim-draw" style={{ "--len": len } as React.CSSProperties} />
      <text x="100" y="104" textAnchor="middle" fontSize="40" fill="var(--m3-on-surface)">{value}%</text>
      <text x="100" y="128" textAnchor="middle" fontSize="12" fill="var(--m3-on-surface-variant)">dimakan</text>
    </svg>
  );
}

function MenuItem({ row, i }: { row: MenuRow; i: number }) {
  const [open, setOpen] = useState(false);
  const TrendIcon = row.trend === "naik" ? ArrowUpRight : row.trend === "turun" ? ArrowDownRight : Minus;
  const high = row.waste >= 40;
  return (
    <li
      className="anim-rise relative"
      style={{ "--i": i + 2 } as React.CSSProperties}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="flex w-full items-center gap-3 rounded-[12px] px-2 py-2.5 text-left transition-colors duration-150"
        style={{ background: open ? "var(--m3-surface-container)" : "transparent" }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        aria-expanded={open}
      >
        <span className="size-2.5 shrink-0 rounded-full" style={{ background: high ? "var(--m3-tertiary)" : "var(--m3-primary)" }} />
        <span className="t-body min-w-0 flex-1 truncate">{row.menu}</span>
        <TrendIcon className="size-4 muted" aria-label={`tren ${row.trend}`} />
        <span className="t-label w-12 text-right" style={{ color: high ? "var(--m3-tertiary)" : "var(--m3-on-surface)" }}>{row.waste}%</span>
      </button>
      {open ? (
        <div
          role="tooltip"
          className="anim-fade absolute right-0 top-full z-30 mt-1 w-[260px] rounded-[16px] p-4 shadow-[var(--m3-shadow-3)]"
          style={{ background: "#141a16", color: "#e8ede9" }}
        >
          <p className="text-[24px] leading-[28px] font-medium">{row.waste}%</p>
          <p className="text-[12px] text-white/70">{row.menu} · sisa rata-rata</p>
          <div className="mt-3 flex flex-col gap-2">
            {row.schools.map((s) => (
              <div key={s.name} className="flex items-center gap-2 text-[12px]">
                <span className="w-[110px] truncate text-white/80">{s.name}</span>
                <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/15">
                  <span className="block h-full rounded-full" style={{ width: `${s.waste}%`, background: s.waste >= 40 ? "#ff9b54" : "#8fd8aa" }} />
                </span>
                <span className="w-8 text-right">{s.waste}%</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </li>
  );
}

function FlowRibbon() {
  const W = 640, H = 170, top = 20, maxH = 110;
  const max = FLOW[0].value;
  const xs = FLOW.map((_, i) => 30 + (i * (W - 60)) / (FLOW.length - 1));
  const hs = FLOW.map((f) => (f.value / max) * maxH);
  const mid = top + maxH / 2;
  // Smooth ribbon through each stage, thickness = portions at that stage.
  let d = `M${xs[0]} ${mid - hs[0] / 2}`;
  for (let i = 1; i < xs.length; i++) {
    const cx = (xs[i - 1] + xs[i]) / 2;
    d += ` C${cx} ${mid - hs[i - 1] / 2} ${cx} ${mid - hs[i] / 2} ${xs[i]} ${mid - hs[i] / 2}`;
  }
  d += ` L${xs.at(-1)} ${mid + hs.at(-1)! / 2}`;
  for (let i = xs.length - 1; i > 0; i--) {
    const cx = (xs[i - 1] + xs[i]) / 2;
    d += ` C${cx} ${mid + hs[i] / 2} ${cx} ${mid + hs[i - 1] / 2} ${xs[i - 1]} ${mid + hs[i - 1] / 2}`;
  }
  d += " Z";
  return (
    <div className="mt-3">
      <div className="grid grid-cols-4 gap-2">
        {FLOW.map((f, i) => (
          <div key={f.stage} className="anim-rise" style={{ "--i": i } as React.CSSProperties}>
            <p className="text-[22px] leading-[28px] md:text-[28px] md:leading-[36px]">{f.value.toLocaleString("id-ID")}</p>
            <p className="t-label">{f.stage}</p>
            <p className="t-label-s muted">{f.note}</p>
          </div>
        ))}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full" role="img" aria-label="Alur porsi dari dimasak sampai sisa">
        <defs>
          <linearGradient id="g-flow" x1="0" x2="1">
            <stop offset="0" stopColor="#3fae5f" />
            <stop offset="0.45" stopColor="#9fc94a" />
            <stop offset="0.75" stopColor="#f0a03c" />
            <stop offset="1" stopColor="#e4572e" />
          </linearGradient>
        </defs>
        <path d={d} fill="url(#g-flow)" opacity="0.9" className="anim-fade" />
        {xs.map((x, i) => (
          <line key={i} x1={x} x2={x} y1={top - 6} y2={top + maxH + 6} stroke="var(--m3-on-surface)" strokeOpacity="0.35" strokeDasharray="3 4" />
        ))}
      </svg>
    </div>
  );
}

function TrendChart({ data }: { data: { day: string; waste: number }[] }) {
  const W = 420, H = 180, padL = 28, padB = 26, padT = 12;
  const lo = 20, hi = 40;
  const X = (i: number) => padL + (i * (W - padL - 16)) / (data.length - 1);
  const Y = (v: number) => padT + ((hi - v) / (hi - lo)) * (H - padT - padB);
  const d = data.map((p, i) => `${i ? "L" : "M"}${X(i)} ${Y(p.waste)}`).join(" ");
  const last = data.at(-1)!;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 w-full" role="img" aria-label={`Sisa makanan turun ke ${last.waste}%`}>
      {[20, 30, 40].map((t) => (
        <g key={t}>
          <line x1={padL} x2={W - 8} y1={Y(t)} y2={Y(t)} stroke="var(--m3-outline-variant)" strokeDasharray="2 4" />
          <text x={padL - 6} y={Y(t) + 4} textAnchor="end" fontSize="11" fill="var(--m3-on-surface-variant)">{t}%</text>
        </g>
      ))}
      <path d={d} fill="none" stroke="var(--m3-primary)" strokeWidth="2.5" strokeLinejoin="round" className="anim-draw" style={{ "--len": 600 } as React.CSSProperties} />
      {data.map((p, i) => (
        <g key={p.day}>
          <circle cx={X(i)} cy={Y(p.waste)} r={i === data.length - 1 ? 5 : 3.5} fill={i === data.length - 1 ? "var(--m3-primary)" : "var(--m3-surface-card)"} stroke="var(--m3-primary)" strokeWidth="2" />
          <text x={X(i)} y={H - 6} textAnchor="middle" fontSize="11" fill="var(--m3-on-surface-variant)">{p.day}</text>
        </g>
      ))}
      <g transform={`translate(${X(data.length - 1) - 58} ${Y(last.waste) - 34})`}>
        <rect width="64" height="24" rx="12" fill="var(--m3-inverse-surface)" />
        <text x="32" y="16" textAnchor="middle" fontSize="12" fill="var(--m3-inverse-on-surface)">{last.waste}% sisa</text>
      </g>
    </svg>
  );
}

/* ---------------------------------------------------------------- O2 */

function Usulan({ applied, onApply }: { applied: boolean; onApply: (n: number) => void }) {
  const [on, setOn] = useState<Record<string, boolean>>(() => Object.fromEntries(PROPOSALS.map((p) => [p.id, true])));
  const [confirm, setConfirm] = useState(false);
  const chosen = PROPOSALS.filter((p) => on[p.id]);
  const removes = chosen.filter((p) => p.kind === "remove").length;
  const adds = chosen.filter((p) => p.kind === "add").length;

  return (
    <div className="flex flex-col gap-4">
      <div className="anim-rise">
        <h1 className="text-[36px] leading-[44px] md:text-[45px] md:leading-[52px]">Usulan perubahan menu</h1>
        <p className="t-body muted mt-1">Minggu depan, 30 Nov – 4 Des 2026 · klik baris untuk memilih</p>
      </div>

      <section className="card anim-rise overflow-hidden" style={{ "--i": 1 } as React.CSSProperties}>
        <div className="flex flex-wrap items-center justify-between gap-2 px-5 py-4">
          <h2 className="t-title">Usulan dari Gemini</h2>
          <GeminiBadge reviewed={applied ? "owner, 23 Nov" : undefined} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-t t-body" style={{ borderColor: "var(--m3-outline-variant)" }}>
            <thead>
              <tr className="t-label muted text-left">
                <th className="px-5 py-3 font-medium">Menu</th>
                <th className="px-3 py-3 font-medium">Alasan</th>
                <th className="px-3 py-3 font-medium">Gizi</th>
                <th className="px-3 py-3 font-medium">Supplier</th>
                <th className="px-3 py-3 text-right font-medium">Jarak</th>
                <th className="w-14 px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {PROPOSALS.map((p, i) => {
                const active = on[p.id];
                const tone = p.kind === "remove" ? "var(--m3-error)" : "var(--m3-primary)";
                const bg = p.kind === "remove" ? "var(--m3-error-container)" : "var(--m3-primary-container)";
                return (
                  <tr
                    key={p.id}
                    onClick={() => !applied && setOn((c) => ({ ...c, [p.id]: !c[p.id] }))}
                    className="anim-rise cursor-pointer border-t transition-colors duration-200"
                    style={{ borderColor: "var(--m3-outline-variant)", background: active ? `color-mix(in srgb, ${bg} 70%, transparent)` : "transparent", "--i": i + 2 } as React.CSSProperties}
                  >
                    <td className="px-5 py-3">
                      <span className="t-label" style={{ color: active ? tone : "var(--m3-on-surface)", textDecoration: active && p.kind === "remove" ? "line-through" : "none" }}>
                        {p.kind === "remove" ? "Hapus · " : "Tambah · "}
                        {p.menu}
                      </span>
                    </td>
                    <td className="max-w-[280px] px-3 py-3">{p.reason}</td>
                    <td className="px-3 py-3 muted">{p.nutrition}</td>
                    <td className="px-3 py-3">{p.supplier}</td>
                    <td className="px-3 py-3 text-right">{p.distanceKm} km</td>
                    <td className="px-5 py-3 text-right">
                      <span
                        role="checkbox"
                        aria-checked={active}
                        aria-label={`Sertakan ${p.menu}`}
                        className="inline-grid size-5 place-items-center rounded-[4px] border-2 transition-colors duration-200"
                        style={{ borderColor: active ? tone : "var(--m3-outline)", background: active ? tone : "transparent", color: "#fff" }}
                      >
                        {active ? <Check className="size-3.5" strokeWidth={3} /> : null}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t px-5 py-4" style={{ borderColor: "var(--m3-outline-variant)" }}>
          <p className="t-body muted">
            {removes} dihapus · {adds} ditambah. Saran AI; keputusan dan tanggung jawab ada pada owner.
          </p>
          <button type="button" className="btn-filled" disabled={applied || chosen.length === 0} onClick={() => setConfirm(true)}>
            {applied ? <><Check className="size-4" /> Sudah diterapkan</> : `Terapkan ${chosen.length} perubahan`}
          </button>
        </div>
      </section>

      {confirm ? (
        <div className="fixed inset-0 z-40 grid place-items-center p-4 anim-fade" style={{ background: "var(--m3-scrim)" }} onClick={() => setConfirm(false)}>
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="dlg-title"
            className="anim-pop w-full max-w-[400px] rounded-[28px] p-6 shadow-[var(--m3-shadow-3)]"
            style={{ background: "var(--m3-surface-high)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="dlg-title" className="t-headline">Terapkan {chosen.length} perubahan?</h2>
            <p className="t-body muted mt-3">
              Menu minggu depan diperbarui dan supplier menerima pesanan baru. Keputusan ini dicatat di audit log atas nama Anda.
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" className="btn-text" onClick={() => setConfirm(false)}>Batal</button>
              <button
                type="button"
                className="btn-filled"
                onClick={() => {
                  setConfirm(false);
                  onApply(chosen.length);
                }}
              >
                Terapkan
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

/* ---------------------------------------------------------------- D1 */

function Trace() {
  const [preset, setPreset] = useState("7 hari");
  const [selected, setSelected] = useState(TRACE_MENUS[0].id);
  const [verified, setVerified] = useState(0); // nodes confirmed so far
  const [running, setRunning] = useState(false);
  const item = TRACE_MENUS.find((t) => t.id === selected)!;

  const verify = () => {
    setRunning(true);
    setVerified(0);
    CHAIN.forEach((_, i) => {
      window.setTimeout(() => {
        setVerified(i + 1);
        if (i === CHAIN.length - 1) setRunning(false);
      }, 180 * (i + 1));
    });
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="anim-rise flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[36px] leading-[44px] md:text-[45px] md:leading-[52px]">Telusuri asal-usul</h1>
          <p className="t-body muted mt-1">Dinas · dari menu bermasalah sampai lot supplier</p>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Rentang tanggal">
          {["Hari ini", "7 hari", "Bulan ini"].map((p) => (
            <button key={p} type="button" className="chip" aria-pressed={preset === p} onClick={() => setPreset(p)}>
              {preset === p ? <Check className="size-4" /> : null}
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <section className="card anim-rise p-2 lg:col-span-4" style={{ "--i": 1 } as React.CSSProperties}>
          <p className="t-label muted px-3 pb-1 pt-3">Menu bermasalah</p>
          <ul>
            {TRACE_MENUS.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => {
                    setSelected(t.id);
                    setVerified(0);
                  }}
                  className="flex w-full items-center gap-3 rounded-[12px] px-3 py-3 text-left transition-colors duration-150"
                  style={{ background: selected === t.id ? "var(--m3-secondary-container)" : "transparent" }}
                  aria-current={selected === t.id ? "true" : undefined}
                >
                  <div className="min-w-0 flex-1">
                    <p className="t-label">{t.menu}</p>
                    <p className="t-body muted">{t.date}</p>
                  </div>
                  <span className="rounded-[8px] px-2 py-1 t-label-s" style={{ background: "var(--m3-tertiary-container)", color: "var(--m3-on-tertiary-container)" }}>{t.issue}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="card anim-rise p-5 lg:col-span-8" style={{ "--i": 2 } as React.CSSProperties} key={selected}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="t-title">{item.menu}</h2>
              <p className="t-body muted">{item.date} · {CHAIN.length} catatan berantai hash</p>
            </div>
            {verified === CHAIN.length ? (
              <span className="anim-pop inline-flex items-center gap-2 rounded-full px-4 py-2 t-label" style={{ background: "var(--m3-primary-container)", color: "var(--m3-on-primary-container)" }}>
                <ShieldCheck className="size-5" /> Rantai terverifikasi
              </span>
            ) : (
              <button type="button" className="btn-filled" onClick={verify} disabled={running}>
                <ShieldCheck className="size-4" /> {running ? "Memverifikasi…" : "Verifikasi rantai"}
              </button>
            )}
          </div>

          <ol className="relative mt-5">
            {CHAIN.map((n, i) => {
              const ok = i < verified;
              return (
                <li key={n.id} className="anim-rise relative flex gap-4 pb-5 last:pb-0" style={{ "--i": i } as React.CSSProperties}>
                  {i < CHAIN.length - 1 ? (
                    <span className="absolute left-[15px] top-8 h-[calc(100%-24px)] w-0.5" style={{ background: ok ? "var(--m3-primary)" : "var(--m3-outline-variant)", transition: "background-color 200ms" }} />
                  ) : null}
                  <span
                    className="relative z-10 grid size-8 shrink-0 place-items-center rounded-full border-2 transition-colors duration-200"
                    style={{ borderColor: ok ? "var(--m3-primary)" : "var(--m3-outline)", background: ok ? "var(--m3-primary)" : "var(--m3-surface-card)", color: ok ? "var(--m3-on-primary)" : "var(--m3-on-surface-variant)" }}
                  >
                    {ok ? <Check className="size-4" strokeWidth={3} /> : <span className="t-label-s">{i + 1}</span>}
                  </span>
                  <div className="min-w-0 flex-1 rounded-[12px] px-4 py-3" style={{ background: "var(--m3-surface-low)" }}>
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <p className="t-label">{n.title}</p>
                      <code className="t-label-s muted">#{n.hash}</code>
                    </div>
                    <p className="t-body">{n.detail}</p>
                    <p className="t-label-s muted">{n.meta}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>
      </div>
    </div>
  );
}
