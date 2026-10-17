import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type {
  Disposition,
  ExecutionStatus,
  Label,
  ReviewStatus,
} from "@/lib/c05-types";

const REVIEW_STYLE: Record<ReviewStatus, { text: string; className: string; dot: string }> = {
  UNVERIFIED: {
    text: "UNVERIFIED",
    className: "border-[var(--review)] text-[var(--review)] bg-transparent",
    dot: "bg-[var(--review)]",
  },
  REVIEW_PENDING: {
    text: "PENDING REVIEW",
    className: "border-[var(--review)] text-[var(--review)] bg-transparent",
    dot: "bg-[var(--review)]",
  },
  APPROVED: {
    text: "APPROVED",
    className: "border-[var(--pass)] text-[var(--pass)] bg-transparent",
    dot: "bg-[var(--pass)]",
  },
  REJECTED: {
    text: "REJECTED",
    className: "border-[var(--defect)] text-[var(--defect)] bg-transparent",
    dot: "bg-[var(--defect)]",
  },
};

const LABEL_STYLE: Record<string, { text: string; className: string }> = {
  meal_complete: { text: "meal_complete", className: "border-[var(--pass)] text-[var(--pass)]" },
  missing_component: {
    text: "missing_component",
    className: "border-[var(--defect)] text-[var(--defect)]",
  },
  uncertain: { text: "uncertain", className: "border-[var(--review)] text-[var(--review)]" },
};

const EXECUTION_STYLE: Record<ExecutionStatus, { className: string }> = {
  CREATED: { className: "border-[var(--hairline)] text-[var(--ink-2)]" },
  RUNNING: { className: "border-[var(--action)] text-[var(--action)]" },
  COMPLETED: { className: "border-[var(--pass)] text-[var(--pass)]" },
  FAILED: { className: "border-[var(--defect)] text-[var(--defect)]" },
};

const DISPOSITION_STYLE: Record<Disposition, { className: string }> = {
  ACCEPT: { className: "border-[var(--pass)] text-[var(--pass)]" },
  HOLD: { className: "border-[var(--review)] text-[var(--review)]" },
  REJECT: { className: "border-[var(--defect)] text-[var(--defect)]" },
};

function Dot({ className }: { className: string }) {
  return (
    <span
      aria-hidden
      className={cn("size-1.5 rounded-full shrink-0", className)}
    />
  );
}

export function StatusBadge({ status }: { status: ReviewStatus }) {
  const style = REVIEW_STYLE[status];
  return (
    <Badge variant="outline" className={cn("gap-1.5 rounded-md font-medium", style.className)}>
      <Dot className={style.dot} />
      {style.text}
    </Badge>
  );
}

export function ExecutionBadge({ status }: { status: ExecutionStatus }) {
  return (
    <Badge variant="outline" className={cn("font-medium", EXECUTION_STYLE[status].className)}>
      {status}
    </Badge>
  );
}

export function DispositionBadge({ disposition }: { disposition: Disposition }) {
  return (
    <Badge variant="outline" className={cn("font-medium", DISPOSITION_STYLE[disposition].className)}>
      QC {disposition}
    </Badge>
  );
}

export function PredictionBadge({ label }: { label: Label | string }) {
  const style = LABEL_STYLE[label] ?? {
    text: label,
    className: "border-[var(--hairline)] text-[var(--ink-2)]",
  };
  return (
    <Badge variant="outline" className={cn("font-mono", style.className)}>
      {style.text}
    </Badge>
  );
}

/**
 * Automatic results never share a visual treatment with human decisions.
 * This block is always outlined amber and always labelled as not yet reviewed.
 */
export function PredictionBlock({
  label,
  regions,
  evidenceIds,
}: {
  label: string | null;
  regions: Array<{ x: number; y: number; w: number; h: number }>;
  evidenceIds: string[];
}) {
  return (
    <div
      className="rounded-[var(--r-panel)] border border-[var(--review)] bg-transparent p-4"
      aria-label="Automatic check result, not yet reviewed"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="label text-[var(--review)]">CHECK RESULT — NOT YET REVIEWED</span>
        {label ? <PredictionBadge label={label} /> : <span className="meta">no result yet</span>}
      </div>
      <p className="meta mt-2">
        {regions.length} marked area(s) · a supervisor confirms every result
      </p>
      {evidenceIds.length > 0 ? (
        <ul className="mono mt-2 space-y-0.5 break-all text-[var(--ink-3)]">
          {evidenceIds.map((id) => (
            <li key={id}>{id}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}