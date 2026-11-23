"use client";

import { useRef, useState } from "react";
import { Camera, Check, ChevronLeft, ImageIcon, RotateCcw, Send, Soup, Truck, UtensilsCrossed } from "lucide-react";
import { AFTER_RESULT, BEFORE_RESULT, CLASSES, MENU_TODAY, type QuadrantState } from "../_data";
import { GeminiBadge, Logo, ModeSwitch, QUAD_BOX, Snackbar } from "../_components";

type Role = "kru" | "guru";
type Step = "receive" | "camera" | "preview" | "analyzing" | "result";

const STATE_STYLE: Record<QuadrantState, { color: string; bg: string; label: string }> = {
  complete: { color: "var(--m3-primary)", bg: "var(--m3-primary-container)", label: "Lengkap" },
  short: { color: "var(--m3-tertiary)", bg: "var(--m3-tertiary-container)", label: "Kurang" },
  unsure: { color: "var(--m3-outline)", bg: "var(--m3-surface-high)", label: "Ragu" },
};

const WEIGHTS = { Q1: 0.3, Q2: 0.3, Q3: 0.25, Q4: 0.15 } as const;

export default function ScanPage() {
  const [role, setRole] = useState<Role>("kru");
  const [step, setStep] = useState<Step>("camera");
  const [photo, setPhoto] = useState<string | null>(null);
  const [usedSample, setUsedSample] = useState(true);
  const [refilled, setRefilled] = useState(false);
  const [received, setReceived] = useState(false);
  const [cls, setCls] = useState("4C");
  const [reasons, setReasons] = useState<string[]>([]);
  const [split, setSplit] = useState(50);
  const [snack, setSnack] = useState<string | null>(null);
  const [flash, setFlash] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);

  const switchRole = (r: Role) => {
    setRole(r);
    setPhoto(null);
    setReasons([]);
    setStep(r === "guru" && !received ? "receive" : "camera");
  };

  const takePhoto = (src: string, sample: boolean) => {
    setPhoto(src);
    setUsedSample(sample);
    setFlash((f) => f + 1);
    setStep("preview");
  };

  const sampleFor = () => {
    if (role === "guru") return "/proto/tray-after.svg";
    return refilled ? "/proto/tray-before-full.svg" : "/proto/tray-before-missing.svg";
  };

  const analyze = () => {
    setStep("analyzing");
    window.setTimeout(() => setStep("result"), 2200);
  };

  const showSnack = (text: string) => {
    setSnack(text);
    window.setTimeout(() => setSnack(null), 3200);
  };

  const beforeResult = refilled
    ? BEFORE_RESULT.map((q) => ({ ...q, state: "complete" as QuadrantState, note: q.key === "Q3" ? "Sayur terisi sesuai manifest" : q.note }))
    : BEFORE_RESULT;
  const shortQuad = beforeResult.find((q) => q.state === "short");
  const wasteTotal = Math.round(AFTER_RESULT.reduce((s, q) => s + q.left * WEIGHTS[q.key], 0));
  const worst = [...AFTER_RESULT].sort((a, b) => b.left - a.left)[0];
  const quadName = (k: string) => MENU_TODAY.quadrants.find((q) => q.key === k)!;

  return (
    <div className="m3 flex min-h-dvh justify-center md:items-center md:py-8" style={{ background: "var(--m3-surface-dim)" }}>
      <div className="hidden w-[300px] flex-col gap-4 self-center pr-10 lg:flex">
        <ModeSwitch current="scan" />
        <p className="t-headline">Mode scan</p>
        <p className="t-body muted">
          Tampilan HP untuk kru dapur dan guru. Buka alamat ini di HP pada jaringan yang sama, atau perkecil jendela browser.
        </p>
        <p className="t-label-s muted">Prototipe UI · hasil analisis adalah simulasi data demo</p>
      </div>

      {/* Phone frame on wide screens, full bleed on phones */}
      <div className="relative flex h-dvh w-full max-w-[430px] flex-col overflow-hidden md:h-[880px] md:rounded-[44px] md:border-[10px] md:border-[#1b1f1c] md:shadow-[var(--m3-shadow-3)]" style={{ background: "var(--m3-surface)" }}>
        {/* Top app bar */}
        <header className="flex h-16 shrink-0 items-center gap-2 px-4">
          {step === "preview" || step === "result" ? (
            <button type="button" aria-label="Kembali" className="grid size-10 place-items-center rounded-full" onClick={() => setStep("camera")}>
              <ChevronLeft className="size-6" />
            </button>
          ) : null}
          <Logo />
          <span className="ml-auto t-label-s muted">{MENU_TODAY.date}</span>
        </header>

        <main className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-44 [&>*]:shrink-0">
          {/* Context card */}
          <section className="card anim-rise flex items-center gap-3 p-4" style={{ "--i": 0 } as React.CSSProperties}>
            <div className="grid size-11 shrink-0 place-items-center rounded-full" style={{ background: "var(--m3-primary-container)", color: "var(--m3-on-primary-container)" }}>
              {role === "kru" ? <Soup className="size-5" /> : <UtensilsCrossed className="size-5" />}
            </div>
            <div className="min-w-0">
              <p className="t-title truncate">{role === "kru" ? `Batch ${MENU_TODAY.batch}` : MENU_TODAY.school}</p>
              <p className="t-body muted truncate">
                {role === "kru" ? `${MENU_TODAY.kitchen} → ${MENU_TODAY.school}` : `Kelas ${cls} · menu ${MENU_TODAY.quadrants.map((q) => q.name.toLowerCase()).join(", ")}`}
              </p>
            </div>
          </section>

          {role === "guru" && step === "receive" ? (
            <ReceiveCard
              received={received}
              onReceive={() => {
                setReceived(true);
                window.setTimeout(() => setStep("camera"), 700);
              }}
            />
          ) : null}

          {step !== "receive" ? (
            <>
              <div>
                <h1 className="t-headline">
                  {role === "kru"
                    ? step === "result" ? "Hasil cek sebelum kirim" : "Foto cartridge sebelum dikirim"
                    : step === "result" ? "Sisa makanan kelas " + cls : "Foto cartridge setelah makan"}
                </h1>
                <p className="t-body muted mt-1">
                  {step === "result"
                    ? "Periksa hasilnya, lalu putuskan."
                    : role === "kru" ? "Arahkan kamera tepat di atas cartridge." : "Cukup 3–5 cartridge per kelas sebagai sampel."}
                </p>
              </div>

              {role === "guru" && step === "camera" ? (
                <div className="flex gap-2 overflow-x-auto pb-1" role="group" aria-label="Pilih kelas">
                  {CLASSES.map((c) => (
                    <button key={c} type="button" className="chip shrink-0" aria-pressed={cls === c} onClick={() => setCls(c)}>
                      {cls === c ? <Check className="size-4" /> : null}
                      {c}
                    </button>
                  ))}
                </div>
              ) : null}

              {/* Viewfinder / photo */}
              <div className="relative overflow-hidden rounded-[16px] anim-pop" style={{ aspectRatio: "4 / 3", background: "#1b1f1c" }} key={`${role}-${step === "result" ? "r" : "v"}`}>
                {role === "guru" && step === "result" ? (
                  <BeforeAfter split={split} />
                ) : photo ? (
                  // eslint-disable-next-line @next/next/no-img-element -- local preview of a captured photo
                  <img src={photo} alt="Foto cartridge" className="absolute inset-0 size-full object-cover" />
                ) : (
                  <p className="absolute inset-x-0 bottom-2 text-center text-[12px] text-white/70">Kamera siap · posisikan 4 sekat di kotak</p>
                )}

                {step === "camera" || step === "preview" ? <QuadGuide /> : null}

                {step === "analyzing" ? (
                  <div className="absolute inset-0 overflow-hidden">
                    <div className="scan-line absolute inset-x-0 h-1/3" style={{ background: "linear-gradient(to bottom, transparent, rgb(166 242 196 / 0.45), transparent)" }} />
                  </div>
                ) : null}

                {step === "result" && role === "kru"
                  ? beforeResult.map((q, i) => {
                      const st = STATE_STYLE[q.state];
                      return (
                        <div
                          key={q.key}
                          className="anim-pop absolute rounded-[10px] border-[3px]"
                          style={{ ...QUAD_BOX[q.key], borderColor: st.color, background: q.state === "short" ? "rgb(255 220 194 / 0.25)" : "transparent", "--i": i } as React.CSSProperties}
                        >
                          <span className="absolute left-1.5 top-1.5 rounded-[6px] px-1.5 py-0.5 t-label-s" style={{ background: st.color, color: "#fff" }}>
                            {q.key} · {st.label}
                          </span>
                        </div>
                      );
                    })
                  : null}

                {flash ? <div key={flash} className="flash pointer-events-none absolute inset-0 bg-white" /> : null}
              </div>

              {role === "guru" && step === "result" ? (
                <label className="flex items-center gap-3">
                  <span className="t-label-s muted">Before</span>
                  <input type="range" min={0} max={100} value={split} onChange={(e) => setSplit(Number(e.target.value))} className="flex-1 accent-[var(--m3-primary)]" aria-label="Geser untuk membandingkan before dan after" />
                  <span className="t-label-s muted">After</span>
                </label>
              ) : null}

              {step === "analyzing" ? (
                <div className="flex items-center gap-3 anim-fade" role="status">
                  <svg className="spin size-6" viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" fill="none" stroke="var(--m3-surface-high)" strokeWidth="3" />
                    <path d="M12 3a9 9 0 0 1 9 9" fill="none" stroke="var(--m3-primary)" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                  <p className="t-body">Gemini memeriksa 4 kuadran…</p>
                </div>
              ) : null}

              {/* Kru result */}
              {step === "result" && role === "kru" ? (
                <section className="flex flex-col gap-3">
                  <div
                    className="anim-rise flex items-start gap-3 rounded-[16px] p-4"
                    style={{ background: shortQuad ? "var(--m3-tertiary-container)" : "var(--m3-primary-container)", color: shortQuad ? "var(--m3-on-tertiary-container)" : "var(--m3-on-primary-container)" }}
                  >
                    {shortQuad ? <RotateCcw className="mt-0.5 size-5 shrink-0" /> : <Check className="mt-0.5 size-5 shrink-0" />}
                    <div>
                      <p className="t-title">{shortQuad ? `${shortQuad.key} ${quadName(shortQuad.key).name} kosong, isi ulang` : "Lengkap, siap dikirim"}</p>
                      <p className="t-body">{shortQuad ? "Cartridge belum sesuai manifest menu hari ini." : "Keempat kuadran sesuai manifest menu."}</p>
                    </div>
                  </div>
                  <ul className="card divide-y" style={{ borderColor: "var(--m3-outline-variant)" }}>
                    {beforeResult.map((q, i) => {
                      const st = STATE_STYLE[q.state];
                      return (
                        <li key={q.key} className="anim-rise flex items-center gap-3 px-4 py-3" style={{ "--i": i + 1, borderColor: "var(--m3-outline-variant)" } as React.CSSProperties}>
                          <span className="grid size-9 shrink-0 place-items-center rounded-full t-label" style={{ background: st.bg, color: st.color }}>{q.key}</span>
                          <div className="min-w-0 flex-1">
                            <p className="t-label">{quadName(q.key).name} · {quadName(q.key).item}</p>
                            <p className="t-body muted">{q.note}</p>
                          </div>
                          <span className="t-label-s" style={{ color: st.color }}>{st.label}</span>
                        </li>
                      );
                    })}
                  </ul>
                  <GeminiBadge />
                  {usedSample ? null : <p className="t-label-s muted">Prototipe: hasil di atas adalah simulasi, bukan analisis foto Anda.</p>}
                </section>
              ) : null}

              {/* Guru result */}
              {step === "result" && role === "guru" ? (
                <section className="flex flex-col gap-3">
                  <div className="card anim-rise flex items-end justify-between p-4">
                    <div>
                      <p className="t-label muted">Perkiraan sisa makanan</p>
                      <p className="t-display" style={{ color: "var(--m3-tertiary)" }}>{wasteTotal}%</p>
                    </div>
                    <p className="t-body max-w-[55%] text-right">
                      {quadName(worst.key).name} paling banyak tersisa ({worst.left}%)
                    </p>
                  </div>
                  <div className="card flex flex-col gap-3 p-4">
                    {AFTER_RESULT.map((q, i) => (
                      <div key={q.key} className="flex flex-col gap-1">
                        <div className="flex items-baseline justify-between">
                          <span className="t-label">{q.key} · {quadName(q.key).name}</span>
                          <span className="t-label-s muted">{q.confidence} · {q.left}% sisa</span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full" style={{ background: "var(--m3-surface-high)" }}>
                          <div className="anim-grow-x h-full rounded-full" style={{ width: `${q.left}%`, background: q.left >= 50 ? "var(--m3-tertiary)" : "var(--m3-primary)", "--i": i } as React.CSSProperties} />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-col gap-2">
                    <p className="t-label">Kenapa tidak habis? (opsional)</p>
                    <div className="flex flex-wrap gap-2">
                      {["Tidak suka", "Porsi besar", "Basi/bau", "Lainnya"].map((r) => (
                        <button
                          key={r}
                          type="button"
                          className="chip"
                          aria-pressed={reasons.includes(r)}
                          onClick={() => setReasons((cur) => (cur.includes(r) ? cur.filter((x) => x !== r) : [...cur, r]))}
                        >
                          {reasons.includes(r) ? <Check className="size-4" /> : null}
                          {r}
                        </button>
                      ))}
                    </div>
                    {reasons.includes("Basi/bau") ? (
                      <p className="anim-fade rounded-[12px] p-3 t-body" style={{ background: "var(--m3-error-container)", color: "var(--m3-on-error-container)" }}>
                        Basi/bau akan dilaporkan sebagai masalah keamanan pangan ke dapur dan dinas.
                      </p>
                    ) : null}
                  </div>
                  <GeminiBadge />
                </section>
              ) : null}
            </>
          ) : null}
        </main>

        {/* Bottom action area */}
        <div className="absolute inset-x-0 bottom-[96px] flex justify-center gap-3 px-4">
          {step === "camera" ? (
            <div className="flex w-full items-center justify-between">
              <button type="button" className="btn-text" onClick={() => takePhoto(sampleFor(), true)}>
                <ImageIcon className="size-5" /> Foto contoh
              </button>
              <button
                type="button"
                aria-label="Ambil foto"
                className="grid size-[72px] place-items-center rounded-[22px] shadow-[var(--m3-shadow-3)] transition-transform active:scale-95"
                style={{ background: "var(--m3-primary-container)", color: "var(--m3-on-primary-container)" }}
                onClick={() => fileRef.current?.click()}
              >
                <Camera className="size-8" />
              </button>
              <span className="w-[120px]" />
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) takePhoto(URL.createObjectURL(f), false);
                  e.target.value = "";
                }}
              />
            </div>
          ) : null}
          {step === "preview" ? (
            <>
              <button type="button" className="btn-tonal flex-1" onClick={() => setStep("camera")}>
                <RotateCcw className="size-4" /> Ulangi
              </button>
              <button type="button" className="btn-filled flex-1" onClick={analyze}>
                <Send className="size-4" /> Kirim cek
              </button>
            </>
          ) : null}
          {step === "result" && role === "kru" ? (
            shortQuad ? (
              <button
                type="button"
                className="btn-filled w-full"
                onClick={() => {
                  setRefilled(true);
                  setPhoto(null);
                  setStep("camera");
                }}
              >
                <Camera className="size-4" /> Sudah diisi, foto ulang
              </button>
            ) : (
              <button type="button" className="btn-filled w-full" onClick={() => showSnack(`Batch ${MENU_TODAY.batch} siap dikirim ke ${MENU_TODAY.school}`)}>
                <Truck className="size-4" /> Tandai siap kirim
              </button>
            )
          ) : null}
          {step === "result" && role === "guru" ? (
            <button type="button" className="btn-filled w-full" onClick={() => showSnack(`Terkirim ke ${MENU_TODAY.kitchen}`)}>
              <Send className="size-4" /> Kirim ke dapur
            </button>
          ) : null}
        </div>

        {/* M3 navigation bar */}
        <nav aria-label="Peran" className="absolute inset-x-0 bottom-0 flex h-20 items-start justify-around pt-3" style={{ background: "var(--m3-surface-container)" }}>
          {([
            ["kru", "Kru dapur", Soup],
            ["guru", "Guru", UtensilsCrossed],
          ] as const).map(([key, label, Icon]) => (
            <button key={key} type="button" className="flex w-24 flex-col items-center gap-1" aria-current={role === key ? "page" : undefined} onClick={() => switchRole(key)}>
              <span
                className="grid h-8 w-16 place-items-center rounded-full transition-colors duration-200"
                style={{ background: role === key ? "var(--m3-secondary-container)" : "transparent", color: role === key ? "var(--m3-on-secondary-container)" : "var(--m3-on-surface-variant)" }}
              >
                <Icon className="size-5" />
              </span>
              <span className="t-label-s" style={{ color: role === key ? "var(--m3-on-surface)" : "var(--m3-on-surface-variant)" }}>{label}</span>
            </button>
          ))}
        </nav>

        {snack ? <Snackbar>{snack}</Snackbar> : null}
      </div>
    </div>
  );
}

