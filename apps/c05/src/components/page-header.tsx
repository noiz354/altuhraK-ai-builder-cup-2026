import { ViewAs } from "@/components/view-as";

/**
 * Shared heading for every working page. It answers the two questions a new
 * visitor has before touching anything: which gap this page closes, and what
 * they are expected to do here.
 */
export function PageHeader({
  step,
  stage,
  title,
  gap,
  goal,
}: {
  step?: number;
  stage: string;
  title: string;
  gap: string;
  goal: string;
}) {
  return (
    <header>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="label text-[var(--brand)]">
            {step ? `Step ${step} of 4 · ` : ""}
            {stage}
          </p>
          <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">{title}</h1>
        </div>
        <ViewAs />
      </div>
      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
        <div className="well p-3">
          <dt className="label font-medium" style={{ color: "var(--defect)" }}>
            The gap
          </dt>
          <dd className="mt-0.5 text-[14px] leading-[20px]">{gap}</dd>
        </div>
        <div className="well p-3">
          <dt className="label font-medium" style={{ color: "var(--pass)" }}>
            What you do here
          </dt>
          <dd className="mt-0.5 text-[14px] leading-[20px]">{goal}</dd>
        </div>
      </dl>
    </header>
  );
}
