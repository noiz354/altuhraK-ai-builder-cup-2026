"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { c05, C05Error } from "@/lib/c05-client";
import type {
  ClaimIncident,
  ClaimIncidentDetail,
  ClaimSignal,
  HealthPriority,
  IncidentStatus,
  Role,
} from "@/lib/c05-types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { HEALTH_COPY, STATUS_COPY, signalCopy } from "@/lib/claim-copy";

const HEALTH_STYLE: Record<HealthPriority, string> = {
  URGENT: "border-[var(--defect)] bg-[var(--defect)] text-white",
  HIGH: "border-[var(--defect)] text-[var(--defect)]",
  ROUTINE: "border-[var(--hairline)] text-[var(--ink-2)]",
};

const LEVEL_COLOR = { low: "var(--pass)", medium: "var(--review)", high: "var(--defect)" } as const;

const STATUS_TEXT = Object.fromEntries(
  Object.entries(STATUS_COPY).map(([k, v]) => [k, v.label]),
) as Record<IncidentStatus, string>;

const DECISIONS: Array<{ status: IncidentStatus; label: string; adminOnly: boolean }> = [
  { status: "ESCALATED_HEALTH", label: "Escalate to health office", adminOnly: false },
  { status: "FIELD_VERIFICATION", label: "Send field verification", adminOnly: false },
  { status: "CLOSED_CONFIRMED", label: "Close · confirmed illness", adminOnly: true },
  { status: "CLOSED_UNSUBSTANTIATED", label: "Close · unsubstantiated", adminOnly: true },
];

const PATTERN_TEXT = {
  consistent_with_outbreak: "Consistent with an outbreak",
  mixed: "Mixed pattern",
  inconsistent_with_records: "Inconsistent with service records",
  insufficient_data: "Insufficient data",
} as const;

function plural(n: number, word: string) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

function fmt(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function HealthBadge({ priority }: { priority: HealthPriority }) {
  return (
    <Badge variant="outline" title={HEALTH_COPY[priority]} className={cn("font-semibold", HEALTH_STYLE[priority])}>
      Health {priority}
    </Badge>
  );
}

function ScoreMeter({ score, level }: { score: number; level: "low" | "medium" | "high" }) {
  return (
    <div
      className="flex items-center gap-2"
      aria-label={`Integrity score ${score} of 100, ${level}`}
      title="Integrity score: 0 = reports fit the delivery records, 100 = strong conflicts. Not a verdict."
    >
      <span className="meta">Conflicts</span>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-[var(--sunken)]">
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: LEVEL_COLOR[level] }} />
      </div>
      <span className="font-mono text-[13px] tabular-nums" style={{ color: LEVEL_COLOR[level] }}>
        {score}
      </span>
    </div>
  );
}