function QuadGuide() {
  return (
    <div className="pointer-events-none absolute inset-0">
      {MENU_TODAY.quadrants.map((q) => (
        <div key={q.key} className="absolute rounded-[10px] border-2 border-dashed border-white/80" style={QUAD_BOX[q.key]}>
          <span className="absolute left-1.5 top-1.5 rounded-[6px] bg-black/55 px-1.5 py-0.5 text-[11px] font-medium text-white">
            {q.key} {q.name}
          </span>
        </div>
      ))}
    </div>
  );
}

function BeforeAfter({ split }: { split: number }) {
  return (
    <>
      {/* eslint-disable-next-line @next/next/no-img-element -- static illustration */}
      <img src="/proto/tray-after.svg" alt="Cartridge setelah makan" className="absolute inset-0 size-full object-cover" />
      <div className="absolute inset-0 overflow-hidden" style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}>
        {/* eslint-disable-next-line @next/next/no-img-element -- static illustration */}
        <img src="/proto/tray-before-full.svg" alt="Cartridge sebelum dikirim" className="absolute inset-0 size-full object-cover" />
      </div>
      <div className="absolute inset-y-0 w-0.5 bg-white shadow" style={{ left: `${split}%` }} />
      <span className="absolute left-2 top-2 rounded-[6px] bg-black/55 px-1.5 py-0.5 text-[11px] font-medium text-white">Before</span>
      <span className="absolute right-2 top-2 rounded-[6px] bg-black/55 px-1.5 py-0.5 text-[11px] font-medium text-white">After</span>
    </>
  );
}

