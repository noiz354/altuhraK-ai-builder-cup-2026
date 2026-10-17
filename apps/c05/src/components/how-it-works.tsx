import Link from "next/link";

/**
 * A short, collapsible "how this page works" strip shown at the top of each
 * working surface. Native <details>, so it needs no client state and keeps
 * working without JavaScript.
 */
export function HowItWorks({
  steps,
  tip,
  open = true,
}: {
  steps: Array<{ title: string; body: string }>;
  tip?: string;
  open?: boolean;
}) {
  return (
    <details open={open} className="panel group p-0">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 select-none">
        <span className="flex items-center gap-2 text-[14px] font-medium">
          <span
            aria-hidden
            className="flex size-5 items-center justify-center rounded-full bg-[var(--brand)] text-[12px] font-bold text-white"
          >
            ?
          </span>
          How this page works
        </span>
        <span className="meta group-open:hidden">Show</span>
        <span className="meta hidden group-open:inline">Hide</span>
      </summary>
      <div className="border-t border-[var(--hairline)] px-4 py-3">
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, n) => (
            <li key={s.title} className="flex gap-2.5">
              <span
                aria-hidden
                className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border border-[var(--brand)] text-[12px] font-semibold text-[var(--brand)]"
              >
                {n + 1}
              </span>
              <span>
                <span className="block text-[14px] font-medium leading-[20px]">{s.title}</span>
                <span className="block text-[13px] leading-[18px] text-[var(--ink-2)]">{s.body}</span>
              </span>
            </li>
          ))}
        </ol>
        <p className="meta mt-3">
          {tip ? `${tip} ` : ""}
          <Link href="/guide" className="text-[var(--action)] underline underline-offset-2">
            Full guide
          </Link>
        </p>
      </div>
    </details>
  );
}