function SignalRow({
  signal,
  active,
  onToggle,
}: {
  signal: ClaimSignal;
  active: boolean;
  onToggle: () => void;
}) {
  const integrity = signal.kind === "integrity";
  const copy = signalCopy(signal.code);
  return (
    <li>
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={active}
        disabled={signal.claim_ids.length === 0}
        className={cn(
          "w-full rounded-[var(--r-control)] border px-3 py-2 text-left transition-colors duration-150",
          active ? "border-[var(--action)] bg-[var(--sunken)]" : "border-[var(--hairline)] hover:bg-[var(--sunken)]",
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <span
            className="text-[14px] font-medium"
            style={{ color: integrity ? "var(--review)" : "var(--pass)" }}
          >
            {copy.title}
          </span>
          {integrity ? <span className="meta tabular-nums">+{signal.weight}</span> : null}
        </div>
        <p className="mt-0.5 text-[13px] leading-[18px]">{signal.detail}</p>
        {active && copy.explain ? (
          <p className="mt-1 text-[12px] leading-[17px] text-[var(--ink-2)]">{copy.explain}</p>
        ) : null}
        <p className="meta mt-0.5">
          {signal.claim_ids.length
            ? `${active ? "Showing" : "Tap to show"} ${signal.claim_ids.length} report(s) · `
            : ""}
          <span className="font-mono">{signal.code}</span>
        </p>
      </button>
    </li>
  );
}

export function ClaimsConsole({ role, kitchenId }: { role: Role; kitchenId: string }) {
  const [incidents, setIncidents] = useState<ClaimIncident[]>([]);
  const [picked, setSelected] = useState<ClaimIncidentDetail | null>(null);
  // Switching kitchen hides an incident from the previous scope without an extra render pass.
  const selected = picked && picked.kitchen_id === kitchenId ? picked : null;
  const [focus, setFocus] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [followup, setFollowup] = useState(false);
  const [busy, setBusy] = useState<"" | "assess" | "decide" | "seed">("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const allowed = role !== "CREW";

  async function refresh() {
    if (!allowed) return;
    try {
      const res = await c05.claimIncidents(role, kitchenId);
      setIncidents(res.incidents);
      setError("");
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), 15000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, kitchenId]);

  async function open(id: string) {
    try {
      setSelected(await c05.claimIncident(id, role));
      setFocus(null);
      setNotice("");
      setComment("");
      setFollowup(false);
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    }
  }

  async function assess() {
    if (!selected) return;
    setBusy("assess");
    try {
      const next = await c05.assessIncident(selected.incident_id, role);
      setSelected(next);
      setNotice(
        next.ai?.inference_status === "INFERENCE_SUCCEEDED"
          ? "Summary added. The score and signals are unchanged."
          : "A summary is not available right now; the conflicts and next steps still apply.",
      );
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    } finally {
      setBusy("");
    }
  }

  async function decide(status: IncidentStatus) {
    if (!selected) return;
    setBusy("decide");
    try {
      const next = await c05.decideIncident(selected.incident_id, {
        role,
        status,
        comment,
        health_followup_confirmed: followup,
      });
      setSelected(next);
      setNotice(`Recorded: ${STATUS_TEXT[status]}.`);
      setComment("");
      await refresh();
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    } finally {
      setBusy("");
    }
  }

  async function seed() {
    setBusy("seed");
    try {
      const res = await c05.seedClaims(role);
      setNotice(`Loaded ${res.claims_loaded} synthetic claims and ${res.service_records} service records.`);
      await refresh();
    } catch (e) {
      setError(e instanceof C05Error ? e.message : String(e));
    } finally {
      setBusy("");
    }
  }

  const focused = useMemo(() => {
    if (!selected || !focus) return null;
    const sig = [...selected.signals, ...selected.corroborating].find((s) => s.code === focus);
    return sig ? new Set(sig.claim_ids) : null;
  }, [selected, focus]);

  const flagsByClaim = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const s of selected?.signals ?? []) {
      for (const id of s.claim_ids) map.set(id, [...(map.get(id) ?? []), s.code]);
    }
    return map;
  }, [selected]);

  if (!allowed) {
    return (
      <p className="panel p-4 text-[15px]">
        Illness claims contain sensitive health reports and are visible to supervisors and admins only.
      </p>
    );
  }

  const closed = selected?.status.startsWith("CLOSED") ?? false;
  const rows = selected
    ? focused
      ? selected.claims.filter((c) => focused.has(c.claim_id))
      : selected.claims
    : [];

  return (
    <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
      <section aria-label="Incidents" className="flex min-w-0 flex-col gap-2">
        <div className="flex items-center justify-between gap-2">
          <h2 className="label">Incidents by kitchen-day</h2>
          {role === "ADMIN" ? (
            <Button type="button" size="sm" variant="outline" onClick={seed} disabled={busy !== ""}>
              {busy === "seed" ? "Loading…" : "Load demo scenario"}
            </Button>
          ) : null}
        </div>
        {incidents.length === 0 ? (
          <p className="panel p-4 meta">
            No illness claims for {kitchenId}.{" "}
            {role === "ADMIN" ? "Load the demo scenario to see how triage works." : ""}
          </p>
        ) : null}
        {incidents.map((i) => (
          <button
            key={i.incident_id}
            type="button"
            onClick={() => open(i.incident_id)}
            aria-current={selected?.incident_id === i.incident_id ? "true" : undefined}
            className={cn(
              "panel p-3 text-left transition-colors duration-150 hover:bg-[var(--sunken)]",
              selected?.incident_id === i.incident_id && "outline-2 outline-[var(--action)]",
            )}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-[13px]">{i.meal_date}</span>
              <HealthBadge priority={i.health_priority} />
            </div>
            <p className="mt-1.5 text-[14px]">
              {plural(i.stats.claims, "report")} · {i.stats.affected_reported} people affected ·{" "}
              {plural(i.stats.sought_medical, "medical visit")}
            </p>
            <div className="mt-2 flex items-center justify-between gap-2">
              <ScoreMeter score={i.integrity_score} level={i.integrity_level} />
              <span className="meta">{STATUS_TEXT[i.status]}</span>
            </div>
          </button>
        ))}
        {error ? <p className="text-[13px] text-[var(--defect)]">{error}</p> : null}
        <div aria-live="polite">{notice ? <p className="text-[13px] text-[var(--pass)]">{notice}</p> : null}</div>
      </section>

      {selected ? (
        <section aria-label="Incident detail" className="flex min-w-0 flex-col gap-4">
          <div className="panel p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="mono text-[var(--ink-3)]">{selected.incident_id}</p>
                <h2 className="mt-0.5 text-[20px] leading-[26px] font-semibold">
                  {selected.kitchen_id} · meals of {selected.meal_date}
                </h2>
                <p className="meta mt-1">
                  First report {fmt(selected.stats.first_submitted)} · last {fmt(selected.stats.last_submitted)}
                </p>
                <Link
                  href={`/supply?date=${selected.meal_date}`}
                  className="mt-2 inline-block text-[14px] font-medium text-[var(--action)] underline underline-offset-2"
                >
                  Trace this day&rsquo;s ingredients and suppliers →
                </Link>
              </div>
              <div className="flex max-w-[260px] flex-col items-end gap-1.5 text-right">
                <HealthBadge priority={selected.health_priority} />
                <p className="meta">{HEALTH_COPY[selected.health_priority]}</p>
                <Badge variant="outline">{STATUS_TEXT[selected.status]}</Badge>
              </div>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                ["Reports", selected.stats.claims],
                ["People affected", selected.stats.affected_reported],
                ["Portions served", selected.stats.portions_served],
                ["Medical / hospital", `${selected.stats.sought_medical} / ${selected.stats.hospitalized}`],
              ].map(([k, v]) => (
                <div key={k} className="well px-3 py-2">
                  <dt className="label">{k}</dt>
                  <dd className="font-mono text-[17px] tabular-nums">{v}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 rounded-[var(--r-control)] border border-[var(--defect)] px-3 py-2 text-[13px] leading-[18px]">
              <strong>Health first.</strong> Treat every report as a possible real illness. Integrity signals decide
              the order of verification work, never whether someone receives care.
            </p>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="panel p-4">
              <div className="flex items-center justify-between gap-2">
                <h3 className="label">What doesn’t add up</h3>
                <ScoreMeter score={selected.integrity_score} level={selected.integrity_level} />
              </div>
              <p className="meta mt-1">
                Conflicts between the reports and delivery records, or between reports. A reason to verify, not a
                verdict.
              </p>
              {selected.signals.length === 0 ? (
                <p className="mt-2 text-[14px] text-[var(--pass)]">
                  Nothing conflicts: the reports fit what was served. Treat as a likely real illness.
                </p>
              ) : (
                <ul className="mt-2 flex flex-col gap-1.5">
                  {selected.signals.map((s) => (
                    <SignalRow
                      key={s.code}
                      signal={s}
                      active={focus === s.code}
                      onToggle={() => setFocus(focus === s.code ? null : s.code)}
                    />
                  ))}
                </ul>
              )}
              {selected.corroborating.length ? (
                <>
                  <h3 className="label mt-4">What supports the reports</h3>
                  <ul className="mt-2 flex flex-col gap-1.5">
                    {selected.corroborating.map((s) => (
                      <SignalRow
                        key={s.code}
                        signal={s}
                        active={focus === s.code}
                        onToggle={() => setFocus(focus === s.code ? null : s.code)}
                      />
                    ))}
                  </ul>
                </>
              ) : null}
            </div>

            <div className="flex flex-col gap-4">
              <div className="rounded-[var(--r-panel)] border border-[var(--review)] bg-[var(--raised)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="label text-[var(--review)]">PATTERN SUMMARY — ADVISORY</span>
                  <Button type="button" size="sm" onClick={assess} disabled={busy !== ""}>
                    {busy === "assess" ? "Summarizing…" : selected.ai ? "Refresh summary" : "Summarize reports"}
                  </Button>
                </div>
                {selected.ai?.summary ? (
                  <>
                    <p className="mt-2 text-[13px] font-medium">
                      {selected.ai.pattern_assessment ? PATTERN_TEXT[selected.ai.pattern_assessment] : null}
                    </p>
                    <p className="mt-1 text-[14px] leading-[20px]">{selected.ai.summary}</p>
                    {selected.ai.observations?.length ? (
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-[13px] leading-[18px]">
                        {selected.ai.observations.map((o, n) => (
                          <li key={n}>
                            {o.text}{" "}
                            {o.claim_ids.length ? (
                              <span className="mono text-[var(--ink-3)]">[{o.claim_ids.slice(0, 3).join(", ")}
                                {o.claim_ids.length > 3 ? ` +${o.claim_ids.length - 3}` : ""}]</span>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    {selected.ai.verification_steps?.length ? (
                      <>
                        <p className="label mt-3">Suggested verification</p>
                        <ol className="mt-1 list-decimal space-y-0.5 pl-5 text-[13px] leading-[18px]">
                          {selected.ai.verification_steps.map((s, n) => (
                            <li key={n}>{s}</li>
                          ))}
                        </ol>
                      </>
                    ) : null}
                  </>
                ) : (
                  <p className="meta mt-2">
                    {selected.ai
                      ? "A summary is not available right now. Try again later; the conflicts and next steps still apply."
                      : "Reads the reports (phone numbers masked) and the conflicts, and explains the pattern in plain English. It cannot change the score or close the case."}
                  </p>
                )}
              </div>

              <div className="panel p-4">
                <h3 className="label">Required next steps</h3>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-[14px] leading-[20px]">
                  {selected.next_steps.map((s, n) => (
                    <li key={n}>{s}</li>
                  ))}
                </ol>
              </div>
            </div>
          </div>

          <div className="panel p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="label">
                Reports{" "}
                {focused && focus ? `· ${signalCopy(focus).title} (${rows.length})` : `(${selected.claims.length})`}
              </h3>
              {focused ? (
                <Button type="button" size="sm" variant="outline" onClick={() => setFocus(null)}>
                  Show all
                </Button>
              ) : null}
            </div>
            <ScrollArea className="mt-2 max-h-[420px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-[12px]">Claim</TableHead>
                    <TableHead className="text-[12px]">School</TableHead>
                    <TableHead className="text-[12px]">Affected</TableHead>
                    <TableHead className="text-[12px]">Onset</TableHead>
                    <TableHead className="text-[12px]">Medical care</TableHead>
                    <TableHead className="text-[12px]">Report</TableHead>
                    <TableHead className="text-[12px]">Conflicts</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((c) => (
                    <TableRow key={c.claim_id} className="align-top">
                      <TableCell className="mono whitespace-nowrap">{c.claim_id.slice(0, 12)}</TableCell>
                      <TableCell className="font-mono text-[12px]">{c.school_id}</TableCell>
                      <TableCell className="tabular-nums">{c.affected_count}</TableCell>
                      <TableCell className="text-[12px] whitespace-nowrap">{fmt(c.onset_at)}</TableCell>
                      <TableCell className="text-[12px]">
                        {c.hospitalized ? "Hospital" : c.sought_medical ? "Clinic" : "—"}
                      </TableCell>
                      <TableCell className="min-w-[220px] text-[12px] leading-[17px] whitespace-normal">
                        <span className="meta">
                          {c.reporter_type} · {c.channel} · {c.symptoms.join(", ")}
                        </span>
                        <br />
                        {c.description || <span className="meta">no description</span>}
                      </TableCell>
                      <TableCell className="text-[11px] whitespace-normal">
                        {(flagsByClaim.get(c.claim_id) ?? []).map((f) => (
                          <span
                            key={f}
                            title={signalCopy(f).title}
                            className="mr-1 mb-1 inline-block rounded-sm border border-[var(--review)] px-1 text-[var(--review)]"
                          >
                            {signalCopy(f).short}
                          </span>
                        ))}
                        {(flagsByClaim.get(c.claim_id) ?? []).length === 0 ? (
                          <span className="meta">none</span>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </div>

          <div className="panel p-4">
            <h3 className="label">Supervisor decision</h3>
            {closed ? (
              <p className="meta mt-2">This incident is closed. Closures are immutable.</p>
            ) : (
              <>
                <div className="mt-2 flex flex-col gap-1.5">
                  <Label htmlFor="decision-comment">Reason (required, recorded in the audit trail)</Label>
                  <Textarea
                    id="decision-comment"
                    rows={3}
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="What was checked and why this decision follows."
                  />
                </div>
                {selected.health_priority !== "ROUTINE" ? (
                  <label className="mt-2 flex items-start gap-2 text-[13px]">
                    <input
                      type="checkbox"
                      checked={followup}
                      onChange={(e) => setFollowup(e.target.checked)}
                      className="mt-0.5 size-4"
                    />
                    Medical follow-up for every reported case is confirmed (required before closing as
                    unsubstantiated).
                  </label>
                ) : null}
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {DECISIONS.map((d) => (
                    <div key={d.status} className="flex flex-col gap-1">
                      <Button
                        type="button"
                        variant={d.status === "ESCALATED_HEALTH" ? "default" : "outline"}
                        disabled={busy !== "" || (d.adminOnly && role !== "ADMIN")}
                        onClick={() => decide(d.status)}
                        className="h-11 w-full"
                      >
                        {d.label}
                      </Button>
                      <p className="meta">
                        {STATUS_COPY[d.status].explain}
                        {d.adminOnly ? " Admin only." : ""}
                      </p>
                    </div>
                  ))}
                </div>
                {role !== "ADMIN" ? <p className="meta mt-2">Closing an incident requires the ADMIN role.</p> : null}
              </>
            )}
            {selected.decisions.length ? (
              <ul className="mt-3 space-y-1">
                {selected.decisions.map((d, n) => (
                  <li key={n} className="meta">
                    {fmt(d.at)} · {d.actor} · {STATUS_TEXT[d.status]} — {d.comment}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </section>
      ) : (
        <p className="meta self-start">Select an incident to see its signals and the reports behind them.</p>
      )}
    </div>
  );
}