function ReceiveCard({ received, onReceive }: { received: boolean; onReceive: () => void }) {
  return (
    <section className="card anim-rise flex flex-col gap-4 p-5" style={{ "--i": 1 } as React.CSSProperties}>
      <div className="flex items-center gap-2">
        <Truck className="size-5" style={{ color: "var(--m3-primary)" }} />
        <p className="t-title">Pengiriman hari ini</p>
      </div>
      <dl className="grid grid-cols-2 gap-3">
        <div><dt className="t-label-s muted">Dari</dt><dd className="t-body">{MENU_TODAY.kitchen}</dd></div>
        <div><dt className="t-label-s muted">Jumlah</dt><dd className="t-body">24 cartridge</dd></div>
        <div><dt className="t-label-s muted">Tiba</dt><dd className="t-body">11.05</dd></div>
        <div><dt className="t-label-s muted">Batch</dt><dd className="t-body">{MENU_TODAY.batch}</dd></div>
      </dl>
      <button
        type="button"
        className="btn-filled h-12 w-full transition-all duration-300"
        style={received ? { background: "var(--m3-primary-container)", color: "var(--m3-on-primary-container)" } : undefined}
        onClick={onReceive}
        disabled={received}
      >
        {received ? <><Check className="size-5" /> Diterima 11.05</> : "Terima 24 cartridge"}
      </button>
    </section>
  );
}
