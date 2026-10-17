import { ClaimReportForm } from "@/components/claim-report-form";

export default function ReportPage() {
  return (
    <div className="mx-auto w-full max-w-[640px]">
      <p className="label text-[var(--brand)]">Step 3 of 4 · After serving · Parents and schools</p>
      <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">Did a school meal make someone unwell?</h1>
      <p className="mt-1 text-[15px] leading-[22px] text-[var(--ink-2)]">
        Tell us what happened. The kitchen and the local health office use these reports to find the cause and
        protect other children.
      </p>
      <ol className="mt-4 grid gap-2 sm:grid-cols-3">
        {[
          ["You report", "Takes about two minutes. No account needed."],
          ["We check", "Staff compare reports with what the kitchen delivered that day."],
          ["Health office follows up", "Serious cases go straight to the Puskesmas / Dinas Kesehatan."],
        ].map(([t, b], n) => (
          <li key={t} className="well flex gap-2.5 p-3">
            <span
              aria-hidden
              className="flex size-6 shrink-0 items-center justify-center rounded-full bg-[var(--brand)] text-[12px] font-bold text-white"
            >
              {n + 1}
            </span>
            <span>
              <span className="block text-[14px] font-medium">{t}</span>
              <span className="block text-[13px] leading-[18px] text-[var(--ink-2)]">{b}</span>
            </span>
          </li>
        ))}
      </ol>
      <div className="mt-4">
        <ClaimReportForm />
      </div>
    </div>
  );
}
