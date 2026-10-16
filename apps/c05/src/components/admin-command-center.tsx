"use client";

import { useEffect, useMemo, useState } from "react";
import { c05, C05Error } from "@/lib/c05-client";
import type {
  AuditEvent,
  Disposition,
  InspectionDetail,
  InspectionSummary,
  Overview,
  Role,
} from "@/lib/c05-types";
import { DispositionBadge, ExecutionBadge, PredictionBlock, StatusBadge } from "@/components/c05-status";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";

function Stat({ label, value, tone }: { label: string; value: number; tone?: "defect" | "review" | "pass" }) {
  const color =
    tone === "defect"
      ? "text-[var(--defect)]"
      : tone === "review"
        ? "text-[var(--review)]"
        : tone === "pass"
          ? "text-[var(--pass)]"
          : "text-[var(--ink)]";
  return (
    <div className="panel p-3">
      <p className="label">{label}</p>
      <p className={`mt-1 text-[28px] leading-[34px] font-semibold tabular-nums ${color}`}>{value}</p>
    </div>
  );
}

export function AdminCommandCenter({ role, kitchenId }: { role: Role; kitchenId: string }) {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [rows, setRows] = useState<InspectionSummary[]>([]);
  const [filter, setFilter] = useState<string>("ALL");
  const [selected, setSelected] = useState<InspectionDetail | null>(null);
  const [comment, setComment] = useState("");
  const [disposition, setDisposition] = useState<Disposition>("HOLD");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    try {
      const [o, l] = await Promise.all([
        c05.overview(role, kitchenId),
        c05.listInspections({ role, kitchen_id: kitchenId }),
      ]);
      setOverview(o);
      setRows(l.inspections);
      setError("");
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), 5000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, kitchenId]);

  async function open(id: string) {
    try {
      setSelected(await c05.inspection(id, role));
      setNotice("");
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    }
  }

  async function decide(decision: "APPROVED" | "REJECTED") {
    if (!selected) return;
    try {
      const updated = await c05.review(selected.inspection_id, { role, decision, qc_disposition: disposition, comment });
      setSelected({ ...selected, ...updated });
      setNotice(decision === "APPROVED" ? "Review approved and recorded." : "Review rejected and recorded.");
      setComment("");
      await refresh();
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    }
  }

  async function reinfer() {
    if (!selected) return;
    try {
      const updated = await c05.reinfer(selected.inspection_id, role);
      setSelected({ ...selected, ...updated, audit: selected.audit });
      setNotice("New revision created. Previous prediction kept.");
      await refresh();
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    }
  }

  const visible = useMemo(
    () => (filter === "ALL" ? rows : rows.filter((r) => r.review_status === filter)),
    [rows, filter],
  );

  const canApprove = role !== "CREW";

  return (
    <div className="flex flex-col gap-4">
      <section aria-label="Operations overview">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-[20px] leading-[26px] font-semibold">Operations overview</h2>
          <Badge variant="outline" className="font-mono">
            {kitchenId}
          </Badge>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          <Stat label="Inspections" value={overview?.inspections_total ?? 0} />
          <Stat label="Unverified" value={overview?.unverified ?? 0} tone="review" />
          <Stat label="Pending review" value={overview?.pending_review ?? 0} tone="review" />
          <Stat label="Approved" value={overview?.approved ?? 0} tone="pass" />
          <Stat label="Rejected" value={overview?.rejected ?? 0} tone="defect" />
          <Stat label="Failed" value={overview?.failed_inference ?? 0} tone="defect" />
        </div>
        {/* Provenance strip. A supervisor must be able to tell, at a glance, how
            many results actually came from the model versus the deterministic
            baseline, and why the rest did not. Collapsing this into one number is
            what made earlier false-success reports possible. */}
        <dl className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="rounded-md border border-[var(--line)] px-3 py-2">
            <dt className="label">Model inference</dt>
            <dd className="font-mono text-[15px] tabular-nums">
              {overview?.model_inference_count ?? 0}
            </dd>
          </div>
          <div className="rounded-md border border-[var(--line)] px-3 py-2">
            <dt className="label">Baseline only</dt>
            <dd className="font-mono text-[15px] tabular-nums">
              {overview?.baseline_only_count ?? 0}
            </dd>
          </div>
          {Object.entries(overview?.inference_status ?? {})
            .filter(([k]) => k !== "INFERENCE_SUCCEEDED" && k !== "NOT_REQUESTED")
            .slice(0, 4)
            .map(([status, count]) => (
              <div key={status} className="rounded-md border border-[var(--line)] px-3 py-2">
                <dt className="label">{status.replace(/_/g, " ").toLowerCase()}</dt>
                <dd className="font-mono text-[15px] tabular-nums text-[var(--defect)]">{count}</dd>
              </div>
            ))}
        </dl>
        {Object.keys(overview?.failure_categories ?? {}).length > 0 ? (
          <p className="meta mt-2">
            Failure categories:{" "}
            {Object.entries(overview?.failure_categories ?? {})
              .map(([code, n]) => `${code}: ${n}`)
              .join(" · ")}
          </p>
        ) : null}
        <p className="meta mt-2">
          Storage measured: {overview ? `${(overview.storage_bytes / 1024).toFixed(1)} KB` : "—"} of a{" "}
          {(overview ? overview.storage_budget_bytes / 1024 ** 3 : 10).toFixed(0)} GB budget ·{" "}
          {Object.entries(overview?.labels ?? {})
            .map(([k, v]) => `${k}: ${v}`)
            .join(" · ") || "no predictions yet"}
        </p>
        {error ? <p className="mt-2 text-[13px] text-[var(--defect)]">{error}</p> : null}
      </section>

      <section className="panel p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="label">Review queue</h3>
          <div className="flex flex-wrap gap-1">
            {["ALL", "UNVERIFIED", "REVIEW_PENDING", "APPROVED", "REJECTED"].map((f) => (
              <Button
                key={f}
                type="button"
                size="sm"
                variant={filter === f ? "default" : "outline"}
                onClick={() => setFilter(f)}
                aria-pressed={filter === f}
              >
                {f.replace("_", " ")}
              </Button>
            ))}
          </div>
        </div>
        <ScrollArea className="mt-3">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-[12px]">Inspection</TableHead>
                <TableHead className="text-[12px]">Batch</TableHead>
                <TableHead className="text-[12px]">Execution</TableHead>
                <TableHead className="text-[12px]">Review</TableHead>
                <TableHead className="text-[12px]">Disposition</TableHead>
                <TableHead className="text-[12px]">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-6 text-center text-[var(--ink-3)]">
                    No records for this filter.
                  </TableCell>
                </TableRow>
              ) : null}
              {visible.map((r) => (
                <TableRow key={r.inspection_id}>
                  <TableCell className="mono">{r.inspection_id.slice(0, 10)}</TableCell>
                  <TableCell className="font-mono text-[12px]">{r.batch_id}</TableCell>
                  <TableCell>
                    <ExecutionBadge status={r.execution_status} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={r.review_status} />
                  </TableCell>
                  <TableCell>
                    {r.qc_disposition ? (
                      <DispositionBadge disposition={r.qc_disposition} />
                    ) : (
                      <span className="meta">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button type="button" size="sm" variant="outline" onClick={() => open(r.inspection_id)}>
                      Open
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollArea>
      </section>

      {selected ? (
        <section className="grid gap-4 lg:grid-cols-2">
          <Card className="panel gap-0 p-4">
            <h3 className="label">Evidence</h3>
            <PredictionBlock
              label={selected.prediction?.predicted_label ?? null}
              regions={selected.prediction?.regions ?? []}
              evidenceIds={selected.evidence_ids}
              modelVersion={selected.model_version}
              latencyMs={selected.latency_ms}
            />
            <div className="mt-3">
              <p className="label">Expected manifest v{selected.manifest_version}</p>
              <ul className="mt-1.5 space-y-1">
                {selected.manifest.components.map((c) => (
                  <li key={c.key} className="well px-3 py-1.5 text-[14px]">
                    {c.label}
                  </li>
                ))}
              </ul>
            </div>
            <ul className="mono mt-3 space-y-0.5 text-[var(--ink-3)]">
              <li>image_sha256 {selected.image_sha256.slice(0, 16)}…</li>
              <li>schema {selected.schema_version}</li>
              <li>prompt {selected.prompt_version}</li>
              <li>revision {selected.revision}</li>
            </ul>
          </Card>

          <Card className="panel gap-0 p-4">
            <h3 className="label">Reviewer controls</h3>
            <p className="meta mt-1">
              {canApprove
                ? "Approving a review is not clearance of the physical meal."
                : "Crew cannot approve. Ask a supervisor."}
            </p>
            <div className="mt-3 flex flex-col gap-1.5">
              <Label htmlFor="disposition">QC disposition</Label>
              <div className="flex gap-2">
                {(["ACCEPT", "HOLD", "REJECT"] as Disposition[]).map((d) => (
                  <Button
                    key={d}
                    type="button"
                    size="sm"
                    variant={disposition === d ? "default" : "outline"}
                    onClick={() => setDisposition(d)}
                    aria-pressed={disposition === d}
                    disabled={!canApprove}
                  >
                    {d}
                  </Button>
                ))}
              </div>
            </div>
            <div className="mt-3 flex flex-col gap-1.5">
              <Label htmlFor="comment">Comment {disposition === "REJECT" ? "(required to reject)" : "(optional)"}</Label>
              <Textarea
                id="comment"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={3}
                disabled={!canApprove}
              />
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button type="button" onClick={() => decide("APPROVED")} disabled={!canApprove} className="h-12">
                Approve review
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => decide("REJECTED")}
                disabled={!canApprove}
                className="h-12"
              >
                Reject review
              </Button>
              <Button type="button" variant="outline" onClick={reinfer} className="h-12">
                Re-infer (new revision)
              </Button>
            </div>
            <div aria-live="polite" className="mt-2">
              {notice ? <p className="text-[13px] text-[var(--pass)]">{notice}</p> : null}
            </div>
            <div className="mt-3">
              <p className="label">Audit trail</p>
              <ScrollArea className="mt-1.5 h-40">
                <ul className="space-y-1">
                  {(selected.audit as AuditEvent[]).map((e) => (
                    <li key={e.seq} className="meta">
                      #{e.seq} {e.event}
                    </li>
                  ))}
                </ul>
              </ScrollArea>
            </div>
          </Card>
        </section>
      ) : (
        <p className="meta">Select an inspection to review its evidence.</p>
      )}
    </div>
  );
}