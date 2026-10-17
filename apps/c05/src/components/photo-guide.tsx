/* eslint-disable @next/next/no-img-element -- small static illustrations from /public */

/**
 * Example photos for the Check meal page. A prototype is easier to judge when
 * people can see what a good capture looks like, what makes a photo unusable,
 * and what each result means — not only read the rules.
 *
 * The images are synthetic illustrations from the training-pipeline fixtures.
 */

export const SAMPLE_PHOTOS = [
  { src: "/examples/complete-tray.jpg", name: "Complete tray", expect: "meal_complete" },
  { src: "/examples/missing-veg-photo.jpg", name: "Vegetables missing", expect: "missing_component" },
  { src: "/examples/too-dark.jpg", name: "Too dark", expect: "uncertain" },
] as const;

const RETAKE = [
  { src: "/examples/too-dark.jpg", title: "Too dark", fix: "Move to the light or turn on a lamp." },
  { src: "/examples/blurry.jpg", title: "Blurry", fix: "Hold still and tap to focus before shooting." },
  { src: "/examples/cut-off.jpg", title: "Cut off", fix: "Step back so the whole tray is in frame." },
  { src: "/examples/covered.jpg", title: "Something covering food", fix: "Remove lids, napkins and hands." },
];

const RESULTS = [
  {
    src: "/examples/complete-tray.jpg",
    label: "meal_complete",
    color: "var(--pass)",
    title: "Complete",
    body: "Rice, protein and vegetables are all visible. The batch goes to the supervisor to accept.",
  },
  {
    src: "/examples/missing-veg-tray.jpg",
    label: "missing_component",
    color: "var(--defect)",
    title: "Missing component",
    body: "Here the vegetable compartment is empty. Refill the tray; the supervisor will likely hold the batch.",
  },
  {
    src: "/examples/blurry.jpg",
    label: "uncertain",
    color: "var(--review)",
    title: "Uncertain",
    body: "The photo cannot tell. Retake it; nothing is decided from an unclear photo.",
  },
];

function Mark({ ok }: { ok: boolean }) {
  return (
    <span
      aria-hidden
      className="flex size-5 shrink-0 items-center justify-center rounded-full text-[12px] font-bold text-white"
      style={{ background: ok ? "var(--pass)" : "var(--defect)" }}
    >
      {ok ? "✓" : "✕"}
    </span>
  );
}

export function PhotoGuide() {
  return (
    <section className="panel flex flex-col gap-4 p-4" aria-labelledby="photo-guide-h">
      <div>
        <h2 id="photo-guide-h" className="text-[18px] font-semibold">
          How to take the photo
        </h2>
        <p className="meta">Example photos are illustrations for this prototype.</p>
      </div>

      <figure className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] sm:items-center">
        <img
          src="/examples/complete-tray.jpg"
          alt="Good example: the whole tray seen from above, evenly lit, all three compartments visible"
          className="w-full rounded-[var(--r-control)] border-2"
          style={{ borderColor: "var(--pass)" }}
        />
        <figcaption>
          <p className="flex items-center gap-2 text-[15px] font-semibold">
            <Mark ok /> A good photo
          </p>
          <ul className="mt-2 flex flex-col gap-1 text-[14px] leading-[20px]">
            <li>• The whole tray is in the frame</li>
            <li>• Taken straight from above</li>
            <li>• Bright, even light, no strong shadow</li>
            <li>• Nothing covering the food</li>
          </ul>
        </figcaption>
      </figure>

      <div>
        <p className="flex items-center gap-2 text-[15px] font-semibold">
          <Mark ok={false} /> Retake if it looks like this
        </p>
        <ul className="mt-2 grid grid-cols-2 gap-2">
          {RETAKE.map((r) => (
            <li key={r.title} className="flex flex-col gap-1">
              <img
                src={r.src}
                alt={`Bad example: ${r.title.toLowerCase()}`}
                className="aspect-[4/3] w-full rounded-[var(--r-control)] border-2 object-cover"
                style={{ borderColor: "var(--defect)" }}
              />
              <span className="text-[13px] font-medium">{r.title}</span>
              <span className="text-[12px] leading-[16px] text-[var(--ink-2)]">{r.fix}</span>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <p className="text-[15px] font-semibold">What the result means</p>
        <ul className="mt-2 flex flex-col gap-2">
          {RESULTS.map((r) => (
            <li key={r.label} className="flex gap-3 rounded-[var(--r-control)] border border-[var(--hairline)] p-2">
              <img src={r.src} alt={`Example of a ${r.title.toLowerCase()} result`} className="h-[72px] w-24 shrink-0 rounded-[6px] object-cover" />
              <div className="min-w-0">
                <p className="text-[14px] font-semibold" style={{ color: r.color }}>
                  {r.title} <span className="meta font-mono font-normal">{r.label}</span>
                </p>
                <p className="text-[13px] leading-[18px] text-[var(--ink-2)]">{r.body}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
