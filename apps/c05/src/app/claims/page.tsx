"use client";

import { useEffect, useState } from "react";
import { c05 } from "@/lib/c05-client";
import type { ClaimTrace, PublicClaim } from "@/lib/c05-types";
import { useSession } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CopyId } from "@/components/copy-id";

const SYMPTOMS = [
  "nausea", "vomiting", "diarrhea", "fever", "headache", "abdominal_pain", "dizziness",
] as const;

const EMPTY = { reporter_name: "", reporter_contact: "", meal_date: "", onset_hours: "6" };

export default function ClaimsPage() {
  const { role, kitchenId } = useSession();
  const [claims, setClaims] = useState<PublicClaim[]>([]);
  const [trace, setTrace] = useState<ClaimTrace | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [symptoms, setSymptoms] = useState<Array<"nausea" | "vomiting" | "diarrhea" | "fever" | "headache" | "abdominal_pain" | "dizziness">>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    c05
      .listClaims(role, kitchenId)
      .then((result) => {
        if (active) setClaims(result.claims);
      })
      .catch((e: unknown) => {
        if (active) setMessage(e instanceof Error ? e.message : String(e));
      });
    return () => {
      active = false;
    };
  }, [role, kitchenId]);

  function toggle(symptom: "nausea" | "vomiting" | "diarrhea" | "fever" | "headache" | "abdominal_pain" | "dizziness") {
    setSymptoms((prev) =>
      prev.includes(symptom) ? prev.filter((s) => s !== symptom) : [...prev, symptom],
    );
  }

  async function submit() {
    setBusy(true);
    setMessage("");
    try {
      const created = await c05.submitClaim({
        kitchen_id: kitchenId,
        school_id: "SCHOOL-DEMO",
        meal_date: form.meal_date,
        reporter_type: "parent",
        contact: form.reporter_contact,
        affected_count: 1,
        symptoms,
        onset_at: new Date().toISOString(),
        sought_medical: false,
        hospitalized: false,
        description: form.reporter_name || "Reported via C05",
      });
      setMessage(
        `Report received. Reference ${created.claim_id}. Contact stored as ${(created as { contact_masked?: string | null }).contact_masked ?? "withheld"} — never in cleartext.`,
      );
      setForm(EMPTY);
      setSymptoms([]);
      const refreshed = await c05.listClaims(role, kitchenId);
      setClaims(refreshed.claims);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 pb-24">
      <header>
        <p className="label text-[var(--brand)]">Illness reports</p>
        <h1 className="mt-1 text-[28px] leading-[34px] font-semibold">Care first, data second</h1>
        <p className="meta mt-1">
          A data conflict never lowers the medical priority of a report. Phone numbers are stored as a
          one-way blind index and shown to staff only as the last four digits.
        </p>
      </header>

      <section className="panel p-4">
        <h2 className="label">Report an illness</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="reporter_name">Your name (optional)</Label>
            <Input
              id="reporter_name"
              value={form.reporter_name}
              onChange={(e) => setForm({ ...form, reporter_name: e.target.value })}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="reporter_contact">Phone number</Label>
            <Input
              id="reporter_contact"
              type="tel"
              value={form.reporter_contact}
              onChange={(e) => setForm({ ...form, reporter_contact: e.target.value })}
              placeholder="+62 812-3456-7890"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="meal_date">Meal date</Label>
            <Input
              id="meal_date"
              type="date"
              value={form.meal_date}
              onChange={(e) => setForm({ ...form, meal_date: e.target.value })}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="onset_hours">Onset, hours after the meal (1–168)</Label>
            <Input
              id="onset_hours"
              type="number"
              min={1}
              max={168}
              value={form.onset_hours}
              onChange={(e) => setForm({ ...form, onset_hours: e.target.value })}
            />
          </div>
        </div>
        <div className="mt-3">
          <Label>Symptoms</Label>
          <div className="mt-2 flex flex-wrap gap-2">
            {SYMPTOMS.map((s) => (
              <Button
                key={s}
                type="button"
                size="sm"
                variant={symptoms.includes(s) ? "default" : "outline"}
                aria-pressed={symptoms.includes(s)}
                onClick={() => toggle(s)}
              >
                {s.replace("_", " ")}
              </Button>
            ))}
          </div>
        </div>
        {message ? <p className="mt-3 text-sm text-[var(--ink-2)]">{message}</p> : null}
        <Button
          type="button"
          className="mt-3 h-12 w-full"
          onClick={submit}
          disabled={busy || symptoms.length === 0 || !form.reporter_contact || !form.meal_date}
        >
          {busy ? "Submitting…" : "Submit report"}
        </Button>
      </section>

      <section className="panel p-4">
        <h2 className="label">Reports in scope · {claims.length}</h2>
        {claims.length === 0 ? (
          <p className="meta mt-3">No reports recorded for this kitchen yet.</p>
        ) : (
          <ul className="mt-3 grid gap-2">
            {claims.map((claim) => (
              <li key={claim.claim_id} className="well p-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-sm">
                    <CopyId value={claim.claim_id} label="Claim" />
                  </p>
                  <span className="text-sm text-[var(--review)]">{claim.status}</span>
                </div>
                <p className="mt-1 text-sm">
                  {claim.meal_date} · {claim.symptoms.join(", ")}
                </p>
                <p className="meta mt-1">Contact {claim.contact_masked ?? "withheld"}</p>
                {claim.integrity && claim.integrity.count > 0 ? (
                  <p className="mt-1 text-sm text-[var(--defect)]">
                    {claim.integrity.count} data conflict{claim.integrity.count === 1 ? "" : "s"} —
                    medical priority remains {claim.integrity.medical_priority}
                  </p>
                ) : null}
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="mt-2"
                  onClick={async () => {
                    try {
                      setTrace(await c05.claimTrace(claim.claim_id, role));
                    } catch (e) {
                      setMessage(e instanceof Error ? e.message : String(e));
                    }
                  }}
                >
                  Trace to supplier
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {trace ? (
        <section className="panel p-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="label">Trace result</h2>
            <span className="text-sm text-[var(--defect)]">{trace.medical_priority}</span>
          </div>
          <p className="meta mt-1">{trace.medical_priority_note}</p>
          <p className="mt-3 text-sm">
            {trace.finding_count} data conflict{trace.finding_count === 1 ? "" : "s"} on{" "}
            {trace.meal_date}
          </p>
          {trace.findings.length > 0 ? (
            <ul className="mt-2 grid gap-2">
              {trace.findings.map((f) => (
                <li key={f.code} className="well p-2">
                  <p className="text-sm font-medium">{f.code}</p>
                  <p className="meta">{f.detail}</p>
                  {f.compared.length > 0 ? (
                    <p className="mono mt-1 text-xs text-[var(--ink-3)]">
                      compared: {f.compared.join(", ")}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
          {trace.related_lots.length > 0 ? (
            <div className="mt-3">
              <h3 className="label">Supplier chain</h3>
              <ul className="mt-1 space-y-1">
                {trace.related_lots.map((lot) => (
                  <li key={lot.lot_id} className="text-sm">
                    {lot.ingredient} · {lot.supplier} · {lot.origin}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}